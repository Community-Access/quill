"""End-to-end encryption for QuillSync (PRD 45.3).

The canonical crypto home for the QuillSync framework. A vault key is derived
from the user's passphrase and never leaves the device. Per-object data-
encryption keys (DEKs) are wrapped by the vault key, so any transport or server
stores only wrapped keys and ciphertext.

Uses ``cryptography`` AES-GCM for AEAD and scrypt for the passphrase KDF.
PRD 45.3 names Argon2id as the preferred KDF; scrypt is the available, audited
fallback used here. Both are tunable cost parameters. Nothing here touches the
network or any application model -- this module is record-agnostic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# scrypt cost. Tunable; kept moderate so unit tests stay fast. Production
# should raise N (e.g. 2**17) per platform guidance.
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LEN = 32  # 256-bit AES key
_NONCE_LEN = 12


@dataclass
class VaultKey:
    """A derived vault key with the salt used to derive it."""

    key: bytes
    salt: bytes

    def to_envelope(self) -> dict:
        """Serialize the derivation parameters (NOT the key) for storage.

        Only the salt and KDF params are stored; the key itself is reproducible
        from the passphrase + salt and is never persisted.
        """
        return {
            "kdf": "scrypt",
            "salt": _b64(self.salt),
            "n": _SCRYPT_N,
            "r": _SCRYPT_R,
            "p": _SCRYPT_P,
        }


def derive_vault_key(passphrase: str, *, salt: bytes | None = None) -> VaultKey:
    """Derive a 256-bit vault key from a passphrase via scrypt."""
    salt = salt if salt is not None else os.urandom(16)
    key = hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_LEN,
        maxmem=256 * 1024 * 1024,
    )
    return VaultKey(key=key, salt=salt)


def new_dek() -> bytes:
    """A fresh per-object data-encryption key."""
    return AESGCM.generate_key(bit_length=256)


def wrap_dek(vault: VaultKey, dek: bytes) -> bytes:
    """Wrap a DEK with the vault key (AES-GCM). Returns nonce + ciphertext."""
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(vault.key).encrypt(nonce, dek, associated_data=b"quillsync:dek")
    return nonce + ct


def unwrap_dek(vault: VaultKey, wrapped: bytes) -> bytes:
    """Unwrap a DEK. Raises on tamper or wrong passphrase."""
    nonce, ct = wrapped[:_NONCE_LEN], wrapped[_NONCE_LEN:]
    return AESGCM(vault.key).decrypt(nonce, ct, associated_data=b"quillsync:dek")


def encrypt_object(dek: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Encrypt an object's plaintext with its DEK. Returns nonce + ciphertext."""
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(dek).encrypt(nonce, plaintext, aad)
    return nonce + ct


def decrypt_object(dek: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
    return AESGCM(dek).decrypt(nonce, ct, aad)


def object_hash(blob: bytes) -> str:
    """Content-addressed id for an encrypted blob (dedup + manifest)."""
    return hashlib.sha256(blob).hexdigest()


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def encrypt_json(dek: bytes, obj: dict) -> bytes:
    return encrypt_object(dek, json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def decrypt_json(dek: bytes, blob: bytes) -> dict:
    # json.loads is Any; the payload is always an object here (encrypt_json is
    # the only writer), and core is strict-typed, so say so rather than
    # letting Any leak out of the sync boundary.
    decoded: dict = json.loads(decrypt_object(dek, blob).decode("utf-8"))
    return decoded
