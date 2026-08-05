"""Secure GitHub token storage.

Migrated onto the unified :class:`quill.core.secrets.SecretsManager`: the
manager is the single owner of the OS vault (Windows
Credential Manager / DPAPI, portable ``keys.enc``, or the macOS Keychain), so
this module no longer reaches into a platform store directly. The credential
name is unchanged -- :class:`SecretRef` ``("github", "token")`` maps to
``quill-github-token`` -- so no stored token needs migrating, and the public
functions keep their exact signatures.
"""

from __future__ import annotations

from quill.core.secrets import SecretRef, default_secrets_manager

_REF = SecretRef("github", "token")


def load_github_token() -> str | None:
    """Return the stored token, or None if none is stored or no secure store."""
    return default_secrets_manager().get(_REF)


def save_github_token(token: str) -> bool:
    """Persist *token* in the OS secure store. Returns True on success."""
    token = token.strip()
    manager = default_secrets_manager()
    manager.set(_REF, token)
    # Confirm the write landed (no secure store on some platforms is a no-op).
    return manager.get(_REF) == token if token else manager.get(_REF) is None


def delete_github_token() -> bool:
    """Remove any stored GitHub token. Returns True if a token was deleted."""
    return default_secrets_manager().delete(_REF)
