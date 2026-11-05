"""What people sent to a form, read aloud and exported (wordpress.md 17a.8).

wx-free. The Responses window shows these rows; nothing here keeps a
response anywhere. Responses are personal data: they arrive only when the
person opens Responses, stay in memory while it is open, are never written
to a log, and are written to a file only where the person chooses (CSV, Word).

The four views are the plan's: the list, newest first; one at a time, as
question and answer pairs; grouped by date (the calendar view); and grouped by
place (the map view), which uses the city, region and country a response gave.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from quill.core.forms.qaf_site import Response

_MONTHS = (
    "January February March April May June July August September October November December"
).split()
_DAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
_PLACE_KEYS = ("city", "town", "state", "region", "province", "country")


@dataclass(frozen=True)
class Row:
    """One line of the window: a response, or a heading over a group of them."""

    text: str
    response: Response | None = None


def parse_time(stamp: str) -> dt.datetime | None:
    """QAF's ``created_at`` (``2026-11-03 14:10:00``, the site's own time)."""
    text = (stamp or "").strip().replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def spoken_day(when: dt.datetime | dt.date, *, weekday: bool = False) -> str:
    day = f"{when.day} {_MONTHS[when.month - 1]}"
    return f"{_DAYS[when.weekday()]} {day} {when.year}" if weekday else day


def spoken_time(when: dt.datetime) -> str:
    hour = when.hour % 12 or 12
    return f"{hour}:{when.minute:02d} {'AM' if when.hour < 12 else 'PM'}"


def sent_at(response: Response) -> str:
    """ "3 November, 2:10 PM", or the stamp as the site gave it."""
    when = parse_time(response.created_at)
    return f"{spoken_day(when)}, {spoken_time(when)}" if when else response.created_at


def answer_text(value: Any) -> str:
    """One answer as words: a list joined, an address in reading order, Yes or No."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(t for t in (answer_text(v) for v in value) if t)
    if isinstance(value, dict):
        return ", ".join(t for t in (answer_text(v) for v in value.values()) if t)
    return " ".join(str(value).split())


def who(response: Response, labels: dict[str, str]) -> str:
    """The name a response gave, else its email address, else nothing."""
    email = ""
    for key, value in response.answers.items():
        text = answer_text(value)
        if not text:
            continue
        name = f"{key} {labels.get(key, '')}".lower()
        if "name" in name and "user" not in name and "@" not in text:
            return text
        if not email and ("@" in text and " " not in text):
            email = text
    return email


def row_text(response: Response, labels: dict[str, str], form_title: str) -> str:
    """ "Response 41, 3 November, 2:10 PM, Jane Smith, Event registration"."""
    parts = [f"Response {response.id}", sent_at(response), who(response, labels), form_title]
    if response.is_starred:
        parts.append("starred")
    return ", ".join(p for p in parts if p)


def list_rows(responses: Iterable[Response], labels: dict[str, str], title: str) -> list[Row]:
    return [Row(row_text(r, labels, title), r) for r in responses]


def pairs(response: Response, labels: dict[str, str]) -> list[tuple[str, str]]:
    """Question and answer, in the form's order, then anything the form no longer asks."""
    out: list[tuple[str, str]] = []
    for key, label in labels.items():
        if key in response.answers:
            out.append((label, answer_text(response.answers[key]) or "no answer"))
    for key, value in response.answers.items():
        if key not in labels:
            out.append((key, answer_text(value) or "no answer"))
    return out


def one_at_a_time(response: Response, labels: dict[str, str], form_title: str) -> str:
    """The whole response, one "question: answer" a line, to read line by line."""
    lines = [f"Response {response.id} to {form_title}, sent {sent_at(response)}."]
    lines += [f"{q}: {a}" for q, a in pairs(response, labels)]
    return "\n".join(lines) + "\n"


def _counted(label: str, group: list[Response]) -> str:
    return f"{label}, {len(group)} {'response' if len(group) == 1 else 'responses'}"


def by_date(responses: Iterable[Response], labels: dict[str, str], title: str) -> list[Row]:
    """The calendar view: a heading for each day, its responses under it, newest day first."""
    days: dict[str, list[Response]] = {}
    for response in responses:
        when = parse_time(response.created_at)
        key = spoken_day(when, weekday=True) if when else "Date not given"
        days.setdefault(key, []).append(response)
    rows: list[Row] = []
    for day, group in days.items():
        rows.append(Row(_counted(day, group)))
        rows += [Row("  " + row_text(r, labels, title), r) for r in group]
    return rows


def place(response: Response) -> str:
    """Where a response says it is: city, region and country, as given."""
    found: dict[str, str] = {}

    def look(key: str, value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                look(str(k), v)
            return
        lowered = key.lower()
        for wanted in _PLACE_KEYS:
            if wanted in lowered and wanted not in found:
                text = answer_text(value)
                if text:
                    found[wanted] = text

    for key, value in response.answers.items():
        look(str(key), value)
    city = found.get("city") or found.get("town", "")
    region = found.get("state") or found.get("region") or found.get("province", "")
    return ", ".join(p for p in (city, region, found.get("country", "")) if p)


def by_place(responses: Iterable[Response], labels: dict[str, str], title: str) -> list[Row]:
    """The map view: a heading for each place, most responses first."""
    places: dict[str, list[Response]] = {}
    for response in responses:
        places.setdefault(place(response) or "No place given", []).append(response)
    ordered = sorted(places.items(), key=lambda kv: (kv[0] == "No place given", -len(kv[1])))
    rows: list[Row] = []
    for name, group in ordered:
        rows.append(Row(_counted(name, group)))
        rows += [Row("  " + row_text(r, labels, title), r) for r in group]
    return rows


VIEWS: tuple[tuple[str, str], ...] = (
    ("list", "List, newest first"),
    ("date", "Grouped by date"),
    ("place", "Grouped by place"),
)


def view_rows(
    view: str, responses: Iterable[Response], labels: dict[str, str], title: str
) -> list[Row]:
    if view == "date":
        return by_date(responses, labels, title)
    if view == "place":
        return by_place(responses, labels, title)
    return list_rows(responses, labels, title)


def find(responses: Iterable[Response], text: str) -> list[Response]:
    """The responses with *text* in any answer, ignoring case."""
    wanted = " ".join(text.split()).lower()
    if not wanted:
        return list(responses)
    return [
        r for r in responses if any(wanted in answer_text(v).lower() for v in r.answers.values())
    ]


def csv_text(responses: Iterable[Response], labels: dict[str, str]) -> str:
    """Every response as CSV: a row each, a column per question, in the form's order."""
    rows = list(responses)
    keys = list(labels)
    for response in rows:
        keys += [k for k in response.answers if k not in keys]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(["Response", "Sent", *(labels.get(k, k) for k in keys)])
    for response in rows:
        when = parse_time(response.created_at)
        stamp = when.strftime("%Y-%m-%d %H:%M") if when else response.created_at
        writer.writerow([response.id, stamp, *(answer_text(response.answers.get(k)) for k in keys)])
    return out.getvalue()


__all__ = [
    "VIEWS",
    "Row",
    "answer_text",
    "by_date",
    "by_place",
    "csv_text",
    "find",
    "list_rows",
    "one_at_a_time",
    "pairs",
    "parse_time",
    "place",
    "row_text",
    "sent_at",
    "view_rows",
    "who",
]
