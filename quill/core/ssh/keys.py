"""Private-key loading across formats for edit-over-SSH (issue #139).

Dispatches a key file to the right loader:

* OpenSSH / PEM (RSA, Ed25519, ECDSA, DSA) -- paramiko's own loaders.
* PuTTY ``.ppk`` (v2/v3, encrypted or not) -- :mod:`quill.core.ssh.putty_key`.
* SecureCRT / ssh.com RFC4716 (``---- BEGIN SSH2 ... ----``) -- recognised, with
  guidance to export OpenSSH or PuTTY format (both read natively here).
"""

from __future__ import annotations

from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.ssh.putty_key import load_ppk, looks_like_ppk

_SSHCOM_MARKERS = (
    "---- BEGIN SSH2 ENCRYPTED PRIVATE KEY ----",
    "---- BEGIN SSH2 PRIVATE KEY ----",
)


class KeyFormatError(CodedError):
    """Raised when a private key file cannot be loaded."""

    code = "QUILL-SSH-KEY-FORMAT"


def looks_like_sshcom(text: str) -> bool:
    """True for SecureCRT / ssh.com (RFC4716-style) private keys."""
    return any(marker in text for marker in _SSHCOM_MARKERS)


def load_private_key(key_path: str, passphrase: str | None = None) -> object:
    """Return a ``paramiko`` private key from ``key_path`` in any supported format."""
    path = Path(key_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise KeyFormatError(f"Could not read key file {key_path}: {error}") from error

    if looks_like_ppk(text):
        return load_ppk(text, passphrase)
    if looks_like_sshcom(text):
        # Follow-up #153: parse the proprietary VanDyke/ssh.com binary format
        # natively once a validating fixture is available. For now SecureCRT
        # users export OpenSSH or .ppk (both read above), and we guide them here.
        raise KeyFormatError(
            "This looks like a SecureCRT / ssh.com key. In SecureCRT, export the "
            "key as OpenSSH or PuTTY (.ppk) format (Tools > Export Public Key / "
            "convert the private key) -- Quill reads both of those natively."
        )
    return _load_openssh(str(path), passphrase)


def _load_openssh(key_path: str, passphrase: str | None) -> object:
    import paramiko  # type: ignore[import-untyped]

    last_error: Exception | None = None
    for key_class_name in ("Ed25519Key", "ECDSAKey", "RSAKey", "DSSKey"):
        key_class = getattr(paramiko, key_class_name, None)
        if key_class is None:
            continue
        try:
            return key_class.from_private_key_file(key_path, password=passphrase or None)
        except Exception as error:  # noqa: BLE001 - wrong algorithm; try the next
            last_error = error
    raise KeyFormatError(
        f"Could not load the private key at {key_path}. Supported formats: OpenSSH, "
        f"PEM, and PuTTY .ppk."
    ) from last_error
