"""Tests for the passphrase secret-backup tool.

The property that matters is that a backup can actually be RESTORED -- an
encrypted file nobody has ever decrypted is not a backup. Everything here
exercises the real cryptography rather than a stub.
"""

from __future__ import annotations

import pytest

from scripts.secret_backup import decrypt, encrypt

_SEED = b"m1oUUJ8wAvRwmO8b+1PaAcfI9IjXITZOun1909AEy28=\n"


def test_round_trip_restores_the_exact_bytes() -> None:
    armoured = encrypt(_SEED, "correct horse battery staple")
    assert decrypt(armoured, "correct horse battery staple") == _SEED


def test_the_plaintext_never_appears_in_the_ciphertext() -> None:
    armoured = encrypt(_SEED, "pw")
    assert _SEED.decode().strip() not in armoured


def test_wrong_passphrase_is_rejected_rather_than_returning_garbage() -> None:
    armoured = encrypt(_SEED, "right")
    with pytest.raises(Exception):  # noqa: B017 - nacl raises its own error type
        decrypt(armoured, "wrong")


def test_tampering_is_detected() -> None:
    """Authenticated encryption: a modified file must fail, not decrypt wrongly."""
    armoured = encrypt(_SEED, "pw")
    lines = armoured.splitlines()
    body = lines[1]
    flipped = ("A" if body[0] != "A" else "B") + body[1:]
    tampered = "\n".join([lines[0], flipped, *lines[2:]])
    with pytest.raises(Exception):  # noqa: B017
        decrypt(tampered, "pw")


def test_same_secret_encrypts_differently_every_time() -> None:
    """A fresh salt and nonce per run: identical inputs must not collide."""
    assert encrypt(_SEED, "pw") != encrypt(_SEED, "pw")


def test_rejects_a_file_it_did_not_write() -> None:
    with pytest.raises(ValueError, match="QUILL-SECRET-BACKUP"):
        decrypt("just some text\n", "pw")


def test_armoured_output_is_printable_ascii() -> None:
    """The backup has to survive being printed, pasted, or emailed."""
    armoured = encrypt(_SEED, "pw")
    assert armoured.isascii()
    assert all(len(line) <= 76 for line in armoured.splitlines())
