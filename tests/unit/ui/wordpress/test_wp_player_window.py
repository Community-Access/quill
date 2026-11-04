"""The player window itself, on a faked engine (wordpress.md 6.1a).

The real shared transport panel is built; only its engine is replaced, so the
test proves this window drives the same panel QUILL and Quill Media Player use
and stops it on every way out.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import wx

from quill.core.wordpress import media_play as mp
from quill.core.wordpress.listening import Cue
from quill.ui import wordpress_player_window as pwin
from quill.ui.audio_studio import player_panel as pp

URL = "https://radio.example/wp-content/uploads/2026/11"


class FakeMpv:
    def __init__(self) -> None:
        self.props: dict[str, str] = {}

    def set_str(self, name: str, value: str) -> int:
        self.props[name] = value
        return 0


class FakeEngine:
    def __init__(self, parent, *, on_loaded, on_finished, on_error, audio_device="") -> None:
        self.on_loaded = on_loaded
        self.loaded: list[str] = []
        self.playing = False
        self.position = 0
        self.closed = False
        self.stopped = 0

    def load(self, path: str) -> bool:
        self.loaded.append(path)
        return True

    def close(self) -> None:
        self.closed = True
        self.playing = False

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def stop(self) -> None:
        self.stopped += 1
        self.playing = False

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self.position = ms

    def position_ms(self) -> int:
        return self.position

    def length_ms(self) -> int:
        return 5000

    def is_playing(self) -> bool:
        return self.playing

    def set_volume(self, percent: int) -> None:
        pass

    def set_rate(self, rate: float) -> None:
        pass


class MpvEngine(FakeEngine):
    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self._mpv = FakeMpv()


class Engines(list):
    """Every engine the panel made, and the class the next one will be."""

    kind: dict[str, type] = {}


@pytest.fixture
def engines(monkeypatch, wx_session_app) -> Engines:
    made = Engines()
    kind: dict[str, type] = {"cls": FakeEngine}

    def create(parent, **kwargs):
        engine = kind["cls"](parent, **kwargs)
        made.append(engine)
        return engine

    monkeypatch.setattr(pp, "create_engine", create)
    made.kind = kind
    return made


def window(playable: mp.Playable, **overrides: Any) -> tuple[pwin.MediaPlayerWindow, dict]:
    said: dict[str, list[Any]] = {"announce": [], "player": [], "browser": [], "captions": []}
    kwargs: dict[str, Any] = {
        "site_name": "Community Radio",
        "show_modal": lambda dialog, label: wx.ID_CANCEL,
        "announce": said["announce"].append,
        "read_captions": lambda track, done: said["captions"].append((track, done)),
        "open_in_player": said["player"].append,
        "open_in_browser": said["browser"].append,
    }
    kwargs.update(overrides)
    return pwin.MediaPlayerWindow(None, playable=playable, **kwargs), said


AUDIO = mp.Playable("Test Tone", f"{URL}/tone.wav", "audio", 2)
VIDEO = mp.Playable(
    "Clip", f"{URL}/clip.mp4", "video", 3, (mp.CaptionTrack(f"{URL}/clip.en.vtt", "English", "en"),)
)


def test_audio_streams_from_the_address_and_plays(engines) -> None:
    win, _said = window(AUDIO)
    try:
        assert win.start()
        engine = engines[-1]
        assert engine.loaded == [AUDIO.url]
        engine.on_loaded(5000)  # autoplay once loaded
        assert engine.playing
        assert win.picture is None and win.captions_button is None
        for name in ("player.prev", "player.next"):
            assert not win.panel.FindWindowByName(name).IsShown()
    finally:
        win.release()
        win.Destroy()
    assert engine.closed and not engine.playing


def test_play_stops_and_releases_when_the_window_closes(engines) -> None:
    pwin.play(
        None,
        lambda dialog, label: wx.ID_CANCEL,
        AUDIO,
        site_name="Community Radio",
        announce=lambda _t: None,
        read_captions=lambda *_a: None,
        open_in_player=lambda _p: None,
        open_in_browser=lambda _u: None,
    )
    engine = engines[-1]
    assert engine.loaded == [AUDIO.url]
    assert engine.closed and engine.stopped >= 1


def test_the_close_box_stops_playback_too(engines) -> None:
    win, _said = window(AUDIO)
    win.start()
    engines[-1].on_loaded(5000)
    win.Close()
    assert engines[-1].closed
    win.Destroy()


def test_video_draws_its_picture_and_reads_captions(engines) -> None:
    engines.kind["cls"] = MpvEngine
    win, said = window(VIDEO)
    try:
        win.start()
        engine = engines[-1]
        assert engine._mpv.props["vid"] == "auto"
        assert engine._mpv.props["wid"] == str(int(win.picture.GetHandle()))
        engine.on_loaded(5000)
        engine.position = 1500
        win.on_captions()
        track, done = said["captions"][0]
        assert track.srclang == "en"
        done([Cue(1.0, 3.0, "Welcome to the station.")])
        assert said["announce"][-1] == "Welcome to the station."
        engine.position = 4000
        win.on_captions()  # read once, kept
        assert len(said["captions"]) == 1
        assert said["announce"][-1].startswith("No caption at")
    finally:
        win.release()
        win.Destroy()


def test_a_video_with_no_picture_route_says_so(engines) -> None:
    win, said = window(mp.Playable("Clip", f"{URL}/clip.mp4", "video"))
    try:
        win.start()
        assert not win.picture.IsShown()
        assert "Open in Browser shows the picture" in said["announce"][-1]
        win.on_captions()
        assert said["announce"][-1] == "This video has no captions track on Community Radio."
    finally:
        win.release()
        win.Destroy()


def test_the_other_routes_pause_here_first(engines) -> None:
    win, said = window(AUDIO)
    try:
        win.start()
        engines[-1].on_loaded(5000)
        win.on_open_in_player()
        assert not engines[-1].playing
        assert said["player"] == [AUDIO]
        win.on_open_in_browser()
        assert said["browser"] == [AUDIO.url]
    finally:
        win.release()
        win.Destroy()


def test_every_control_has_help_and_no_access_key_twice(engines) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    win, _said = window(VIDEO)
    try:
        letters: list[str] = []
        for child in _walk(win):
            if isinstance(child, (wx.Button, wx.Choice, wx.Slider)) and child.IsShown():
                assert child.GetHelpText(), child.GetLabel()
            if isinstance(child, (wx.Button, wx.StaticText)) and child.IsShown():
                found = re.search(r"&(\w)", child.GetLabel())
                if found:
                    letters.append(found.group(1).lower())
        assert len(letters) == len(set(letters)), letters
        assert win.FindWindowById(wx.ID_CANCEL).GetLabel() == "Close"
        assert win.GetHelpText()
    finally:
        win.release()
        win.Destroy()


def _walk(parent: wx.Window):
    for child in parent.GetChildren():
        yield child
        yield from _walk(child)
