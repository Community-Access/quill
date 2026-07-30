"""Tests for the wx-free schedule-form builder (12-hour time, timezone, edit id).

The dialog itself is wx; ``build_schedule_entry`` is the pure validation/build
step it delegates to, so it is testable without constructing any widgets.
"""

from __future__ import annotations

from datetime import datetime

from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.ui.radio.schedule_recording_dialog import _entry_summary, build_schedule_entry

# Recurrence dropdown order: Once=0, Daily=1, Weekly=2.
_ONCE, _DAILY, _WEEKLY = 0, 1, 2


def _daily(**overrides: object) -> tuple[object, object]:
    kwargs = dict(
        name="WXYZ",
        url="https://example.com/stream",
        recurrence_index=_DAILY,
        time_text="08:00",
        date_text="",
        weekday_index=0,
        timezone_name="",
        duration_minutes=60,
    )
    kwargs.update(overrides)
    return build_schedule_entry(**kwargs)  # type: ignore[arg-type]


def test_accepts_12_hour_time() -> None:
    entry, error = _daily(time_text="7:30 PM")
    assert error is None
    assert entry is not None
    assert entry.run_at.endswith("T19:30:00")


def test_accepts_24_hour_time() -> None:
    entry, error = _daily(time_text="19:30")
    assert error is None
    assert entry is not None
    assert entry.run_at.endswith("T19:30:00")


def test_rejects_garbage_time() -> None:
    entry, error = _daily(time_text="half past nine")
    assert entry is None
    assert error is not None and "7:30 PM" in error


def test_requires_name_and_url() -> None:
    assert _daily(name="")[0] is None
    assert _daily(url="  ")[0] is None


def test_timezone_is_carried_onto_the_entry() -> None:
    entry, error = _daily(timezone_name="America/New_York")
    assert error is None
    assert entry is not None
    assert entry.timezone == "America/New_York"


def test_weekly_records_the_weekday_only_for_weekly() -> None:
    weekly, _ = _daily(recurrence_index=_WEEKLY, weekday_index=3)
    assert weekly is not None and weekly.weekday == 3
    daily, _ = _daily(recurrence_index=_DAILY, weekday_index=3)
    assert daily is not None and daily.weekday == -1


def test_editing_id_is_reused_instead_of_a_new_one() -> None:
    entry, error = _daily(editing_id="keep-me")
    assert error is None
    assert entry is not None and entry.id == "keep-me"
    fresh, _ = _daily()
    assert fresh is not None and fresh.id != "keep-me"


def test_local_once_must_be_in_the_future() -> None:
    now = datetime(2026, 7, 14, 12, 0, 0)
    past, error = build_schedule_entry(
        name="X",
        url="https://x",
        recurrence_index=_ONCE,
        time_text="08:00",
        date_text="2026-07-14",
        weekday_index=0,
        timezone_name="",
        duration_minutes=60,
        now=now,
    )
    assert past is None
    assert error is not None and "future" in error
    future, error2 = build_schedule_entry(
        name="X",
        url="https://x",
        recurrence_index=_ONCE,
        time_text="18:00",
        date_text="2026-07-14",
        weekday_index=0,
        timezone_name="",
        duration_minutes=60,
        now=now,
    )
    assert error2 is None
    assert future is not None and future.run_at == "2026-07-14T18:00:00"


def test_zoned_once_skips_the_naive_future_guard() -> None:
    # A one-time recording in another zone is judged in that zone at fire time,
    # so the naive-local "must be in the future" guard does not apply.
    now = datetime(2026, 7, 14, 12, 0, 0)
    entry, error = build_schedule_entry(
        name="X",
        url="https://x",
        recurrence_index=_ONCE,
        time_text="08:00",
        date_text="2026-07-14",
        weekday_index=0,
        timezone_name="America/New_York",
        duration_minutes=60,
        now=now,
    )
    assert error is None
    assert entry is not None and entry.timezone == "America/New_York"


def test_duration_of_zero_minutes_is_rejected() -> None:
    # #1213: the form now offers hours + minutes; both zero means no recording.
    entry, error = _daily(duration_minutes=0)
    assert entry is None
    assert "at least one minute" in (error or "")


def test_hours_and_minutes_combine_into_total_minutes() -> None:
    # The dialog computes hours*60 + minutes; the builder stores the total.
    entry, error = _daily(duration_minutes=2 * 60 + 30)
    assert error is None
    assert entry is not None
    assert entry.duration_minutes == 150


def _summary_entry(**overrides: object) -> RecordingScheduleEntry:
    base = dict(
        id="e1",
        station_name="WXYZ",
        stream_url="https://cdn.example.com/live",
        recurrence="daily",
        run_at="2026-01-01T08:00:00",
        duration_minutes=60,
    )
    base.update(overrides)
    return RecordingScheduleEntry(**base)  # type: ignore[arg-type]


def test_entry_summary_shows_the_stream_host() -> None:
    # #1220: the list showed no URL, so a duplicate (same name/time, same URL)
    # looked identical to its original. The host now disambiguates them.
    summary = _entry_summary(_summary_entry())
    assert "[cdn.example.com]" in summary
    assert "WXYZ" in summary and "daily at 08:00" in summary


def test_entry_summary_omits_host_when_url_has_none() -> None:
    summary = _entry_summary(_summary_entry(stream_url=""))
    assert "[" not in summary
