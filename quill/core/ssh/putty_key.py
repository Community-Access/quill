"""Load PuTTY ``.ppk`` private keys natively (issue #139).

paramiko reads OpenSSH keys but not PuTTY's format, so this parses PPK v2 and v3
(encrypted and unencrypted) and hands back a ready-to-use ``paramiko`` key. It
relies only on ``cryptography`` primitives (AES, HMAC, SHA, Argon2id) that ship
with paramiko, so no extra dependency is needed.

The public/private blobs inside a ``.ppk`` use the standard SSH wire format
(identical to what flows on the wire), so the key fields are decoded the same way
paramiko encodes them; the PuTTY-specific part is only the file envelope, the MAC,
and the passphrase key-derivation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

from cryptography.hazmat.primitives.asymmetric import (  # type: ignore[import-not-found]
    dsa,
    ec,
    ed25519,
    rsa,
)
from cryptography.hazmat.primitives.ciphers import (  # type: ignore[import-not-found]
    Cipher,
    algorithms,
    modes,
)

from quill.core.error_codes import CodedError

_MAC_KEY_MAGIC = b"putty-private-key-file-mac-key"
_EC_CURVES = {
    "ecdsa-sha2-nistp256": ec.SECP256R1(),
    "ecdsa-sha2-nistp384": ec.SECP384R1(),
    "ecdsa-sha2-nistp521": ec.SECP521R1(),
}


class PuttyKeyError(CodedError):
    """Raised when a ``.ppk`` file cannot be parsed or its MAC/passphrase fails."""

    code = "QUILL-SSH-PPK-INVALID"


def looks_like_ppk(text: str) -> bool:
    return text.lstrip().startswith("PuTTY-User-Key-File-")


# --- SSH wire-format readers --------------------------------------------------


class _Reader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read_bytes(self, count: int) -> bytes:
        chunk = self._data[self._pos : self._pos + count]
        if len(chunk) != count:
            raise PuttyKeyError("Truncated key blob")
        self._pos += count
        return chunk

    def read_string(self) -> bytes:
        (length,) = (int.from_bytes(self.read_bytes(4), "big"),)
        return self.read_bytes(length)

    def read_mpint(self) -> int:
        return int.from_bytes(self.read_string(), "big")


def _parse_headers(text: str) -> tuple[dict[str, str], list[str]]:
    """Split the PPK into single-value headers and the order they appeared."""
    headers: dict[str, str] = {}
    order: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        name, _, value = line.partition(":")
        name = name.strip()
        value = value.strip()
        if name.endswith("-Lines"):
            try:
                count = int(value)
            except ValueError as exc:
                raise PuttyKeyError(f"Invalid {name} count {value!r} in PPK file") from exc
            body = "".join(lines[index + 1 : index + 1 + count])
            headers[name] = body
            order.append(name)
            index += 1 + count
            continue
        headers[name] = value
        order.append(name)
        index += 1
    return headers, order


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _mac_data(
    algorithm: str, encryption: str, comment: str, public: bytes, private: bytes
) -> bytes:
    return b"".join(
        _ssh_string(part)
        for part in (
            algorithm.encode(),
            encryption.encode(),
            comment.encode(),
            public,
            private,
        )
    )


def _derive_v2(passphrase: bytes) -> tuple[bytes, bytes]:
    key = (
        hashlib.sha1(b"\x00\x00\x00\x00" + passphrase).digest()
        + hashlib.sha1(b"\x00\x00\x00\x01" + passphrase).digest()
    )[:32]
    return key, b"\x00" * 16


def _derive_v3(headers: dict[str, str], passphrase: bytes) -> tuple[bytes, bytes, bytes]:
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id  # type: ignore[import-not-found]

    flavour = headers.get("Key-Derivation", "Argon2id")
    if flavour != "Argon2id":
        raise PuttyKeyError(f"Unsupported PPK key derivation {flavour!r}")
    try:
        salt = bytes.fromhex(headers["Argon2-Salt"])
        out = Argon2id(
            salt=salt,
            length=80,
            iterations=int(headers["Argon2-Passes"]),
            lanes=int(headers["Argon2-Parallelism"]),
            memory_cost=int(headers["Argon2-Memory"]),
        ).derive(passphrase)
    except (KeyError, ValueError) as exc:
        # Missing Argon2-* header (KeyError) or a non-hex salt / non-integer
        # parameter (ValueError) -- surface as a PuTTY key error, not a raw one.
        raise PuttyKeyError(f"Malformed Argon2 parameters in PPK file: {exc}") from exc
    return out[:32], out[32:48], out[48:80]


def load_ppk(text: str, passphrase: str | None = None) -> object:
    """Parse a ``.ppk`` file's text and return a ``paramiko`` private key."""
    headers, _order = _parse_headers(text)
    version_key = next((name for name in headers if name.startswith("PuTTY-User-Key-File-")), None)
    if version_key is None:
        raise PuttyKeyError("Not a PuTTY private key file")
    try:
        version = int(version_key.rsplit("-", 1)[1])
    except ValueError as exc:
        raise PuttyKeyError(f"Unrecognised PPK version header {version_key!r}") from exc
    algorithm = headers[version_key].strip()
    encryption = headers.get("Encryption", "none").strip()
    comment = headers.get("Comment", "")
    try:
        # base64.b64decode raises binascii.Error (a ValueError subclass) on a
        # corrupt body -- keep it a PuttyKeyError so callers speak one message.
        public = base64.b64decode(headers.get("Public-Lines", ""))
        private_raw = base64.b64decode(headers.get("Private-Lines", ""))
    except ValueError as exc:
        raise PuttyKeyError("Malformed base64 in the PPK key body") from exc
    stored_mac = headers.get("Private-MAC", "").strip()
    passphrase_bytes = (passphrase or "").encode()

    if encryption == "none":
        private = private_raw
        if version == 3:
            mac_key = b""
        else:
            mac_key = hashlib.sha1(_MAC_KEY_MAGIC + passphrase_bytes).digest()
    elif encryption == "aes256-cbc":
        if not passphrase_bytes:
            raise PuttyKeyError("This key is encrypted; a passphrase is required")
        if version == 3:
            cipher_key, iv, mac_key = _derive_v3(headers, passphrase_bytes)
        else:
            cipher_key, iv = _derive_v2(passphrase_bytes)
            mac_key = hashlib.sha1(_MAC_KEY_MAGIC + passphrase_bytes).digest()
        try:
            decryptor = Cipher(algorithms.AES(cipher_key), modes.CBC(iv)).decryptor()
            private = decryptor.update(private_raw) + decryptor.finalize()
        except ValueError as exc:
            # e.g. ciphertext not a multiple of the AES block size.
            raise PuttyKeyError("Could not decrypt the PPK key body") from exc
    else:
        raise PuttyKeyError(f"Unsupported PPK encryption {encryption!r}")

    digest = hashlib.sha256 if version == 3 else hashlib.sha1
    expected = hmac.new(
        mac_key, _mac_data(algorithm, encryption, comment, public, private), digest
    ).hexdigest()
    if not hmac.compare_digest(expected, stored_mac.lower()):
        if encryption != "none":
            raise PuttyKeyError("Wrong passphrase or corrupted key (MAC check failed)")
        raise PuttyKeyError("Corrupted key (MAC check failed)")

    crypto_key = _build_crypto_key(algorithm, public, private)
    return _to_paramiko(algorithm, crypto_key)


def _build_crypto_key(algorithm: str, public: bytes, private: bytes) -> Any:
    pub = _Reader(public)
    pub_algorithm = pub.read_string().decode()
    if pub_algorithm != algorithm:
        raise PuttyKeyError("Key algorithm mismatch between header and blob")
    priv = _Reader(private)

    if algorithm == "ssh-rsa":
        e = pub.read_mpint()
        n = pub.read_mpint()
        d = priv.read_mpint()
        p = priv.read_mpint()
        q = priv.read_mpint()
        iqmp = priv.read_mpint()
        numbers = rsa.RSAPrivateNumbers(
            p=p,
            q=q,
            d=d,
            dmp1=rsa.rsa_crt_dmp1(d, p),
            dmq1=rsa.rsa_crt_dmq1(d, q),
            iqmp=iqmp,
            public_numbers=rsa.RSAPublicNumbers(e=e, n=n),
        )
        return numbers.private_key()

    if algorithm == "ssh-dss":
        p = pub.read_mpint()
        q = pub.read_mpint()
        g = pub.read_mpint()
        y = pub.read_mpint()
        x = priv.read_mpint()
        params = dsa.DSAParameterNumbers(p=p, q=q, g=g)
        return dsa.DSAPrivateNumbers(
            x=x, public_numbers=dsa.DSAPublicNumbers(y=y, parameter_numbers=params)
        ).private_key()

    if algorithm in _EC_CURVES:
        pub.read_string()  # curve identifier
        point = pub.read_string()
        secret = priv.read_mpint()
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(_EC_CURVES[algorithm], point)
        return ec.derive_private_key(secret, _EC_CURVES[algorithm]), public_key

    if algorithm == "ssh-ed25519":
        pub.read_string()  # 32-byte public point
        seed = priv.read_string()
        return ed25519.Ed25519PrivateKey.from_private_bytes(seed)

    raise PuttyKeyError(f"Unsupported key algorithm {algorithm!r}")


def _to_paramiko(algorithm: str, crypto_key: Any) -> object:
    import io

    import paramiko  # type: ignore[import-untyped]
    from cryptography.hazmat.primitives import serialization  # type: ignore[import-not-found]

    if algorithm == "ssh-ed25519":
        pem = crypto_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
        return paramiko.Ed25519Key.from_private_key(io.StringIO(pem.decode()))

    if algorithm in _EC_CURVES:
        private_key, _public_key = crypto_key
        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        return paramiko.ECDSAKey.from_private_key(io.StringIO(pem.decode()))

    pem = crypto_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    if algorithm == "ssh-rsa":
        return paramiko.RSAKey.from_private_key(io.StringIO(pem.decode()))
    if algorithm == "ssh-dss":
        return paramiko.DSSKey.from_private_key(io.StringIO(pem.decode()))
    raise PuttyKeyError(f"Unsupported key algorithm {algorithm!r}")
