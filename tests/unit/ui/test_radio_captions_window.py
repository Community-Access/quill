"""The Captions window, and the keys the Video Window carries itself.

Two reports from 2026-08-23, both about a window that could not answer a key:

* "toggling captions on and off is not showing the captions in a window" --
  captions were drawn into the picture by mpv and nowhere else.
* "ctrl+shift+v shows the video window but pressing the key does not close it"
  -- a menu accelerator only fires for the frame that owns the menu bar, so
  standing in the Video Window none of the video commands existed.

Real wx here, because both are about wx behaviour (a timer-driven text control
and an accelerator table); nothing is shown to the screen.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.ui.radio import video_commands
from quill.ui.radio.captions_window import WAITING, CaptionsWindow


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Cue:
    def __init__(self, start_ms: int, text: str) -> None:
        self.start_ms = start_ms
        self.end_ms = start_ms + 1000
        self.text = text


CUES = [_Cue(0, "Good evening."), _Cue(2000, "Tonight, the weather.")]


def test_the_window_shows_the_line_being_spoken(wx_app) -> None:
    frame = wx.Frame(None)
    position = {"ms": 0}
    window = CaptionsWindow(frame, title="A Lecture", cues=CUES, position_ms=lambda: position["ms"])

    assert window.tick() is True
    assert window.text.GetValue() == "> Good evening."

    position["ms"] = 2500
    assert window.tick() is True
    assert window.text.GetValue().splitlines() == ["Good evening.", "> Tonight, the weather."]
    assert window.current_caption() == "Tonight, the weather."

    # Nothing changed, so nothing is rewritten -- a text control that is
    # rebuilt four times a second is a text control nobody can read.
    assert window.tick() is False
    frame.Destroy()


def test_the_window_says_what_it_is_waiting_for(wx_app) -> None:
    frame = wx.Frame(None)
    window = CaptionsWindow(frame, cues=CUES, position_ms=None)

    assert window.tick() is False
    assert window.text.GetValue() == WAITING
    frame.Destroy()


def test_a_player_that_raises_does_not_take_the_window_down(wx_app) -> None:
    frame = wx.Frame(None)

    def _boom() -> int:
        raise RuntimeError("stopped")

    window = CaptionsWindow(frame, cues=CUES, position_ms=_boom)
    assert window.tick() is False
    frame.Destroy()


def test_automatic_captions_say_so_in_the_label(wx_app) -> None:
    frame = wx.Frame(None)
    window = CaptionsWindow(frame, cues=CUES, position_ms=lambda: 0, is_automatic=True)
    labels = [
        child.GetLabel() for child in window.frame.GetChildren() if isinstance(child, wx.StaticText)
    ]
    assert any("machine-generated" in label for label in labels)
    frame.Destroy()


def test_a_new_track_replaces_the_old_one(wx_app) -> None:
    frame = wx.Frame(None)
    window = CaptionsWindow(frame, cues=CUES, position_ms=lambda: 5000)
    window.tick()

    window.set_cues([_Cue(0, "A different video.")])

    assert window.text.GetValue() == "> A different video."
    frame.Destroy()


# -- the Video Window's own keys ---------------------------------------------------


class _FakeVideoWindow:
    def __init__(self, frame: Any) -> None:
        self.frame = frame


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []
        self._video_window: Any = None
        self._radio_controller = None

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_the_video_window_carries_the_keys_its_commands_live_on(wx_app) -> None:
    frame = wx.Frame(None)
    host = _Host()

    landed = video_commands.install_window_keys(host, _FakeVideoWindow(frame))

    # Every one of them, or the window advertises keys that do nothing.
    assert landed == len(video_commands.VIDEO_WINDOW_KEYS)
    assert frame.GetAcceleratorTable().IsOk()
    frame.Destroy()


def test_show_video_is_among_them_because_it_is_how_you_close_it(wx_app) -> None:
    keys = dict((verb, key) for key, verb in video_commands.VIDEO_WINDOW_KEYS)
    assert keys["hide"] in ("Ctrl+Shift+V", "Ctrl+W", "Ctrl+F4")
    assert "Ctrl+Shift+V" in [key for key, _verb in video_commands.VIDEO_WINDOW_KEYS]
    # And the transcript key the surface description promises.
    assert "Ctrl+Shift+T" in [key for key, _verb in video_commands.VIDEO_WINDOW_KEYS]


def test_the_hide_verb_hides(wx_app) -> None:
    class _Engine:
        def __init__(self) -> None:
            self.attached: list[Any] = []

        def attach_video(self, handle: Any) -> bool:
            self.attached.append(handle)
            return True

    class _Controller:
        def __init__(self, engine: Any) -> None:
            self._engine = engine

    engine = _Engine()
    host = _Host()
    host._radio_controller = _Controller(engine)
    host._video_window = _FakeVideoWindow(wx.Frame(None))
    host._video_window.close = lambda: None  # type: ignore[attr-defined]

    video_commands._window_verb(host, "hide")

    assert engine.attached == [None]
    assert host._video_window is None
    assert video_commands.HIDDEN in host.said
