"""Tests for scheduled radio recordings: due-entry logic and persistence
(pure; the scheduler thread itself is exercised via due_entries directly)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quill.core.radio.recording_schedule import (
    RecordingScheduleEntry,
    due_entries,
    is_due,
    load_schedule,
    new_id,
    save_schedule,
)

_UTC = UTC


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


# -- per-entry timezone (#7): interpret the entry's wall-clock in its own zone --


def test_timezone_field_round_trips_and_defaults_to_empty() -> None:
    assert _entry().timezone == ""
    entry = _entry(timezone="America/New_York")
    reloaded = RecordingScheduleEntry.from_dict(entry.to_dict())
    assert reloaded is not None
    assert reloaded.timezone == "America/New_York"
    # A legacy record without the key defaults to "" (local).
    legacy = RecordingScheduleEntry.from_dict({
        "id": "e1",
        "station_name": "X",
        "stream_url": "https://x",
        "run_at": "2026-01-01T08:00:00",
    })
    assert legacy is not None
    assert legacy.timezone == ""


def test_zoned_daily_fires_at_the_entrys_local_hour_not_the_systems() -> None:
    # A daily 19:00 America/New_York entry. In July (EDT, UTC-4), 19:00 local
    # is 23:00 UTC. It must fire at that instant regardless of where the machine
    # (and the passed `now`) is -- the Pacific-user-records-an-Eastern-show case.
    entry = _entry(recurrence="daily", run_at="2026-01-01T19:00:00", timezone="America/New_York")
    assert is_due(entry, datetime(2026, 7, 14, 23, 0, tzinfo=_UTC)) is True  # 19:00 EDT
    assert is_due(entry, datetime(2026, 7, 14, 22, 0, tzinfo=_UTC)) is False  # 18:00 EDT
    assert is_due(entry, datetime(2026, 7, 15, 2, 0, tzinfo=_UTC)) is False  # 22:00 EDT


def test_zoned_weekly_uses_the_weekday_in_the_entrys_zone() -> None:
    # 21:00 America/Los_Angeles Tuesday. In July (PDT, UTC-7) that is 04:00 UTC
    # Wednesday -- the UTC weekday differs from the entry-zone weekday, and the
    # entry-zone weekday (Tuesday) is what must match.
    entry = _entry(
        recurrence="weekly", run_at="2026-01-01T21:00:00", weekday=1, timezone="America/Los_Angeles"
    )
    # 2026-07-14 is a Tuesday; 21:00 PDT == 2026-07-15 04:00 UTC.
    assert is_due(entry, datetime(2026, 7, 15, 4, 0, tzinfo=_UTC)) is True
    # Same wall clock a week's wrong day: 2026-07-15 21:00 PDT (a Wednesday).
    assert is_due(entry, datetime(2026, 7, 16, 4, 0, tzinfo=_UTC)) is False


def test_zoned_once_compares_the_absolute_instant() -> None:
    # A one-time 19:00 America/New_York recording fires at the real instant,
    # 23:00 UTC, not when the machine clock reads 19:00.
    entry = _entry(recurrence="once", run_at="2026-07-14T19:00:00", timezone="America/New_York")
    assert is_due(entry, datetime(2026, 7, 14, 23, 0, tzinfo=_UTC)) is True
    assert is_due(entry, datetime(2026, 7, 14, 22, 59, tzinfo=_UTC)) is False


def test_invalid_timezone_degrades_to_local_naive_behavior() -> None:
    # A bad zone name must not crash the scheduler thread; it degrades to the
    # naive local comparison (as if timezone were empty).
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00", timezone="Not/AZone")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True


def test_scheduler_update_replaces_in_place_and_persists(tmp_path: Path) -> None:
    from quill.core.radio.recording_schedule import RecordingScheduler

    # A scheduler with a stubbed recorder; we only exercise the store methods.
    class _NullRecorder:
        def start(self, **_kwargs: object) -> None:  # pragma: no cover - not called
            raise AssertionError

    from quill.core.radio.recording import RecordingSettings

    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=_NullRecorder(),  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
    )
    try:
        original = _entry(id="k1", station_name="Old", recurrence="daily")
        scheduler.add(original)
        edited = _entry(id="k1", station_name="New", recurrence="daily", duration_minutes=30)
        assert scheduler.update(edited) is True
        assert [e.station_name for e in scheduler.entries] == ["New"]
        assert scheduler.update(_entry(id="missing")) is False
        # Persisted: a fresh load sees the edit.
        reloaded = load_schedule(tmp_path)
        assert len(reloaded) == 1
        assert reloaded[0].station_name == "New"
        assert reloaded[0].duration_minutes == 30
    finally:
        scheduler.shutdown()
