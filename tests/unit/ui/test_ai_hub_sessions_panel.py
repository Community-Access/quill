"""Smoke + behavior tests for the AI Hub Sessions tab (Phase 4 fold).

The standalone "AI Session Branches" menu item folded into the Hub. These tests
drive the panel under a wx.App: it builds, and Browse handles the empty-session
state by announcing rather than opening a browser.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

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
