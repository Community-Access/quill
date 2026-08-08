"""SFTP transport (issue #154).

Built on top of :mod:`paramiko`. The transport is intentionally *password-only*
in v1.0; users with key material (.ppk, ssh.com key, etc.) are pointed at
File > SSH (issue #139) which is the dedicated editing path with a richer
key-management story.

The boundary is documented in :mod:`quill.core.remote_sites`. In practice:

* File > SSH (issue #139) → :mod:`quill.core.ssh.client` with the
  ``SftpFileService`` + ``trust_first_use`` policy.
* File > Open from Remote (issue #154) → :class:`SftpTransport` here, with a
  DPAPI-stored password and the same ``paramiko.RejectPolicy`` host-key
  behaviour.
"""

from __future__ import annotations

import io
import time
from typing import Any

from quill.core.remote_sites import RemoteSite
from quill.io.remote_transport import (
    DownloadResult,
    ProgressCallback,
    RemoteAuthError,
    RemoteEntry,
    RemoteNotFoundError,
    RemoteTransport,
    RemoteTransportError,
    chunked_copy,
    merge_headers,
)

_MAX_BANNER_BYTES = 32 * 1024


class SftpDependencyError(RemoteTransportError):
    """Raised when :mod:`paramiko` is not importable."""


def _import_paramiko() -> Any:
    try:
        import paramiko  # type: ignore[import-not-found, import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised in CI via stub
        raise SftpDependencyError(
            "SFTP support requires the 'paramiko' package. Install QUILL with the "
            "sftp extra to enable it."
        ) from exc
    return paramiko


class SftpTransport(RemoteTransport):
    """Password-authenticated SFTP transport."""

    def __init__(
        self,
        site: RemoteSite,
        *,
        password: str,
        timeout: float = 30.0,
    ) -> None:
        self._site = site
        self._password = password
        self._timeout = timeout
        self._client: Any = None
        self._sftp: Any = None

    # --- lifecycle -----------------------------------------------------------

    def _connect(self) -> tuple[Any, Any]:
        if self._client is not None and self._sftp is not None:
            return self._client, self._sftp
        paramiko = _import_paramiko()
        from quill.core.ssh.client import apply_pinned_host_keys

        client = paramiko.SSHClient()
        # Same pinning story as File > SSH: known keys (user known_hosts +
        # QUILL's managed pin file) are always loaded, so RejectPolicy can
        # actually accept known hosts, and with trust_first_use the accepted
        # first key is PERSISTED — a different key on a later connect raises
        # BadHostKeyException instead of being silently trusted every time.
        apply_pinned_host_keys(client, writable=self._site.trust_first_use)
        if self._site.trust_first_use:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                hostname=self._site.host,
                port=self._site.port or 22,
                username=self._site.username or "",
                password=self._password or "",
                timeout=self._timeout,
                allow_agent=False,
                look_for_keys=False,
            )
        except paramiko.BadHostKeyException as exc:
            raise RemoteTransportError(
                f"The server key for {self._site.host} has CHANGED since it was "
                "first trusted. This can mean a different machine is answering "
                "(possibly an attacker in the path). If the change is expected, "
                "remove the host's line from the pinned known_hosts file under "
                "the QUILL data directory (ssh/known_hosts) and connect again."
            ) from exc
        except paramiko.AuthenticationException as exc:
            raise RemoteAuthError(f"SFTP login failed for {self._site.username!r}") from exc
        except paramiko.SSHException as exc:
            raise RemoteTransportError(f"SFTP connection error: {exc}") from exc
        except OSError as exc:
            raise RemoteTransportError(f"Could not reach {self._site.host}: {exc}") from exc
        sftp = client.open_sftp()
        self._client = client
        self._sftp = sftp
        return client, sftp

    def close(self) -> None:
        sftp = self._sftp
        client = self._client
        self._sftp = None
        self._client = None
        if sftp is not None:
            try:
                sftp.close()
            except OSError:
                pass
        if client is not None:
            try:
                client.close()
            except OSError:
                pass

    # --- public API ----------------------------------------------------------

    def list_dir(self, path: str) -> list[RemoteEntry]:
        _, sftp = self._connect()
        target = path or self._site.root_dir or "/"
        try:
            raw_entries = sftp.listdir_attr(target)
        except OSError as exc:
            message = str(exc)
            if "No such file" in message or "not found" in message.lower():
                raise RemoteNotFoundError(message) from exc
            raise RemoteTransportError(message) from exc
        entries: list[RemoteEntry] = []
        for attr in raw_entries:
            name = getattr(attr, "filename", "") or ""
            if not name or name in {".", ".."}:
                continue
            stat = getattr(attr, "st_mode", None)
            try:
                is_dir = bool(stat) and int(str(stat)) & 0o170000 == 0o040000
            except (TypeError, ValueError):
                is_dir = False
            try:
                size = int(getattr(attr, "st_size", 0) or 0)
            except (TypeError, ValueError):
                size = 0
            try:
                mtime = float(getattr(attr, "st_mtime", 0) or 0)
            except (TypeError, ValueError):
                mtime = 0.0
            entries.append(RemoteEntry(name=name, is_dir=is_dir, size=size, modified=mtime))
        entries.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
        return entries

    def download(
        self,
        remote_path: str,
        local_path: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> DownloadResult:
        _, sftp = self._connect()
        start = time.monotonic()
        with sftp.open(remote_path, "rb") as handle:
            handle.prefetch()
            source = io.BufferedReader(handle, buffer_size=64 * 1024)  # type: ignore[arg-type]
            with open(local_path, "wb") as dest:
                written = chunked_copy(source, dest, total=None, progress=progress)
        return DownloadResult(
            path=local_path,
            size=written,
            mime_type="",
            elapsed_ms=int((time.monotonic() - start) * 1000),
            headers=merge_headers([]),
        )

    def upload(
        self,
        local_path: str,
        remote_path: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> DownloadResult:
        _, sftp = self._connect()
        start = time.monotonic()
        total = _file_size(local_path)
        with open(local_path, "rb") as source, sftp.open(remote_path, "wb") as handle:
            chunked_copy(source, handle, total=total, progress=progress)
        return DownloadResult(
            path=local_path,
            size=total,
            mime_type="",
            elapsed_ms=int((time.monotonic() - start) * 1000),
            headers=merge_headers([]),
        )


def _file_size(path: str) -> int:
    import os

    return int(os.path.getsize(path))
