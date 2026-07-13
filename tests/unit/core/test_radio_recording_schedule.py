"""Tests for scheduled radio recordings: due-entry logic and persistence
(pure; the scheduler thread itself is exercised via due_entries directly)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from quill.core.radio.recording_schedule import (
    RecordingScheduleEntry,
    due_entries,
    is_due,
    load_schedule,
    new_id,
    save_schedule,
)


def _entry(**overrides: object) -> RecordingScheduleEntry:
    base = dict(
        id="e1",
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        recurrence="once",
        run_at="2026-07-14T08:00:00",
        duration_minutes=60,
    )
    base.update(overrides)
    return RecordingScheduleEntry(**base)  # type: ignore[arg-type]


def test_once_is_due_after_its_moment_and_not_fired_yet() -> None:
    entry = _entry(recurrence="once", run_at="2026-07-14T08:00:00")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    assert is_due(entry, datetime(2026, 7, 14, 7, 59, 59)) is False


def test_once_is_not_due_again_after_firing() -> None:
    entry = _entry(recurrence="once", run_at="2026-07-14T08:00:00", last_fired_date="2026-07-14")
    assert is_due(entry, datetime(2026, 7, 14, 9, 0, 0)) is False


def test_disabled_entry_never_due() -> None:
    entry = _entry(enabled=False)
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is False


def test_daily_is_due_at_matching_time_once_per_day() -> None:
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    assert is_due(entry, datetime(2026, 7, 14, 8, 1, 0)) is False
    entry.last_fired_date = "2026-07-14"
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is False
    # A new day resets eligibility.
    assert is_due(entry, datetime(2026, 7, 15, 8, 0, 0)) is True


def test_weekly_only_due_on_matching_weekday() -> None:
    # 2026-07-14 is a Tuesday (weekday 1).
    entry = _entry(recurrence="weekly", run_at="2026-01-01T08:00:00", weekday=1)
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    entry2 = _entry(recurrence="weekly", run_at="2026-01-01T08:00:00", weekday=2)
    assert is_due(entry2, datetime(2026, 7, 14, 8, 0, 0)) is False


def test_due_entries_filters_a_mixed_list() -> None:
    now = datetime(2026, 7, 14, 8, 0, 0)
    due = _entry(id="due", recurrence="once", run_at="2026-07-14T08:00:00")
    not_due = _entry(id="not-due", recurrence="once", run_at="2026-07-15T08:00:00")
    result = due_entries([due, not_due], now)
    assert [e.id for e in result] == ["due"]


def test_from_dict_requires_core_fields() -> None:
    assert RecordingScheduleEntry.from_dict({"station_name": "X"}) is None
    assert (
        RecordingScheduleEntry.from_dict({
            "id": "e1",
            "station_name": "X",
            "stream_url": "https://x",
            "run_at": "2026-01-01T08:00:00",
        })
        is not None
    )


def test_from_dict_defaults_unknown_recurrence_to_once() -> None:
    entry = RecordingScheduleEntry.from_dict({
        "id": "e1",
        "station_name": "X",
        "stream_url": "https://x",
        "run_at": "2026-01-01T08:00:00",
        "recurrence": "monthly",
    })
    assert entry is not None
    assert entry.recurrence == "once"


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    entries = [_entry(id=new_id()), _entry(id=new_id(), recurrence="weekly", weekday=3)]
    save_schedule(tmp_path, entries)
    reloaded = load_schedule(tmp_path)
    assert len(reloaded) == 2
    assert {e.id for e in reloaded} == {e.id for e in entries}


def test_load_schedule_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_schedule(tmp_path) == []


def test_load_schedule_corrupt_file_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "radio_recording_schedule.json").write_text("not json", encoding="utf-8")
    assert load_schedule(tmp_path) == []
