"""RadioPlayerController routes a ``spotify:`` station to the Spotify Web
Playback engine and never applies the cross-engine (wx/mpv) fallback to it,
while ordinary stream stations keep using the classic engine. Uses injected
fakes so no real WebView, network, or Spotify account is touched."""

from __future__ import annotations

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.ui.radio.player_controller import RadioPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self, *, name: str) -> None:
        self.name = name
        self.loaded: list[str] = []
        self.closed = False
        self.load_result = True

    def load(self, source: str) -> bool:
        self.loaded.append(source)
        return self.load_result

    def play(self, *_a, **_k) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def set_volume(self, _percent: int) -> None:
        pass


def _make_controller() -> tuple[RadioPlayerController, _FakeEngine, _FakeEngine]:
    frame = wx.Frame(None)
    controller = RadioPlayerController(
        frame, playback_engine="wx", spotify_token_provider=lambda: "fake-token"
    )
    wx_fake = _FakeEngine(name="wx")
    spotify_fake = _FakeEngine(name="spotify")
    controller._wx_engine = wx_fake
    controller._engine = wx_fake
    # Pre-inject the Spotify engine so _ensure_spotify_engine returns it
    # instead of constructing a real WebView-backed SpotifyWebEngine.
    controller._spotify_engine = spotify_fake
    return controller, wx_fake, spotify_fake


def _spotify_station() -> RadioStation:
    return RadioStation(name="My Track", stream_url="spotify:track:4iV5W9uYEdYUVa79Axb7Rh")


def _stream_station() -> RadioStation:
    return RadioStation(name="Jazz FM", stream_url="http://example.test/jazz")


def test_spotify_station_plays_on_the_spotify_engine() -> None:
    controller, _wx_fake, spotify_fake = _make_controller()
    controller.play_station(_spotify_station())
    assert controller._engine is spotify_fake
    assert spotify_fake.loaded == ["spotify:track:4iV5W9uYEdYUVa79Axb7Rh"]


def test_spotify_station_never_falls_back_to_a_stream_engine() -> None:
    controller, wx_fake, spotify_fake = _make_controller()
    spotify_fake.load_result = False  # SDK not ready / no Premium
    fallback_calls: list[bool] = []
    controller._attempt_engine_fallback = lambda: fallback_calls.append(True) or True  # type: ignore[assignment]
    controller.play_station(_spotify_station())
    assert fallback_calls == [], "a spotify: URI must never be retried on wx/mpv"
    assert controller._engine is spotify_fake
    assert wx_fake.loaded == []


def test_stream_station_uses_the_classic_engine_not_spotify() -> None:
    controller, wx_fake, spotify_fake = _make_controller()
    controller.play_station(_stream_station())
    assert controller._engine is wx_fake
    assert wx_fake.loaded == ["http://example.test/jazz"]
    assert spotify_fake.loaded == []


def test_switching_from_spotify_back_to_a_stream_closes_the_spotify_engine() -> None:
    controller, wx_fake, spotify_fake = _make_controller()
    controller.play_station(_spotify_station())
    assert controller._engine is spotify_fake
    controller.play_station(_stream_station())
    assert spotify_fake.closed is True
    assert controller._engine is wx_fake
    assert controller._spotify_engine is None


def test_no_token_provider_means_no_spotify_engine() -> None:
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx", spotify_token_provider=None)
    assert controller._ensure_spotify_engine() is None
