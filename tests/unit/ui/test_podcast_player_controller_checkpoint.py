"""PodcastPlayerController's position-checkpoint callback: fires with the
*outgoing* episode's identity and position at pause/stop/switch, never on
natural finish (that's on_episode_finished's job) -- the fix for a real gap
where episode.position_ms was read (to resume) but never written."""

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
    def __init__(self) -> None:
        self._position = 0
        self.closed = False
        self.paused = False

    def load(self, _source: str) -> bool:
        return True

    def play(self) -> None:
        self.paused = False

    def pause(self) -> None:
        self.paused = True

    def close(self) -> None:
        self.closed = True

    def seek(self, ms: int, *, resume: bool = False) -> None:
        self._position = ms

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return 100_000

    def is_playing(self) -> bool:
        return not self.paused


def _make_controller() -> tuple[PodcastPlayerController, list[tuple[str, str, int]], _FakeEngine]:
    checkpoints: list[tuple[str, str, int]] = []
    frame = wx.Frame(None)
    controller = PodcastPlayerController(
        frame,
        on_position_checkpoint=lambda show_id, guid, ms: checkpoints.append((show_id, guid, ms)),
    )
    fake = _FakeEngine()
    controller._engine = fake  # bypass the real engine picked by create_engine
    return controller, checkpoints, fake


def _start_playing(
    controller: PodcastPlayerController, fake: _FakeEngine, **kwargs: object
) -> None:
    controller.play_episode(
        show_id=kwargs.get("show_id", "show-1"),
        episode_guid=kwargs.get("episode_guid", "ep-1"),
        title="Title",
        source="https://example.com/ep.mp3",
    )
    controller._on_loaded(100_000)  # simulate the engine's load callback firing


def test_pause_reports_a_checkpoint_for_the_current_episode() -> None:
    controller, checkpoints, fake = _make_controller()
    _start_playing(controller, fake)
    fake._position = 45_000
    controller.toggle_play_pause()
    assert checkpoints == [("show-1", "ep-1", 45_000)]


def test_stop_reports_a_checkpoint_before_clearing_state() -> None:
    controller, checkpoints, fake = _make_controller()
    _start_playing(controller, fake)
    fake._position = 12_345
    controller.stop()
    assert checkpoints == [("show-1", "ep-1", 12_345)]
    assert controller.state.show_id is None


def test_switching_episodes_checkpoints_the_outgoing_one() -> None:
    controller, checkpoints, fake = _make_controller()
    _start_playing(controller, fake, show_id="show-1", episode_guid="ep-1")
    fake._position = 30_000
    _start_playing(controller, fake, show_id="show-1", episode_guid="ep-2")
    assert checkpoints == [("show-1", "ep-1", 30_000)]


def test_no_checkpoint_when_nothing_was_ever_playing() -> None:
    controller, checkpoints, _fake = _make_controller()
    controller.stop()
    assert checkpoints == []


def test_shutdown_checkpoints_the_active_episode() -> None:
    controller, checkpoints, fake = _make_controller()
    _start_playing(controller, fake)
    fake._position = 5_000
    controller.shutdown()
    assert checkpoints == [("show-1", "ep-1", 5_000)]
