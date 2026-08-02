"""Playing a YouTube station (#1268): the controller's asynchronous resolve.

A YouTube link needs a network round trip before anything can play, so the
controller resolves it off the UI thread and applies the result back on it.
These tests drive that path with a fake resolver and pump wx's event loop, so
they never touch yt-dlp or the network.
"""

from __future__ import annotations

import threading

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.ui.radio.player_controller import RadioPlayerController, RadioPlayerState

_YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
_RESOLVED = "https://media.test/audio.m4a"


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self.loads: list[str] = []
        self.closed = False

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def set_volume(self, percent: int) -> None:
        pass

    def set_audio_device(self, name: str) -> None:
        pass


def _controller(frame: wx.Frame, resolver, engine: _FakeEngine) -> RadioPlayerController:
    controller = RadioPlayerController(frame, playback_engine="wx", resolve_youtube=resolver)
    controller._wx_engine = engine  # type: ignore[assignment]
    controller._engine = engine  # type: ignore[assignment]
    return controller


def _pump(predicate, *, limit: int = 200) -> None:
    """Run wx's event loop until *predicate* holds (the resolve lands via CallAfter)."""
    for _ in range(limit):
        if predicate():
            return
        wx.Yield()
        wx.MilliSleep(5)


def _youtube_station() -> RadioStation:
    return RadioStation(name="A Live Broadcast", stream_url=_YOUTUBE, source="YouTube")


def test_youtube_station_plays_the_resolved_stream_not_the_page(wx_app) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()
    controller = _controller(frame, lambda _url: _RESOLVED, engine)

    controller.play_station(_youtube_station())
    _pump(lambda: bool(engine.loads))

    assert engine.loads == [_RESOLVED]
    # The station itself keeps the durable page URL: that is what a favorite,
    # the recorder, and the now-playing line must hold, not an expiring address.
    assert controller.state.station is not None
    assert controller.state.station.stream_url == _YOUTUBE
    assert controller.current_playback_url() == _RESOLVED
    frame.Destroy()


def test_connecting_is_announced_before_the_resolve_finishes(wx_app) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()
    release = threading.Event()
    controller = _controller(frame, lambda _url: (release.wait(2), _RESOLVED)[1], engine)

    controller.play_station(_youtube_station())

    # The listener hears "Connecting" immediately -- the UI is never frozen
    # waiting on the network.
    assert controller.state.state is RadioPlayerState.CONNECTING
    assert not engine.loads
    release.set()
    _pump(lambda: bool(engine.loads))
    assert engine.loads == [_RESOLVED]
    frame.Destroy()


def test_a_resolve_that_lands_after_stop_does_not_start_playing(wx_app) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()
    release = threading.Event()
    controller = _controller(frame, lambda _url: (release.wait(2), _RESOLVED)[1], engine)

    controller.play_station(_youtube_station())
    controller.stop()
    release.set()
    for _ in range(40):
        wx.Yield()
        wx.MilliSleep(5)

    assert engine.loads == []
    assert controller.state.state is RadioPlayerState.STOPPED
    frame.Destroy()


def test_a_failed_resolve_reports_the_reason(wx_app) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()

    def boom(_url: str) -> str:
        raise RuntimeError("That video is private.")

    controller = _controller(frame, boom, engine)
    controller.play_station(_youtube_station())
    _pump(lambda: controller.state.state is RadioPlayerState.ERROR)

    assert controller.state.state is RadioPlayerState.ERROR
    assert "private" in controller.state.message
    assert engine.loads == []
    frame.Destroy()


def test_without_a_resolver_a_youtube_station_errors_instead_of_loading_a_web_page(
    wx_app,
) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()
    controller = RadioPlayerController(frame, playback_engine="wx")
    controller._wx_engine = engine  # type: ignore[assignment]
    controller._engine = engine  # type: ignore[assignment]

    controller.play_station(_youtube_station())

    assert controller.state.state is RadioPlayerState.ERROR
    assert engine.loads == []
    frame.Destroy()


def test_an_ordinary_station_still_plays_synchronously(wx_app) -> None:
    # The asynchronous path is YouTube-only; nothing else pays for it.
    frame = wx.Frame(None)
    engine = _FakeEngine()
    controller = _controller(frame, lambda _url: _RESOLVED, engine)

    controller.play_station(RadioStation(name="Normal", stream_url="http://example.test/live"))

    assert engine.loads == ["http://example.test/live"]
    assert controller.current_playback_url() == "http://example.test/live"
    frame.Destroy()


def test_switching_stations_mid_resolve_plays_the_second_one(wx_app) -> None:
    frame = wx.Frame(None)
    engine = _FakeEngine()
    first_release = threading.Event()

    def resolver(url: str) -> str:
        if url == _YOUTUBE:
            first_release.wait(2)
            return "https://media.test/first.m4a"
        return "https://media.test/second.m4a"

    controller = _controller(frame, resolver, engine)
    controller.play_station(_youtube_station())
    controller.play_station(
        RadioStation(name="Second", stream_url="https://youtu.be/AAAAAAAAAAA", source="YouTube")
    )
    _pump(lambda: bool(engine.loads))
    first_release.set()
    for _ in range(40):
        wx.Yield()
        wx.MilliSleep(5)

    assert engine.loads == ["https://media.test/second.m4a"]
    frame.Destroy()
