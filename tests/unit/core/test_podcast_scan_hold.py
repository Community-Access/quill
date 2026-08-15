"""Hold to scan forward, release to drop back.

The one thing that must never happen is being left at four times speed without
knowing it -- a player stuck at 4x with no announcement is indistinguishable
from a broken one. Everything here defends that.
"""

from __future__ import annotations

from quill.core.podcasts.scan_hold import (
    BEGIN_MESSAGE,
    RELEASE_GRACE_MS,
    SCAN_RATE,
    ScanState,
    begin,
    end,
    end_message,
    keep_alive,
    should_end,
)


def test_four_times_is_fast_enough_to_be_useful_and_slow_enough_to_follow() -> None:
    # Past about six it is noise, and scanning you cannot follow is just
    # seeking with extra steps.
    assert 2.0 < SCAN_RATE <= 6.0


def test_holding_the_key_starts_the_scan_once() -> None:
    state = ScanState()
    assert begin(state, current_rate=1.5, now_ms=0) is True
    # Auto-repeat: the fiftieth repeat must extend the scan, not restart it.
    assert begin(state, current_rate=SCAN_RATE, now_ms=50) is False
    assert state.restore_rate == 1.5


def test_the_speed_you_were_at_is_the_speed_you_get_back() -> None:
    # Somebody who listens at 1.5 must not be handed back 1.0 for scanning.
    state = ScanState()
    begin(state, current_rate=1.5, now_ms=0)
    assert end(state) == 1.5
    assert state.active is False


def test_a_scan_ends_when_the_repeats_stop() -> None:
    state = ScanState()
    begin(state, current_rate=1.0, now_ms=1000)
    assert should_end(state, now_ms=1000 + RELEASE_GRACE_MS - 1) is False
    assert should_end(state, now_ms=1000 + RELEASE_GRACE_MS) is True


def test_a_repeat_keeps_it_alive() -> None:
    state = ScanState()
    begin(state, current_rate=1.0, now_ms=0)
    keep_alive(state, now_ms=RELEASE_GRACE_MS)
    assert should_end(state, now_ms=RELEASE_GRACE_MS + 1) is False


def test_nothing_ends_a_scan_that_never_started() -> None:
    assert should_end(ScanState(), now_ms=10_000) is False


def test_the_grace_window_outlasts_the_slowest_key_repeat() -> None:
    # Windows' slowest auto-repeat is about two per second; anything under
    # 500 ms of grace would make a held key stutter in and out of scanning.
    assert RELEASE_GRACE_MS >= 400


def test_both_edges_are_announced_and_the_end_names_the_speed() -> None:
    assert BEGIN_MESSAGE.endswith(".")
    assert "4" in BEGIN_MESSAGE
    assert end_message(1.0) == "Back to normal speed."
    assert end_message(1.5) == "Back to 1.5 times speed."
    assert end_message(0.8) == "Back to 0.8 times speed."


def test_a_broken_restore_rate_never_yields_silence() -> None:
    state = ScanState(active=True, restore_rate=0.0)
    assert end(state) == 1.0
