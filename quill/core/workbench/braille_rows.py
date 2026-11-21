"""Short rows for braille displays (GitHub PRD 22.4 and F1, GH-R-114).

A list row read on a 40-cell display is read a display at a time, so every
cell spent on a column's name or a long date is a pan. With **Short rows for
braille** on (Workbench Options, Lists), a list shows one column whose text is
the row shaped for braille:

- **the most important field first:** the row's number and title together
  ("#42 Crash on start"), or its name, message or tag;
- **no column names,** and nothing empty;
- **abbreviations** for the words a list repeats (``closed`` is ``cl``, a
  pull request is ``PR``, a passing run ``ok``), counts with a one-letter
  unit (``3c`` for three comments), and dates as day and month ("9 Nov"), with
  the year only when it is not this year.

Nothing is cut off: a display pans, and a shortened title would hide the one
thing the row is for. The Details pane still says everything in full, and
F1 on Short rows for braille lists the abbreviations.

Provider-neutral and wx-free: it shapes cells a provider already made, so the
same rule could serve the WordPress Workbench.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Sequence

__all__ = [
    "ABBREVIATIONS",
    "BRAILLE_COLUMN",
    "LEAD_COLUMNS",
    "UNITS",
    "abbreviations_help",
    "braille_row",
]

#: The one column a braille-shaped list shows.
BRAILLE_COLUMN = "row"

#: The columns that name a row, most important first. ``number`` is joined to
#: the first of the others ("#42 Crash on start").
LEAD_COLUMNS: tuple[str, ...] = ("title", "name", "message", "tag", "result")

#: Words a list repeats, as a braille reader is spared them.
ABBREVIATIONS: dict[str, str] = {
    "pull request": "PR",
    "issue": "iss",
    "closed": "cl",
    "merged": "mrgd",
    "draft": "dft",
    "prerelease": "pre",
    "protected": "prot",
    "success": "ok",
    "failure": "fail",
    "cancelled": "canc",
    "in_progress": "running",
    "completed": "done",
    "skipped": "skip",
    "active": "on",
    "disabled_manually": "off",
}

#: Count columns and the one letter that says what the number counts.
UNITS: dict[str, str] = {
    "comments": "c",
    "downloads": "dl",
    "assets": "a",
}

_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _short_date(text: str, today: dt.date) -> str:
    match = _DATE.match(text)
    if match is None:
        return text
    year, month, day = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        return text
    words = f"{day} {_MONTHS[month - 1]}"
    return words if year == today.year else f"{words} {year % 100:02d}"


def _shorten(column: str, value: str, today: dt.date) -> str:
    value = value.strip()
    if not value:
        return ""
    if column in UNITS:
        return "" if value == "0" else f"{value}{UNITS[column]}"
    if column == "run_number":
        return f"run {value}"
    shortened = _short_date(value, today)
    if shortened != value:
        return shortened
    return ABBREVIATIONS.get(value.lower(), value)


def braille_row(
    cells: Sequence[str], columns: Sequence[str], *, today: dt.date | None = None
) -> str:
    """One braille-shaped line from a row's *cells* under *columns*."""
    day = today or dt.date.today()
    values = {column: str(cell or "").strip() for column, cell in zip(columns, cells, strict=False)}
    lead_column = next((c for c in LEAD_COLUMNS if values.get(c)), "")
    lead = values.get(lead_column, "")
    number = values.get("number") or values.get("short_sha") or ""
    if number:
        mark = f"#{number}" if number.isdigit() else number
        lead = f"{mark} {lead}".strip()
    parts = [lead] if lead else []
    used = {lead_column, "number", "short_sha"}
    for column in columns:
        if column in used:
            continue
        used.add(column)
        part = _shorten(column, values.get(column, ""), day)
        if part and part not in parts:
            parts.append(part)
    return "; ".join(parts)


def abbreviations_help() -> str:
    """What F1 on the option says: every abbreviation, once."""
    words = ", ".join(f"{short} for {long}" for long, short in ABBREVIATIONS.items())
    units = ", ".join(f"3{unit} for 3 {column}" for column, unit in UNITS.items())
    return f"Rows put the number and title first. Words: {words}. Counts: {units}."
