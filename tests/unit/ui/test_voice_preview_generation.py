"""Starting a new voice preview must stop/supersede the previous one."""

from __future__ import annotations

import time

import pytest
import wx

from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_second_preview_supersedes_the_first(wx_app, monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)  # bypass __init__: only exercising _preview_voice
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {})()
    # MainFrame.__new__ bypasses __init__, so this __init__-set attribute
    # (main_frame.py:1098) is missing; without it, _finish_background_task's
    # completion path raises AttributeError before on_success ever runs.
    frame._status_page_live_updates = False
    calls: list[str] = []

    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: calls.append(f"status:{a[0]}"))
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: calls.append(f"announce:{a[0]}"))

    def fake_play(_self, path):
        calls.append(f"play:{path}")

    monkeypatch.setattr(MainFrame, "_play_preview_asset", fake_play)
    monkeypatch.setattr(
        frame, "_voice_preview_sample_path", lambda *a, **k: __import__("pathlib").Path("a.wav")
    )

    # First preview (sample playback -- runs on a background thread).
    frame._preview_voice("piper", "voice-a", live=False)
    # Immediately start a second preview before the first's background thread
    # has necessarily finished; the first's generation must now be stale.
    frame._preview_voice("piper", "voice-b", live=False)

    # Let both background threads (and their wx.CallAfter completions) run.
    for _ in range(20):
        wx.YieldIfNeeded()
        time.sleep(0.02)

    finished_count = sum(1 for c in calls if c == "status:Preview finished")
    assert finished_count == 1, calls
    frame.frame.Destroy()
