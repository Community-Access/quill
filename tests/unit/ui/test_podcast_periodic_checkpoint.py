"""The resume position survives an unclean exit (podcasts).

The checkpoint used to fire at pause, stop, switch and shutdown only -- every
path that runs *because the listener acted*. A session that ended any other way
took the position with it: a crash, a power cut, Task Manager, or any shutdown
that never reached ``shutdown()``. Come back the next day and you are wherever
you last pressed pause, which after an uninterrupted hour is an hour ago.

The one-second poll that already runs for the outro skip now also checkpoints,
throttled, so an unclean exit costs at most a few seconds of listening.

Same harness as ``test_podcast_player_controller_checkpoint.py``: one module
wx.App, one frame, a fake engine.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.podcasts.player_controller import (
    _CHECKPOINT_EVERY_S,
    PodcastPlayerController,
    PodcastPlayerState,
)


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self.position = 0

    def load(self, _source: str) -> bool:
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def seek(self, ms: int, *, resume: bool = False) -> None:
        self.position = ms

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def position_ms(self) -> int:
        return self.position

    def length_ms(self) -> int:
        return 3_600_000

    def is_playing(self) -> bool:
        return True


def _rig() -> tuple[PodcastPlayerController, list[tuple[str, str, int]], _FakeEngine]:
    checkpoints: list[tuple[str, str, int]] = []
    frame = wx.Frame(None)
    controller = PodcastPlayerController(
        frame,
        on_position_checkpoint=lambda show_id, guid, ms: checkpoints.append((show_id, guid, ms)),
    )
    fake = _FakeEngine()
    controller._engine = fake  # bypass the real engine picked by create_engine
    controller._state.show_id = "show-1"
    controller._state.episode_guid = "ep-1"
    controller._state.state = PodcastPlayerState.PLAYING
    return controller, checkpoints, fake


def test_playing_on_writes_the_position_without_being_asked() -> None:
    controller, checkpoints, fake = _rig()

    fake.position = _CHECKPOINT_EVERY_S * 1000
    controller._checkpoint_periodically()

    assert checkpoints == [("show-1", "ep-1", _CHECKPOINT_EVERY_S * 1000)]


def test_the_write_is_throttled() -> None:
    """It persists the whole library, so once a second would be wasteful."""
    controller, checkpoints, fake = _rig()

    for second in range(1, _CHECKPOINT_EVERY_S):
        fake.position = second * 1000
        controller._checkpoint_periodically()
    assert checkpoints == [], "nothing written before the interval elapses"

    fake.position = _CHECKPOINT_EVERY_S * 1000
    controller._checkpoint_periodically()
    assert len(checkpoints) == 1


def test_it_keeps_checkpointing_as_the_episode_runs() -> None:
    controller, checkpoints, fake = _rig()

    for second in range(1, _CHECKPOINT_EVERY_S * 3 + 1):
        fake.position = second * 1000
        controller._checkpoint_periodically()

    assert [ms for _s, _g, ms in checkpoints] == [
        _CHECKPOINT_EVERY_S * 1000,
        _CHECKPOINT_EVERY_S * 2000,
        _CHECKPOINT_EVERY_S * 3000,
    ]


def test_a_large_backward_seek_checkpoints_immediately() -> None:
    """The throttle compares distance, not direction: jumping back is exactly
    the moment the stored position is most wrong."""
    controller, checkpoints, fake = _rig()
    fake.position = 60 * 60 * 1000
    controller._checkpoint_periodically()
    checkpoints.clear()

    fake.position = 10 * 60 * 1000
    controller._checkpoint_periodically()

    assert [ms for _s, _g, ms in checkpoints] == [10 * 60 * 1000]


def test_nothing_is_written_while_paused() -> None:
    """Pause already checkpoints once; repeating it every second would rewrite
    the library for a listener who walked away."""
    controller, checkpoints, fake = _rig()
    controller._state.state = PodcastPlayerState.PAUSED

    fake.position = _CHECKPOINT_EVERY_S * 5000
    controller._checkpoint_periodically()

    assert checkpoints == []


def test_nothing_is_written_when_stopped() -> None:
    controller, checkpoints, fake = _rig()
    controller._state.state = PodcastPlayerState.STOPPED

    fake.position = _CHECKPOINT_EVERY_S * 5000
    controller._checkpoint_periodically()

    assert checkpoints == []


def test_the_existing_poll_drives_it() -> None:
    """Wired to the timer that already runs, not a second timer."""
    controller, checkpoints, fake = _rig()
    controller._auto_skip_outro_ms = 0

    fake.position = _CHECKPOINT_EVERY_S * 1000
    controller._on_outro_poll(None)

    assert len(checkpoints) == 1
