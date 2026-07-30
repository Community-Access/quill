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
    missed_occurrences,
    new_id,
    next_occurrence,
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


def test_next_occurrence_once_returns_the_target() -> None:
    entry = _entry(recurrence="once", run_at="2026-07-20T08:00:00")
    got = next_occurrence(entry, datetime(2026, 7, 14, 9, 0))
    assert got is not None
    assert got.hour == 8 and got.day == 20


def test_next_occurrence_daily_rolls_to_tomorrow_when_time_passed() -> None:
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00")
    # It's 09:00 today, so today's 08:00 is gone -> tomorrow's 08:00.
    got = next_occurrence(entry, datetime(2026, 7, 14, 9, 0))
    assert got is not None
    assert (got.hour, got.day) == (8, 15)


def test_next_occurrence_daily_is_today_when_still_ahead() -> None:
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00")
    got = next_occurrence(entry, datetime(2026, 7, 14, 7, 0))
    assert got is not None
    assert (got.hour, got.day) == (8, 14)


def test_next_occurrence_weekly_finds_next_matching_weekday() -> None:
    # 2026-07-14 is a Tuesday (weekday 1); target weekday Friday (4).
    entry = _entry(recurrence="weekly", run_at="2026-01-01T08:00:00", weekday=4)
    got = next_occurrence(entry, datetime(2026, 7, 14, 9, 0))
    assert got is not None
    assert got.weekday() == 4 and got.day == 17


def test_next_occurrence_orders_a_mixed_list_chronologically() -> None:
    now = datetime(2026, 7, 14, 9, 0)
    later_today = _entry(id="a", recurrence="daily", run_at="2026-01-01T22:00:00")
    tomorrow = _entry(id="b", recurrence="daily", run_at="2026-01-01T06:00:00")
    once_soon = _entry(id="c", recurrence="once", run_at="2026-07-14T12:00:00")
    order = sorted([tomorrow, later_today, once_soon], key=lambda e: next_occurrence(e, now))
    assert [e.id for e in order] == ["c", "a", "b"]  # 12:00 today, 22:00 today, 06:00 tomorrow


def test_missed_occurrences_once_in_window() -> None:
    entry = _entry(recurrence="once", run_at="2026-07-14T08:00:00")
    since = datetime(2026, 7, 14, 7, 0)
    now = datetime(2026, 7, 14, 9, 0)
    missed = missed_occurrences([entry], since=since, now=now)
    assert len(missed) == 1
    assert missed[0][0] is entry


def test_missed_occurrences_once_already_fired_or_outside_window() -> None:
    fired = _entry(recurrence="once", run_at="2026-07-14T08:00:00", last_fired_date="2026-07-14")
    assert (
        missed_occurrences(
            [fired], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 14, 9, 0)
        )
        == []
    )
    future = _entry(recurrence="once", run_at="2026-07-20T08:00:00")
    assert (
        missed_occurrences(
            [future], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 14, 9, 0)
        )
        == []
    )


def test_missed_occurrences_daily_counts_each_day() -> None:
    entry = _entry(recurrence="daily", run_at="2026-07-14T08:00:00")
    # Closed from the 14th 07:00 through the 16th 09:00: 14th, 15th, 16th fire.
    missed = missed_occurrences(
        [entry], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 16, 9, 0)
    )
    assert len(missed) == 3
    assert [m[1].date().isoformat() for m in missed] == ["2026-07-14", "2026-07-15", "2026-07-16"]


def test_missed_occurrences_weekly_only_on_its_weekday() -> None:
    # 2026-07-14 is a Tuesday (weekday 1).
    entry = _entry(recurrence="weekly", run_at="2026-07-14T08:00:00", weekday=1)
    missed = missed_occurrences(
        [entry], since=datetime(2026, 7, 13, 0, 0), now=datetime(2026, 7, 27, 0, 0)
    )
    assert [m[1].date().isoformat() for m in missed] == ["2026-07-14", "2026-07-21"]


def test_describe_missed_summary_and_empty() -> None:
    from quill.core.radio.recording_schedule import describe_missed

    assert describe_missed([]) == ""
    entry = _entry(station_name="WQXR", recurrence="once", run_at="2026-07-14T08:00:00")
    msg = describe_missed([(entry, datetime(2026, 7, 14, 8, 0).astimezone())])
    assert "1 scheduled recording was missed" in msg
    assert "WQXR" in msg


def test_missed_occurrences_skips_disabled_and_empty_window() -> None:
    disabled = _entry(recurrence="daily", run_at="2026-07-14T08:00:00", enabled=False)
    assert (
        missed_occurrences(
            [disabled], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 16, 9, 0)
        )
        == []
    )
    active = _entry(recurrence="daily", run_at="2026-07-14T08:00:00")
    # since >= now yields nothing (e.g. a blank "last seen" defaulting to now).
    assert (
        missed_occurrences(
            [active], since=datetime(2026, 7, 16, 9, 0), now=datetime(2026, 7, 16, 9, 0)
        )
        == []
    )


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


def test_daily_is_due_throughout_its_window_once_per_day() -> None:
    # R2: the window model fires any time *now* is in [start, start+duration),
    # not only on the exact start minute. A poll that lands a minute past
    # still fires (with the remaining minutes), so a stall across the target
    # minute no longer drops the occurrence.
    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00", duration_minutes=60)
    assert is_due(entry, datetime(2026, 7, 14, 8, 0, 0)) is True
    assert is_due(entry, datetime(2026, 7, 14, 8, 1, 0)) is True  # late start still in window
    assert is_due(entry, datetime(2026, 7, 14, 8, 59, 59)) is True
    assert is_due(entry, datetime(2026, 7, 14, 9, 0, 0)) is False  # window closed
    entry.last_fired_date = "2026-07-14"
    assert is_due(entry, datetime(2026, 7, 14, 8, 30, 0)) is False  # already fired today
    # A new day resets eligibility.
    assert is_due(entry, datetime(2026, 7, 15, 8, 0, 0)) is True


def test_remaining_minutes_shrinks_for_a_late_start() -> None:
    # R2: a fire inside the window records only the remaining minutes so a late
    # launch does not overshoot the intended end.
    from quill.core.radio.recording_schedule import remaining_minutes

    entry = _entry(recurrence="daily", run_at="2026-01-01T08:00:00", duration_minutes=60)
    assert remaining_minutes(entry, datetime(2026, 7, 14, 8, 0, 0)) == 60
    assert remaining_minutes(entry, datetime(2026, 7, 14, 8, 30, 0)) == 30
    assert remaining_minutes(entry, datetime(2026, 7, 14, 8, 59, 30)) == 1  # floored to 1


def test_missed_occurrences_excludes_window_still_open_at_now() -> None:
    # R2/11.7: an occurrence whose window is still open at *now* will start late
    # on this launch, so it is not "missed" -- do not double-announce it.
    entry = _entry(recurrence="daily", run_at="2026-07-14T08:00:00", duration_minutes=60)
    # Closed 07:00 -> 08:30: the 08:00 window (08:00-09:00) is still open at
    # 08:30, so it must not be reported as missed (the scheduler will catch up).
    missed = missed_occurrences(
        [entry], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 14, 8, 30)
    )
    assert missed == []
    # Once the window has closed (09:01), the 08:00 occurrence is genuinely missed.
    missed = missed_occurrences(
        [entry], since=datetime(2026, 7, 14, 7, 0), now=datetime(2026, 7, 14, 9, 1)
    )
    assert len(missed) == 1


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


# -- R2 scheduler firing: stamp only on success, defer when busy, retry on error --


def test_scheduler_stamps_only_on_success_and_disables_once(tmp_path: Path) -> None:
    from quill.core.radio.recording import RecordingSettings
    from quill.core.radio.recording_schedule import RecordingScheduler, _today_in_zone

    calls: list[int] = []

    class _Recorder:
        def start(self, **kwargs: object) -> None:
            calls.append(int(kwargs.get("duration_minutes", 0)))  # type: ignore[arg-type]

    entry = _entry(id="once1", recurrence="once", run_at="2026-07-14T08:00:00")
    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=_Recorder(),  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
    )
    try:
        scheduler.add(entry)
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 0, 0))
        assert calls == [60]
        # Stamped + once-entry auto-disabled on success (R2).
        when = datetime(2026, 7, 14, 8, 0, 0)
        assert scheduler.entries[0].last_fired_date == _today_in_zone(entry, when)
        assert scheduler.entries[0].enabled is False
    finally:
        scheduler.shutdown()


def test_scheduler_defers_when_concurrency_cap_reached_and_does_not_stamp(tmp_path: Path) -> None:
    # Concurrent recording: a fire is only deferred when the concurrency *cap*
    # is reached (RecordingLimitError). The generic "already in progress" refusal
    # no longer exists -- overlapping shows just record together.
    from quill.core.radio.recording import RecordingLimitError, RecordingSettings
    from quill.core.radio.recording_schedule import RecordingScheduler

    busy_calls: list[str] = []

    class _AtCapRecorder:
        def start(self, **kwargs: object) -> None:
            raise RecordingLimitError("The maximum of 1 simultaneous recording is already running.")

    entry = _entry(id="daily1", recurrence="daily", run_at="2026-07-14T08:00:00")
    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=_AtCapRecorder(),  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
        on_busy=lambda e: busy_calls.append(e.id),
    )
    try:
        scheduler.add(entry)
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 10, 0))
        # Announced once, not stamped (so the next poll retries within the window).
        assert busy_calls == ["daily1"]
        assert scheduler.entries[0].last_fired_date == ""
        # A second fire in the same window does not re-announce (once per entry).
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 20, 0))
        assert busy_calls == ["daily1"]
        assert scheduler.entries[0].last_fired_date == ""
    finally:
        scheduler.shutdown()


def test_scheduler_fires_overlapping_entries_concurrently(tmp_path: Path) -> None:
    # Two due entries each start their own recording (no busy-defer): the whole
    # point of concurrent recording.
    from quill.core.radio.recording import RecordingSettings
    from quill.core.radio.recording_schedule import RecordingScheduler

    started: list[str] = []

    class _Recorder:
        def start(self, *, station_name: str, **kwargs: object) -> None:
            started.append(station_name)

    scheduler = RecordingScheduler(
        data_dir=tmp_path,
        recorder=_Recorder(),  # type: ignore[arg-type]
        recording_settings=RecordingSettings(),
    )
    try:
        a = _entry(id="a", station_name="A", recurrence="daily", run_at="2026-07-14T08:00:00")
        b = _entry(id="b", station_name="B", recurrence="daily", run_at="2026-07-14T08:00:00")
        now = datetime(2026, 7, 14, 8, 5, 0)
        scheduler._fire(a, now)
        scheduler._fire(b, now)
        assert started == ["A", "B"]
    finally:
        scheduler.shutdown()


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
