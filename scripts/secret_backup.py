"""Encrypt/decrypt a small secret file with a passphrase.

Built for the release keys that must survive this machine -- the update-feed
signing seed (``~/.config/quill/quill-feed-priv.key``) and the artifact
signing key -- so an encrypted copy can safely sit in cloud sync, on a USB
stick, or in an email to yourself, none of which are safe for the plaintext.

Deliberately built on PyNaCl, which QUILL already depends on for signing, so
this adds no new dependency and no new cryptographic surface:

* Argon2id (``nacl.pwhash.argon2id``) stretches the passphrase into a
  32-byte key. Memory-hard, so a stolen file resists offline guessing far
  better than a plain hash would.
* XSalsa20-Poly1305 (``nacl.secret.SecretBox``) encrypts and authenticates.
  Tampering is detected on decrypt rather than silently producing garbage.

The passphrase is read from a prompt, never from a command-line argument --
arguments land in shell history and in the process list, where other users
on the machine can read them.

Usage::

    python scripts/secret_backup.py encrypt <plaintext-in> <encrypted-out>
    python scripts/secret_backup.py decrypt <encrypted-in> [plaintext-out]

``decrypt`` with no output path prints to stdout. The encrypted file is
ASCII, so it survives being pasted into a note or printed.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import sys
from pathlib import Path

_MAGIC = "QUILL-SECRET-BACKUP-v1"
_SALT_BYTES = 16


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    from nacl import pwhash, secret

    return pwhash.argon2id.kdf(
        secret.SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        # SENSITIVE, not INTERACTIVE: this protects a long-lived signing key,
        # and a few seconds on the one occasion you restore it is a good trade
        # for making a stolen file far more expensive to brute-force.
        opslimit=pwhash.argon2id.OPSLIMIT_SENSITIVE,
        memlimit=pwhash.argon2id.MEMLIMIT_SENSITIVE,
    )


def encrypt(plaintext: bytes, passphrase: str) -> str:
    """Return the armoured ciphertext for *plaintext*."""
    from nacl import secret, utils

    salt = utils.random(_SALT_BYTES)
    box = secret.SecretBox(_derive_key(passphrase, salt))
    encrypted = box.encrypt(plaintext)  # nonce is prepended by SecretBox
    body = base64.b64encode(salt + encrypted).decode("ascii")
    wrapped = "\n".join(body[i : i + 76] for i in range(0, len(body), 76))
    return f"{_MAGIC}\n{wrapped}\n"


def decrypt(armoured: str, passphrase: str) -> bytes:
    """Return the plaintext for an armoured ciphertext produced by :func:`encrypt`."""
    from nacl import secret

    lines = [line.strip() for line in armoured.splitlines() if line.strip()]
    if not lines or lines[0] != _MAGIC:
        raise ValueError(f"not a {_MAGIC} file")
    raw = base64.b64decode("".join(lines[1:]))
    salt, encrypted = raw[:_SALT_BYTES], raw[_SALT_BYTES:]
    box = secret.SecretBox(_derive_key(passphrase, salt))
    return bytes(box.decrypt(encrypted))


def _read_passphrase(*, confirm: bool) -> str:
    passphrase = getpass.getpass("Passphrase: ")
    if not passphrase:
        raise SystemExit("A passphrase is required.")
    if confirm and passphrase != getpass.getpass("Confirm passphrase: "):
        raise SystemExit("Passphrases did not match; nothing was written.")
    return passphrase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encrypt", help="Encrypt a secret file with a passphrase.")
    enc.add_argument("source", type=Path)
    enc.add_argument("target", type=Path)

    dec = sub.add_parser("decrypt", help="Decrypt a file produced by 'encrypt'.")
    dec.add_argument("source", type=Path)
    dec.add_argument("target", type=Path, nargs="?")

    args = parser.parse_args(argv)

    if args.command == "encrypt":
        plaintext = args.source.read_bytes()
        armoured = encrypt(plaintext, _read_passphrase(confirm=True))
        args.target.write_text(armoured, encoding="utf-8", newline="\n")
        print(f"Encrypted {args.source} -> {args.target}")
        print("Verify you can restore it before deleting any other copy:")
        print(f"    python scripts/secret_backup.py decrypt {args.target}")
        return 0

    armoured = args.source.read_text(encoding="utf-8")
    try:
        plaintext = decrypt(armoured, _read_passphrase(confirm=False))
    except Exception as error:  # noqa: BLE001 - wrong passphrase or tampering
        raise SystemExit(f"Could not decrypt: {error}") from error
    if args.target:
        args.target.write_bytes(plaintext)
        print(f"Decrypted {args.source} -> {args.target}")
    else:
        sys.stdout.write(plaintext.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
