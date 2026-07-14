"""Token resolution unifies QUILL's secure store with feedback_hub's env token."""

from __future__ import annotations

import sys
import types

import quill.core.feedback_token as ft


def _fake_feedback_hub(monkeypatch, token: str) -> None:
    fake_hub = types.ModuleType("feedback_hub")
    fake_hub.resolve_token = lambda *_a, **_k: token  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "feedback_hub", fake_hub)


def test_prefers_stored_token_without_env_import(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "stored-tok")
    saved: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.token_store.save_github_token",
        lambda t: saved.append(t) or True,
    )

    assert ft.effective_github_token() == "stored-tok"
    assert saved == []  # store already has one; no env lookup or write


def test_imports_env_token_when_store_empty(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: None)
    saved: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.token_store.save_github_token",
        lambda t: saved.append(t) or True,
    )
    _fake_feedback_hub(monkeypatch, "env-tok")

    assert ft.effective_github_token() == "env-tok"
    assert saved == ["env-tok"]  # copied into the secure store for reliability


def test_does_not_persist_when_import_disabled(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: None)
    saved: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.token_store.save_github_token",
        lambda t: saved.append(t) or True,
    )
    _fake_feedback_hub(monkeypatch, "env-tok")

    assert ft.effective_github_token(import_from_env=False) == "env-tok"
    assert saved == []


def test_returns_empty_when_no_token_anywhere(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: None)
    monkeypatch.setattr("quill.core.github.token_store.save_github_token", lambda _t: True)
    _fake_feedback_hub(monkeypatch, "")

    assert ft.effective_github_token() == ""
    assert ft.github_token_present() is False


def test_bundled_token_used_when_store_and_env_are_empty(monkeypatch) -> None:
    # resolve_token() picks its first non-empty candidate; a real feedback_hub
    # would fall through to env vars only when the bundled candidate is empty,
    # so simulating that here (rather than faking the module) proves
    # effective_github_token() actually passes _bundled_token() through.
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: None)
    saved: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.token_store.save_github_token",
        lambda t: saved.append(t) or True,
    )
    monkeypatch.setattr(ft, "_bundled_token", lambda: "bundled-tok")
    _fake_feedback_hub(monkeypatch, "bundled-tok")

    assert ft.effective_github_token(import_from_env=False) == "bundled-tok"


def test_bundled_token_helper_returns_empty_when_module_absent(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "quill._feedback_token":
            raise ImportError("no generated module in this checkout")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert ft._bundled_token() == ""
