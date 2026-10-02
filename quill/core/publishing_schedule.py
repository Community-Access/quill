from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ScheduledPublishChoice:
    """What the Schedule Publish dialog returns: what to publish, and when.

    Moved here from ``quill/ui/publishing_tools.py`` (GATE-11, 2026-10-01);
    it holds no UI and belongs beside the validation it pairs with.
    """

    content_kind: str
    scheduled_at: datetime
