"""Unlock codes: offline-verifiable, signed pre-beta feature access.

A small number of currently ``locked_off`` features (see
``core/feature_catalog.py``) are meant for trusted testers ahead of general
availability -- the first is ``core.adp`` (a voice-conversation experience
still in research). Rather than build a server-side gate, an unlock code is
a short string that encodes which feature it grants and (optionally) an
expiry date, signed with a dedicated Ed25519 key that never leaves the
person minting codes. QUILL verifies the signature offline against a
bundled public key -- no network call, and no way to fabricate a working
code without the private key, unlike a plain settings flag a user could
just edit by hand.

This is a separate trust domain from ``quill/tools/signing.py``'s Quillin
publisher key (different key, different purpose) but reuses that module's
Ed25519 key-file format and CLI (``python -m quill.tools.signing keygen``)
so there is only one keygen implementation in the codebase.

Code shape: ``QUILL-XXXX-XXXX-...`` -- base32 (case-insensitive on redeem)
of ``payload_bytes + 64_byte_signature``, grouped in fours. The signature
alone is ~104 base32 characters, so every code is long regardless of
payload size; the payload itself is kept to a bare ``feature_id|expires``
string to avoid growing it further. Meant to be copy-pasted, not typed by
hand.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

if TYPE_CHECKING:
    from nacl import signing as nacl_signing

CODE_PREFIX = "QUILL-"
_SIGNATURE_LEN = 64
_BUNDLED_PUBLIC_KEY_PATH = Path(__file__).resolve().parent / "unlock-pub.key"


def _read_bundled_public_key() -> str:
    try:
        return _BUNDLED_PUBLIC_KEY_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


PUBLIC_KEY_B64: str = _read_bundled_public_key()


@dataclass(frozen=True, slots=True)
class UnlockCodePayload:
    """What an unlock code grants. ``expires`` is an ISO date string
    (``YYYY-MM-DD``) or ``None`` for a code that never expires.

    Deliberately just ``feature_id|expires`` -- not JSON, and no tester name
    or issued date -- to keep the signed payload (and so the final code) as
    short as possible; a 64-byte Ed25519 signature already makes every code
    long by itself. Who a code was given to is Jeff's own bookkeeping (the
    mint CLI's ``--tester`` flag echoes it back to stdout for his notes) and
    never needs to round-trip through the code itself."""

    feature_id: str
    expires: str | None = None

    def to_bytes(self) -> bytes:
        if "|" in self.feature_id:
            raise ValueError("feature_id must not contain '|'.")
        return f"{self.feature_id}|{self.expires or ''}".encode()

    @classmethod
    def from_bytes(cls, raw: bytes) -> UnlockCodePayload:
        text = raw.decode("utf-8")
        feature_id, _, expires = text.partition("|")
        return cls(feature_id=feature_id, expires=expires or None)


def encode_code(payload_bytes: bytes, signature: bytes) -> str:
    if len(signature) != _SIGNATURE_LEN:
        raise ValueError(f"Ed25519 signature must be {_SIGNATURE_LEN} bytes.")
    raw = payload_bytes + signature
    b32 = base64.b32encode(raw).decode("ascii").rstrip("=")
    groups = [b32[i : i + 4] for i in range(0, len(b32), 4)]
    return CODE_PREFIX + "-".join(groups)


def decode_code(code: str) -> tuple[bytes, bytes]:
    """Return ``(payload_bytes, signature)``. Raises ``ValueError`` on any
    malformed input -- never partial/garbage data."""

    cleaned = code.strip().upper()
    if cleaned.startswith(CODE_PREFIX):
        cleaned = cleaned[len(CODE_PREFIX) :]
    b32 = cleaned.replace("-", "").replace(" ", "")
    if not b32:
        raise ValueError("Empty unlock code.")
    padded = b32 + ("=" * (-len(b32) % 8))
    raw = base64.b32decode(padded)
    if len(raw) <= _SIGNATURE_LEN:
        raise ValueError("Unlock code is too short to contain a signature.")
    return raw[:-_SIGNATURE_LEN], raw[-_SIGNATURE_LEN:]


def mint_code(
    feature_id: str,
    secret_key: nacl_signing.SigningKey,
    *,
    expires: str | None = None,
) -> str:
    """Sign a new unlock code. Called only by the mint CLI -- ``secret_key``
    is never bundled with QUILL itself."""

    payload = UnlockCodePayload(feature_id=feature_id, expires=expires)
    payload_bytes = payload.to_bytes()
    signature = secret_key.sign(payload_bytes).signature
    return encode_code(payload_bytes, signature)


@dataclass(frozen=True, slots=True)
class RedeemResult:
    ok: bool
    feature_id: str | None = None
    error: str | None = None


def _load_public_key(public_key_b64: str) -> nacl_signing.VerifyKey | None:
    from nacl import signing as nacl_signing

    if not public_key_b64:
        return None
    try:
        raw = base64.b64decode(public_key_b64.strip())
    except (ValueError, TypeError):
        return None
    if len(raw) != 32:
        return None
    return nacl_signing.VerifyKey(raw)


def redeem_code(
    code: str,
    *,
    public_key_b64: str | None = None,
    today: date | None = None,
) -> RedeemResult:
    """Verify a code's signature and expiry. Fail-closed: never raises."""

    try:
        payload_bytes, signature = decode_code(code)
    except ValueError as exc:
        return RedeemResult(False, error=f"Not a valid unlock code: {exc}")

    try:
        from nacl.exceptions import BadSignatureError
    except ModuleNotFoundError:
        return RedeemResult(False, error="PyNaCl is not installed")

    verify_key = _load_public_key(public_key_b64 if public_key_b64 is not None else PUBLIC_KEY_B64)
    if verify_key is None:
        return RedeemResult(False, error="No unlock-code public key is bundled with QUILL.")

    try:
        verify_key.verify(payload_bytes, signature)
    except BadSignatureError:
        return RedeemResult(False, error="Signature does not match -- not a genuine unlock code.")

    try:
        payload = UnlockCodePayload.from_bytes(payload_bytes)
    except UnicodeDecodeError:
        return RedeemResult(False, error="Unlock code payload is malformed.")

    if not payload.feature_id:
        return RedeemResult(False, error="Unlock code names no feature.")

    if payload.expires:
        try:
            expires_date = date.fromisoformat(payload.expires)
        except ValueError:
            return RedeemResult(False, error="Unlock code has an unreadable expiry date.")
        if (today or date.today()) > expires_date:
            return RedeemResult(False, error=f"This unlock code expired on {payload.expires}.")

    return RedeemResult(True, feature_id=payload.feature_id)


def unlock_codes_path() -> Path:
    return app_data_dir() / "unlock_codes.json"


@dataclass(slots=True)
class UnlockCodeStore:
    """Persists the raw redeemed code *strings*, not a derived boolean --
    every read re-verifies each code's signature and expiry, so editing the
    JSON file by hand cannot grant a feature that was never validly
    unlocked."""

    codes: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> UnlockCodeStore:
        raw = read_json(unlock_codes_path(), default={})
        if not isinstance(raw, dict):
            return cls()
        codes = raw.get("codes")
        if not isinstance(codes, list):
            return cls()
        return cls(codes=[str(c) for c in codes if isinstance(c, str)])

    def save(self) -> None:
        write_json_atomic(
            unlock_codes_path(),
            {"codes": self.codes},
            base=app_data_dir(),
        )

    def add(self, code: str) -> None:
        if code not in self.codes:
            self.codes.append(code)

    def unlocked_feature_ids(self, *, today: date | None = None) -> frozenset[str]:
        unlocked: set[str] = set()
        for code in self.codes:
            result = redeem_code(code, today=today)
            if result.ok and result.feature_id:
                unlocked.add(result.feature_id)
        return frozenset(unlocked)
