"""SFTP file service for edit-over-SSH (issue #139).

:class:`SftpFileService` wraps an SFTP handle (paramiko's ``SFTPClient`` or any
object exposing the same ``listdir_attr``/``open``/``stat``/``rename`` methods)
so the browse + read + write-with-backup logic can be unit-tested with a fake,
no network or ``paramiko`` required.

:func:`connect` builds a real connection via ``paramiko`` and raises a plain,
actionable message when the optional dependency is not installed.
"""

from __future__ import annotations

import stat as stat_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.ssh.sites import AUTH_AGENT, AUTH_KEY, DEFAULT_PORT
from quill.core.ssh.transfer import backup_name

_INSTALL_HINT = (
    "Editing files over SSH needs the 'paramiko' package, which is not installed. "
    "Install it with: pip install paramiko"
)


class SshDependencyError(CodedError):
    """Raised when an SSH action is requested but ``paramiko`` is unavailable."""

    code = "QUILL-SSH-CLIENT-NO-PARAMIKO"


@dataclass(slots=True)
class RemoteEntry:
    """One entry in a remote directory listing."""

    name: str
    is_dir: bool
    size: int
    mtime: float


class SftpFileService:
    """Browse and transfer files over an established SFTP handle."""

    def __init__(self, sftp: object) -> None:
        self._sftp = sftp

    def list_dir(self, path: str) -> list[RemoteEntry]:
        """List ``path``, directories first then files, each alphabetical."""
        entries: list[RemoteEntry] = []
        for attr in self._sftp.listdir_attr(path):  # type: ignore[attr-defined]
            mode = int(getattr(attr, "st_mode", 0) or 0)
            entries.append(
                RemoteEntry(
                    name=attr.filename,
                    is_dir=stat_module.S_ISDIR(mode),
                    size=int(getattr(attr, "st_size", 0) or 0),
                    mtime=float(getattr(attr, "st_mtime", 0) or 0),
                )
            )
        return sorted(entries, key=lambda entry: (not entry.is_dir, entry.name.lower()))

    def read_file(self, path: str) -> bytes:
        with self._sftp.open(path, "rb") as handle:  # type: ignore[attr-defined]
            return bytes(handle.read())

    def write_file(self, path: str, data: bytes, *, make_backup: bool = True) -> str | None:
        """Write ``data`` to ``path``, backing up any existing file as ``path~``.

        Returns the backup path when one was made, else ``None``. The backup is
        created by renaming the original (the conventional editor behaviour), so
        ``test.txt`` becomes ``test.txt~`` before the new content is written.
        """
        backup: str | None = None
        if make_backup and self._exists(path):
            backup = backup_name(path)
            self._replace(path, backup)
        with self._sftp.open(path, "wb") as handle:  # type: ignore[attr-defined]
            handle.write(data)
        return backup

    def _exists(self, path: str) -> bool:
        try:
            self._sftp.stat(path)  # type: ignore[attr-defined]
        except OSError:
            return False
        return True

    def _replace(self, src: str, dst: str) -> None:
        # POSIX rename overwrites an existing destination atomically; fall back to
        # remove-then-rename for servers without the posix-rename extension.
        posix_rename = getattr(self._sftp, "posix_rename", None)
        if callable(posix_rename):
            posix_rename(src, dst)
            return
        try:
            self._sftp.remove(dst)  # type: ignore[attr-defined]
        except OSError:
            pass
        self._sftp.rename(src, dst)  # type: ignore[attr-defined]


class SftpConnection:
    """An open SSH connection and its SFTP channel; a file-service factory."""

    def __init__(self, client: object, sftp: object) -> None:
        self._client = client
        self.service = SftpFileService(sftp)

    def close(self) -> None:
        for target in (getattr(self, "_client", None),):
            try:
                if target is not None:
                    target.close()
            except Exception:  # noqa: BLE001 - closing must never raise
                pass

    def __enter__(self) -> SftpConnection:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _import_paramiko() -> Any:
    try:
        import paramiko  # type: ignore[import-untyped]
    except Exception as exc:  # noqa: BLE001
        raise SshDependencyError(_INSTALL_HINT) from exc
    return paramiko


def _managed_known_hosts_path() -> Path:
    """The QUILL-owned, writable ``known_hosts`` used to pin SSH host keys."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "ssh" / "known_hosts"


def _load_pinned_host_keys(client: Any, *, writable: bool) -> None:
    """Populate ``client`` with every host key QUILL knows about.

    Always merges the user's ``~/.ssh/known_hosts`` (read-only). When
    ``writable`` is true, the QUILL-managed ``known_hosts`` is loaded via
    ``load_host_keys`` so that paramiko's ``AutoAddPolicy`` persists a
    newly-accepted key back to it -- turning "trust first use" into real
    trust-on-first-use pinning: the *first* key seen for a host is saved,
    and a *different* key on a later connect raises ``BadHostKeyException``
    instead of being silently accepted.
    """
    # User's OpenSSH known_hosts, merged read-only (never our save target).
    user_known_hosts = Path.home() / ".ssh" / "known_hosts"
    if user_known_hosts.is_file():
        try:
            client.get_host_keys().load(str(user_known_hosts))
        except Exception:  # noqa: BLE001 - a malformed user file must not block connect
            pass
    if not writable:
        return
    managed = _managed_known_hosts_path()
    try:
        managed.parent.mkdir(parents=True, exist_ok=True)
        if not managed.exists():
            managed.touch()
        # Sets the save target so AutoAddPolicy writes accepted keys back.
        client.load_host_keys(str(managed))
    except Exception:  # noqa: BLE001 - fall back to in-memory-only if the store is unusable
        pass


def connect(
    host: str,
    *,
    port: int = DEFAULT_PORT,
    username: str = "",
    password: str | None = None,
    auth: str = "password",
    key_path: str = "",
    key_passphrase: str | None = None,
    timeout: float = 15.0,
    trust_first_use: bool | None = None,
) -> SftpConnection:
    """Open an SSH/SFTP connection. Requires the optional ``paramiko`` package.

    Host-key policy (SEC-9): by default an unknown host key causes the
    connection to be rejected. Set ``trust_first_use=True`` to opt into
    trust-on-first-use pinning -- the first key seen for a host is saved to
    a QUILL-managed ``known_hosts`` and a *changed* key on a later connect
    is rejected (``BadHostKeyException``), never silently accepted. Callers
    that already have the user's :class:`~quill.core.settings.Settings`
    should pass ``trust_first_use=settings.ssh_trust_first_use`` explicitly.
    """
    paramiko = _import_paramiko()
    if trust_first_use is None:
        try:
            from quill.core.settings import load_settings as _load_settings

            trust_first_use = _load_settings().ssh_trust_first_use
        except Exception:  # noqa: BLE001 - never let a settings read block connect
            trust_first_use = False
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    # Merge user + QUILL-managed known_hosts so a previously-pinned key is
    # verified (and a mismatch rejected) regardless of the policy below.
    _load_pinned_host_keys(client, writable=bool(trust_first_use))
    if trust_first_use:
        # Trust-on-first-use: an *unknown* host is accepted and its key is
        # persisted to the managed known_hosts (via AutoAddPolicy + the
        # save target set in _load_pinned_host_keys). A subsequent connect
        # presenting a *different* key raises BadHostKeyException before
        # this policy is ever consulted -- so this is genuine pinning, not
        # blanket acceptance.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        # Default: reject unknown host keys. ``paramiko.RejectPolicy``
        # is the strongest available; it raises ``SSHException`` on any
        # key that is not already known, which is what we want for a
        # first connect.
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

    pkey = None
    if auth == AUTH_KEY and key_path:
        from quill.core.ssh.keys import load_private_key

        pkey = load_private_key(key_path, key_passphrase)

    client.connect(
        hostname=host,
        port=port,
        username=username or None,
        password=password if auth == "password" else None,
        pkey=pkey,
        timeout=timeout,
        allow_agent=(auth == AUTH_AGENT),
        look_for_keys=(auth in (AUTH_AGENT, AUTH_KEY)),
    )
    return SftpConnection(client, client.open_sftp())
