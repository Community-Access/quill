"""Queue schedules: posting slots by account or group (PRD 18.4, 18.2).

A ``QueueSchedule`` describes *when* a queue is allowed to publish: a set of
weekly slots (weekday + time in a named IANA time zone), a minimum spacing
between posts, a daily limit, blackout windows, and a daily quiet period. The
two public functions are pure and clock-injectable so scheduling policy is
unit-testable without a database or wall clock:

- ``next_slot`` finds the next available posting time after a reference instant,
  honoring spacing, daily limit, blackout windows, and quiet hours (PRD 18.2
  "next available slot").
- ``slots_between`` enumerates the concrete slot timestamps in a window.

All wall-clock reasoning goes through :mod:`zoneinfo`, so a slot defined as
"09:00 America/New_York" lands on the correct UTC instant on both sides of a
daylight-saving transition. Timestamps are integer milliseconds since the Unix
epoch (UTC), matching :mod:`quill_social.model`. Schedules persist in the
generic document store under kind ``"queue_schedule"``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quill_social.model import new_id, now_ms

# Document store kind for persisted schedules.
DOC_KIND = "queue_schedule"

# How far ahead ``next_slot`` will look before giving up (defensive bound so a
# schedule with no usable slots cannot loop forever).
_HORIZON_DAYS = 366

_MS_PER_MIN = 60_000
_MS_PER_DAY = 86_400_000


@dataclass
class Slot:
    """One weekly posting slot: ``weekday`` 0=Monday .. 6=Sunday, local time."""

    weekday: int = 0
    hour: int = 9
    minute: int = 0

    def to_dict(self) -> dict:
        return {"weekday": self.weekday, "hour": self.hour, "minute": self.minute}

    @classmethod
    def from_dict(cls, d: dict) -> Slot:
        return cls(
            weekday=int(d.get("weekday", 0)),
            hour=int(d.get("hour", 0)),
            minute=int(d.get("minute", 0)),
        )


@dataclass
class BlackoutWindow:
    """An absolute UTC range during which the queue must not publish."""

    start_ms: int = 0
    end_ms: int = 0
    reason: str = ""

    def contains(self, ms: int) -> bool:
        return self.start_ms <= ms < self.end_ms

    def to_dict(self) -> dict:
        return {"start_ms": self.start_ms, "end_ms": self.end_ms, "reason": self.reason}

    @classmethod
    def from_dict(cls, d: dict) -> BlackoutWindow:
        return cls(
            start_ms=int(d.get("start_ms", 0) or 0),
            end_ms=int(d.get("end_ms", 0) or 0),
            reason=d.get("reason", ""),
        )


@dataclass
class QueueSchedule:
    """Posting-slot policy for one account or account group (PRD 18.4).

    ``quiet_start_min`` / ``quiet_end_min`` are minutes-of-day in local time and
    may wrap past midnight (e.g. 1320 to 420 means 22:00 to 07:00). A daily
    limit or spacing of 0 means "no limit". ``account_ids`` and ``group`` are
    both optional; a schedule may target either.
    """

    schedule_id: str = field(default_factory=lambda: new_id("qsched"))
    name: str = ""
    account_ids: list[str] = field(default_factory=list)
    group: str = ""
    timezone: str = "UTC"
    slots: list[Slot] = field(default_factory=list)
    min_spacing_min: int = 0
    daily_limit: int = 0
    blackout_windows: list[BlackoutWindow] = field(default_factory=list)
    quiet_start_min: int | None = None
    quiet_end_min: int | None = None
    content_type: str = ""
    campaign_id: str = ""

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "account_ids": list(self.account_ids),
            "group": self.group,
            "timezone": self.timezone,
            "slots": [s.to_dict() for s in self.slots],
            "min_spacing_min": self.min_spacing_min,
            "daily_limit": self.daily_limit,
            "blackout_windows": [b.to_dict() for b in self.blackout_windows],
            "quiet_start_min": self.quiet_start_min,
            "quiet_end_min": self.quiet_end_min,
            "content_type": self.content_type,
            "campaign_id": self.campaign_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> QueueSchedule:
        return cls(
            schedule_id=d.get("schedule_id") or new_id("qsched"),
            name=d.get("name", ""),
            account_ids=list(d.get("account_ids", [])),
            group=d.get("group", ""),
            timezone=d.get("timezone", "UTC"),
            slots=[Slot.from_dict(s) for s in d.get("slots", [])],
            min_spacing_min=int(d.get("min_spacing_min", 0) or 0),
            daily_limit=int(d.get("daily_limit", 0) or 0),
            blackout_windows=[
                BlackoutWindow.from_dict(b) for b in d.get("blackout_windows", [])
            ],
            quiet_start_min=d.get("quiet_start_min"),
            quiet_end_min=d.get("quiet_end_min"),
            content_type=d.get("content_type", ""),
            campaign_id=d.get("campaign_id", ""),
        )


# -- time helpers -------------------------------------------------------------


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _local(ms: int, zone: ZoneInfo) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=zone)


def _slot_ms(day: datetime, slot: Slot, zone: ZoneInfo) -> int:
    """Concrete UTC ms for ``slot`` on the calendar day of ``day`` (DST-aware)."""
    local_dt = datetime(day.year, day.month, day.day, slot.hour, slot.minute, tzinfo=zone)
    return int(local_dt.timestamp() * 1000)


def _minute_of_day(ms: int, zone: ZoneInfo) -> int:
    dt = _local(ms, zone)
    return dt.hour * 60 + dt.minute


def _in_quiet(ms: int, schedule: QueueSchedule, zone: ZoneInfo) -> bool:
    start, end = schedule.quiet_start_min, schedule.quiet_end_min
    if start is None or end is None or start == end:
        return False
    minute = _minute_of_day(ms, zone)
    if start < end:
        return start <= minute < end
    # Wraps past midnight (e.g. 22:00 to 07:00).
    return minute >= start or minute < end


def _in_blackout(ms: int, schedule: QueueSchedule) -> bool:
    return any(w.contains(ms) for w in schedule.blackout_windows)


# -- public API ---------------------------------------------------------------


def slots_between(schedule: QueueSchedule, start_ms: int, end_ms: int) -> list[int]:
    """Enumerate concrete slot timestamps in ``[start_ms, end_ms)``, ascending.

    Blackout windows and quiet hours are honored so the enumeration reflects
    only slots the queue could actually use. DST transitions are handled by
    :mod:`zoneinfo`, so a wall-clock slot maps to the correct UTC instant.
    """
    if not schedule.slots or end_ms <= start_ms:
        return []
    zone = _zone(schedule.timezone)
    by_weekday: dict[int, list[Slot]] = {}
    for slot in schedule.slots:
        by_weekday.setdefault(slot.weekday % 7, []).append(slot)

    out: list[int] = []
    # Start one day early so a slot on the boundary day is not missed after tz
    # conversion, then filter by the exact window below.
    cursor = _local(start_ms, zone).date() - timedelta(days=1)
    last = _local(end_ms, zone).date() + timedelta(days=1)
    while cursor <= last:
        for slot in by_weekday.get(cursor.weekday(), ()):
            anchor = datetime(cursor.year, cursor.month, cursor.day, tzinfo=zone)
            ms = _slot_ms(anchor, slot, zone)
            if start_ms <= ms < end_ms and not _in_blackout(ms, schedule) \
                    and not _in_quiet(ms, schedule, zone):
                out.append(ms)
        cursor += timedelta(days=1)
    out.sort()
    return out


def next_slot(
    schedule: QueueSchedule,
    after_ms: int,
    existing_slots: list[int] | None = None,
    *,
    now: int | None = None,
) -> int | None:
    """Next available posting time strictly after ``after_ms`` (PRD 18.2).

    Honors, in order: the reference instant and ``now`` (a slot may not be in
    the past), blackout windows, quiet hours, minimum spacing versus
    ``existing_slots``, and the per-local-day limit. Returns ``None`` if no slot
    is available within the search horizon.
    """
    at = now if now is not None else now_ms()
    existing = sorted(existing_slots or [])
    zone = _zone(schedule.timezone)
    floor = max(after_ms + 1, at)
    horizon = floor + _HORIZON_DAYS * _MS_PER_DAY
    spacing_ms = schedule.min_spacing_min * _MS_PER_MIN

    for candidate in slots_between(schedule, floor, horizon):
        if spacing_ms and any(abs(candidate - e) < spacing_ms for e in existing):
            continue
        if schedule.daily_limit > 0:
            day = _local(candidate, zone).date()
            used = sum(1 for e in existing if _local(e, zone).date() == day)
            if used >= schedule.daily_limit:
                continue
        return candidate
    return None


# -- persistence --------------------------------------------------------------


def save(store, schedule: QueueSchedule, *, ordinal: int = 0) -> QueueSchedule:
    """Persist a schedule to the document store (kind ``queue_schedule``)."""
    store.put_document(DOC_KIND, schedule.schedule_id, schedule.to_dict(), ordinal=ordinal)
    return schedule


def load(store, schedule_id: str) -> QueueSchedule | None:
    data = store.get_document(DOC_KIND, schedule_id)
    return QueueSchedule.from_dict(data) if data else None


def load_all(store) -> list[QueueSchedule]:
    return [QueueSchedule.from_dict(d) for d in store.list_documents(DOC_KIND)]
