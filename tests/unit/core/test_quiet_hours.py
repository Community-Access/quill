"""11.9: a window in which the apps stop speaking on their own.

The distinction that has to hold: quiet hours never silence the answer to a
keypress. Everything still happens -- feeds are checked, downloads run -- and
only the speech nobody asked for waits.
"""

from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from quill.core import quiet_hours
from quill.core.quiet_hours import Kind, QuietHours


def _night() -> QuietHours:
    return QuietHours(enabled=True, start="22:00", end="07:00")


@pytest.mark.parametrize("moment", [time(22, 0), time(23, 59), time(0, 0), time(6, 59)])
def test_a_window_that_crosses_midnight_covers_the_night(moment: time) -> None:
    assert quiet_hours.is_quiet_at(_night(), moment) is True


@pytest.mark.parametrize("moment", [time(7, 0), time(12, 0), time(21, 59)])
def test_and_nothing_outside_it(moment: time) -> None:
    assert quiet_hours.is_quiet_at(_night(), moment) is False


def test_a_daytime_window_does_not_wrap() -> None:
    hours = QuietHours(enabled=True, start="09:00", end="17:00")
    assert quiet_hours.is_quiet_at(hours, time(12, 0)) is True
    assert quiet_hours.is_quiet_at(hours, time(8, 59)) is False
    assert quiet_hours.is_quiet_at(hours, time(17, 0)) is False


def test_a_zero_length_window_means_nothing_not_everything() -> None:
    """Somebody who set both ends the same has not asked for permanent silence."""
    hours = QuietHours(enabled=True, start="09:00", end="09:00")
    assert quiet_hours.is_quiet_at(hours, time(9, 0)) is False
    assert quiet_hours.is_quiet_at(hours, time(3, 0)) is False


def test_turned_off_is_never_quiet() -> None:
    hours = QuietHours(enabled=False, start="22:00", end="07:00")
    assert quiet_hours.is_quiet_at(hours, time(2, 0)) is False


@pytest.mark.parametrize(
    "kind", [Kind.TICK, Kind.NEW_EPISODE, Kind.DOWNLOAD, Kind.REMINDER, Kind.BACKGROUND]
)
def test_unprompted_speech_is_held_back(kind: str) -> None:
    assert quiet_hours.silences(_night(), kind, time(2, 0)) is True


def test_urgent_speech_is_never_held_back() -> None:
    """A recording that failed at 3 a.m. is the thing somebody set this for."""
    assert quiet_hours.silences(_night(), Kind.URGENT, time(2, 0)) is False


def test_an_answer_to_a_keypress_is_never_held_back() -> None:
    """Anything not in the silenceable vocabulary is prompted, by construction."""
    assert quiet_hours.silences(_night(), "playing_now", time(2, 0)) is False


def test_reminders_can_be_let_through_by_one_explicit_override() -> None:
    hours = QuietHours(enabled=True, start="22:00", end="07:00", allow_reminders=True)
    assert quiet_hours.silences(hours, Kind.REMINDER, time(2, 0)) is False
    assert quiet_hours.silences(hours, Kind.TICK, time(2, 0)) is True


def test_the_readout_says_what_it_does_not_do() -> None:
    text = quiet_hours.describe(_night())
    assert "still checked" in text
    assert "press a key for still answers" in text
    assert "Reminders are held back too." in text


def test_the_off_readout_is_not_a_promise_of_silence() -> None:
    assert quiet_hours.describe(QuietHours()).startswith("Quiet hours are off.")


def test_an_unreadable_clock_falls_back_rather_than_raising() -> None:
    assert quiet_hours.parse_clock("half past nine", "07:00") == time(7, 0)
    assert quiet_hours.parse_clock("25:00", "07:00") == time(7, 0)
    assert quiet_hours.parse_clock("", "") == time(0, 0)


def test_the_window_round_trips_through_the_shared_file(tmp_path: Path) -> None:
    hours = QuietHours(enabled=True, start="23:30", end="06:30", allow_reminders=True)
    quiet_hours.save_quiet_hours(tmp_path, hours)
    back = quiet_hours.load_quiet_hours(tmp_path)
    assert (back.enabled, back.start, back.end, back.allow_reminders) == (
        True,
        "23:30",
        "06:30",
        True,
    )


def test_a_missing_or_corrupt_file_reads_as_off(tmp_path: Path) -> None:
    assert quiet_hours.load_quiet_hours(tmp_path).enabled is False
    quiet_hours.store_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert quiet_hours.load_quiet_hours(tmp_path).enabled is False


def test_the_toggle_sentence_names_the_window() -> None:
    assert quiet_hours.toggle_sentence(_night()).startswith("Quiet hours on, 22:00 to 07:00.")
    assert quiet_hours.toggle_sentence(QuietHours()) == (
        "Quiet hours off. Background announcements speak again."
    )
