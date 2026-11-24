"""FUX-08: hearing a setting before keeping it (quill/ui/setting_preview.py)."""

from __future__ import annotations

import pytest

from quill.ui.setting_preview import (
    NOTHING_HEARD,
    SOUNDS_OFF,
    PreviewSequence,
    PreviewStep,
    edge_step,
    feedback_step,
)


class _Timer:
    def __init__(self, delay, fn, *args) -> None:
        self.delay, self.fn, self.args, self.running = delay, fn, args, True

    def IsRunning(self) -> bool:  # noqa: N802 - wx's name
        return self.running

    def Stop(self) -> None:  # noqa: N802 - wx's name
        self.running = False

    def fire(self) -> None:
        if self.running:
            self.running = False
            self.fn(*self.args)


class _Clock:
    def __init__(self) -> None:
        self.timers: list[_Timer] = []

    def __call__(self, delay, fn, *args) -> _Timer:
        timer = _Timer(delay, fn, *args)
        self.timers.append(timer)
        return timer

    def run_all(self) -> None:
        for timer in list(self.timers):
            timer.fire()


def _sequence(*, sounds_on: bool = True):
    said: list[str] = []
    played: list[str] = []
    clock = _Clock()
    sequence = PreviewSequence(
        said.append, cue=played.append, sounds_on=lambda: sounds_on, call_later=clock
    )
    return sequence, said, played, clock


@pytest.mark.parametrize(
    ("mode", "has_sound", "expected"),
    [
        ("sound", True, PreviewStep(sound="tone")),
        ("sound", False, PreviewStep(words="Words.")),  # no sound in the scheme: speaks
        ("speech", True, PreviewStep(words="Words.")),
        ("both", True, PreviewStep(sound="tone", words="Words.")),
        ("silent", True, PreviewStep()),
    ],
)
def test_feedback_step_resolves_like_the_real_moment(mode, has_sound, expected) -> None:
    assert feedback_step(mode, event="tone", words="Words.", has_sound=has_sound) == expected


def test_edge_step_speaks_when_the_sound_is_wanted_but_missing() -> None:
    assert edge_step(
        cue_sounds=True, announce=False, event="on", words="On.", has_sound=False
    ) == PreviewStep(words="On.")
    assert edge_step(
        cue_sounds=False, announce=False, event="on", words="On.", has_sound=True
    ).silent


def test_the_first_step_is_heard_at_once_and_the_rest_a_moment_apart() -> None:
    sequence, said, played, clock = _sequence()
    sequence.play([PreviewStep(sound="on"), PreviewStep(words="Phrase."), PreviewStep()])
    assert played == ["on"] and said == []
    assert [timer.delay for timer in clock.timers] == [1800]  # the silent step is skipped
    assert sequence.playing
    clock.run_all()
    assert said == ["Phrase."]
    assert not sequence.playing


def test_stop_cancels_what_is_left_and_says_so() -> None:
    sequence, said, _played, clock = _sequence()
    sequence.play([PreviewStep(sound="on"), PreviewStep(words="Phrase.")])
    assert sequence.stop() is True
    clock.run_all()
    assert said == []
    assert sequence.stop() is False  # nothing left to stop


def test_all_silent_says_nothing_will_be_heard_once() -> None:
    sequence, said, played, _clock = _sequence()
    sequence.play([PreviewStep(), PreviewStep()])
    assert said == [NOTHING_HEARD] and played == []


def test_sounds_off_is_said_once_not_once_a_step() -> None:
    sequence, said, played, clock = _sequence(sounds_on=False)
    sequence.play([PreviewStep(sound="on"), PreviewStep(sound="off", words="Off.")])
    clock.run_all()
    assert played == []
    assert said == [SOUNDS_OFF, "Off."]


def _escape(window):
    import wx

    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetEventObject(window)
    event.SetKeyCode(wx.WXK_ESCAPE)
    window.ProcessEvent(event)


def test_escape_stops_the_preview_and_leaves_the_window_open(wx_session_app) -> None:
    import wx

    dialog = wx.Dialog(None)
    try:
        reached: list[bool] = []
        dialog.Bind(wx.EVT_CHAR_HOOK, lambda _e: reached.append(True))  # the window's own Escape
        sequence, said, _played, clock = _sequence()
        sequence.guard(dialog)
        sequence.play([PreviewStep(sound="on"), PreviewStep(words="Later.")])
        _escape(dialog)
        assert not sequence.playing
        assert reached == []  # Escape stopped the preview and went no further
        clock.run_all()
        assert said == []
        _escape(dialog)  # with nothing playing, Escape is the window's again
        assert reached == [True]
    finally:
        dialog.Destroy()


def test_closing_the_window_stops_the_preview(wx_session_app) -> None:
    import wx

    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    sequence, said, _played, clock = _sequence()
    sequence.guard(panel)
    sequence.play([PreviewStep(sound="on"), PreviewStep(words="Later.")])
    panel.Destroy()
    frame.Destroy()
    clock.run_all()
    assert said == []


def test_leaving_the_window_stops_the_preview(wx_session_app) -> None:
    import wx

    dialog = wx.Dialog(None)
    try:
        sequence, said, _played, clock = _sequence()
        sequence.guard(dialog)
        sequence.play([PreviewStep(sound="on"), PreviewStep(words="Later.")])
        event = wx.ActivateEvent(wx.wxEVT_ACTIVATE, False)
        event.SetEventObject(dialog)
        dialog.ProcessEvent(event)  # a child dialog, or another program, in front
        clock.run_all()
        assert said == []
    finally:
        dialog.Destroy()
