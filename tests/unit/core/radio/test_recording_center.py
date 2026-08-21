"""The Recordings window says what is happening and what happens next.

The status line counted rows -- "14 recorded, 1 recording now, 3 scheduled" --
which answers "how many?" and never answers "when?". The one thing somebody
opens that window for on a Thursday evening is whether tonight's show is
covered, and that fact lived only inside the scheduled rows.

Note what these tests do *not* cover, deliberately: there is no third window.
``recordings_index.list_recordings`` already returns active, recorded and
scheduled in one list, so the gap was the sentence above it, not the surface.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from quill.core.radio.recording_center import (
    NextUp,
    describe_next,
    next_from_entries,
    summary_line,
)
from quill.core.radio.recording_progress import RecordingProgress

_NOW = datetime(2026, 8, 20, 19, 0, 0)  # a Thursday evening


def _active(minutes_ago: int, minutes: int, requested: bool) -> RecordingProgress:
    return RecordingProgress(
        started_at=_NOW - timedelta(minutes=minutes_ago),
        minutes=minutes,
        duration_requested=requested,
    )


def _line(**kwargs: object) -> str:
    base: dict[str, object] = {
        "active": [],
        "next_up": None,
        "recorded_count": 0,
        "scheduled_count": 0,
        "folder": "",
        "now": _NOW,
    }
    base.update(kwargs)
    return summary_line(**base)  # type: ignore[arg-type]


def test_the_headline_leads_with_now_then_next_then_the_shelf() -> None:
    line = _line(
        active=[_active(18, 60, True)],
        next_up=NextUp("KFI", _NOW + timedelta(days=1, hours=-8)),
        recorded_count=14,
        folder=r"D:\Music",
    )
    assert line.startswith("Recording, 42 min left.")
    assert "Next: KFI at 11:00 tomorrow" in line
    assert "14 recorded" in line
    assert line.endswith(r"In D:\Music.")


def test_an_idle_evening_with_nothing_scheduled_says_both() -> None:
    assert _line(recorded_count=3) == "Not recording. Nothing scheduled. 3 recorded."


def test_a_recording_with_no_chosen_length_counts_up() -> None:
    # Reuses recording_progress, so this sentence and the F6 status cell can
    # never disagree about the same capture.
    assert _line(active=[_active(18, 180, False)]).startswith("Recording, 18 min so far.")


def test_the_next_occurrence_within_the_hour_is_given_in_minutes() -> None:
    # "in 12 minutes" tells you whether you can leave the room; "at 19:12"
    # makes you work it out.
    assert describe_next(NextUp("KFI", _NOW + timedelta(minutes=12)), _NOW) == "KFI in 12 minutes"
    assert describe_next(NextUp("KFI", _NOW + timedelta(seconds=30)), _NOW) == "KFI in 1 minute"


def test_further_out_uses_a_day_a_person_would_say() -> None:
    assert "today" in describe_next(NextUp("KFI", _NOW + timedelta(hours=3)), _NOW)
    assert "tomorrow" in describe_next(NextUp("KFI", _NOW + timedelta(days=1)), _NOW)
    # Inside a week, the weekday is unambiguous and needs no counting.
    assert "Sunday" in describe_next(NextUp("KFI", _NOW + timedelta(days=3)), _NOW)
    # Past a week it stops being unambiguous, so the date comes back.
    assert "2026-09-03" in describe_next(NextUp("KFI", _NOW + timedelta(days=14)), _NOW)


def test_schedules_that_cannot_fire_are_reported_as_such() -> None:
    # THE CASE THAT SENT PEOPLE HUNTING: three scheduled entries, none of them
    # coming up. "3 scheduled" alone reads as covered.
    line = _line(scheduled_count=3, next_up=None)
    assert "3 scheduled, none coming up" in line


def test_no_next_up_and_no_schedules_reads_as_nothing_scheduled() -> None:
    assert "Nothing scheduled" in _line()


def test_the_soonest_enabled_occurrence_wins() -> None:
    entries = [
        SimpleNamespace(station_name="Later", enabled=True, _next=_NOW + timedelta(hours=5)),
        SimpleNamespace(station_name="Sooner", enabled=True, _next=_NOW + timedelta(hours=2)),
    ]
    next_up = _next_from(entries)
    assert next_up is not None
    assert next_up.station_name == "Sooner"


def test_a_disabled_entry_is_not_coming_up() -> None:
    entries = [SimpleNamespace(station_name="Off", enabled=False, _next=_NOW + timedelta(hours=1))]
    assert _next_from(entries) is None


def test_an_occurrence_in_the_past_is_not_coming_up() -> None:
    entries = [SimpleNamespace(station_name="Gone", enabled=True, _next=_NOW - timedelta(hours=1))]
    assert _next_from(entries) is None


def test_one_unreadable_entry_does_not_lose_the_others() -> None:
    entries = [
        SimpleNamespace(station_name="Broken", enabled=True, _next="boom"),
        SimpleNamespace(station_name="Fine", enabled=True, _next=_NOW + timedelta(hours=1)),
    ]
    next_up = _next_from(entries)
    assert next_up is not None
    assert next_up.station_name == "Fine"


def _next_from(entries: list[SimpleNamespace]) -> NextUp | None:
    """Drive ``next_from_entries`` with a stubbed occurrence calculator.

    The real one lives in ``recording_schedule`` and owns recurrence, weekday
    and time-zone arithmetic; re-implementing any of that here would test a
    second copy rather than the module under test.
    """
    import quill.core.radio.recording_schedule as schedule

    original = schedule.next_occurrence

    def _fake(entry: object, now: datetime) -> datetime | None:
        value = getattr(entry, "_next", None)
        if not isinstance(value, datetime):
            raise ValueError("unreadable entry")
        return value

    schedule.next_occurrence = _fake  # type: ignore[assignment]
    try:
        return next_from_entries(list(entries), _NOW)
    finally:
        schedule.next_occurrence = original  # type: ignore[assignment]
