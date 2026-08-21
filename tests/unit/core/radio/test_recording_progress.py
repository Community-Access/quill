"""The Recording cell says how far along a capture is, and never invents a deadline.

The status strip's Recording cell used to read ``Idle`` / ``Recording`` /
``2 recording`` while the sleep-timer cell beside it said ``12 min left``, so
the one question somebody arrows over to that cell to ask went unanswered.

The trap these guard is the one that makes this more than a subtraction: every
job carries ``minutes``, but for a capture the listener never gave a length to
that number is ``settings.max_duration_minutes`` -- a safety cap. Counting down
to a cap announces an intention nobody expressed, so an open-ended capture must
count *up* and a deliberate one must count *down*.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from quill.core.radio.recording_progress import (
    RecordingProgress,
    recording_cell_help,
    recording_cell_text,
)

_NOW = datetime(2026, 8, 20, 14, 0, 0)


def _open_ended(minutes_ago: int, cap: int = 180) -> RecordingProgress:
    """A Record Now capture: a safety cap stands in for a length nobody chose."""
    return RecordingProgress(
        started_at=_NOW - timedelta(minutes=minutes_ago),
        minutes=cap,
        duration_requested=False,
    )


def _deliberate(minutes_ago: int, length: int) -> RecordingProgress:
    """A scheduled capture, or a length typed into Record Station."""
    return RecordingProgress(
        started_at=_NOW - timedelta(minutes=minutes_ago),
        minutes=length,
        duration_requested=True,
    )


def test_no_recordings_reads_idle() -> None:
    assert recording_cell_text([], _NOW) == "Idle"


def test_a_deliberate_length_counts_down() -> None:
    # Asked for 60 minutes, 18 gone: the listener chose this end, so show it.
    assert recording_cell_text([_deliberate(18, 60)], _NOW) == "42 min left"


def test_an_open_ended_capture_counts_up_instead() -> None:
    # THE CASE THIS EXISTS FOR. 180 is a disk-safety cap, not a plan, so
    # "162 min left" would be the app inventing a deadline.
    assert recording_cell_text([_open_ended(18)], _NOW) == "18 min so far"


def test_a_zero_length_is_not_a_deadline_either() -> None:
    # minutes <= 0 cannot describe an end whatever the flag says.
    job = RecordingProgress(
        started_at=_NOW - timedelta(minutes=5), minutes=0, duration_requested=True
    )
    assert recording_cell_text([job], _NOW) == "5 min so far"


def test_elapsed_floors_and_remaining_ceilings() -> None:
    # 18m30s elapsed is "at least 18", and 41m30s left is "no more than 42".
    # Rounding both the same way would make one of the two overstate.
    started = _NOW - timedelta(minutes=18, seconds=30)
    assert recording_cell_text([RecordingProgress(started, 0, False)], _NOW) == "18 min so far"
    assert recording_cell_text([RecordingProgress(started, 60, True)], _NOW) == "42 min left"


def test_sub_minute_edges_use_words_rather_than_zero() -> None:
    # "0 min left" reads as finished when it is not.
    assert recording_cell_text([_deliberate(60, 60)], _NOW) == "less than a minute left"
    assert recording_cell_text([_open_ended(0)], _NOW) == "under a minute so far"


def test_several_recordings_lead_with_the_count() -> None:
    text = recording_cell_text([_deliberate(18, 60), _deliberate(5, 30)], _NOW)
    # The soonest end wins the one number the cell has room for: 25 beats 42.
    assert text == "2 recordings, 25 min left"


def test_a_deliberate_end_outranks_a_longer_open_ended_capture() -> None:
    # An open-ended capture running for three hours has no end to miss; the
    # 30-minute one does, so that is the number worth the space.
    text = recording_cell_text([_open_ended(180), _deliberate(5, 30)], _NOW)
    assert text == "2 recordings, 25 min left"


def test_several_open_ended_recordings_report_the_longest_running() -> None:
    text = recording_cell_text([_open_ended(4), _open_ended(41)], _NOW)
    assert text == "2 recordings, 41 min so far"


def test_a_clock_that_moved_backwards_never_reports_negative_time() -> None:
    # A daylight-saving fall-back or an NTP step must not produce "-59 min".
    future = RecordingProgress(
        started_at=_NOW + timedelta(minutes=59), minutes=0, duration_requested=False
    )
    assert recording_cell_text([future], _NOW) == "under a minute so far"


def test_a_capture_past_its_end_clamps_rather_than_going_negative() -> None:
    assert recording_cell_text([_deliberate(90, 60)], _NOW) == "less than a minute left"


def test_the_hint_says_which_measurement_is_on_screen() -> None:
    # The number alone cannot tell you whether it counts up or down.
    assert "counts down" in recording_cell_help([_deliberate(18, 60)], _NOW)
    assert "how long the recording has been running" in recording_cell_help([_open_ended(18)], _NOW)


def test_the_hint_stays_general_when_nothing_is_recording() -> None:
    help_text = recording_cell_help([], _NOW)
    assert "Press Enter to start or stop" in help_text
    assert "counts down" not in help_text
