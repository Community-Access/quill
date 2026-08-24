"""Repeating events: one ``VEVENT`` that means twenty (list.md 6.10).

ACB's August 2026 export wrote every occurrence out separately, so the first
version of the calendar read it correctly by ignoring recurrence entirely. That
is a fact about one month, not about the format -- My Calendar emits ``RRULE``
when a series is defined as a series, and the day it does, a weekly programme
would appear **once** instead of every week. That failure is the dangerous kind:
it reads as a thin schedule rather than as a bug, so nobody reports it.

So recurrence is expanded, and the expansion is deliberately narrow:

* **Only what a radio schedule actually uses** -- ``FREQ`` of ``DAILY``,
  ``WEEKLY``, ``MONTHLY`` or ``YEARLY``, with ``INTERVAL``, ``COUNT``,
  ``UNTIL``, ``BYDAY`` and ``EXDATE``. Not ``BYSETPOS``, not ``BYMONTHDAY``
  arithmetic beyond the anchor, not the parts of RFC 5545 that exist for
  calendaring applications rather than for programme listings. An unsupported
  part is *ignored*, never guessed at.
* **Always inside a window.** The caller says which fortnight or month it is
  showing, and expansion never produces an occurrence outside it. An unbounded
  ``RRULE`` -- no ``COUNT``, no ``UNTIL`` -- is legal and infinite, and a
  parser that tried to honour it literally would hang on a feed.
* **Bounded even inside the window**, by :data:`MAX_OCCURRENCES`. A malformed
  rule that steps by zero would otherwise loop for ever; the guard is on the
  count rather than on the arithmetic so no single mistake can defeat it.

**The series keeps one identity.** Every occurrence carries the parent's uid
with its own start appended (``105795-4440@20260826T190000Z``), so a reminder
set on next Tuesday's episode attaches to next Tuesday and not to the series --
and so the de-duplication in :mod:`quill.core.radio.acb_calendar` still sees
each occurrence as its own programme.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

#: The ceiling on occurrences from one rule, whatever the window says. A
#: fortnight of a hourly programme is 336; a year of a daily one is 365. Five
#: hundred is past anything a radio schedule means and far short of a hang.
MAX_OCCURRENCES = 500

#: RFC 5545 weekday codes, Monday first to match ``datetime.weekday()``.
_WEEKDAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")

#: The frequencies worth supporting. Anything else is ignored rather than
#: approximated -- a programme placed on a guessed day is worse than one that
#: only appears where the feed literally put it.
_SUPPORTED = frozenset({"DAILY", "WEEKLY", "MONTHLY", "YEARLY"})


def expand(
    event: Any, rule: str, *, window_start: datetime, window_end: datetime, exdates: str = ""
) -> list[Any]:
    """Every occurrence of *event* inside the window, the original included.

    Returns ``[event]`` unchanged when the rule is absent, unreadable, or names
    a frequency this does not support -- so a feed that grows a part nobody
    anticipated loses the repeats, never the programme.
    """
    parts = parse_rule(rule)
    freq = parts.get("FREQ", "")
    if not parts or freq not in _SUPPORTED:
        return [event]

    interval = max(1, _int(parts.get("INTERVAL"), 1))
    count = _int(parts.get("COUNT"), 0)
    until = _timestamp(parts.get("UNTIL", ""))
    days = _byday(parts.get("BYDAY", ""))
    skipped = _exdates(exdates)

    starts = _starts(event.start, freq, interval, days, window_start, window_end, until, count)
    out: list[Any] = []
    for start in starts:
        if start in skipped:
            continue
        out.append(_occurrence(event, start))
    # DTSTART is always the first instance of a recurrence set (RFC 5545
    # 3.8.5.3), whatever the rule says afterwards. This is not pedantry: the
    # first real RRULE ACB published carries an UNTIL that falls *before* the
    # event it is attached to, so a strict reading of the bounds drops the
    # programme entirely (found against the live feed, 2026-08-24). A schedule
    # that quietly omits a published programme is the worst failure this app
    # has; showing it once is what every other calendar does with the same
    # entry.
    #
    # The anchor still has to be inside the window -- a series that began in
    # March, seen in August, must not be dragged forward -- and an EXDATE that
    # names it still cancels it, because that is somebody saying so explicitly.
    anchor = event.start
    if not out and window_start <= anchor <= window_end and anchor not in skipped:
        out.append(_occurrence(event, anchor))
    return out


def parse_rule(rule: str) -> dict[str, str]:
    """``FREQ=WEEKLY;BYDAY=MO,WE`` -> ``{"FREQ": "WEEKLY", "BYDAY": "MO,WE"}``.

    Upper-cased keys, values left alone: a weekday code is upper-case by the
    spec, and a ``UNTIL`` timestamp has a meaningful trailing ``Z``.
    """
    found: dict[str, str] = {}
    for chunk in str(rule or "").split(";"):
        name, sep, value = chunk.partition("=")
        if sep and name.strip():
            found[name.strip().upper()] = value.strip()
    return found


def _starts(
    anchor: datetime,
    freq: str,
    interval: int,
    days: tuple[int, ...],
    window_start: datetime,
    window_end: datetime,
    until: datetime | None,
    count: int,
) -> list[datetime]:
    """Every start this rule produces, in order, bounded three ways."""
    finish = min(window_end, until) if until is not None else window_end
    produced = 0
    out: list[datetime] = []
    for moment in _steps(anchor, freq, interval, days):
        produced += 1
        if produced > MAX_OCCURRENCES:
            break
        # COUNT is over the whole **series**, not over the window: a rule with
        # COUNT=4 that began in March has produced its four by August, and a
        # window-relative count would resurrect them in every later month.
        # So it is checked against everything stepped over, not against what
        # survived the window.
        if count and produced > count:
            break
        if moment > finish:
            break
        if moment >= window_start:
            out.append(moment)
    return out


def _steps(anchor: datetime, freq: str, interval: int, days: tuple[int, ...]) -> Any:
    """The rule's moments, in order, without regard to any window.

    A generator so the bounding above can simply stop -- an unbounded ``RRULE``
    is legal, and materialising one is the shape of a hang.
    """
    if freq == "WEEKLY" and days:
        yield from _weekly_by_day(anchor, interval, days)
        return
    step = {
        "DAILY": timedelta(days=interval),
        "WEEKLY": timedelta(weeks=interval),
    }.get(freq)
    moment = anchor
    for _ in range(MAX_OCCURRENCES + 1):
        yield moment
        moment = (
            moment + step
            if step is not None
            else _add_months(moment, interval * (12 if freq == "YEARLY" else 1))
        )


def _weekly_by_day(anchor: datetime, interval: int, days: tuple[int, ...]) -> Any:
    """``FREQ=WEEKLY;BYDAY=MO,WE,FR`` -- three programmes a week, not one.

    Weeks are counted from the anchor's own week, so ``INTERVAL=2`` means "the
    same days, every other week" rather than "every other listed day".
    """
    week_start = anchor - timedelta(days=anchor.weekday())
    produced = 0
    week = 0
    while produced <= MAX_OCCURRENCES:
        base = week_start + timedelta(weeks=week * interval)
        for weekday in sorted(days):
            moment = base + timedelta(days=weekday)
            moment = moment.replace(
                hour=anchor.hour, minute=anchor.minute, second=anchor.second, microsecond=0
            )
            if moment < anchor:
                continue
            produced += 1
            yield moment
        week += 1


def _add_months(moment: datetime, months: int) -> datetime:
    """*moment* shifted by whole months, clamped to a real day.

    The 31st plus one month is the 28th, 29th or 30th, depending -- clamped
    rather than rolled into the next month, because a monthly programme on the
    31st means "the end of the month", not "the 1st".
    """
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, _days_in_month(year, month))
    return moment.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    import calendar

    return calendar.monthrange(year, month)[1]


def _occurrence(event: Any, start: datetime) -> Any:
    """One occurrence: the parent event moved, keeping its length.

    The uid carries the parent's plus this start, so a reminder set on next
    Tuesday attaches to next Tuesday rather than to the series -- and so two
    occurrences never look like a duplicate of each other.
    """
    length = event.end - event.start if event.end is not None else None
    return replace(
        event,
        uid=f"{event.uid}@{start.strftime('%Y%m%dT%H%M%SZ')}",
        start=start,
        end=start + length if length is not None else None,
    )


def _byday(value: str) -> tuple[int, ...]:
    """``MO,WE,FR`` -> ``(0, 2, 4)``, ignoring any ordinal prefix.

    ``2FR`` ("the second Friday") is read as "Friday": the ordinal belongs to
    ``BYSETPOS``-style monthly rules this does not support, and dropping the
    number produces *more* occurrences rather than a wrong one -- which a
    listener can see and disbelieve, where a missing programme is invisible.
    """
    found: list[int] = []
    for chunk in str(value or "").split(","):
        code = chunk.strip().upper().lstrip("+-0123456789")
        if code in _WEEKDAYS:
            index = _WEEKDAYS.index(code)
            if index not in found:
                found.append(index)
    return tuple(found)


def _exdates(value: str) -> set[datetime]:
    """The ``EXDATE`` moments a series skips -- a cancelled week."""
    out: set[datetime] = set()
    for chunk in str(value or "").split(","):
        moment = _timestamp(chunk)
        if moment is not None:
            out.add(moment)
    return out


def _timestamp(value: str) -> datetime | None:
    from quill.core.radio.ics import parse_timestamp

    return parse_timestamp(value)


def _int(value: object, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def window_for(moment: datetime, *, months: int = 2) -> tuple[datetime, datetime]:
    """The expansion window for a month view: this month and the next.

    The same two months the feed's own address asks for, so a rule never
    produces occurrences the rest of the calendar has no room to show.
    """
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return (start, _add_months(start, max(1, months)))


__all__ = ["MAX_OCCURRENCES", "expand", "parse_rule", "window_for"]
