"""PodcastPlayerController routes a ``spotify:episode:`` source to the Spotify
Web Playback engine (DRM audio the mpv/wx engines cannot play) and keeps
ordinary episode sources on the stream engine. Injected fakes -- no real
WebView, network, or Spotify account."""

from __future__ import annotations

import pytest
import wx

from quill.ui.podcasts.player_controller import PodcastPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self, *, name: str) -> None:
        self.name = name
        self.loaded: list[str] = []
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
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def set_rate(self, _rate: float) -> None:
        pass

    def position_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return False


def _make_controller() -> tuple[PodcastPlayerController, _FakeEngine, _FakeEngine]:
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame, spotify_token_provider=lambda: "fake-token")
    stream_fake = _FakeEngine(name="stream")
    spotify_fake = _FakeEngine(name="spotify")
    controller._stream_engine = stream_fake
    controller._engine = stream_fake
    controller._spotify_engine = spotify_fake  # pre-inject so no real WebView
    return controller, stream_fake, spotify_fake


def _play(controller: PodcastPlayerController, source: str) -> None:
    controller.play_episode(show_id="s", episode_guid="g", title="An Episode", source=source)


def test_spotify_episode_routes_to_the_spotify_engine() -> None:
    controller, stream_fake, spotify_fake = _make_controller()
    _play(controller, "spotify:episode:5abc")
    assert controller._engine is spotify_fake
    assert spotify_fake.loaded == ["spotify:episode:5abc"]
    assert stream_fake.loaded == []


def test_ordinary_episode_stays_on_the_stream_engine() -> None:
    controller, stream_fake, spotify_fake = _make_controller()
    _play(controller, "https://example.test/ep1.mp3")
    assert controller._engine is stream_fake
    assert spotify_fake.loaded == []
    assert stream_fake.loaded  # the stream engine loaded a (possibly relayed) url


def test_switching_back_to_a_stream_episode_restores_the_stream_engine() -> None:
    controller, stream_fake, spotify_fake = _make_controller()
    _play(controller, "spotify:episode:5abc")
    assert controller._engine is spotify_fake
    _play(controller, "https://example.test/ep2.mp3")
    assert controller._engine is stream_fake


def test_no_token_provider_means_no_spotify_engine() -> None:
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame, spotify_token_provider=None)
    assert controller._ensure_spotify_engine() is None
