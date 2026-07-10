"""Tests for the unified credential store's portable-mode macOS path (#35).

Portable mode has no DPAPI-equivalent single-folder store off Windows. On
macOS the login Keychain is the best available store, so a portable-mode Mac
build now routes load/save/delete to the Keychain with a warning instead of
silently dropping the credential. The Keychain helpers are stubbed here so the
test runs on any host (the real Keychain CLI is macOS-only).
"""

from __future__ import annotations

import logging

import pytest

import quill.platform.windows.credential_store as cs

_CRED = "quill-openrouter-api-key"


@pytest.fixture(autouse=True)
def _portable_macos(monkeypatch):
    monkeypatch.setattr(cs, "_IS_WINDOWS", False)
    monkeypatch.setattr(cs, "_IS_MACOS", True)
    monkeypatch.setattr(cs, "is_portable_mode", lambda: True)
    # Ensure the env-var override never preempts the store under test.
    for env in ("QUILL_OPENROUTER_KEY", "QUILL_ASSISTANT_KEY"):
        monkeypatch.delenv(env, raising=False)
    yield


def test_portable_macos_load_delegates_to_keychain_with_warning(monkeypatch, caplog):
    monkeypatch.setattr(cs, "_macos_keychain_load", lambda name: f"kc:{name}")
    with caplog.at_level(logging.WARNING, logger=cs.logger.name):
        assert cs.load_secret(_CRED) == f"kc:{_CRED}"
    assert any("Windows-only" in r.message for r in caplog.records)


def test_portable_macos_save_delegates_to_keychain(monkeypatch):
    saved: dict[str, str] = {}

    def _save(name: str, secret: str) -> None:
        saved[name] = secret

    monkeypatch.setattr(cs, "_macos_keychain_save", _save)
    cs.save_secret(_CRED, "hunter2")
    assert saved == {_CRED: "hunter2"}


def test_portable_macos_save_empty_clears_via_keychain(monkeypatch):
    cleared: list[str] = []

    def _save(name: str, secret: str) -> None:
        if not secret:
            cleared.append(name)

    monkeypatch.setattr(cs, "_macos_keychain_save", _save)
    cs.save_secret(_CRED, "")
    assert cleared == [_CRED]


def test_portable_macos_delete_delegates_to_keychain(monkeypatch):
    monkeypatch.setattr(cs, "_macos_keychain_delete", lambda name: True)
    assert cs.delete_secret(_CRED) is True


def test_portable_other_platform_drops_without_warning(monkeypatch, caplog):
    monkeypatch.setattr(cs, "_IS_MACOS", False)
    with caplog.at_level(logging.WARNING, logger=cs.logger.name):
        assert cs.load_secret(_CRED) == ""
    assert not any("Windows-only" in r.message for r in caplog.records)
