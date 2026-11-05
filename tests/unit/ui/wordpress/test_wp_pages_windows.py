"""The real Schedule Publish window and the host's repeating timer, built with wx."""

from __future__ import annotations

from typing import Any

import wx

from quill.ui import wordpress_schedule_dialog as sdlg
from quill.ui.main_frame_wordpress import start_wx_repeating


def test_the_schedule_window_returns_what_was_typed(wx_session_app) -> None:
    frame = wx.Frame(None)
    seen: list[Any] = []

    def show_modal(dialog: Any, label: str) -> int:
        seen.append(dialog)
        assert label == "Schedule Publish"
        assert dialog.zone.GetStringSelection() == "UTC"
        assert dialog.error.GetValue() == "Choose a publish time that is in the future."
        dialog.time.SetValue(" 16:15 ")
        return wx.ID_OK

    try:
        answer = sdlg.ask_schedule(
            frame,
            show_modal,
            title="Schedule Publish",
            purpose="When.",
            date_text="2099-01-02",
            time_text="09:00",
            zones=["This computer's time zone", "UTC"],
            zone_index=1,
            error="Choose a publish time that is in the future.",
        )
    finally:
        frame.Destroy()
    assert answer == sdlg.ScheduleAnswer("2099-01-02", "16:15", 1)
    assert seen


def test_cancelling_the_schedule_window_is_none(wx_session_app) -> None:
    frame = wx.Frame(None)
    try:
        answer = sdlg.ask_schedule(
            frame,
            lambda _d, _l: wx.ID_CANCEL,
            title="Schedule Publish",
            purpose="When.",
            date_text="",
            time_text="",
            zones=["UTC"],
        )
    finally:
        frame.Destroy()
    assert answer is None


def test_the_repeating_timer_calls_back_until_stopped(wx_session_app, monkeypatch) -> None:
    made: list[Any] = []

    class RecordingTimer(wx.Timer):
        def __init__(self, owner: Any) -> None:
            super().__init__(owner)
            made.append(self)

    monkeypatch.setattr(wx, "Timer", RecordingTimer)
    frame = wx.Frame(None)
    calls: list[int] = []
    stop = start_wx_repeating(frame, 120, lambda: calls.append(1))
    try:
        timer = made[0]
        assert timer.IsRunning() and timer.GetInterval() == 120_000
        timer.Notify()  # what wx does when the interval passes
        assert calls == [1]
        stop()
        assert not timer.IsRunning()
        timer.Notify()
        assert calls == [1]
        stop()  # stopping twice is harmless
    finally:
        stop()
        frame.Destroy()


def test_the_timer_stops_itself_when_its_window_is_destroyed(wx_session_app, monkeypatch):
    made: list[Any] = []

    class RecordingTimer(wx.Timer):
        def __init__(self, owner: Any) -> None:
            super().__init__(owner)
            made.append(self)

    monkeypatch.setattr(wx, "Timer", RecordingTimer)
    parent = wx.Frame(None)
    try:
        owner = wx.Panel(parent)
        start_wx_repeating(owner, 120, lambda: None)
        owner.Destroy()  # a child window is destroyed at once
        assert not made[0].IsRunning()
    finally:
        parent.Destroy()
