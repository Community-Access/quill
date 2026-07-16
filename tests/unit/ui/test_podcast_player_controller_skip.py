"""PodcastPlayerController's skip-interval wiring: auto_skip_intro_ms only
applies to a fresh start (never a resume), and auto_skip_outro_ms ends an
episode early via a position poll, going through the exact same
_on_finished path a natural end would (auto-advance, delete-after-play,
...  all still fire). No real audio engine -- a fake stands in."""

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
    def __init__(self) -> None:
        self._position = 0
        self._length = 120_000
        self.loaded_sources: list[str] = []

    def load(self, source: str) -> bool:
        self.loaded_sources.append(source)
        self._position = 0
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self._position = ms

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return self._length

    def is_playing(self) -> bool:
        return True


def _make_controller() -> tuple[PodcastPlayerController, _FakeEngine]:
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame)
    fake_engine = _FakeEngine()
    controller._engine = fake_engine  # bypass the real engine picked by create_engine
    return controller, fake_engine


def test_auto_skip_intro_applies_on_a_fresh_start() -> None:
    controller, _engine = _make_controller()
    controller.play_episode(
        show_id="show-1", episode_guid="ep-1", title="T", source="src", auto_skip_intro_ms=15_000
    )
    controller._on_loaded(0)
    assert controller.position_ms() == 15_000


def test_auto_skip_intro_never_applies_when_resuming() -> None:
    controller, _engine = _make_controller()
    controller.play_episode(
        show_id="show-1",
        episode_guid="ep-1",
        title="T",
        source="src",
        resume_ms=30_000,
        auto_skip_intro_ms=15_000,
    )
    controller._on_loaded(0)
    assert controller.position_ms() == 30_000


def test_auto_skip_outro_ends_the_episode_early() -> None:
    controller, engine = _make_controller()
    controller.play_episode(
        show_id="show-1", episode_guid="ep-1", title="T", source="src", auto_skip_outro_ms=5_000
    )
    controller._on_loaded(0)
    engine._position = 116_000  # within 5s of the 120s fake length
    finished: list[tuple[str, str]] = []
    controller._on_episode_finished = lambda sid, gid: finished.append((sid, gid))
    controller._on_outro_poll(None)
    assert finished == [("show-1", "ep-1")]
    assert controller.state.state is PodcastPlayerState.STOPPED


def test_auto_skip_outro_does_not_fire_before_the_threshold() -> None:
    controller, engine = _make_controller()
    controller.play_episode(
        show_id="show-1", episode_guid="ep-1", title="T", source="src", auto_skip_outro_ms=5_000
    )
    controller._on_loaded(0)
    engine._position = 100_000  # well before the outro window
    finished: list[tuple[str, str]] = []
    controller._on_episode_finished = lambda sid, gid: finished.append((sid, gid))
    controller._on_outro_poll(None)
    assert finished == []
    assert controller.state.state is PodcastPlayerState.PLAYING


def test_auto_skip_outro_disabled_by_default() -> None:
    controller, engine = _make_controller()
    controller.play_episode(show_id="show-1", episode_guid="ep-1", title="T", source="src")
    controller._on_loaded(0)
    engine._position = 119_999  # one ms from the true end
    finished: list[tuple[str, str]] = []
    controller._on_episode_finished = lambda sid, gid: finished.append((sid, gid))
    controller._on_outro_poll(None)
    assert finished == []


def test_auto_skip_outro_only_fires_once_per_episode() -> None:
    controller, engine = _make_controller()
    controller.play_episode(
        show_id="show-1", episode_guid="ep-1", title="T", source="src", auto_skip_outro_ms=5_000
    )
    controller._on_loaded(0)
    engine._position = 116_000
    finished: list[tuple[str, str]] = []
    controller._on_episode_finished = lambda sid, gid: finished.append((sid, gid))
    controller._on_outro_poll(None)
    controller._on_outro_poll(None)
    controller._on_outro_poll(None)
    assert finished == [("show-1", "ep-1")]
