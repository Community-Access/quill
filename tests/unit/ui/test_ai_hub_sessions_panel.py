"""Smoke + behavior tests for the AI Hub Sessions tab (Phase 4 fold).

The standalone "AI Session Branches" menu item folded into the Hub. These tests
drive the panel under a wx.App: it builds, and Browse handles the empty-session
state by announcing rather than opening a browser.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.ai_hub_sessions_panel import SessionsPanel  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
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
            "quill.core.ai.sessions.most_recent_session", lambda: None, raising=True
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
