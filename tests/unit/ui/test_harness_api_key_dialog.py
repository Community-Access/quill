"""Behavioral tests for HarnessApiKeyDialog: the API-key onboarding gap for
OpenAI Agents SDK / Claude Agent SDK found while fixing the AI Setup Wizard
stuck-active bug (#915's underlying crash)."""

from __future__ import annotations

import pytest
import wx

from quill.ui.harness_api_key_dialog import HarnessApiKeyDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make_dialog(wx_app, monkeypatch, *, existing_key: str = ""):
    store: dict[str, str] = {}
    if existing_key:
        store["openai_agents"] = existing_key
    monkeypatch.setattr(
        "quill.core.assistant_ai.save_provider_api_key",
        lambda p, k: store.__setitem__(p, k) or True,
    )
    monkeypatch.setattr("quill.core.assistant_ai.load_provider_api_key", lambda p: store.get(p, ""))
    monkeypatch.setattr(
        "quill.core.assistant_ai.clear_provider_api_key", lambda p: store.pop(p, None)
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    frame = wx.Frame(None)
    dlg = HarnessApiKeyDialog(
        frame, "openai_agents", "OpenAI Agents SDK", lambda *a, **k: wx.ID_CANCEL
    )
    return dlg, frame, store


def test_save_persists_applies_and_clears_the_field(wx_app, monkeypatch) -> None:
    dlg, frame, store = _make_dialog(wx_app, monkeypatch)

    dlg.key_ctrl.SetValue("sk-abc123")
    dlg._on_save(None)

    assert store["openai_agents"] == "sk-abc123"
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-abc123"
    assert dlg.key_ctrl.GetValue() == ""
    dlg.dialog.Destroy()
    frame.Destroy()


def test_save_with_empty_field_does_not_persist(wx_app, monkeypatch) -> None:
    dlg, frame, store = _make_dialog(wx_app, monkeypatch)

    dlg._on_save(None)

    assert "openai_agents" not in store
    dlg.dialog.Destroy()
    frame.Destroy()


def test_remove_clears_stored_key(wx_app, monkeypatch) -> None:
    dlg, frame, store = _make_dialog(wx_app, monkeypatch, existing_key="sk-existing")
    assert dlg.remove_btn.IsEnabled()

    dlg._on_remove(None)

    assert "openai_agents" not in store
    assert not dlg.remove_btn.IsEnabled()
    dlg.dialog.Destroy()
    frame.Destroy()


def test_remove_disabled_when_no_key_saved(wx_app, monkeypatch) -> None:
    dlg, frame, _store = _make_dialog(wx_app, monkeypatch)
    assert not dlg.remove_btn.IsEnabled()
    dlg.dialog.Destroy()
    frame.Destroy()


def test_existing_key_is_reported_in_status_on_open(wx_app, monkeypatch) -> None:
    dlg, frame, _store = _make_dialog(wx_app, monkeypatch, existing_key="sk-existing")
    assert "already saved" in dlg.status.GetLabel()
    dlg.dialog.Destroy()
    frame.Destroy()
