"""The QUILL Secrets Manager -- one hardened façade over the OS secret vault.

This is the single, uniform entry point every subsystem uses to read and write
secrets (OAuth token bundles, API keys, per-title content keys). It wraps the
existing platform store in :mod:`quill.platform.windows.credential_store` -- the
env-var / portable-DPAPI / Credential-Manager / macOS-Keychain chain -- so no
feature module has to talk to DPAPI, the Credential Manager, or the Keychain
directly. Keeping exactly one owner of the OS vault is what makes the security
guarantees uniform and testable (see ``bard.md`` Part C).

Design points:

* **Namespaced identities.** Every secret is addressed by a :class:`SecretRef`
  ``(namespace, name)`` that maps to the established credential-name convention
  ``quill-<namespace>-<name>`` -- so it drops straight onto ``credential_store``
  and the env-var override mapping keeps working.
* **JSON bundles.** :meth:`SecretsManager.get_json` / :meth:`set_json`
  standardize the access/refresh/expires_at/scope token-bundle pattern that the
  per-service stores hand-roll today.
* **One-call account wipe.** :meth:`SecretsManager.wipe_namespace` clears every
  entry a namespace ever wrote (the "Sign out of BARD" call). It does this
  without any OS-specific enumeration API by keeping a tiny per-namespace index
  of *names* (never values) inside the same store.
* **Nothing here is a secret in source.** Values live only in the OS vault; this
  module never persists a secret to a file, to settings, or to the repository.

wx-free and strict-typed (always in ``mypy`` scope).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from quill.core.error_codes import CodedError

__all__ = [
    "SecretBackend",
    "SecretRef",
    "SecretsError",
    "SecretsManager",
    "default_secrets_manager",
]

# A namespace/name segment: lowercase alphanumerics with internal separators.
# Conservative on purpose -- these compose into the OS credential target name.
_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")

# Reserved name for the per-namespace index entry. User code may not use it.
_INDEX_NAME = "__index__"


class SecretsError(CodedError):
    """Raised for invalid secret identities or malformed manager input."""

    code = "QUILL-SECRETS-REF-INVALID"


@dataclass(frozen=True, slots=True)
class SecretRef:
    """A namespaced secret identity, e.g. ``SecretRef("bard", "patron-tokens")``.

    ``namespace`` and ``name`` are each a short lowercase segment
    (``[a-z0-9]`` then ``[a-z0-9._-]``). They compose into the credential name
    ``quill-<namespace>-<name>`` used by
    :mod:`quill.platform.windows.credential_store`.
    """

    namespace: str
    name: str

    def __post_init__(self) -> None:
        _validate_segment(self.namespace, field="namespace")
        _validate_segment(self.name, field="name", allow_index=False)

    @property
    def cred_name(self) -> str:
        """The underlying OS credential target name."""
        return f"quill-{self.namespace}-{self.name}"


def _validate_segment(value: str, *, field: str, allow_index: bool = True) -> None:
    if not isinstance(value, str) or not _SEGMENT_RE.match(value):
        raise SecretsError(f"{field} must match {_SEGMENT_RE.pattern!r}; got {value!r}")
    if not allow_index and value == _INDEX_NAME:
        raise SecretsError(f"{field} {_INDEX_NAME!r} is reserved")


@runtime_checkable
class SecretBackend(Protocol):
    """The minimal OS-vault interface the manager depends on.

    The default implementation wraps
    :mod:`quill.platform.windows.credential_store`; tests inject an in-memory
    fake so the manager is exercised without touching the real vault.
    """

    def load(self, cred_name: str) -> str: ...
    def save(self, cred_name: str, value: str) -> None: ...
    def delete(self, cred_name: str) -> bool: ...


class _CredentialStoreBackend:
    """Default backend: the unified env-var / DPAPI / Credential-Manager chain."""

    def load(self, cred_name: str) -> str:
        from quill.platform.windows.credential_store import load_secret

        return load_secret(cred_name)

    def save(self, cred_name: str, value: str) -> None:
        from quill.platform.windows.credential_store import save_secret

        save_secret(cred_name, value)

    def delete(self, cred_name: str) -> bool:
        from quill.platform.windows.credential_store import delete_secret

        return delete_secret(cred_name)


class SecretsManager:
    """Uniform read/write/wipe over the OS secret vault, keyed by :class:`SecretRef`.

    Construct with no arguments for the real store, or pass a ``backend`` for
    tests. The manager is stateless beyond the backend it delegates to; the only
    persisted bookkeeping is a per-namespace name index kept in the same vault.
    """

    def __init__(self, backend: SecretBackend | None = None) -> None:
        self._backend: SecretBackend = backend or _CredentialStoreBackend()

    # -- single-secret operations -------------------------------------------

    def get(self, ref: SecretRef) -> str | None:
        """Return the secret, or ``None`` when nothing is stored."""
        value = self._backend.load(ref.cred_name)
        return value or None

    def set(self, ref: SecretRef, value: str) -> None:
        """Store ``value``. An empty string deletes the entry (see :meth:`delete`)."""
        if not value:
            self.delete(ref)
            return
        self._backend.save(ref.cred_name, value)
        self._index_add(ref)

    def delete(self, ref: SecretRef) -> bool:
        """Remove the entry. Returns ``True`` when one existed."""
        existed = self._backend.delete(ref.cred_name)
        self._index_remove(ref)
        return existed

    # -- JSON bundle helpers -------------------------------------------------

    def get_json(self, ref: SecretRef) -> dict[str, object] | None:
        """Return the stored JSON object, or ``None`` when absent or malformed."""
        raw = self.get(ref)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    def set_json(self, ref: SecretRef, value: dict[str, object]) -> None:
        """Serialize ``value`` to JSON and store it."""
        self.set(ref, json.dumps(value))

    # -- namespace-wide wipe -------------------------------------------------

    def wipe_namespace(self, namespace: str) -> int:
        """Delete every entry the namespace has stored. Returns the count removed.

        This is the one call sign-out / account-removal invokes. It reads the
        per-namespace name index, deletes each named secret, then drops the index
        itself.
        """
        _validate_segment(namespace, field="namespace")
        names = self._index_names(namespace)
        removed = 0
        for name in names:
            if self._backend.delete(f"quill-{namespace}-{name}"):
                removed += 1
        self._backend.delete(self._index_cred_name(namespace))
        return removed

    # -- index bookkeeping ---------------------------------------------------

    def _index_cred_name(self, namespace: str) -> str:
        # The per-namespace index lives beside the namespace's secrets under the
        # reserved name, which SecretRef refuses -- so build the target directly.
        return f"quill-{namespace}-{_INDEX_NAME}"

    def _index_names(self, namespace: str) -> list[str]:
        raw = self._backend.load(self._index_cred_name(namespace))
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        return [str(item) for item in data if isinstance(item, str)]

    def _index_write(self, namespace: str, names: list[str]) -> None:
        if names:
            self._backend.save(self._index_cred_name(namespace), json.dumps(sorted(set(names))))
        else:
            self._backend.delete(self._index_cred_name(namespace))

    def _index_add(self, ref: SecretRef) -> None:
        names = self._index_names(ref.namespace)
        if ref.name not in names:
            names.append(ref.name)
            self._index_write(ref.namespace, names)

    def _index_remove(self, ref: SecretRef) -> None:
        names = self._index_names(ref.namespace)
        if ref.name in names:
            names = [n for n in names if n != ref.name]
            self._index_write(ref.namespace, names)


_DEFAULT: SecretsManager | None = None


def default_secrets_manager() -> SecretsManager:
    """Return the process-wide default manager (backed by the real OS vault)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = SecretsManager()
    return _DEFAULT
