"""The Events Calendar, recognised (wordpress.md 9.15).

When a site has The Events Calendar (``tribe/events/v1``), QUILL adds three
small things, sized to be useful in a sentence: an event's start, end and
venue in Properties, New Event, and a plain Coming Up list. The event itself
is an ordinary post of the ``tribe_events`` type, so Open, Save and Publish
need nothing new.

Dates are the plugin's own local ``YYYY-MM-DD HH:MM:SS``. They are spoken
with fixed English day and month names, so the words never depend on the
computer's locale.

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import rendered

NAMESPACE = "tribe/events/v1"
#: The post types an event can be opened as.
EVENT_KINDS = frozenset({"tribe_events"})

_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class EventDateError(CodedError, ValueError):
    """A start or end QUILL cannot read; the message says the shape it takes."""

    code = "QUILL-WP-EVENTS-DATE"


@dataclass(frozen=True)
class Event:
    id: int
    title: str
    start: str
    end: str
    all_day: bool = False
    venue_id: int = 0
    venue: str = ""
    url: str = ""
    status: str = ""

    def when(self) -> str:
        return spoken_span(self.start, self.end, all_day=self.all_day)

    def spoken(self) -> str:
        where = f", at {self.venue}" if self.venue else ""
        return f"{self.title}, {self.when()}{where}"

    def facts(self) -> str:
        """Lines for Properties."""
        return (
            f"Event starts: {spoken_moment(self.start, all_day=self.all_day)}\n"
            f"Event ends: {spoken_moment(self.end, all_day=self.all_day)}\n"
            f"Venue: {self.venue or 'none'}\n"
        )


@dataclass(frozen=True)
class Venue:
    id: int
    name: str


def _moment(stamp: str) -> datetime | None:
    try:
        return datetime.strptime(stamp.strip()[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _day(moment: datetime) -> str:
    return f"{_DAYS[moment.weekday()]} {moment.day} {_MONTHS[moment.month - 1]} {moment.year}"


def spoken_moment(stamp: str, *, all_day: bool = False) -> str:
    """``2026-11-21 10:00:00`` -> "Saturday 21 November 2026 at 10:00"."""
    moment = _moment(stamp)
    if moment is None:
        return stamp or "not set"
    return _day(moment) if all_day else f"{_day(moment)} at {moment:%H:%M}"


def spoken_span(start: str, end: str, *, all_day: bool = False) -> str:
    """One day: "Saturday 21 November 2026, 10:00 to 16:00"; longer: from ... to ..."""
    first, last = _moment(start), _moment(end)
    if first is None:
        return "no date set"
    if last is None or last <= first:
        return spoken_moment(start, all_day=all_day)
    if first.date() == last.date():
        return (
            f"{_day(first)}, all day"
            if all_day
            else f"{_day(first)}, {first:%H:%M} to {last:%H:%M}"
        )
    return f"from {spoken_moment(start, all_day=all_day)} to {spoken_moment(end, all_day=all_day)}"


_WHEN = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$")


def parse_when(text: str, *, label: str = "The date") -> str:
    """ "2026-11-21 10:00" -> "2026-11-21 10:00:00"; a date alone starts at midnight."""
    match = _WHEN.match(text.strip())
    if match is None:
        raise EventDateError(
            f"{label} needs a date and time QUILL can read, such as 2026-11-21 10:00."
        )
    year, month, day, hour, minute, second = (int(g) if g else 0 for g in match.groups())
    try:
        moment = datetime(year, month, day, hour, minute, second)
    except ValueError as exc:
        raise EventDateError(f"{label} is not a real date: {text.strip()}.") from exc
    return f"{moment:%Y-%m-%d %H:%M:%S}"


def event_from(raw: Any) -> Event:
    data = raw if isinstance(raw, dict) else {}
    venue = _as_dict(data.get("venue"))
    return Event(
        id=int(data.get("id", 0) or 0),
        title=rendered(data.get("title")) or "Untitled event",
        start=str(data.get("start_date", "") or ""),
        end=str(data.get("end_date", "") or ""),
        all_day=bool(data.get("all_day", False)),
        venue_id=int(venue.get("id", 0) or 0) if venue else 0,
        venue=rendered(venue.get("venue")) if venue else "",
        url=str(data.get("url", "") or ""),
        status=str(data.get("status", "") or ""),
    )


def coming_up(api: WordPressApi, *, per_page: int = 50) -> list[Event]:
    """Events from now on, soonest first."""
    raw = api.get(f"{NAMESPACE}/events", start_date="now", per_page=per_page)
    rows = raw.get("events", []) if isinstance(raw, dict) else []
    return [event_from(r) for r in rows if isinstance(r, dict)]


def load_event(api: WordPressApi, event_id: int) -> Event:
    return event_from(api.get(f"{NAMESPACE}/events/{event_id}"))


def list_venues(api: WordPressApi) -> list[Venue]:
    raw = api.get(f"{NAMESPACE}/venues", per_page=50)
    rows = raw.get("venues", []) if isinstance(raw, dict) else []
    return [
        Venue(int(r.get("id", 0) or 0), rendered(r.get("venue")) or f"Venue {r.get('id')}")
        for r in rows
        if isinstance(r, dict)
    ]


def create_event(api: WordPressApi, title: str, start: str, end: str, venue_id: int = 0) -> Event:
    """A new event, as a draft: nothing is public until it is published."""
    body: dict[str, Any] = {
        "title": title,
        "start_date": start,
        "end_date": end,
        "status": "draft",
    }
    if venue_id:
        body["venue"] = venue_id
    return event_from(api.post(f"{NAMESPACE}/events", body))


def update_event(
    api: WordPressApi, event_id: int, start: str, end: str, venue_id: int = 0
) -> Event:
    body: dict[str, Any] = {"start_date": start, "end_date": end}
    if venue_id:
        body["venue"] = venue_id
    return event_from(api.post(f"{NAMESPACE}/events/{event_id}", body))
