"""Saved remote-site profiles for the File > Open from Remote menu (issue #154).

This is the cross-protocol site manager. The existing
:mod:`quill.core.ssh.sites` covers the *edit-over-SSH* path (File > SSH) with
its own profile store (``ssh_sites.json``); the two are deliberately
separate:

========================  ==============================  ===================================
Property                  File > SSH (#139)               File > Open from Remote (#154-#157)
========================  ==============================  ===================================
Use case                  Linux admin / config editing    Convenience file retrieval (FTP,
                                                        SFTP, WebDAV, S3) for writers
Authentication            Password (memory), agent,       Password (DPAPI-persisted). Key/agent
                          .ppk, SecureCRT, ssh.com key    users go through File > SSH instead
Host-key policy           Per-site, ``paramiko.Reject``   FTP: n/a. SFTP: ``RejectPolicy`` by
                          default, ``trust_first_use``    default with ``trust_first_use`` per
                          per setting                     setting
Credential storage        Memory only; nothing on disk    DPAPI (Windows) / macOS Keychain
                                                        fallback. Never plaintext.
Storage file              ``ssh_sites.json``              ``remote_sites.json``
UI entry                  File > SSH submenu              File > Open from Remote...
========================  ==============================  ===================================

A :class:`RemoteSite` carries protocol-agnostic fields (``id``, ``name``,
``host``, ``port``, ``username``, ``root_dir``, ``trust_first_use``) plus an
``extra: dict[str, str]`` field that holds protocol-specific metadata (S3
bucket, WebDAV base path, S3 endpoint URL, ...). Keeping the extras as a flat
string-string dict means a new transport (issue #156 WebDAV, #157 S3) only
adds a key to ``extra``; the shared dataclass and the shared store do not
change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

# Protocol identifiers. ``extra`` keys are conventionally prefixed with the
# protocol name (e.g. ``s3_bucket``, ``webdav_base``) so the dialog UI can
# render only the fields a given protocol actually needs.
PROTOCOL_FTP = "ftp"
PROTOCOL_SFTP = "sftp"
PROTOCOL_WEBDAV = "webdav"
PROTOCOL_S3 = "s3"
_VALID_PROTOCOLS = frozenset({PROTOCOL_FTP, PROTOCOL_SFTP, PROTOCOL_WEBDAV, PROTOCOL_S3})

DEFAULT_PORTS: dict[str, int] = {
    PROTOCOL_FTP: 21,
    PROTOCOL_SFTP: 22,
    PROTOCOL_WEBDAV: 443,
    PROTOCOL_S3: 443,
}

_SITES_FILENAME = "remote_sites.json"
_SECRET_TARGET_PREFIX = "QUILL:remote-site:"


def default_port(protocol: str) -> int:
    """Return the conventional default port for a protocol (21/22/443/443)."""

    return DEFAULT_PORTS.get(protocol, 0)


@dataclass(slots=True)
class RemoteSite:
    """A saved remote-site profile.

    The ``password`` field is *not* persisted to disk. It is only used at the
    prompt boundary (``_prompt_for_password``) and is handed to a transport
    via a sidecar :class:`RemoteSiteSecrets` lookup. Persisted passwords live
    in DPAPI / macOS Keychain (see :func:`save_password`).
    """

    id: str
    name: str
    protocol: str
    host: str = ""
    port: int = 0
    username: str = ""
    root_dir: str = ""
    trust_first_use: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    def normalised(self) -> RemoteSite:
        """Return a copy with the protocol/port/host/id normalised."""

        protocol = self.protocol.strip().lower() if self.protocol else PROTOCOL_FTP
        if protocol not in _VALID_PROTOCOLS:
            protocol = PROTOCOL_FTP
        port = self.port if isinstance(self.port, int) and self.port > 0 else default_port(protocol)
        site_id = (self.id or self.name).strip() or protocol
        # ``extra`` is a string-string dict; coerce non-string values to keep
        # JSON round-trips lossless. Booleans, ints, and bytes are common in
        # the editor settings layer; here we normalise to strings so the JSON
        # snapshot is portable across the macOS/Windows edit-in-place flow.
        cleaned_extra: dict[str, str] = {}
        for raw_key, raw_value in (self.extra or {}).items():
            key = str(raw_key).strip()
            if not key:
                continue
            cleaned_extra[key] = str(raw_value)
        return RemoteSite(
            id=site_id,
            name=self.name.strip() or site_id,
            protocol=protocol,
            host=self.host.strip(),
            port=port,
            username=self.username.strip(),
            root_dir=self.root_dir.strip(),
            trust_first_use=bool(self.trust_first_use),
            extra=cleaned_extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation (used by :func:`save_sites`)."""

        site = self.normalised()
        return {
            "id": site.id,
            "name": site.name,
            "protocol": site.protocol,
            "host": site.host,
            "port": site.port,
            "username": site.username,
            "root_dir": site.root_dir,
            "trust_first_use": site.trust_first_use,
            "extra": dict(site.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RemoteSite:
        raw_extra = data.get("extra", {})
        if not isinstance(raw_extra, dict):
            raw_extra = {}
        return cls(
            id=str(data.get("id", "") or "").strip(),
            name=str(data.get("name", "") or "").strip(),
            protocol=str(data.get("protocol", PROTOCOL_FTP) or PROTOCOL_FTP),
            host=str(data.get("host", "") or "").strip(),
            port=int(data.get("port", 0) or 0),
            username=str(data.get("username", "") or "").strip(),
            root_dir=str(data.get("root_dir", "") or "").strip(),
            trust_first_use=bool(data.get("trust_first_use", False)),
            extra={str(key): str(value) for key, value in raw_extra.items()},
        )


def _sites_path() -> Path:
    return Path(app_data_dir()) / _SITES_FILENAME


def load_sites() -> list[RemoteSite]:
    """Return saved sites sorted by friendly name (case-insensitive)."""

    raw = read_json(_sites_path(), [])
    # Accept the versioned envelope {"schema_version", "sites": [...]} and the
    # legacy bare list, so old files keep loading.
    items = raw.get("sites", []) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    sites: list[RemoteSite] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        site = RemoteSite.from_dict(item).normalised()
        if site.id:
            sites.append(site)
    return sorted(sites, key=lambda site: site.name.lower())


def save_sites(sites: list[RemoteSite]) -> None:
    """Persist ``sites`` to the JSON store under the app-data directory."""

    payload = {"schema_version": 1, "sites": [site.to_dict() for site in sites]}
    base = app_data_dir()
    write_json_atomic(_sites_path(), payload, base=base)


def upsert_site(site: RemoteSite) -> list[RemoteSite]:
    """Add ``site`` or replace an existing one with the same id. Returns the new list."""

    normalised = site.normalised()
    if not normalised.id:
        raise ValueError("RemoteSite.id is required")
    others = [existing for existing in load_sites() if existing.id != normalised.id]
    others.append(normalised)
    save_sites(others)
    return load_sites()


def delete_site(site_id: str) -> list[RemoteSite]:
    """Remove the site with ``site_id`` and return the surviving list."""

    target = site_id.strip()
    remaining = [site for site in load_sites() if site.id != target]
    save_sites(remaining)
    # Best-effort: drop the stored password too. Failures here are not fatal
    # because the user can always re-enter a password.
    try:
        delete_password(target)
    except Exception:  # noqa: BLE001 - never let cleanup fail a delete
        pass
    return remaining


# --- Password store ---------------------------------------------------------
#
# The convenience remote site is a *convenience* path: users expect their
# passwords to persist across sessions. We store them DPAPI-encrypted on
# Windows, with a macOS Keychain fallback. The fallback uses the same
# protect_secret / unprotect_secret facade so the call sites stay identical.


def _target_name(site_id: str) -> str:
    return f"{_SECRET_TARGET_PREFIX}{site_id.strip()}"


def save_password(site_id: str, password: str) -> None:
    """Persist ``password`` for ``site_id`` using DPAPI / macOS Keychain."""

    if not site_id or not password:
        return
    # Windows: Windows Credential Manager is the primary store (matches the
    # assistant API key path). DPAPI is the portable fallback. macOS uses the
    # Keychain facade.
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            save_generic_credential,
        )

        if credential_manager_available():
            save_generic_credential(_target_name(site_id), password, user_name="quill-remote-site")
            return
    except Exception:  # noqa: BLE001 - any platform failure falls through
        pass
    try:
        from quill.core.storage import write_json_atomic
        from quill.platform.windows.dpapi import protect_secret  # type: ignore[import]

        encoded = protect_secret(password)
        path = _sites_path().parent / "remote-site-secrets.json"
        existing = read_json(path, default={}) or {}
        if not isinstance(existing, dict):
            existing = {}
        existing[site_id] = encoded
        write_json_atomic(path, existing, base=app_data_dir())
    except Exception:  # noqa: BLE001
        from quill.platform.macos.keychain import protect_secret

        encoded = protect_secret(password)
        path = _sites_path().parent / "remote-site-secrets.json"
        existing = read_json(path, default={}) or {}
        if not isinstance(existing, dict):
            existing = {}
        existing[site_id] = encoded
        write_json_atomic(path, existing, base=app_data_dir())


def load_password(site_id: str) -> str:
    """Return the stored password for ``site_id`` (or ``""`` if none)."""

    target = site_id.strip()
    if not target:
        return ""
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            load_generic_credential,
        )

        if credential_manager_available():
            credential = load_generic_credential(_target_name(site_id))
            if credential is not None:
                return credential.secret
            return ""
    except Exception:  # noqa: BLE001
        pass
    try:
        from quill.core.storage import read_json

        path = _sites_path().parent / "remote-site-secrets.json"
        data = read_json(path, default={})
        if not isinstance(data, dict):
            return ""
        encoded = str(data.get(target, "") or "")
        if not encoded:
            return ""
    except Exception:  # noqa: BLE001
        return ""
    try:
        from quill.platform.windows.dpapi import unprotect_secret  # type: ignore[import]

        return unprotect_secret(encoded)
    except Exception:  # noqa: BLE001
        try:
            from quill.platform.macos.keychain import unprotect_secret

            return unprotect_secret(encoded)
        except Exception:  # noqa: BLE001
            return ""


def delete_password(site_id: str) -> bool:
    """Forget the stored password for ``site_id``. Returns True if one was removed."""

    target = site_id.strip()
    if not target:
        return False
    removed = False
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            delete_generic_credential,
        )

        if credential_manager_available():
            removed = bool(delete_generic_credential(_target_name(target)))
    except Exception:  # noqa: BLE001
        pass
    try:
        from quill.core.storage import read_json, write_json_atomic

        path = _sites_path().parent / "remote-site-secrets.json"
        data = read_json(path, default={})
        if isinstance(data, dict) and target in data:
            del data[target]
            write_json_atomic(path, data, base=app_data_dir())
            removed = True
    except Exception:  # noqa: BLE001
        pass
    return removed
