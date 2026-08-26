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


# -- submitting without a token at all -------------------------------------------


def test_reports_can_be_sent_with_no_token_when_a_server_is_configured(monkeypatch):
    """The point of the server: a build that posts to it ships no credential.

    Every installer currently compiles a fine-grained token in, so anybody who
    unzips one has it. Issues-only scope on one repository bounds that to issue
    spam, which is why it was tolerable -- but it stops being necessary once
    the server holds the credential instead.
    """
    from quill.core import feedback_token as module

    monkeypatch.setattr(module, "effective_github_token", lambda **_: "")
    monkeypatch.delenv("QUILL_FEEDBACK_SERVER_URL", raising=False)

    assert module.feedback_server_url()
    assert module.can_submit_reports() is True


def test_with_no_server_and_no_token_there_is_nothing_to_offer(monkeypatch):
    """Then Report a Bug must fall back to the web form rather than opening a
    dialog whose Submit button cannot work."""
    from quill.core import feedback_token as module

    monkeypatch.setenv("QUILL_FEEDBACK_SERVER_URL", "")
    monkeypatch.setattr(module, "github_token_present", lambda: False)

    assert module.feedback_server_url() == ""
    assert module.can_submit_reports() is False


def test_a_token_alone_is_still_enough(monkeypatch):
    """A fork with no server of its own keeps working."""
    from quill.core import feedback_token as module

    monkeypatch.setenv("QUILL_FEEDBACK_SERVER_URL", "")
    monkeypatch.setattr(module, "github_token_present", lambda: True)

    assert module.can_submit_reports() is True


def test_the_server_url_is_overridable(monkeypatch):
    """The hostname is not settled -- see section 6 of the feedback redesign --
    so it must never be something only a rebuild can change."""
    from quill.core import feedback_token as module

    monkeypatch.setenv("QUILL_FEEDBACK_SERVER_URL", "https://example.test/submit/feedback")
    assert module.feedback_server_url() == "https://example.test/submit/feedback"


def test_submission_kwargs_offers_both_transports(monkeypatch):
    """One place, so the two dialog call sites cannot drift. feedback-hub
    prefers server_url when both are present."""
    from quill.core import feedback_token as module

    monkeypatch.delenv("QUILL_FEEDBACK_SERVER_URL", raising=False)
    monkeypatch.setattr(module, "effective_github_token", lambda **_: "tok")

    kwargs = module.submission_kwargs()
    assert set(kwargs) == {"server_url", "github_token"}
    assert kwargs["server_url"].startswith("https://")
