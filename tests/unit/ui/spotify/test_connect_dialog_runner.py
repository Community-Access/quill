"""Connect to Spotify runs its sign-in through QuillTaskManager's real signature.

The 2026-11-04 report ("it says it is opening my browser, then nothing
happens") was this call: ``submit(work, on_success=..., name=...)`` against a
``submit(name, func, ...)`` signature, which raised before the browser could
open. These tests use the real task manager, so a signature drift fails here.
"""

from __future__ import annotations

import threading

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


class _Done(Exception):
    pass


def test_connect_submits_to_the_real_task_manager(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    shared_wx_app()
    from quill.stability.task_manager import TaskManager
    from quill.ui.spotify import connect_dialog as cd

    ran = threading.Event()

    def fake_sign_in(client_id, *, safe_mode=False):
        ran.set()
        raise _Done("stop here")

    monkeypatch.setattr(cd, "perform_sign_in", fake_sign_in)
    said: list[str] = []
    manager = TaskManager()
    frame = wx.Frame(None)
    try:
        dialog = cd.SpotifyConnectDialog(frame, announce=said.append, task_runner=manager)
        dialog._client_id.SetValue("clientid1234")
        dialog._on_connect(None)  # must not raise
        assert ran.wait(10), "the sign-in never started"
        for _ in range(200):
            wx.Yield()
            if said and "Could not connect" in said[-1]:
                break
            threading.Event().wait(0.02)
        assert said[0].startswith("Opening your browser")
        assert said[-1].startswith("Could not connect to Spotify: stop here")
        assert dialog._connect.IsEnabled()
        dialog.Destroy()
    finally:
        frame.Destroy()
        manager.shutdown(wait=False, cancel_pending=True)


def test_the_dialog_shows_the_exact_redirect_address(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    shared_wx_app()
    from quill.core.spotify.auth import DEFAULT_REDIRECT_URI
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.spotify.connect_dialog import SpotifyConnectDialog

    ensure_help_provider(wx)  # SetHelpText stores nothing without a provider

    frame = wx.Frame(None)
    try:
        dialog = SpotifyConnectDialog(frame, announce=lambda _t: None)
        assert dialog._redirect.GetValue() == DEFAULT_REDIRECT_URI
        assert "127.0.0.1" in dialog._redirect.GetHelpText()
        dialog.Destroy()
    finally:
        frame.Destroy()
