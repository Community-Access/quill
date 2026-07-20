"""Beacon-facing re-export of the QuillSync crypto (PRD 45.3).

The canonical implementation lives in :mod:`quillsync.crypto` so every QUILL
companion app shares one audited crypto path. This module re-exports it under
the historical ``quill.apps.beacon.sync_crypto`` name so existing callers and tests
keep working unchanged.
"""

from __future__ import annotations

from quill.apps.beacon.quillsync.crypto import (  # noqa: F401  # noqa: F401
    VaultKey,
    _b64,
    _unb64,
    decrypt_json,
    decrypt_object,
    derive_vault_key,
    encrypt_json,
    encrypt_object,
    new_dek,
    object_hash,
    unwrap_dek,
    wrap_dek,
)

__all__ = [
    "VaultKey",
    "derive_vault_key",
    "new_dek",
    "wrap_dek",
    "unwrap_dek",
    "encrypt_object",
    "decrypt_object",
    "object_hash",
    "encrypt_json",
    "decrypt_json",
    "_b64",
    "_unb64",
]
