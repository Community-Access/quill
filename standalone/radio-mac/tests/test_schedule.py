"""Tests for quill_radio_mac.core.recording_schedule: due-entry logic
(once/daily/weekly, last_fired_date guards) and persistence. Pure; the
scheduler thread itself is exercised indirectly via due_entries and a
short-poll firing test with a fake recorder (no real ffmpeg/network)."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from quill_radio_mac.core.recording import RadioRecorder, RecordingSettings
from quill_radio_mac.core.recording_schedule import (
    RecordingScheduleEntry,
    RecordingScheduler,
    due_entries,
    is_due,
    load_schedule,
    new_id,
    save_schedule,
)


def _entry(**overrides: object) -> RecordingScheduleEntry:
    base: dict = dict(
        id="e1",
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        recurrence="once",
        run_at="2026-07-14T08:00:00",
        duration_minutes=60,
    )
    base.update(overrides)
    return RecordingScheduleEntry(**base)  # type: ignore[arg-type]


def test_once_is_due_after_its_moment_and_not_fired_yet():
    entry = _entry(recurrence="once", run_at="2026-07-14T08:00:00")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    assert is_due(entry, datetime(2026, 7, 14, 7, 59, 59)) is False


def test_once_is_not_due_again_after_firing():
    entry = _entry(recurrence="once", run_at="2026-07-14T08:00:00", last_fired_date="2026-07-14")
    assert is_due(entry, datetime(2026, 7, 14, 9, 0, 0)) is False


def test_disabled_entry_never_due():
    entry = _entry(enabled=False)
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is False


def test_once_with_unparseable_run_at_is_never_due():
    entry = _entry(recurrence="once", run_at="not-a-date")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is False


def test_daily_is_due_at_matching_time_once_per_day():
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00")
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    assert is_due(entry, datetime(2026, 7, 14, 8, 1, 0)) is False
    entry.last_fired_date = "2026-07-14"
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is False
    # A new day resets eligibility.
    assert is_due(entry, datetime(2026, 7, 15, 8, 0, 0)) is True


def test_weekly_only_due_on_matching_weekday():
    # 2026-07-14 is a Tuesday (weekday 1).
    entry = _entry(recurrence="weekly", run_at="2026-01-01T08:00:00", weekday=1)
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    entry2 = _entry(recurrence="weekly", run_at="2026-01-01T08:00:00", weekday=2)
    assert is_due(entry2, datetime(2026, 7, 14, 8, 0, 0)) is False


def test_due_entries_filters_a_mixed_list():
    now = datetime(2026, 7, 14, 8, 0, 0)
    due = _entry(id="due", recurrence="once", run_at="2026-07-14T08:00:00")
    not_due = _entry(id="not-due", recurrence="once", run_at="2026-07-15T08:00:00")
    result = due_entries([due, not_due], now)
    assert [e.id for e in result] == ["due"]


def test_from_dict_requires_core_fields():
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


def test_from_dict_defaults_unknown_recurrence_to_once():
    entry = RecordingScheduleEntry.from_dict({
        "id": "e1",
        "station_name": "X",
        "stream_url": "https://x",
        "run_at": "2026-01-01T08:00:00",
        "recurrence": "monthly",
    })
    assert entry is not None
    assert entry.recurrence == "once"


def test_save_and_load_round_trip(tmp_path: Path):
    entries = [_entry(id=new_id()), _entry(id=new_id(), recurrence="weekly", weekday=3)]
    save_schedule(tmp_path, entries)
    reloaded = load_schedule(tmp_path)
    assert len(reloaded) == 2
    assert {e.id for e in reloaded} == {e.id for e in entries}


def test_load_schedule_missing_file_returns_empty(tmp_path: Path):
    assert load_schedule(tmp_path) == []


def test_load_schedule_corrupt_file_returns_empty(tmp_path: Path):
    (tmp_path / "radio_recording_schedule.json").write_text("not json", encoding="utf-8")
    assert load_schedule(tmp_path) == []


def test_load_schedule_non_list_json_returns_empty(tmp_path: Path):
    (tmp_path / "radio_recording_schedule.json").write_text('{"not": "a list"}', encoding="utf-8")
    assert load_schedule(tmp_path) == []


# -- RecordingScheduler: add/remove and firing (fake recorder, no ffmpeg) --


class _FakeRecorder:
    """Stands in for RadioRecorder: records start() calls without
    touching subprocess/ffmpeg at all."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def start(self, **kwargs):
        self.calls.append(kwargs)
        return Path("fake.mp3")


def test_add_and_remove_persist(tmp_path: Path):
    recorder = _FakeRecorder()
    scheduler = RecordingScheduler(
        data_dir=tmp_path, recorder=recorder, recording_settings=RecordingSettings()  # type: ignore[arg-type]
    )
    try:
        entry = _entry(id=new_id())
        scheduler.add(entry)
        assert load_schedule(tmp_path) and load_schedule(tmp_path)[0].id == entry.id
        assert scheduler.remove(entry.id) is True
        assert load_schedule(tmp_path) == []
        assert scheduler.remove("nonexistent") is False
    finally:
        scheduler.shutdown()


def test_fire_starts_recorder_and_marks_fired(tmp_path: Path):
    recorder = _FakeRecorder()
    fired = []
    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=recorder,  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
        on_fired=lambda entry, error: fired.append((entry.id, error)),
    )
    try:
        entry = _entry(id=new_id())
        scheduler.entries.append(entry)
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 0, 0))
        assert fired == [(entry.id, "")]
        assert entry.last_fired_date == "2026-07-14"
        assert recorder.calls and recorder.calls[0]["station_name"] == "WXYZ"
    finally:
        scheduler.shutdown()


def test_fire_reports_error_when_recorder_raises(tmp_path: Path):
    from quill_radio_mac.core.recording import RecordingError

    class _RaisingRecorder:
        def start(self, **kwargs):
            raise RecordingError("no ffmpeg")

    fired = []
    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=_RaisingRecorder(),  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
        on_fired=lambda entry, error: fired.append((entry.id, error)),
    )
    try:
        entry = _entry(id=new_id())
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 0, 0))
        assert fired[0][0] == entry.id
        assert "no ffmpeg" in fired[0][1]
    finally:
        scheduler.shutdown()


def test_scheduler_loads_existing_entries_on_construction(tmp_path: Path):
    save_schedule(tmp_path, [_entry(id=new_id())])
    recorder = _FakeRecorder()
    scheduler = RecordingScheduler(
        data_dir=tmp_path, recorder=recorder, recording_settings=RecordingSettings()  # type: ignore[arg-type]
    )
    try:
        assert len(scheduler.entries) == 1
    finally:
        scheduler.shutdown()
