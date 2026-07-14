from __future__ import annotations

import sys
import types

from quill.core.speech import hf_auth


def test_looks_rate_limited_detects_429_and_phrases() -> None:
    assert hf_auth.looks_rate_limited(Exception("HTTP Error 429: Too Many Requests"))
    assert hf_auth.looks_rate_limited("you hit the rate limit")
    assert not hf_auth.looks_rate_limited(Exception("404 Not Found"))
    assert not hf_auth.looks_rate_limited("connection reset")


def _fake_credential_store(store: dict[str, str]) -> types.ModuleType:
    mod = types.ModuleType("quill.platform.windows.credential_store")
    mod.load_secret = lambda name: store.get(name, "")  # type: ignore[attr-defined]
    mod.save_secret = lambda name, secret: store.__setitem__(name, secret)  # type: ignore[attr-defined]
    mod.delete_secret = lambda name: store.pop(name, None)  # type: ignore[attr-defined]
    return mod


def test_token_round_trip(monkeypatch) -> None:
    store: dict[str, str] = {}
    monkeypatch.setitem(
        sys.modules, "quill.platform.windows.credential_store", _fake_credential_store(store)
    )
    assert hf_auth.load_hf_token() == ""
    hf_auth.save_hf_token("  hf_abc123  ")
    assert store[hf_auth.HF_TOKEN_CRED] == "hf_abc123"  # trimmed
    assert hf_auth.load_hf_token() == "hf_abc123"
    # Blank clears it.
    hf_auth.save_hf_token("")
    assert hf_auth.HF_TOKEN_CRED not in store
    assert hf_auth.load_hf_token() == ""


def test_load_hf_token_swallows_store_errors(monkeypatch) -> None:
    broken = types.ModuleType("quill.platform.windows.credential_store")

    def _boom(_name):
        raise RuntimeError("locked")

    broken.load_secret = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quill.platform.windows.credential_store", broken)
    assert hf_auth.load_hf_token() == ""
