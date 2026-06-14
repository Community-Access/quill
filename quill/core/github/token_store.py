"""Secure GitHub token storage.

Backed by the Windows Credential Manager (DPAPI) on Windows and the login
Keychain on macOS (#160), so the token persists on both platforms. Other
platforms have no secure store and report that nothing was saved.
"""

from __future__ import annotations

import sys

_CRED_NAME = "quill-github-token"


def load_github_token() -> str | None:
    """Return the stored token, or None if none is stored or no secure store."""
    if sys.platform == "darwin":
        try:
            from quill.platform.macos.keychain import get_secret

            return get_secret(_CRED_NAME)
        except Exception:  # noqa: BLE001 - keychain errors are non-fatal
            return None
    if sys.platform != "win32":
        return None
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        cred = load_generic_credential(_CRED_NAME)
        return cred.secret if cred else None
    except Exception:  # noqa: BLE001 - credential errors are non-fatal
        return None


def save_github_token(token: str) -> bool:
    """Persist *token* in the OS secure store. Returns True on success."""
    if sys.platform == "darwin":
        try:
            from quill.platform.macos.keychain import set_secret

            set_secret(_CRED_NAME, token)
            return True
        except Exception:  # noqa: BLE001
            return False
    if sys.platform != "win32":
        return False
    try:
        from quill.platform.windows.credential_manager import save_generic_credential

        save_generic_credential(_CRED_NAME, token)
        return True
    except Exception:  # noqa: BLE001
        return False


def delete_github_token() -> bool:
    """Remove any stored GitHub token. Returns True if a token was deleted."""
    if sys.platform == "darwin":
        try:
            from quill.platform.macos.keychain import delete_secret, get_secret

            existed = get_secret(_CRED_NAME) is not None
            delete_secret(_CRED_NAME)
            return existed
        except Exception:  # noqa: BLE001
            return False
    if sys.platform != "win32":
        return False
    try:
        from quill.platform.windows.credential_manager import delete_generic_credential

        return delete_generic_credential(_CRED_NAME)
    except Exception:  # noqa: BLE001
        return False
