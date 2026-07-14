from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from quill.core.publishing_schedule import validate_scheduled_publish_time


def test_validate_scheduled_publish_time_rejects_naive_datetime() -> None:
    when = datetime(2026, 7, 1, 12, 0)

    assert (
        validate_scheduled_publish_time(when)
        == "Choose a time zone for the scheduled publish time."
    )


def test_validate_scheduled_publish_time_rejects_past_time() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    when = now - timedelta(hours=1)

    assert (
        validate_scheduled_publish_time(when, now=now)
        == "Choose a publish time that is in the future."
    )


def test_validate_scheduled_publish_time_rejects_time_equal_to_now() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)

    assert (
        validate_scheduled_publish_time(now, now=now)
        == "Choose a publish time that is in the future."
    )


def test_validate_scheduled_publish_time_accepts_future_time_in_any_zone() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    when = now + timedelta(hours=2, minutes=30)

    assert validate_scheduled_publish_time(when, now=now) is None


def test_validate_scheduled_publish_time_compares_across_offsets() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    # 13:30 in UTC+2 is 11:30 UTC: one hour in the past relative to `now`.
    when = datetime(2026, 6, 21, 13, 30, tzinfo=timezone(timedelta(hours=2)))

    assert (
        validate_scheduled_publish_time(when, now=now)
        == "Choose a publish time that is in the future."
    )
