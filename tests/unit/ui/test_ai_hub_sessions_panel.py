"""Smoke + behavior tests for the AI Hub Sessions tab (Phase 4 fold).

The standalone "AI Session Branches" menu item folded into the Hub. These tests
drive the panel under a wx.App: it builds, and Browse handles the empty-session
state by announcing rather than opening a browser.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

from quill.core.ai.copilot_preferences import (
    CopilotPreferences,
    load_copilot_preferences,
)
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.ai_hub_sessions_panel import SessionsPanel, create_sessions_panel  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


def _make(wx_app):
    frame = wx.Frame(None)
    announced: list[str] = []
    panel = SessionsPanel(frame, parent_dialog=frame, announce=announced.append)
    return frame, panel, announced


def test_panel_builds_with_browse_button(wx_app):
    frame, panel, _announced = _make(wx_app)
    try:
        assert panel.browse_btn.GetLabel().startswith("&Browse")
        assert panel.browse_btn.GetName() == "Browse AI session branches"
    finally:
        frame.Destroy()


def test_browse_with_no_sessions_announces_empty_state(wx_app, monkeypatch):
    frame, panel, announced = _make(wx_app)
    try:
        monkeypatch.setattr(
            "quill.core.ai.sessions.most_recent_session",
            lambda *, directory=None: None,
            raising=True,
        )
        shown: list[str] = []
        monkeypatch.setattr(
            "quill.ui.dialog_contract.show_message_box",
            lambda *a, **k: shown.append(a[0]),
        )
        panel._on_browse(None)
        assert any("No saved AI writing sessions" in m for m in announced)
        assert shown and "No saved AI writing sessions" in shown[0]
    finally:
        frame.Destroy()


def test_browse_uses_the_supplied_app_session_directory(wx_app, tmp_path, monkeypatch):
    directory = tmp_path / "lite-ai-sessions"
    frame = wx.Frame(None)
    panel = SessionsPanel(
        frame,
        parent_dialog=frame,
        announce=lambda _message: None,
        directory=directory,
    )
    seen: list[object] = []
    monkeypatch.setattr(
        "quill.core.ai.sessions.most_recent_session",
        lambda *, directory=None: seen.append(directory),
    )
    monkeypatch.setattr("quill.ui.dialog_contract.show_message_box", lambda *a, **k: None)
    try:
        panel._on_browse(None)
        assert seen == [directory]
    finally:
        frame.Destroy()


def test_lite_panel_uses_its_app_data_directory(wx_app, tmp_path):
    frame = wx.Frame(None)
    panel = create_sessions_panel(
        frame,
        parent_dialog=frame,
        announce=lambda _message: None,
        app_name="QUILL Lite",
        app_context=type("LiteContext", (), {"data_dir": tmp_path})(),
    )
    try:
        assert panel._directory == tmp_path / "ai-sessions"
        assert panel.keep_sessions.GetValue() is False
        assert panel.long_context.GetValue() is False
        assert panel.long_context.IsEnabled() is False
        assert panel.share_skills.GetValue() is False
        assert panel.auto_tier.GetName() == "GitHub Copilot Auto model priority"
    finally:
        frame.Destroy()


def test_options_are_saved_only_when_explicitly_enabled(wx_app, tmp_path):
    frame = wx.Frame(None)
    panel = SessionsPanel(
        frame,
        parent_dialog=frame,
        announce=lambda _message: None,
        data_dir=tmp_path,
    )
    try:
        panel.auto_tier.SetSelection(0)
        panel.keep_sessions.SetValue(True)
        panel.long_context.SetValue(True)
        panel.share_skills.SetValue(True)
        panel.save_preferences()
        assert load_copilot_preferences(tmp_path) == CopilotPreferences(
            auto_tier="efficiency",
            keep_sessions=True,
            long_context=True,
            share_enabled_skills=True,
        )
    finally:
        frame.Destroy()


def test_save_failure_is_announced_and_reported(wx_app, tmp_path, monkeypatch):
    frame = wx.Frame(None)
    said: list[str] = []
    panel = SessionsPanel(
        frame,
        parent_dialog=frame,
        announce=said.append,
        data_dir=tmp_path,
    )

    def fail_save(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("quill.ui.ai_hub_sessions_panel.save_copilot_preferences", fail_save)
    try:
        assert panel.save_preferences() is False
        assert panel.status.GetLabel() == (
            "Copilot options could not be saved. Check the app data folder and try again."
        )
        assert said == [panel.status.GetLabel()]
    finally:
        frame.Destroy()


def test_saved_session_resume_is_one_explicit_next_task_choice(wx_app, tmp_path):
    frame = wx.Frame(None)
    panel = SessionsPanel(
        frame,
        parent_dialog=frame,
        announce=lambda _message: None,
        data_dir=tmp_path,
    )
    try:
        panel._sessions = (type("SessionInfo", (), {"session_id": "saved-1"})(),)
        panel.sessions_list.Append("saved-1 - 2026-02-01 12:00")
        panel.sessions_list.SetSelection(0)
        panel._on_resume_selected(None)
        panel.save_preferences()

        assert panel.keep_sessions.GetValue() is True
        assert load_copilot_preferences(tmp_path).resume_session_id == "saved-1"
    finally:
        frame.Destroy()


def test_long_context_requires_session_retention(wx_app, tmp_path):
    frame = wx.Frame(None)
    panel = SessionsPanel(
        frame,
        parent_dialog=frame,
        announce=lambda _message: None,
        data_dir=tmp_path,
    )
    try:
        assert panel.long_context.IsEnabled() is False
        panel.keep_sessions.SetValue(True)
        panel._on_keep_sessions_changed(None)
        assert panel.long_context.IsEnabled() is True
        panel.long_context.SetValue(True)
        panel.keep_sessions.SetValue(False)
        panel._on_keep_sessions_changed(None)
        assert panel.long_context.IsEnabled() is False
        assert panel.long_context.GetValue() is False
        panel.save_preferences()
        assert load_copilot_preferences(tmp_path).long_context is False
    finally:
        frame.Destroy()


def test_session_deletion_requires_selection_and_explicit_confirmation(wx_app):
    frame, panel, _announced = _make(wx_app)
    try:
        panel._sessions = (type("SessionInfo", (), {"session_id": "saved-1"})(),)
        panel.sessions_list.Append("saved-1 - 2026-02-01 12:00")
        panel.sessions_list.SetSelection(0)
        panel._on_session_selection(None)
        assert panel.delete_session_btn.IsEnabled() is False

        panel.confirm_delete.SetValue(True)
        panel._on_session_selection(None)
        assert panel.delete_session_btn.IsEnabled() is True
    finally:
        frame.Destroy()


def test_lite_panel_requires_its_app_data_directory(wx_app):
    frame = wx.Frame(None)
    try:
        with pytest.raises(RuntimeError, match="app data directory"):
            create_sessions_panel(
                frame,
                parent_dialog=frame,
                announce=lambda _message: None,
                app_name="QUILL Lite",
                app_context=None,
            )
    finally:
        frame.Destroy()
