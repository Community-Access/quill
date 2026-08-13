"""A dropped stream stops being an interruption.

While a streamed episode plays, its bytes are also written to the playback
cache, and that fetch runs far ahead of realtime. So when the connection goes,
the audio the listener was about to hear is usually already on disk, and the
right answer is to keep playing from it rather than to report an error.

These tests cover the controller half of that: when it asks for a local
fallback, when it accepts one, and -- just as important -- when it gives up and
tells the truth instead.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.podcasts.player_controller import PodcastPlayerController, PodcastPlayerState


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self, *, position: int = 0) -> None:
        self.loaded: list[str] = []
        self.seeks: list[int] = []
        self._position = position

    def load(self, source: str) -> bool:
        self.loaded.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def seek(self, ms: int, *, resume: bool = False) -> None:
        self.seeks.append(ms)

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return True


def _controller(fallback, *, position: int = 90_000):
    frame = wx.Frame(None)
    states: list[tuple] = []
    controller = PodcastPlayerController(
        frame,
        local_fallback=fallback,
        on_state_changed=lambda s: states.append((s.state, s.message)),
    )
    engine = _FakeEngine(position=position)
    controller._engine = engine
    controller._stream_engine = engine
    return controller, engine, states


def _play(controller) -> None:
    controller.play_episode(
        show_id="s",
        episode_guid="g",
        title="An episode",
        source="https://example.test/ep.mp3",
    )


def test_a_drop_reloads_the_local_file_at_the_same_position() -> None:
    controller, engine, states = _controller(lambda _pos: "C:/cache/ep.mp3")
    _play(controller)
    engine.loaded.clear()
    controller._on_error("connection reset")
    assert engine.loaded == ["C:/cache/ep.mp3"]
    assert controller.state.state is not PodcastPlayerState.ERROR


def test_the_fallback_is_asked_where_the_listener_actually_is() -> None:
    asked: list[int] = []

    def fallback(position: int) -> str:
        asked.append(position)
        return ""

    controller, _engine, _states = _controller(fallback, position=123_000)
    _play(controller)
    controller._on_error("connection reset")
    assert asked == [123_000]


def test_no_local_bytes_reports_the_error_honestly() -> None:
    controller, _engine, _states = _controller(lambda _pos: "")
    _play(controller)
    controller._on_error("connection reset")
    assert controller.state.state is PodcastPlayerState.ERROR
    assert controller.state.message == "connection reset"


def test_recovery_is_not_attempted_twice_for_the_same_file() -> None:
    """If the local file fails too, say so rather than looping on it."""
    controller, _engine, _states = _controller(lambda _pos: "C:/cache/ep.mp3")
    _play(controller)
    controller._on_error("connection reset")
    controller._on_error("that file is unreadable")
    assert controller.state.state is PodcastPlayerState.ERROR
    assert controller.state.message == "that file is unreadable"


def test_a_new_episode_may_recover_again() -> None:
    controller, engine, _states = _controller(lambda _pos: "C:/cache/ep.mp3")
    _play(controller)
    controller._on_error("connection reset")
    controller.play_episode(
        show_id="s", episode_guid="g2", title="Another", source="https://example.test/ep2.mp3"
    )
    engine.loaded.clear()
    controller._on_error("connection reset")
    assert engine.loaded == ["C:/cache/ep.mp3"]


def test_a_failing_lookup_is_simply_no_fallback() -> None:
    def fallback(_position: int) -> str:
        raise OSError("the cache directory went away")

    controller, _engine, _states = _controller(fallback)
    _play(controller)
    controller._on_error("connection reset")
    assert controller.state.state is PodcastPlayerState.ERROR


def test_nothing_loaded_means_nothing_to_recover() -> None:
    controller, _engine, _states = _controller(lambda _pos: "C:/cache/ep.mp3")
    controller._on_error("no media")
    assert controller.state.state is PodcastPlayerState.ERROR


def test_a_controller_with_no_fallback_behaves_exactly_as_before() -> None:
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame)
    controller._engine = _FakeEngine()
    _play(controller)
    controller._on_error("connection reset")
    assert controller.state.state is PodcastPlayerState.ERROR
