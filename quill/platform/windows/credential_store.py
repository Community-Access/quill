"""Unified API-key store: env var > portable DPAPI file > Credential Manager.

Portable mode is active when ``QUILL_PORTABLE=1`` is set.  In portable mode
all credentials are stored in a DPAPI-encrypted file (``keys.enc`` in the
QUILL data directory) so the entire QUILL installation can live in a single
folder without touching the Windows Credential Manager.

Priority (highest to lowest):
  1. Env-var override  ``QUILL_<CANONICAL>_KEY``
  2. Portable file store (``keys.enc``)  — when ``QUILL_PORTABLE=1``
  3. Windows Credential Manager           — standard installs

Env-var name mapping examples::

    quill-openrouter-api-key  ->  QUILL_OPENROUTER_KEY
    quill-openai-api-key      ->  QUILL_OPENAI_KEY
    quill-ollama-api-key      ->  QUILL_OLLAMA_KEY
    QUILL:assistant:api-key   ->  QUILL_ASSISTANT_KEY

The portable store uses DPAPI so it is protected by the Windows user-account
key.  It is **not** portable across different Windows machines or accounts.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_PORTABLE_STORE_ENTROPY = b"quill-portable-keys-v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cred_to_env_var(cred_name: str) -> str:
    """Map a credential name to its env-var override.

    >>> _cred_to_env_var("quill-openrouter-api-key")
    'QUILL_OPENROUTER_KEY'
    >>> _cred_to_env_var("QUILL:assistant:api-key")
    'QUILL_ASSISTANT_KEY'
    """
    normalized = cred_name.upper().replace(":", "_").replace("-", "_")
    if normalized.startswith("QUILL_"):
        normalized = normalized[6:]
    if normalized.endswith("_API_KEY"):
        normalized = normalized[:-8] + "_KEY"
    return f"QUILL_{normalized}"


def is_portable_mode() -> bool:
    """Return True when ``QUILL_PORTABLE=1`` is set in the environment."""
    return os.environ.get("QUILL_PORTABLE") == "1"


def _keys_enc_path() -> Path:
    try:
        from quill.core.paths import app_data_dir

        return app_data_dir() / "keys.enc"
    except Exception:
        return Path.home() / ".quill" / "keys.enc"


def _read_store() -> dict[str, str]:
    path = _keys_enc_path()
    if not path.exists():
        return {}
    try:
        from quill.core.storage import read_json

        data = read_json(path, default={})
        if isinstance(data, dict):
            creds = data.get("credentials", {})
            return creds if isinstance(creds, dict) else {}
    except Exception:
        logger.warning("portable key store unreadable: %s", path)
    return {}


def _write_store(credentials: dict[str, str]) -> None:
    try:
        from quill.core.storage import write_json_atomic

        write_json_atomic(_keys_enc_path(), {"version": 1, "credentials": credentials})
    except Exception:
        logger.error("portable key store write failed")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_secret(cred_name: str) -> str:
    """Return the secret for *cred_name*, or ``""`` when not found."""
    env_val = os.environ.get(_cred_to_env_var(cred_name), "").strip()
    if env_val:
        return env_val

    if is_portable_mode():
        if not _IS_WINDOWS:
            return ""
        stored = _read_store().get(cred_name, "")
        if not stored:
            return ""
        try:
            from quill.platform.windows.dpapi import unprotect_secret

            return unprotect_secret(stored, entropy=_PORTABLE_STORE_ENTROPY).strip()
        except Exception:
            logger.warning("failed to decrypt portable key '%s'", cred_name)
        return ""

    if not _IS_WINDOWS:
        # macOS: the login Keychain is the real store (#160). Other platforms
        # have no secure store, so a key simply isn't persisted there.
        if _IS_MACOS:
            try:
                from quill.platform.macos.keychain import get_secret

                return (get_secret(cred_name) or "").strip()
            except Exception:  # noqa: BLE001 - keychain unavailable
                return ""
        return ""
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            load_generic_credential,
        )

        if credential_manager_available():
            result = load_generic_credential(cred_name)
            return result.secret.strip() if result else ""
    except Exception:
        pass
    return ""


def save_secret(cred_name: str, secret: str) -> None:
    """Persist *secret* under *cred_name*.  Deletes the entry when *secret* is empty."""
    secret = secret.strip()
    if os.environ.get(_cred_to_env_var(cred_name), "").strip():
        return  # never overwrite an env-var override

    if is_portable_mode():
        if not _IS_WINDOWS:
            return
        store = _read_store()
        if secret:
            from quill.platform.windows.dpapi import protect_secret

            store[cred_name] = protect_secret(secret, entropy=_PORTABLE_STORE_ENTROPY)
        else:
            store.pop(cred_name, None)
        _write_store(store)
        return

    if not _IS_WINDOWS:
        # macOS: persist to the login Keychain (#160). Empty secret clears it.
        if _IS_MACOS:
            try:
                from quill.platform.macos.keychain import (
                    delete_secret as _kc_delete,
                )
                from quill.platform.macos.keychain import (
                    set_secret as _kc_set,
                )

                if secret:
                    _kc_set(cred_name, secret)
                else:
                    _kc_delete(cred_name)
            except Exception:  # noqa: BLE001 - keychain unavailable
                pass
        return
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            delete_generic_credential,
            save_generic_credential,
        )

        if not credential_manager_available():
            return
        if secret:
            save_generic_credential(cred_name, secret)
        else:
            try:
                delete_generic_credential(cred_name)
            except OSError:
                pass
    except Exception:
        pass


def delete_secret(cred_name: str) -> bool:
    """Remove *cred_name* from the active store.  Returns True when found."""
    if is_portable_mode():
        if not _IS_WINDOWS:
            return False
        store = _read_store()
        if cred_name in store:
            del store[cred_name]
            _write_store(store)
            return True
        return False

    if not _IS_WINDOWS:
        # macOS: remove from the login Keychain, reporting whether it existed.
        if _IS_MACOS:
            try:
                from quill.platform.macos.keychain import (
                    delete_secret as _kc_delete,
                )
                from quill.platform.macos.keychain import (
                    get_secret as _kc_get,
                )

                existed = _kc_get(cred_name) is not None
                _kc_delete(cred_name)
                return existed
            except Exception:  # noqa: BLE001 - keychain unavailable
                return False
        return False
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            delete_generic_credential,
        )

        if credential_manager_available():
            return bool(delete_generic_credential(cred_name))
    except Exception:
        pass
    return False
