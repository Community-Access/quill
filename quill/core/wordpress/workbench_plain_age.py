"""How old, in the plain-language batch grammar (PRD 15.8): "older than a year", "before 2024".

:func:`find_age` takes the age out of a batch phrase's filters and turns it
into the dates WordPress's ``before`` and ``after`` query parameters take, by
the item's date. It reads a fixed set of shapes, so the same words always
mean the same dates:

- ``older than a year``, ``older than six months``, ``older than 30 days``,
  ``older than 3 weeks`` (counted back from today);
- ``newer than two weeks`` (or ``younger than``);
- ``before March 2024``, ``before 2024``, ``before 15 March 2024``,
  ``before 2024-03-15``; and ``after`` or ``since`` any of those.

Anything else after one of those words is :class:`AgeError`, never a guess.
Wx-free.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

from quill.core.error_codes import CodedError

__all__ = ["Age", "AgeError", "find_age"]

_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}  # fmt: skip
_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
_AGE = re.compile(
    r"\b(?P<rel>older than|newer than|younger than|before|after|since)\s+"
    r"(?P<what>.+?)(?=\s+(?:by|in)\b|$)",
    re.IGNORECASE,
)
_SPAN = re.compile(
    r"^(?P<n>\d+|[a-z]+)\s+(?P<unit>day|week|month|year)s?(?:\s+old)?$", re.IGNORECASE
)


class AgeError(CodedError):
    """An age the batch grammar does not read."""

    code = "QUILL-WP-WORKBENCH-AGE"

    @property
    def plain(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class Age:
    """WordPress's ``before`` and ``after`` (ISO dates, either may be empty), and the words."""

    before: str = ""
    after: str = ""
    words: str = ""


def _months_back(today: date, months: int) -> date:
    index = today.year * 12 + today.month - 1 - months
    year, month = divmod(index, 12)
    day = min(today.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day)


def _span_start(what: str, today: date) -> date:
    found = _SPAN.match(what.strip())
    if not found:
        raise AgeError(
            f"QUILL does not read {what!r} as an age. Say, for example, older than a year, "
            "older than six months or older than 30 days."
        )
    raw = found.group("n").lower()
    count = int(raw) if raw.isdigit() else _NUMBERS.get(raw, 0)
    if count <= 0:
        raise AgeError(f"QUILL does not read {raw!r} as a number here.")
    unit = found.group("unit").lower()
    if unit == "day":
        return today - timedelta(days=count)
    if unit == "week":
        return today - timedelta(weeks=count)
    return _months_back(today, count * (12 if unit == "year" else 1))


def _calendar_span(what: str) -> tuple[date, date]:
    """The first and last day *what* names: a year, a month of a year, or a day."""
    text = what.strip().rstrip(",").lower().replace(",", " ")
    parts = text.split()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            day = date.fromisoformat(text)
            return day, day
        if len(parts) == 1 and re.fullmatch(r"\d{4}", parts[0]):
            year = int(parts[0])
            return date(year, 1, 1), date(year, 12, 31)
        if len(parts) == 2 and parts[0] in _MONTHS and parts[1].isdigit():
            year, month = int(parts[1]), _MONTHS[parts[0]]
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        if len(parts) == 3:
            day_first = parts[0].isdigit() and parts[1] in _MONTHS
            day_text, month_text = (parts[0], parts[1]) if day_first else (parts[1], parts[0])
            if month_text in _MONTHS and day_text.isdigit() and parts[2].isdigit():
                day = date(int(parts[2]), _MONTHS[month_text], int(day_text))
                return day, day
    except ValueError:
        pass
    raise AgeError(
        f"QUILL does not read {what!r} as a date. Say, for example, before March 2024, "
        "before 2024 or before 15 March 2024."
    )


def _iso(day: date, end: bool = False) -> str:
    return f"{day.isoformat()}T{'23:59:59' if end else '00:00:00'}"


def find_age(text: str, today: date) -> tuple[Age, str]:
    """The age in *text* and *text* without it; an empty :class:`Age` when it names none."""
    found = _AGE.search(text)
    if not found:
        return Age(), text
    rel, what = found.group("rel").lower(), found.group("what")
    rest = (text[: found.start()] + text[found.end() :]).strip()
    words = f"{rel} {what.strip()}"
    if rel == "older than":
        return Age(before=_iso(_span_start(what, today)), words=words), rest
    if rel in ("newer than", "younger than"):
        return Age(after=_iso(_span_start(what, today)), words=words), rest
    first, last = _calendar_span(what)
    if rel == "before":
        return Age(before=_iso(first), words=words), rest
    if rel == "after":
        return Age(after=_iso(last, end=True), words=words), rest
    return Age(after=_iso(first - timedelta(days=1), end=True), words=words), rest
