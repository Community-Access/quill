from __future__ import annotations

from datetime import UTC, datetime


def validate_scheduled_publish_time(
    when: datetime,
    *,
    now: datetime | None = None,
) -> str | None:
    if when.tzinfo is None or when.tzinfo.utcoffset(when) is None:
        return "Choose a time zone for the scheduled publish time."
    reference = now if now is not None else datetime.now(UTC)
    if when <= reference:
        return "Choose a publish time that is in the future."
    return None
