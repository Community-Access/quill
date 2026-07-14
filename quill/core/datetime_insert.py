"""Date and time insertion helpers (EDS-2) and date calculation (EDS-3).

These functions are UI-framework agnostic. ``format_datetime`` accepts either a
``strftime``-style format (containing ``%``) or a small set of .NET-style tokens
(``yyyy``, ``MM``, ``dd``, ``HH``, ``mm``, ``ss``, ``yy``) for friendliness.

The Insert-menu date/time items that historically called into this module were
removed in the date/time consolidation. The ``com.quill.bundled.insert-tools``
Quillin now owns ``Insert > Date and Time`` as a Layer 1 snippet pack, and the
mixin handlers in :mod:`quill.ui.main_frame_power_tools` no longer import this
module. ``calculate_date``, ``format_datetime`` and the rest remain available
for tests, third-party Quillins, and any future feature that needs them.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime

__all__ = [
    "DEFAULT_DATETIME_FORMAT",
    "calculate_date",
    "format_datetime",
    "nth_weekday_of_month",
    "parse_weekday",
]

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# Ordered longest-first so that, for example, ``yyyy`` is replaced before ``yy``.
_NET_TOKENS: tuple[tuple[str, str], ...] = (
    ("yyyy", "%Y"),
    ("yy", "%y"),
    ("MM", "%m"),
    ("dd", "%d"),
    ("HH", "%H"),
    ("mm", "%M"),
    ("ss", "%S"),
)

_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _to_strftime(fmt: str) -> str:
    if "%" in fmt:
        return fmt
    result = fmt
    for token, replacement in _NET_TOKENS:
        result = result.replace(token, replacement)
    return result


def format_datetime(moment: datetime, fmt: str = DEFAULT_DATETIME_FORMAT) -> str:
    """Format ``moment`` using a strftime- or .NET-style format string."""
    return moment.strftime(_to_strftime(fmt))


def parse_weekday(name: str) -> int:
    """Return the Python weekday index (Monday=0) for a weekday name."""
    key = name.strip().lower()
    if key in _WEEKDAYS:
        return _WEEKDAYS[key]
    for full, index in _WEEKDAYS.items():
        if full.startswith(key) and len(key) >= 3:
            return index
    raise ValueError(f"Unknown weekday: {name}")


def nth_weekday_of_month(year: int, month: int, week: int, weekday: int) -> date:
    """Return the date of the ``week``-th ``weekday`` in ``month``.

    ``weekday`` uses Monday=0. ``week`` is 1-based; a negative ``week`` counts
    from the end of the month (``-1`` -> the last such weekday).
    """
    if weekday < 0 or weekday > 6:
        raise ValueError("weekday must be between 0 (Monday) and 6 (Sunday)")
    if week == 0:
        raise ValueError("week must be non-zero")
    first_weekday, days_in_month = calendar.monthrange(year, month)
    offset = (weekday - first_weekday) % 7
    first_occurrence = 1 + offset
    if week > 0:
        day = first_occurrence + (week - 1) * 7
        if day > days_in_month:
            raise ValueError("No such weekday occurrence in month")
    else:
        day = first_occurrence
        while day + 7 <= days_in_month:
            day += 7
        day += (week + 1) * 7
        if day < 1:
            raise ValueError("No such weekday occurrence in month")
    return date(year, month, day)


def calculate_date(
    year: int,
    month: int,
    *,
    week: int | None = None,
    weekday: int | None = None,
    day: int | None = None,
) -> date:
    """Compute a date from either a fixed ``day`` or an nth-``weekday`` rule."""
    if day is not None:
        return date(year, month, day)
    if week is not None and weekday is not None:
        return nth_weekday_of_month(year, month, week, weekday)
    raise ValueError("Provide either a day, or a week and weekday")
