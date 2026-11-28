"""Understanding a typed date for Weather on a Past Date ("Go to Date").

A calendar control reads poorly with a screen reader, so the window takes a
plain text field and this module makes sense of what was typed:

* ``2011-03-14``, ``14 March 2011``, ``March 14, 2011``, ``Mar 14 2011``
* ``3/14/2011`` or ``14/3/2011``, in the order the system writes dates (``MDY``,
  ``DMY`` or ``YMD``); the answer always says which order it read, and a date
  only one order allows (a 14 in the first place) is read that way.
* ``today``, ``yesterday``, ``3 days ago``, ``2 weeks ago``, ``last week``,
  ``last month``, ``last year``, ``a year ago today``
* a year alone (``2011``) or a month and year (``March 2011``, ``2011-03``,
  ``3/2011``), which mean a span to browse rather than one day.

:func:`check` then says, in plain words, why a day cannot be used: it is in
the future, it is before 1940, or (not an error) it is in the last few days, so
the recent data is used instead of the archive.

Pure and strict-typed; "today" and the date order are always passed in.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

from quill.core.error_codes import CodedError

EARLIEST = date(1940, 1, 1)
#: Open-Meteo's archive runs about this many days behind today.
ARCHIVE_LAG_DAYS = 5

_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
_MONTHS["sept"] = 9
_ORDER_WORDS = {
    "MDY": "month first",
    "DMY": "day first",
    "YMD": "year first",
}
_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}  # fmt: skip
NOT_UNDERSTOOD = (
    "Quill Weather did not understand that date. Try 2011-03-14, March 14, 2011, "
    "3 days ago, or a year such as 2011."
)


@dataclass(frozen=True, slots=True)
class DateQuery:
    """What was understood: one day (``start == end``) or a span to browse.

    ``note`` is the sentence to say about how it was read ("Read as March 4,
    2011, month first, as your system writes dates."), or ''."""

    start: date
    end: date
    note: str = ""

    @property
    def is_span(self) -> bool:
        return self.start != self.end


class DateNotUnderstood(CodedError, ValueError):
    """The text is not a date this module can read. ``args[0]`` is the sentence."""

    code = "QUILL-WEATHER-DATE-NOTUNDERSTOOD"


def long_date(d: date) -> str:
    """'Monday, March 14, 2011'."""
    return f"{calendar.day_name[d.weekday()]}, {calendar.month_name[d.month]} {d.day}, {d.year}"


def _month_span(year: int, month: int) -> DateQuery:
    last = calendar.monthrange(year, month)[1]
    return DateQuery(date(year, month, 1), date(year, month, last))


def _make(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise DateNotUnderstood(
            f"There is no such date: {calendar.month_name[month] if 1 <= month <= 12 else month} "
            f"{day}, {year}."
        ) from exc


def _shift_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def shift(d: date, *, days: int = 0, months: int = 0, years: int = 0) -> date:
    """Move a date; months and years keep the day where they can (Jan 31 + 1
    month is Feb 28 or 29; Feb 29 + 1 year is Feb 28)."""
    moved = _shift_months(d, months + 12 * years) if months or years else d
    return moved + timedelta(days=days)


def _relative(text: str, today: date) -> DateQuery | None:
    if text in ("today", "now"):
        return DateQuery(today, today)
    if text == "yesterday":
        day = today - timedelta(days=1)
        return DateQuery(day, day)
    if text in ("last week", "a week ago"):
        day = today - timedelta(days=7)
        return DateQuery(day, day)
    if text in ("last month", "a month ago"):
        day = shift(today, months=-1)
        return DateQuery(day, day)
    if text in ("last year", "a year ago", "a year ago today", "this day last year"):
        day = shift(today, years=-1)
        return DateQuery(day, day)
    match = re.fullmatch(r"(\d+|[a-z]+) (day|week|month|year)s? ago(?: today)?", text)
    if not match:
        return None
    raw, unit = match.groups()
    count = int(raw) if raw.isdigit() else _NUMBER_WORDS.get(raw)
    if count is None:
        return None
    if unit == "day":
        day = today - timedelta(days=count)
    elif unit == "week":
        day = today - timedelta(weeks=count)
    elif unit == "month":
        day = shift(today, months=-count)
    else:
        day = shift(today, years=-count)
    return DateQuery(day, day)


def _numeric(parts: list[int], order: str) -> DateQuery:
    """Three numbers in the system's order, or the only order they allow."""
    a, b, c = parts
    if a > 31:  # 2011/3/14 is year first whatever the system says
        when = _make(a, b, c)
        return DateQuery(when, when)
    candidates = {
        "MDY": (c, a, b),
        "DMY": (c, b, a),
    }
    preferred = order if order in candidates else "MDY"
    other = "DMY" if preferred == "MDY" else "MDY"
    year, month, day = candidates[preferred]
    used = preferred
    if month > 12:  # this order cannot be right; the other one can
        year, month, day = candidates[other]
        used = other
    if month > 12:  # neither order makes a date
        raise DateNotUnderstood(NOT_UNDERSTOOD)
    if year < 100:
        year += 2000 if year < 50 else 1900
    when = _make(year, month, day)
    if used != preferred:
        why = f"{_ORDER_WORDS[used]}, because {a} cannot be a month"
    elif order == preferred:
        why = f"{_ORDER_WORDS[used]}, as your system writes dates"
    else:  # a year-first system, and the year is last: month first is a guess
        why = f"{_ORDER_WORDS[used]}"
    note = f"Read as {calendar.month_name[when.month]} {when.day}, {when.year}, {why}."
    return DateQuery(when, when, note)


def parse(text: str, *, today: date, order: str = "MDY") -> DateQuery:
    """Understand *text*, or raise :class:`DateNotUnderstood` with the sentence."""
    raw = " ".join(text.strip().lower().replace(",", " ").split())
    if not raw:
        raise DateNotUnderstood("Type a date first, such as 2011-03-14 or yesterday.")
    found = _relative(raw, today)
    if found is not None:
        return found
    if re.fullmatch(r"\d{4}", raw):
        year = int(raw)
        return DateQuery(date(year, 1, 1), date(year, 12, 31))
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", raw):
        when = _make(int(m[1]), int(m[2]), int(m[3]))
        return DateQuery(when, when)
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})", raw):
        month = int(m[2])
        if not 1 <= month <= 12:
            raise DateNotUnderstood(NOT_UNDERSTOOD)
        return _month_span(int(m[1]), month)
    if m := re.fullmatch(r"(\d{1,4})[/.-](\d{1,2})[/.-](\d{1,4})", raw):
        return _numeric([int(m[1]), int(m[2]), int(m[3])], order)
    if m := re.fullmatch(r"(\d{1,2})[/.-](\d{4})", raw):
        month = int(m[1])
        if not 1 <= month <= 12:
            raise DateNotUnderstood(NOT_UNDERSTOOD)
        return _month_span(int(m[2]), month)
    words = raw.replace(".", "").split()
    words = [re.sub(r"(st|nd|rd|th)$", "", w) if re.fullmatch(r"\d+(st|nd|rd|th)", w) else w
             for w in words]  # fmt: skip
    if len(words) == 2 and words[0] in _MONTHS and words[1].isdigit() and len(words[1]) == 4:
        return _month_span(int(words[1]), _MONTHS[words[0]])
    if len(words) == 3:
        first, second, third = words
        if first in _MONTHS and second.isdigit() and third.isdigit():  # March 14 2011
            when = _make(int(third), _MONTHS[first], int(second))
            return DateQuery(when, when)
        if second in _MONTHS and first.isdigit() and third.isdigit():  # 14 March 2011
            when = _make(int(third), _MONTHS[second], int(first))
            return DateQuery(when, when)
    raise DateNotUnderstood(NOT_UNDERSTOOD)


def check(day: date, *, today: date) -> tuple[bool, str]:
    """(usable, sentence). Unusable: the future, or before 1940. Usable with a
    note: the last few days, which come from the recent data."""
    if day > today:
        return False, (
            f"{long_date(day)} is in the future. Weather on a Past Date shows days up to "
            "today; Weather Now has the forecast."
        )
    if day < EARLIEST:
        return False, (
            f"{long_date(day)} is before 1940. Open-Meteo's history starts on January 1, 1940."
        )
    if day > today - timedelta(days=ARCHIVE_LAG_DAYS):
        return True, (
            "That is within the last 5 days, so it uses Open-Meteo's recent data "
            "instead of the archive, which runs about 5 days behind."
        )
    return True, ""


def clip_span(query: DateQuery, *, today: date) -> tuple[DateQuery | None, str]:
    """A span clipped to 1940 to today, or None and the reason when none is left."""
    start, end = max(query.start, EARLIEST), min(query.end, today)
    if end < start:
        if query.start > today:
            return None, "That span is in the future, so there is nothing to show yet."
        return None, "That span is before 1940. Open-Meteo's history starts on January 1, 1940."
    return DateQuery(start, end, query.note), ""


def system_date_order() -> str:
    """'MDY', 'DMY' or 'YMD' from the user's Windows short-date setting; 'MDY'
    when it cannot be read (or off Windows)."""
    import sys

    if sys.platform != "win32":
        return "MDY"
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(8)
        locale_idate = 0x21  # LOCALE_IDATE: 0 MDY, 1 DMY, 2 YMD
        got = ctypes.windll.kernel32.GetLocaleInfoEx(None, locale_idate, buffer, len(buffer))
        if got:
            return {"0": "MDY", "1": "DMY", "2": "YMD"}.get(buffer.value.strip(), "MDY")
    except (AttributeError, OSError):
        pass
    return "MDY"
