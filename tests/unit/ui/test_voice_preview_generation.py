"""Starting a new voice preview must stop/supersede the previous one."""

from __future__ import annotations

import time

import pytest
import wx

from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    # Without a real wx.App().MainLoop() running (never entered in these unit
    # tests), wx.Yield()/YieldIfNeeded() is a no-op for wx.Timer-backed
    # callbacks (wx.CallLater) unless an event loop object is registered as
    # active -- wx.CallAfter's ProcessPendingEvents path doesn't need this,
    # but the generating-cue tests below poll for a real CallLater firing.
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    yield app
    wx.EventLoop.SetActive(None)
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


def test_generating_cue_fires_once_after_the_delay(wx_app, monkeypatch) -> None:
    from quill.core.sound_events import SoundEvent

    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {"voice_preview_announce_generating": True})()
    posted: list[str] = []
    announced: list[str] = []

    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: None)
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: announced.append(a[0]))
    monkeypatch.setattr(
        "quill.ui.main_frame.post_sound", lambda event_id: posted.append(event_id)
    )

    frame._stop_active_voice_preview()
    my_generation = frame._preview_generation
    frame._preview_cue_timer = wx.CallLater(50, frame._fire_generating_cue, my_generation)

    for _ in range(30):
        wx.YieldIfNeeded()
        time.sleep(0.02)
        if posted:
            break

    assert posted == [SoundEvent.VOICE_PREVIEW_GENERATING.value]
    assert announced == ["Generating preview, please wait."]
    frame.frame.Destroy()


def test_generating_cue_does_not_fire_if_superseded_first(wx_app, monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {"voice_preview_announce_generating": True})()
    posted: list[str] = []
    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: None)
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: None)
    monkeypatch.setattr(
        "quill.ui.main_frame.post_sound", lambda event_id: posted.append(event_id)
    )

    frame._stop_active_voice_preview()
    stale_generation = frame._preview_generation
    frame._preview_cue_timer = wx.CallLater(50, frame._fire_generating_cue, stale_generation)
    # Supersede before the timer fires.
    frame._stop_active_voice_preview()

    for _ in range(30):
        wx.YieldIfNeeded()
        time.sleep(0.02)

    assert posted == []
    frame.frame.Destroy()


def test_generating_cue_is_cancelled_when_synthesis_finishes_first(
    wx_app, monkeypatch
) -> None:
    """A fast preview (e.g. eSpeak) that finishes well within the 400ms cue
    delay must not leave a stray cue timer behind: ``_synth_done`` must
    cancel it, or the cue would fire after "Preview finished" was already
    reported."""
    from pathlib import Path

    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type(
        "S",
        (),
        {
            "voice_preview_announce_generating": True,
            "read_aloud_espeak_executable": "",
            "read_aloud_espeak_rate": 175,
        },
    )()
    # MainFrame.__new__ bypasses __init__, so this __init__-set attribute
    # (main_frame.py:1098) is missing; without it, _finish_background_task's
    # completion path raises AttributeError before on_success ever runs.
    frame._status_page_live_updates = False
    posted: list[str] = []

    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: None)
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: None)
    monkeypatch.setattr(
        "quill.ui.main_frame.post_sound", lambda event_id: posted.append(event_id)
    )
    monkeypatch.setattr(
        "quill.ui.main_frame.discover_espeak_executable",
        lambda *_a, **_k: Path("espeak.exe"),
    )
    monkeypatch.setattr(
        "quill.ui.main_frame.synthesize_with_espeak", lambda *a, **k: None
    )
    monkeypatch.setattr(MainFrame, "_play_preview_asset", lambda _self, _path: None)

    # A synthesis engine mocked to return instantly: the background thread
    # (and its wx.CallAfter completion) should race ahead of the 400ms cue
    # timer started right before dispatch, and _synth_done must cancel it.
    frame._preview_voice("espeak", "voice-a", live=True)

    for _ in range(30):
        wx.YieldIfNeeded()
        time.sleep(0.02)

    assert posted == []
    frame.frame.Destroy()
