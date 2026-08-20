"""A dropped live station reconnects; a finished recording does not.

The fault these pin (John, 2026-08-13): iHeart's HLS form carries a thirty-second
window and a five-second token, so one failed refresh drains the buffer and the
stream ends twenty to thirty seconds later. The controller read EOF on a live
station as "the stream ended" and stopped, with no retry reachable -- the only
retry path there is gated on ``CONNECTING``.

These exercise ``quill.ui.radio.live_reconnect`` against a stand-in host rather
than a real controller, for the same reason ``resume_playback`` is tested that
way: the module takes a host and touches nothing else, so a real wx controller
would add a window to the test and prove nothing extra.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.radio import live_reconnect
from quill.ui.radio.playback_state import RadioPlayerState


class _State:
    def __init__(self, station: Any) -> None:
        self.station = station
        self.state = RadioPlayerState.PLAYING
        self.message = ""


class _Station:
    def __init__(self, name: str = "KFI AM 640") -> None:
        self.display_name = name


class _Engine:
    def __init__(self, *, loads: bool = True) -> None:
        self.loads = loads
        self.load_calls: list[str] = []

    def load(self, url: str) -> bool:
        self.load_calls.append(url)
        return self.loads


class _Host:
    """The controller surface ``live_reconnect`` actually uses."""

    def __init__(self, *, bounded: bool = False, loads: bool = True) -> None:
        self._state = _State(_Station())
        self._engine = _Engine(loads=loads)
        self._play_token = 7
        self._bounded = bounded
        self.states: list[tuple[RadioPlayerState, str]] = []
        self.scheduled: list[tuple[int, Any]] = []

    def is_seekable(self) -> bool:
        return self._bounded

    def _resolve_playback_url(self, _station: Any) -> str:
        return "https://stream.example/zc177"

    def _set_state(self, state: RadioPlayerState, *, message: str = "", **_kw: Any) -> None:
        self._state.state = state
        self._state.message = message
        self.states.append((state, message))

    def _schedule_later(self, delay_ms: int, work: Any) -> None:
        self.scheduled.append((delay_ms, work))

    def run_scheduled(self) -> None:
        """Fire every pending retry, in order."""
        pending, self.scheduled = self.scheduled, []
        for _delay, work in pending:
            work()


def test_a_dropped_live_station_schedules_a_reconnect_and_says_so() -> None:
    host = _Host()

    assert live_reconnect.handle_finished(host) is True

    state, message = host.states[-1]
    # RECONNECTING, not CONNECTING: "connecting" is what a station somebody
    # just chose does. A listener who pressed nothing is owed a different word,
    # and the status line now renders this state's message instead of throwing
    # it away.
    assert state is RadioPlayerState.RECONNECTING
    # The station is named and the attempt is counted out loud: a silent retry
    # is indistinguishable from a hung player.
    assert "KFI AM 640" in message
    assert "Attempt 1 of 3" in message
    assert host.scheduled and host.scheduled[0][0] == live_reconnect.BACKOFF_MS[0]


def test_a_finished_recording_is_not_reconnected() -> None:
    # EOF on a bounded source is the real end of the thing. Reconnecting would
    # replay a LibriVox chapter the listener just finished.
    host = _Host(bounded=True)

    assert live_reconnect.handle_finished(host) is False
    assert host.states == []
    assert host.scheduled == []


def test_with_no_station_there_is_nothing_to_reconnect_to() -> None:
    host = _Host()
    host._state.station = None

    assert live_reconnect.handle_finished(host) is False


def test_the_retry_loads_the_stream_again() -> None:
    host = _Host()

    live_reconnect.handle_finished(host)
    host.run_scheduled()

    assert host._engine.load_calls == ["https://stream.example/zc177"]
    # Loading is not playing: the recovery is announced by _on_loaded, not here.
    assert host.states[-1][0] is RadioPlayerState.RECONNECTING


def test_a_retry_whose_token_is_stale_is_dropped() -> None:
    # Stop, or playing something else, moves the play token on. A retry that
    # was already waiting must not hijack whatever is playing now.
    host = _Host()
    live_reconnect.handle_finished(host)
    host._play_token += 1

    host.run_scheduled()

    assert host._engine.load_calls == []


def test_it_gives_up_after_three_attempts_and_says_why() -> None:
    host = _Host(loads=False)

    assert live_reconnect.handle_finished(host) is True
    for _ in range(6):  # more than enough to exhaust the budget
        if not host.scheduled:
            break
        host.run_scheduled()

    assert len(host._engine.load_calls) == live_reconnect.MAX_ATTEMPTS
    state, message = host.states[-1]
    assert state is RadioPlayerState.STOPPED
    assert "could not be reconnected" in message
    assert "off the air" in message
    # The counter is cleared, so the next station starts from a clean slate.
    assert live_reconnect._attempts(host) == 0


def test_backoff_widens_rather_than_hammering() -> None:
    host = _Host(loads=False)
    live_reconnect.handle_finished(host)
    delays = []
    for _ in range(live_reconnect.MAX_ATTEMPTS):
        if not host.scheduled:
            break
        delays.append(host.scheduled[0][0])
        host.run_scheduled()

    assert delays == sorted(delays)
    assert delays[0] < delays[-1]


def test_a_recovered_load_announces_once_and_clears() -> None:
    host = _Host()
    live_reconnect.handle_finished(host)

    first = live_reconnect.announce_recovery(host)
    second = live_reconnect.announce_recovery(host)

    assert "Reconnected to KFI AM 640." == first
    # Cleared, so an ordinary station change never claims a reconnection.
    assert second == ""


def test_an_ordinary_load_announces_nothing() -> None:
    host = _Host()
    assert live_reconnect.announce_recovery(host) == ""


@pytest.mark.parametrize("attempts", [0, 1, 2])
def test_reset_forgets_the_count(attempts: int) -> None:
    host = _Host()
    host._live_reconnect_attempts = attempts

    live_reconnect.reset(host)

    assert live_reconnect._attempts(host) == 0
