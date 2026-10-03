"""When a podcast is checked for new episodes: a schedule, not only an interval (qc.md 5e).

Jeff: "we need richer refresh podcast intervals both globally and per podcast
so that the user has far more control."

A daily news show, a weekly interview and a podcast that publishes at 6 a.m.
on Tuesdays want three different answers, and "every 3 hours" is the wrong
answer to all three. So a :class:`Schedule` has a *kind*:

* **manual** -- never on its own.
* **interval** -- every so many minutes, typed, not chosen from eight rows.
* **times** -- at set times of day, on chosen days of the week.
* **learned** -- around when it usually publishes: the day-of-week and hour
  of the last twelve episodes, checked every 15 minutes for the two hours
  around the usual time, hourly for the rest of that day, daily otherwise.
* **publisher** -- what the feed itself declares (``sy:updatePeriod`` and
  ``sy:updateFrequency``, or Podcasting 2.0 ``podcast:updateFrequency``).

Everything here is pure and tested against a fixed clock. :func:`next_due`
is the one question the monitor asks; :func:`describe` is the one sentence
the settings, the Feed Check columns and the confirmation all read, so the
app never describes a schedule two ways. A schedule is stored as one JSON
string setting (``refresh_schedule``) that exists at every level -- the shared
default, a folder, a podcast -- and an empty string means "not set here",
which the legacy ``refresh_minutes`` then answers for, so nobody's checking
changes on upgrade (:func:`from_legacy`).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from email.utils import parsedate_to_datetime

__all__ = [
    "INTERVAL",
    "KINDS",
    "KIND_LABELS",
    "LEARNED",
    "MANUAL",
    "PUBLISHER",
    "TIMES",
    "Hint",
    "Pattern",
    "Schedule",
    "decode",
    "describe",
    "encode",
    "from_legacy",
    "learn",
    "next_due",
    "parse_hint",
    "parse_published",
]

MANUAL = "manual"
INTERVAL = "interval"
TIMES = "times"
LEARNED = "learned"
PUBLISHER = "publisher"
KINDS: tuple[str, ...] = (MANUAL, INTERVAL, TIMES, LEARNED, PUBLISHER)
KIND_LABELS: dict[str, str] = {
    MANUAL: "Manually only",
    INTERVAL: "Every so often",
    TIMES: "At set times",
    LEARNED: "Around when it usually publishes",
    PUBLISHER: "Follow the publisher's hint",
}

_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_WEEKDAYS = (0, 1, 2, 3, 4)
_MIN_INTERVAL = 5
_MAX_INTERVAL = 10080
_LEARN_FROM = 12
#: How many minutes after a learned time the close checks keep going.
_CLOSE_WINDOW_MINUTES = 120
_CLOSE_EVERY = 15
_SAME_DAY_EVERY = 60
_OTHER_DAYS_EVERY = 1440


@dataclass(frozen=True, slots=True)
class Schedule:
    kind: str = MANUAL
    #: Minutes, for INTERVAL.
    minutes: int = 60
    #: "HH:MM" strings, for TIMES (one to six).
    times: tuple[str, ...] = ()
    #: Weekday numbers, Monday 0, for TIMES; empty means every day.
    days: tuple[int, ...] = ()
    #: A pinned learned pattern (weekday, hour); None means keep learning.
    pinned: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class Pattern:
    """What the learning found: the usual day and hour, and how sure it is."""

    weekday: int | None
    hour: int
    #: How many of the recent episodes agreed.
    agreement: int = 0

    def describe(self) -> str:
        when = "most days" if self.weekday is None else f"{_DAY_NAMES[self.weekday]}s"
        return f"Usually {when} about {_hour_words(self.hour)}; checking closely then."


@dataclass(frozen=True, slots=True)
class Hint:
    """What a feed declares about its own cadence, normalised to minutes."""

    minutes: int = 0
    words: str = ""

    @property
    def is_known(self) -> bool:
        return self.minutes > 0


# -- encoding ------------------------------------------------------------------- #


def encode(schedule: Schedule) -> str:
    data: dict[str, object] = {"kind": schedule.kind}
    if schedule.kind == INTERVAL:
        data["minutes"] = schedule.minutes
    elif schedule.kind == TIMES:
        data["times"] = list(schedule.times)
        data["days"] = list(schedule.days)
    elif schedule.kind == LEARNED and schedule.pinned is not None:
        data["pinned"] = list(schedule.pinned)
    return json.dumps(data, separators=(",", ":"))


def decode(text: object) -> Schedule | None:
    """A saved schedule, or None when there is none (or it is unreadable)."""
    try:
        raw = json.loads(str(text or ""))
    except (TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind", "") or "")
    if kind not in KINDS:
        return None
    minutes = _clamp_minutes(raw.get("minutes", 60))
    times = tuple(_clock(item) for item in _as_list(raw.get("times")) if _clock(item))
    days = tuple(sorted({int(str(item)) for item in _as_list(raw.get("days")) if _is_day(item)}))
    pinned_raw = raw.get("pinned")
    pinned = None
    if isinstance(pinned_raw, list) and len(pinned_raw) == 2 and _is_day(pinned_raw[0]):
        pinned = (int(str(pinned_raw[0])), max(0, min(23, int(str(pinned_raw[1])))))
    return Schedule(kind, minutes, times[:6], days, pinned)


def from_legacy(refresh_minutes: object) -> Schedule:
    """What the old ``refresh_minutes`` meant: 0 was manual, anything else an interval."""
    try:
        minutes = int(str(refresh_minutes or 0))
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return Schedule(MANUAL)
    return Schedule(INTERVAL, _clamp_minutes(minutes))


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _is_day(value: object) -> bool:
    try:
        return 0 <= int(str(value)) <= 6
    except (TypeError, ValueError):
        return False


def _clamp_minutes(value: object) -> int:
    try:
        minutes = int(str(value))
    except (TypeError, ValueError):
        minutes = 60
    return max(_MIN_INTERVAL, min(_MAX_INTERVAL, minutes))


def _clock(value: object) -> str:
    """ "6:00" -> "06:00"; anything unreadable -> ""."""
    text = str(value or "").strip()
    if ":" not in text:
        return ""
    hours, _, minutes = text.partition(":")
    try:
        hour, minute = int(hours), int(minutes)
    except ValueError:
        return ""
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return ""
    return f"{hour:02d}:{minute:02d}"


# -- words -------------------------------------------------------------------------- #


def _hour_words(hour: int) -> str:
    if hour == 0:
        return "midnight"
    if hour == 12:
        return "noon"
    return f"{hour % 12} {'a.m.' if hour < 12 else 'p.m.'}"


def _minutes_words(minutes: int) -> str:
    if minutes % 1440 == 0:
        days = minutes // 1440
        return "day" if days == 1 else f"{days} days"
    if minutes % 60 == 0:
        hours = minutes // 60
        return "hour" if hours == 1 else f"{hours} hours"
    return f"{minutes} minutes"


def _days_words(days: tuple[int, ...]) -> str:
    if not days or len(days) == 7:
        return ""
    if tuple(days) == _WEEKDAYS:
        return "weekdays"
    if tuple(days) == (5, 6):
        return "weekends"
    return " and ".join(_DAY_NAMES[day] + "s" for day in days)


def describe(
    schedule: Schedule, *, pattern: Pattern | None = None, hint: Hint | None = None
) -> str:
    """The schedule as the settings, Feed Check and the confirmation all say it."""
    if schedule.kind == MANUAL:
        return "Never checks on its own."
    if schedule.kind == INTERVAL:
        return f"Every {_minutes_words(schedule.minutes)}."
    if schedule.kind == TIMES:
        if not schedule.times:
            return "At set times, none chosen yet."
        when = " and ".join(schedule.times)
        days = _days_words(schedule.days)
        return f"At {when}, {days}." if days else f"At {when}."
    if schedule.kind == LEARNED:
        if schedule.pinned is not None:
            return (
                Pattern(schedule.pinned[0], schedule.pinned[1])
                .describe()
                .replace("Usually", "Pinned to")
            )
        if pattern is None:
            return "Learning when it usually publishes; checking daily until it knows."
        return pattern.describe()
    if hint is None or not hint.is_known:
        return "The publisher gives no hint; checking daily until it does."
    return f"The publisher says {hint.words}."


# -- learning ------------------------------------------------------------------------ #


def parse_published(text: object) -> datetime | None:
    """A feed's published string as a datetime, or None. RFC 2822 first (what
    RSS writes), ISO 8601 second (what Atom writes)."""
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def learn(published: list[datetime]) -> Pattern | None:
    """The usual weekday and hour of the newest *published* moments.

    None until three episodes agree on an hour (within one hour either way);
    a weekday only when most of them share one, otherwise "most days".
    """
    recent = sorted((moment for moment in published if moment is not None), reverse=True)
    recent = recent[:_LEARN_FROM]
    if len(recent) < 3:
        return None
    hours = Counter(moment.hour for moment in recent)
    hour, _count = hours.most_common(1)[0]
    near = sum(
        1 for moment in recent if abs(moment.hour - hour) <= 1 or abs(moment.hour - hour) >= 23
    )
    if near < 3:
        return None
    weekdays = Counter(moment.weekday() for moment in recent)
    weekday, day_count = weekdays.most_common(1)[0]
    chosen: int | None = weekday if day_count * 2 > len(recent) else None
    return Pattern(chosen, hour, near)


# -- the publisher's hint ------------------------------------------------------------- #

_PERIOD_MINUTES = {
    "hourly": 60,
    "daily": 1440,
    "weekly": 10080,
    "monthly": 43200,
    "yearly": 525600,
}


def parse_hint(feed_text: str) -> Hint:
    """``sy:updatePeriod``/``sy:updateFrequency`` or ``podcast:updateFrequency``
    from the channel header, as minutes. Tolerant: no hint is a Hint of 0."""
    import re

    text = feed_text or ""
    period = re.search(r"<sy:updatePeriod>\s*(\w+)\s*</sy:updatePeriod>", text, re.IGNORECASE)
    frequency = re.search(
        r"<sy:updateFrequency>\s*(\d+)\s*</sy:updateFrequency>", text, re.IGNORECASE
    )
    if period and period.group(1).lower() in _PERIOD_MINUTES:
        times = int(frequency.group(1)) if frequency else 1
        base = _PERIOD_MINUTES[period.group(1).lower()]
        minutes = max(_MIN_INTERVAL, base // max(1, times))
        words = (
            period.group(1).lower() if times <= 1 else f"{times} times {period.group(1).lower()}"
        )
        return Hint(minutes, words)
    p20 = re.search(
        r"<podcast:updateFrequency\b([^>]*)>(.*?)</podcast:updateFrequency>",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if p20:
        attributes, words = p20.group(1), re.sub(r"\s+", " ", p20.group(2)).strip()
        rrule = re.search(r'rrule="([^"]*)"', attributes, re.IGNORECASE)
        minutes = _minutes_from_rrule(rrule.group(1) if rrule else "")
        if minutes:
            return Hint(minutes, words or "on the schedule the feed declares")
    return Hint()


def _minutes_from_rrule(rrule: str) -> int:
    parts = dict(item.split("=", 1) for item in rrule.upper().split(";") if "=" in item)
    freq = parts.get("FREQ", "")
    try:
        interval = max(1, int(parts.get("INTERVAL", "1")))
    except ValueError:
        interval = 1
    base = {"HOURLY": 60, "DAILY": 1440, "WEEKLY": 10080, "MONTHLY": 43200, "YEARLY": 525600}.get(
        freq, 0
    )
    if not base:
        return 0
    by_day = parts.get("BYDAY", "")
    per_week = len([item for item in by_day.split(",") if item]) if freq == "WEEKLY" else 0
    if per_week > 1:
        base = base // per_week
    return max(_MIN_INTERVAL, base * interval)


# -- when next ------------------------------------------------------------------------ #


def next_due(
    schedule: Schedule,
    now: datetime,
    last_checked: datetime | None,
    *,
    published: list[datetime] | None = None,
    hint: Hint | None = None,
) -> datetime | None:
    """The moment this schedule next wants a check; None for never.

    A podcast never checked before is due now under every kind but manual --
    which is what makes a newly followed podcast arrive without waiting.
    """
    if schedule.kind == MANUAL:
        return None
    if last_checked is None:
        return now
    if schedule.kind == INTERVAL:
        return last_checked + timedelta(minutes=schedule.minutes)
    if schedule.kind == TIMES:
        return _next_set_time(schedule, last_checked)
    if schedule.kind == LEARNED:
        pattern = (
            Pattern(schedule.pinned[0], schedule.pinned[1])
            if schedule.pinned is not None
            else learn(list(published or []))
        )
        if pattern is None:
            return last_checked + timedelta(minutes=_OTHER_DAYS_EVERY)
        return last_checked + timedelta(minutes=_learned_cadence(pattern, now))
    minutes = hint.minutes if hint is not None and hint.is_known else _OTHER_DAYS_EVERY
    return last_checked + timedelta(minutes=minutes)


def _next_set_time(schedule: Schedule, after: datetime) -> datetime | None:
    times = sorted(schedule.times)
    if not times:
        return None
    days = set(schedule.days) if schedule.days else set(range(7))
    for day_offset in range(0, 8):
        day = (after + timedelta(days=day_offset)).date()
        if day.weekday() not in days:
            continue
        for clock in times:
            hour, minute = (int(part) for part in clock.split(":"))
            candidate = datetime.combine(day, time(hour, minute), tzinfo=after.tzinfo)
            if candidate > after:
                return candidate
    return None


def _learned_cadence(pattern: Pattern, now: datetime) -> int:
    """15 minutes in the two hours around the usual time, hourly the rest of
    that day, daily otherwise."""
    if pattern.weekday is not None and now.weekday() != pattern.weekday:
        return _OTHER_DAYS_EVERY
    usual = now.replace(hour=pattern.hour, minute=0, second=0, microsecond=0)
    gap = (now - usual).total_seconds() / 60
    if -_CLOSE_WINDOW_MINUTES <= gap <= _CLOSE_WINDOW_MINUTES:
        return _CLOSE_EVERY
    return _SAME_DAY_EVERY
