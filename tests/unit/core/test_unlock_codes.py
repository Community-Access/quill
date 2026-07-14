"""Unlock codes: mint/verify round trip, tamper/expiry rejection, and the
atomic-JSON redeemed-code store."""

from __future__ import annotations

import base64
from datetime import date, timedelta
from pathlib import Path

import pytest

from quill.core import paths

pytest.importorskip("nacl", reason="PyNaCl (the [signing] extra) is not installed")
from nacl import signing as nacl_signing  # noqa: E402

from quill.core.unlock_codes import (  # noqa: E402
    CODE_PREFIX,
    UnlockCodeStore,
    decode_code,
    encode_code,
    mint_code,
    redeem_code,
)


@pytest.fixture
def data_dir_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    data_dir = fake_home / "quill-data"
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return data_dir


@pytest.fixture
def keypair() -> tuple[nacl_signing.SigningKey, nacl_signing.VerifyKey]:
    sk = nacl_signing.SigningKey.generate()
    return sk, sk.verify_key


def _pubkey_b64(vk: nacl_signing.VerifyKey) -> str:
    return base64.b64encode(bytes(vk)).decode()


def test_mint_and_redeem_round_trip(keypair):
    sk, vk = keypair
    code = mint_code("core.adp", sk)
    result = redeem_code(code, public_key_b64=_pubkey_b64(vk))
    assert result.ok
    assert result.feature_id == "core.adp"


def test_code_has_expected_prefix_and_is_decodable(keypair):
    sk, _vk = keypair
    code = mint_code("core.adp", sk)
    assert code.startswith("QUILL-")
    payload_bytes, signature = decode_code(code)
    assert len(signature) == 64
    assert b"core.adp" in payload_bytes


def test_redeem_rejects_wrong_public_key(keypair):
    sk, _vk = keypair
    other_vk = nacl_signing.SigningKey.generate().verify_key
    code = mint_code("core.adp", sk)
    result = redeem_code(code, public_key_b64=_pubkey_b64(other_vk))
    assert not result.ok
    assert result.feature_id is None


def test_redeem_rejects_tampered_code(keypair):
    sk, vk = keypair
    code = mint_code("core.adp", sk)
    # Flip the first body character (right after the "QUILL-" prefix), never
    # the last: base32 without padding can leave unused zero-padding bits in
    # the final character, which base64.b32decode truncates rather than
    # validates -- flipping only those bits (a real, if rare, outcome when
    # the character was already the all-zero symbol) silently round-trips to
    # the *same* bytes, leaving the signature untouched and this test flaky.
    # The first character always encodes real payload bits.
    prefix_len = len(CODE_PREFIX)
    first = code[prefix_len]
    tampered = code[:prefix_len] + ("A" if first != "A" else "B") + code[prefix_len + 1 :]
    result = redeem_code(tampered, public_key_b64=_pubkey_b64(vk))
    assert not result.ok


def test_redeem_rejects_garbage_input():
    result = redeem_code("not-a-real-code")
    assert not result.ok
    assert result.error


def test_redeem_honors_expiry(keypair):
    sk, vk = keypair
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    code = mint_code("core.adp", sk, expires=yesterday)
    result = redeem_code(code, public_key_b64=_pubkey_b64(vk))
    assert not result.ok
    assert "expired" in (result.error or "")


def test_redeem_accepts_not_yet_expired(keypair):
    sk, vk = keypair
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    code = mint_code("core.adp", sk, expires=tomorrow)
    result = redeem_code(code, public_key_b64=_pubkey_b64(vk))
    assert result.ok


def test_encode_decode_round_trip():
    payload = b"core.adp|"
    signature = b"\x00" * 64
    code = encode_code(payload, signature)
    decoded_payload, decoded_signature = decode_code(code)
    assert decoded_payload == payload
    assert decoded_signature == signature


def test_decode_rejects_too_short_input():
    with pytest.raises(ValueError):
        decode_code("QUILL-AAAA")


class TestUnlockCodeStore:
    def test_load_missing_file_returns_empty(self, data_dir_env: Path):
        store = UnlockCodeStore.load()
        assert store.codes == []

    def test_save_and_load_round_trip(self, data_dir_env: Path):
        store = UnlockCodeStore()
        store.add("QUILL-SOMETHING")
        store.save()
        reloaded = UnlockCodeStore.load()
        assert reloaded.codes == ["QUILL-SOMETHING"]

    def test_add_is_idempotent(self):
        store = UnlockCodeStore()
        store.add("QUILL-X")
        store.add("QUILL-X")
        assert store.codes == ["QUILL-X"]

    def test_unlocked_feature_ids_reverifies_every_code(self, keypair, monkeypatch):
        sk, vk = keypair
        monkeypatch.setattr("quill.core.unlock_codes.PUBLIC_KEY_B64", _pubkey_b64(vk))
        good = mint_code("core.adp", sk)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        expired = mint_code("core.other", sk, expires=yesterday)
        store = UnlockCodeStore(codes=[good, expired, "garbage"])
        unlocked = store.unlocked_feature_ids()
        assert unlocked == frozenset({"core.adp"})
