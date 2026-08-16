"""Being awake when a scheduled recording is due.

The bug behind this module was invisible from inside the app: a recording set
for 11:00 started at 11:03, and the only honest explanation was that the
computer had been asleep and nothing had asked it not to be. The scheduler
polls every twenty seconds, so twenty seconds is the whole budget -- minutes
mean the machine, not the code.

What is pinned here is the arithmetic that decides *when* to hold standby off
and *when* to ask the OS to wake, against a clock passed in. The Windows end
(schtasks) and the UI glue are deliberately elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.core.radio.schedule_wake import (
    IMMINENT_MINUTES,
    describe,
    is_imminent,
    next_wake_moment,
    seconds_until_next,
)


def _entry(hhmm: str, *, enabled: bool = True, recurrence: str = "daily") -> RecordingScheduleEntry:
    return RecordingScheduleEntry(
        id=f"e-{hhmm}-{recurrence}",
        station_name="A Station",
        stream_url="https://example.org/stream",
        run_at=f"2026-01-01T{hhmm}" if ":" in hhmm else hhmm,
        duration_minutes=180,
        recurrence=recurrence,
        enabled=enabled,
    )


def test_nothing_scheduled_is_not_a_reason_to_stay_awake() -> None:
    now = datetime(2026, 8, 15, 10, 0)
    assert seconds_until_next([], now) is None
    assert is_imminent([], now) is False
    assert next_wake_moment([], now) is None
    assert describe([], now) == "No recordings are scheduled."


def test_the_soonest_entry_wins() -> None:
    now = datetime(2026, 8, 15, 10, 0)
    entries = [_entry("14:00"), _entry("11:00"), _entry("23:30")]
    assert seconds_until_next(entries, now) == 60 * 60


def test_a_disabled_entry_never_keeps_the_machine_awake() -> None:
    now = datetime(2026, 8, 15, 10, 58)
    assert is_imminent([_entry("11:00", enabled=False)], now) is False


def test_standby_is_held_off_as_the_moment_approaches() -> None:
    """The 11:03 bug, in one assertion.

    At 10:58 the recording is two minutes out and the machine must not be
    allowed to doze; at 10:50 it is twelve minutes out and there is no reason
    to keep anybody's computer up.
    """
    entries = [_entry("11:00")]
    assert is_imminent(entries, datetime(2026, 8, 15, 10, 58)) is True
    assert is_imminent(entries, datetime(2026, 8, 15, 10, 50)) is False


def test_the_imminent_window_is_the_documented_one() -> None:
    entries = [_entry("11:00")]
    edge = datetime(2026, 8, 15, 11, 0) - timedelta(minutes=IMMINENT_MINUTES)
    assert is_imminent(entries, edge) is True
    assert is_imminent(entries, edge - timedelta(seconds=1)) is False


def test_the_wake_is_registered_before_the_recording_not_at_it() -> None:
    """Waking *at* 11:00 is too late: the machine has to come up, maybe show a
    sign-in screen, and possibly start the app, before the scheduler's first
    poll can fire the entry."""
    now = datetime(2026, 8, 15, 8, 0)
    moment = next_wake_moment([_entry("11:00")], now, lead_minutes=2)
    assert moment == datetime(2026, 8, 15, 10, 58)


def test_a_wake_is_never_registered_in_the_past() -> None:
    """A moment that has already passed either fires instantly or is refused,
    and neither is what the caller meant."""
    now = datetime(2026, 8, 15, 10, 59, 30)
    moment = next_wake_moment([_entry("11:00")], now, lead_minutes=2)
    assert moment is not None
    assert moment >= now + timedelta(minutes=1)


def test_an_occurrence_under_way_reads_as_now_rather_than_negative() -> None:
    entries = [_entry("11:00")]
    assert seconds_until_next(entries, datetime(2026, 8, 15, 11, 0)) == 0.0


def test_a_malformed_entry_costs_only_itself() -> None:
    """This runs on a UI timer; one unparseable time must not take the feature
    down with it."""
    entries = [_entry("not a time"), _entry("11:00")]
    assert seconds_until_next(entries, datetime(2026, 8, 15, 10, 0)) == 60 * 60


def test_the_countdown_is_spoken_in_words() -> None:
    now = datetime(2026, 8, 15, 8, 55)
    said = describe([_entry("11:00")], now)
    assert said == "Next scheduled recording in 2 hours, 5 minutes."
    assert ":" not in said  # never a timecode -- this is read aloud


def test_a_recording_due_now_says_so() -> None:
    assert describe([_entry("11:00")], datetime(2026, 8, 15, 11, 0)) == (
        "A scheduled recording is due now."
    )
