"""A stall becomes a state, and stops lying to every surface that reads one.

Before this, ``MpvRadioEngine`` called the host's announcer directly when mpv
reported ``paused-for-cache``: the words "Buffering..." arrived, and the
playback state stayed PLAYING. The status-bar cell, the tray tooltip and the
mini-player therefore all claimed playback through dead air.

Splitting BUFFERING out of PLAYING is the fix, and the risk: every site that
compared against PLAYING alone meant *running*, and would have broken quietly.
The last two tests here pin the two that would have hurt most -- Play/Pause
turning into a restart mid-stall, and the once-per-run earcon latch.
"""

from __future__ import annotations

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.ui.radio.playback_state import ACTIVE_STATES, RUNNING_STATES, RadioPlayerState
from quill.ui.radio.player_controller import RadioPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self.paused = False
        self.played = False
        self.loads: list[str] = []

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        self.played = True

    def pause(self) -> None:
        self.paused = True

    def close(self) -> None:
        pass

    def set_volume(self, percent: int) -> None:
        pass


def _controller() -> tuple[RadioPlayerController, _FakeEngine, list[str]]:
    """A controller pinned to the classic engine, with the buffering announcer
    recorded rather than spoken. "wx" pins the engine so a dev machine with a
    real libmpv does not swap the fake out from under the test."""
    frame = wx.Frame(None)
    said: list[str] = []
    controller = RadioPlayerController(
        frame,
        playback_engine="wx",
        on_buffering=lambda: said.append("Buffering..."),
    )
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller._state.station = RadioStation(name="WQXR", stream_url="http://example.test/wqxr")
    controller._state.state = RadioPlayerState.PLAYING
    return controller, fake, said


# -- the state itself ----------------------------------------------------------


def test_a_stall_leaves_playing_and_still_announces() -> None:
    controller, _fake, said = _controller()

    controller._handle_buffering(True)

    assert controller.state.state is RadioPlayerState.BUFFERING
    # The announcement is unchanged: the once-per-run earcon latch lives in the
    # host and is not the controller's to second-guess.
    assert said == ["Buffering..."]
    assert controller.state.status_text == "Radio: buffering WQXR..."


def test_the_end_of_a_stall_returns_to_playing() -> None:
    controller, _fake, _said = _controller()

    controller._handle_buffering(True)
    controller._handle_buffering(False)

    assert controller.state.state is RadioPlayerState.PLAYING
    assert controller.state.status_text == "Radio: playing WQXR"


def test_a_stall_report_after_a_stop_is_ignored() -> None:
    # A poll that lands after the listener moved on describes a stream nobody
    # is listening to; acting on it would resurrect a stopped player.
    controller, _fake, said = _controller()
    controller._state.state = RadioPlayerState.STOPPED

    controller._handle_buffering(True)

    assert controller.state.state is RadioPlayerState.STOPPED
    assert said == []


def test_a_stall_report_during_a_reconnect_is_ignored() -> None:
    controller, _fake, _said = _controller()
    controller._state.state = RadioPlayerState.RECONNECTING

    controller._handle_buffering(True)

    assert controller.state.state is RadioPlayerState.RECONNECTING


# -- the sets that stop the split from breaking everything else ----------------


def test_buffering_and_reconnecting_count_as_a_stream_being_on_the_air() -> None:
    # Twelve surfaces ask this: the Stop/Play label, the favorites context
    # menu, the browse dialogs' badge, the sleep inhibitor, the close guard.
    for state in (
        RadioPlayerState.CONNECTING,
        RadioPlayerState.BUFFERING,
        RadioPlayerState.PLAYING,
        RadioPlayerState.RECONNECTING,
    ):
        assert state in ACTIVE_STATES
    for state in (RadioPlayerState.STOPPED, RadioPlayerState.PAUSED, RadioPlayerState.ERROR):
        assert state not in ACTIVE_STATES


def test_running_is_narrower_than_active() -> None:
    # Connecting and reconnecting are on the way to running, not running.
    assert RUNNING_STATES == {RadioPlayerState.PLAYING, RadioPlayerState.BUFFERING}
    assert RUNNING_STATES < ACTIVE_STATES


def test_play_pause_during_a_stall_pauses_instead_of_restarting() -> None:
    # The regression the split would have introduced: comparing against PLAYING
    # alone dropped a stalled stream through to "play this station", so the one
    # key a listener presses to silence a stuttering stream restarted it.
    controller, fake, _said = _controller()
    controller._handle_buffering(True)

    controller.toggle_play_pause()

    assert fake.paused is True
    assert fake.loads == []
    assert controller.state.state is RadioPlayerState.PAUSED
