"""Dependency-free date recognition for line operations.

Extracted from :mod:`quill.core.format_ops` (GATE-11) so the date-aware line
sort has a small, reusable home. :func:`parse_first_date` finds the first
recognizable date in a string and returns a sortable ``(year, month, day)``
tuple, recognizing the common styles real documents use: numeric dates with
``/ - .`` separators (ISO ``YYYY-MM-DD`` plus day/month-first forms) and English
month-name dates (``Jan 5, 2020`` / ``5 January 2020``).
"""

from __future__ import annotations

import re

_MONTH_NAMES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_NUMERIC_DATE_RE = re.compile(r"\b(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})\b")
_MONTH_FIRST_DATE_RE = re.compile(
    r"\b(?P<month>[A-Za-z]{3,9})\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{2,4})\b",
    re.IGNORECASE,
)
_DAY_FIRST_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]{3,9})\.?,?\s+(?P<year>\d{2,4})\b",
    re.IGNORECASE,
)


def _normalize_two_digit_year(year: int) -> int:
    """Expand a 2-digit year using the strptime ``%y`` pivot (00-68 -> 2000s)."""
    return 2000 + year if year < 69 else 1900 + year


def _valid_ymd(year: int, month: int, day: int) -> tuple[int, int, int] | None:
    if 1 <= month <= 12 and 1 <= day <= 31:
        return (year, month, day)
    return None


def _interpret_numeric_date(
    first_raw: str, second_raw: str, third_raw: str, *, day_first: bool
) -> tuple[int, int, int] | None:
    first, second, third = int(first_raw), int(second_raw), int(third_raw)
    # A 4-digit leading group means ISO order: year, month, day.
    if len(first_raw) == 4:
        return _valid_ymd(first, second, third)
    # Otherwise the trailing group is the year and the first two are day/month.
    year = _normalize_two_digit_year(third) if len(third_raw) <= 2 else third
    if first > 12 and second <= 12:
        month, day = second, first  # first component can only be the day
    elif second > 12 and first <= 12:
        month, day = first, second  # second component can only be the day
    elif day_first:
        month, day = second, first
    else:
        month, day = first, second
    return _valid_ymd(year, month, day)


def _interpret_month_name_date(
    month_raw: str, day_raw: str, year_raw: str
) -> tuple[int, int, int] | None:
    month = _MONTH_NAMES.get(month_raw.lower())
    if month is None:
        return None
    year = int(year_raw)
    if len(year_raw) <= 2:
        year = _normalize_two_digit_year(year)
    return _valid_ymd(year, month, int(day_raw))


def parse_first_date(text: str, *, day_first: bool = False) -> tuple[int, int, int] | None:
    """Return ``(year, month, day)`` for the first recognizable date in *text*.

    Recognizes numeric dates with ``/ - .`` separators (ISO ``YYYY-MM-DD`` plus
    day/month-first numeric forms) and English month-name dates (``Jan 5, 2020``,
    ``5 January 2020``). ``day_first`` breaks the ambiguity for a numeric date
    whose day and month are both <= 12 (e.g. ``03/04/2020``); an unambiguous
    component (> 12) always decides regardless of the flag. Returns ``None`` when
    no date is found so callers can sink undated lines.
    """
    candidates: list[tuple[int, tuple[int, int, int]]] = []
    for match in _NUMERIC_DATE_RE.finditer(text):
        parsed = _interpret_numeric_date(
            match.group(1), match.group(2), match.group(3), day_first=day_first
        )
        if parsed is not None:
            candidates.append((match.start(), parsed))
            break
    for regex in (_MONTH_FIRST_DATE_RE, _DAY_FIRST_DATE_RE):
        for match in regex.finditer(text):
            parsed = _interpret_month_name_date(
                match.group("month"), match.group("day"), match.group("year")
            )
            if parsed is not None:
                candidates.append((match.start(), parsed))
                break
    if not candidates:
        return None
    # The leftmost recognized date wins ("the first date token per line").
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]
