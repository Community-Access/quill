"""The one unencrypted file in the remote: how the second machine derives the key.

The vault key is derived from a recovery phrase **and a salt**, and the second
machine has only the phrase. So the salt has to travel, and the remote folder is
where it travels: ``quillsync/vault.json``, holding the scrypt parameters, the
salt, and one small encrypted check value.

That file gives away nothing. A salt is not a secret -- it exists to make a
precomputed attack useless, not to be hidden -- and the check value is a fixed
known string encrypted with the derived key, which reveals the phrase only to
somebody who already has it.

**The check value is the whole point of this module.** Without it, a mistyped
phrase produces a key that decrypts nothing, and the first sign is a decryption
failure part-way through a pull, after some records have already been written.
With it, the phrase is verified before anything is read or written, and the
answer is "that recovery phrase does not match this folder" -- which is a
sentence somebody can act on.

**Never overwritten.** Re-deriving a vault over a folder that already has one
would orphan every commit already there: the old records stay, unreadable
forever, and the new machine looks like it synced correctly to an empty remote.
:func:`load_or_create` reads an existing vault and only ever writes a new one.

wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.sync import crypto
from quill.core.sync.crypto import VaultKey

#: Where the vault descriptor lives inside the chosen remote folder.
VAULT_PATH = ("quillsync", "vault.json")

#: The plaintext behind the check value. Fixed and public on purpose: what
#: proves the phrase is that the *ciphertext* decrypts, not what is inside.
_CHECK_PLAINTEXT = b"quillsync-vault-check-v1"

#: Bumped only if the derivation or the check format changes, so an older build
#: refuses a vault it would misread rather than corrupting it.
VAULT_VERSION = 1


class VaultError(CodedError):
    """A vault file that cannot be used, with a sentence saying why."""

    code = "QUILL-SYNC-VAULT-UNUSABLE"


@dataclass(frozen=True, slots=True)
class VaultInfo:
    """A remote's vault: the key in hand, and whether this call created it."""

    key: VaultKey
    created: bool


def vault_path(remote_dir: Path | str) -> Path:
    return Path(remote_dir).joinpath(*VAULT_PATH)


def exists(remote_dir: Path | str) -> bool:
    """Whether this folder has already been set up for sync."""
    return vault_path(remote_dir).is_file()


def _check_value(key: VaultKey) -> dict[str, str]:
    """The check, as two separate base64 fields.

    Two fields rather than one concatenated blob with a separator: the wrapped
    key is ciphertext, any byte of it can be any value, and a separator byte
    that occurs inside the data splits it in the wrong place -- which shows up
    as "that recovery phrase does not match" for a phrase that is perfectly
    correct.
    """
    dek = crypto.new_dek()
    return {
        "dek": base64.b64encode(crypto.wrap_dek(key, dek)).decode("ascii"),
        "blob": base64.b64encode(crypto.encrypt_object(dek, _CHECK_PLAINTEXT)).decode("ascii"),
    }


def _verify(key: VaultKey, check: object) -> bool:
    if not isinstance(check, dict):
        return False
    try:
        dek = crypto.unwrap_dek(key, base64.b64decode(str(check.get("dek", ""))))
        blob = base64.b64decode(str(check.get("blob", "")))
        return crypto.decrypt_object(dek, blob) == _CHECK_PLAINTEXT
    except Exception:  # noqa: BLE001 - any failure means "wrong phrase"
        return False


def create(remote_dir: Path | str, phrase: str) -> VaultInfo:
    """Set this folder up for sync with *phrase*. Refuses to overwrite one.

    The refusal is the important half: overwriting would orphan every commit
    already in the folder -- unreadable forever, while the machine that did it
    appears to have synced correctly to an empty remote.
    """
    path = vault_path(remote_dir)
    if path.is_file():
        raise VaultError(
            "That folder is already set up for syncing. Enter its recovery "
            "phrase instead of making a new one."
        )
    key = crypto.derive_vault_key(phrase)
    envelope = key.to_envelope()
    envelope["version"] = VAULT_VERSION
    envelope["check"] = _check_value(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return VaultInfo(key=key, created=True)


def open_existing(remote_dir: Path | str, phrase: str) -> VaultInfo:
    """Derive the key for a folder already set up, verifying the phrase first."""
    path = vault_path(remote_dir)
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise VaultError(
            "That folder is not set up for syncing, or its sync file cannot be read."
        ) from error
    if not isinstance(envelope, dict):
        raise VaultError("That folder's sync file is not readable.")
    if int(envelope.get("version", 1)) > VAULT_VERSION:
        # Refuse rather than guess: a newer format read by an older build is
        # how a remote gets corrupted by the machine that was trying to join it.
        raise VaultError(
            "That folder was set up by a newer version of QUILL. Update this "
            "copy before syncing with it."
        )
    try:
        salt = base64.b64decode(str(envelope.get("salt", "")).encode("ascii"))
    except Exception as error:  # noqa: BLE001
        raise VaultError("That folder's sync file is not readable.") from error
    key = crypto.derive_vault_key(phrase, salt=salt)
    check = envelope.get("check")
    if check and not _verify(key, check):
        # Checked before anything is read or written, so a mistyped phrase is a
        # sentence rather than a decryption failure part-way through a pull.
        raise VaultError(
            "That recovery phrase does not match this folder. Check the words "
            "and try again -- nothing was changed."
        )
    return VaultInfo(key=key, created=False)


def load_or_create(remote_dir: Path | str, phrase: str) -> VaultInfo:
    """Join an existing vault, or set one up if the folder has none."""
    if exists(remote_dir):
        return open_existing(remote_dir, phrase)
    return create(remote_dir, phrase)
