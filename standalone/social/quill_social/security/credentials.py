"""Credential storage by reference, plus secret redaction (PRD 31.1).

The database must only ever hold a *reference* to a credential (a service +
account + opaque handle), never the raw token. The real secret lives in the OS
credential manager (Windows Credential Manager, macOS Keychain) and is resolved
only at the boundary, through a live :class:`CredentialStore`. This is the
"database stores references, not raw tokens" rule from PRD 31.1.

``InMemoryCredentialStore`` is the deterministic default so the app and tests
run without any OS dependency: it keeps secrets in process memory and hands back
references. ``WindowsCredentialManagerStore`` is the documented boundary; it
imports cleanly and reports ``available()`` based on whether the ``keyring``
dependency is present, raising a clear error rather than requiring it.

``redact`` masks secret-looking substrings so tokens never reach a log or a
diagnostic bundle.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

REDACTED = "[REDACTED]"


@dataclass
class CredentialRef:
    """A durable, non-secret pointer to a credential (PRD 31.1).

    This is the ONLY credential artifact that may be persisted in the database.
    It contains no token material -- just what is needed to look the secret up in
    the OS credential store.
    """

    service: str = ""
    account: str = ""
    handle: str = ""  # opaque store key; not a secret

    def to_dict(self) -> dict:
        return {"service": self.service, "account": self.account, "handle": self.handle}

    @classmethod
    def from_dict(cls, d: dict) -> CredentialRef:
        return cls(
            service=d.get("service", ""),
            account=d.get("account", ""),
            handle=d.get("handle", ""),
        )


def _handle_for(service: str, account: str) -> str:
    """A stable, non-secret store key for a (service, account) pair."""
    return f"quill_social:{service}:{account}"


class CredentialStore(ABC):
    """Interface for storing secrets by reference (PRD 31.1).

    Implementations persist the secret in a secure backend and return a
    :class:`CredentialRef`. Callers persist only the reference. ``resolve`` is
    the boundary that returns real secret material and must never be used to put
    a token into the database.
    """

    @abstractmethod
    def store(self, service: str, account: str, secret: str) -> CredentialRef:
        """Store ``secret`` securely and return its reference (no token)."""

    @abstractmethod
    def reference(self, service: str, account: str) -> CredentialRef | None:
        """Return the reference for a stored credential, or ``None``."""

    @abstractmethod
    def resolve(self, ref: CredentialRef) -> str | None:
        """Boundary: return the real secret for a reference (never persisted)."""

    @abstractmethod
    def delete(self, service: str, account: str) -> None:
        """Remove the stored secret and its reference (supports revocation)."""

    @classmethod
    def available(cls) -> bool:
        """Whether this backend's dependency is installed and usable."""
        return True


class InMemoryCredentialStore(CredentialStore):
    """Deterministic default: secrets in process memory, references handed out.

    Nothing here is written to the database. The store maps opaque handles to
    secrets; the database only ever sees the :class:`CredentialRef`.
    """

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def store(self, service: str, account: str, secret: str) -> CredentialRef:
        handle = _handle_for(service, account)
        self._secrets[handle] = secret
        return CredentialRef(service=service, account=account, handle=handle)

    def reference(self, service: str, account: str) -> CredentialRef | None:
        handle = _handle_for(service, account)
        if handle not in self._secrets:
            return None
        return CredentialRef(service=service, account=account, handle=handle)

    def resolve(self, ref: CredentialRef) -> str | None:
        return self._secrets.get(ref.handle)

    def delete(self, service: str, account: str) -> None:
        self._secrets.pop(_handle_for(service, account), None)


class WindowsCredentialManagerStore(CredentialStore):
    """Boundary: back references with Windows Credential Manager (PRD 31.1).

    Imports cleanly whether or not ``keyring`` is installed. ``available()``
    reports the dependency's presence; the read/write methods raise a clear
    error when it is absent, so this class can be selected and inspected without
    requiring the dependency to be present.
    """

    _SERVICE_NS = "QUILL Social"

    def __init__(self) -> None:
        self._keyring = self._load_keyring()

    @staticmethod
    def _load_keyring():
        try:
            import keyring  # noqa: F401
        except ImportError:
            return None
        return keyring

    @classmethod
    def available(cls) -> bool:
        return cls._load_keyring() is not None

    def _require(self):
        if self._keyring is None:
            raise RuntimeError(
                "Windows Credential Manager backend is not available; install the "
                "'security' extra (keyring) to use it."
            )
        return self._keyring

    def store(self, service: str, account: str, secret: str) -> CredentialRef:
        kr = self._require()
        handle = _handle_for(service, account)
        kr.set_password(self._SERVICE_NS, handle, secret)
        return CredentialRef(service=service, account=account, handle=handle)

    def reference(self, service: str, account: str) -> CredentialRef | None:
        kr = self._require()
        handle = _handle_for(service, account)
        if kr.get_password(self._SERVICE_NS, handle) is None:
            return None
        return CredentialRef(service=service, account=account, handle=handle)

    def resolve(self, ref: CredentialRef) -> str | None:
        kr = self._require()
        return kr.get_password(self._SERVICE_NS, ref.handle)

    def delete(self, service: str, account: str) -> None:
        kr = self._require()
        handle = _handle_for(service, account)
        try:
            kr.delete_password(self._SERVICE_NS, handle)
        except Exception:  # noqa: BLE001 -- deleting a missing key is not an error
            pass


# -- redaction ----------------------------------------------------------------

# key=value / key: value where the key names a secret.
_KV_SECRET = re.compile(
    r"(?i)\b(authorization|token|access[_-]?token|refresh[_-]?token|secret|"
    r"client[_-]?secret|password|passwd|api[_-]?key|bearer)\b"
    r"(\s*[:=]\s*|\s+)"
    r"(['\"]?)([^\s'\",;]+)\3"
)

# A standalone long token-like run (JWTs, hex/base64 keys) not otherwise caught.
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")


def redact(text: str) -> str:
    """Mask secret-looking substrings in ``text`` (PRD 31.1, "redact secrets").

    Handles ``key=value`` / ``key: value`` secret fields, ``Bearer <token>``
    headers, and standalone long token-like runs. Deterministic and safe to run
    over any log line or diagnostic file before it leaves the machine.
    """
    if not text:
        return text

    def _kv(m: re.Match) -> str:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{REDACTED}{m.group(3)}"

    masked = _KV_SECRET.sub(_kv, text)
    masked = _LONG_TOKEN.sub(REDACTED, masked)
    return masked
