"""The Events Calendar in the Workbench: events, venues and organizers (Package 11).

All through ``tribe/events/v1``, whose collections answer with an object
(``{"events": [...], "total_pages": n}``), so they are paged here rather than
by the client's list reader.

**Time zones.** An event's start and end are in its own time zone, which the
plugin returns as ``timezone`` with ``utc_start_date`` beside it. Every row
says the event's time and zone, and your computer's time too when it
differs, from the UTC time the site gave (:func:`your_time`). New Event
leaves the zone out unless one is typed, so the plugin uses the site's.

**Recurring events** are Events Calendar Pro's. The REST API returns one
occurrence at a time and no recurrence rule, so a row in a series says it is
one occurrence, and Edit and Move to Trash refuse it with where the series is
changed (:func:`recurring_words`). A site without Pro has none.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, tzinfo
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_events import (
    NAMESPACE,
    EventDateError,
    parse_when,
    spoken_moment,
    spoken_span,
)
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "NAMESPACE",
    "EventSpec",
    "OrganizerSpec",
    "VenueSpec",
    "collect",
    "event_body",
    "event_preview",
    "event_row",
    "organizer_body",
    "organizer_row",
    "place_preview",
    "recurring_words",
    "venue_body",
    "venue_row",
    "your_time",
]

_PER_PAGE = 50
_PAGES = 6


def collect(api: Any, what: str, params: Mapping[str, object]) -> list[dict[str, Any]]:
    """Every *what* (``events``, ``venues``, ``organizers``) the route returns, page by page."""
    found: list[dict[str, Any]] = []
    for page in range(1, _PAGES + 1):
        answer = api.get(f"{NAMESPACE}/{what}", page=page, per_page=_PER_PAGE, **dict(params))
        items = answer.get(what, []) if isinstance(answer, Mapping) else []
        found += [i for i in items if isinstance(i, dict)]
        pages = int(answer.get("total_pages", 1) or 1) if isinstance(answer, Mapping) else 1
        if page >= pages or not items:
            break
    return found


def your_time(utc_stamp: str, *, local: tzinfo | None = None) -> str:
    """The UTC start as your computer's clock reads it ("" when the site gave none)."""
    try:
        moment = datetime.strptime(utc_stamp.strip()[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ""
    there = moment.replace(tzinfo=UTC).astimezone(local)
    return spoken_moment(f"{there:%Y-%m-%d %H:%M:%S}")


def recurring_words(raw: Mapping[str, Any]) -> str:
    """A sentence when the event is one occurrence of a recurring series, else ""."""
    flags = (
        raw.get("recurring"),
        raw.get("is_recurring"),
        raw.get("series"),
        raw.get("recurrence"),
    )
    if not any(flags):
        return ""
    return (
        "This is one occurrence of a recurring series from Events Calendar Pro. The REST API "
        "gives each occurrence but not the series' rule, so the series is changed or removed "
        "in Events in wp-admin, not here."
    )


def _names(items: Any, key: str) -> str:
    rows = items if isinstance(items, list) else ([items] if isinstance(items, Mapping) else [])
    return ", ".join(rendered(i.get(key)) for i in rows if isinstance(i, Mapping) and i.get(key))


def event_row(raw: Mapping[str, Any], site: str, *, local: tzinfo | None = None) -> WbRow:
    title = rendered(raw.get("title")) or "Untitled event"
    start, end = str(raw.get("start_date", "") or ""), str(raw.get("end_date", "") or "")
    all_day = bool(raw.get("all_day"))
    when = spoken_span(start, end, all_day=all_day)
    zone = str(raw.get("timezone", "") or "the site's time zone")
    abbr = str(raw.get("timezone_abbr", "") or "")
    venue = _names(raw.get("venue"), "venue")
    organizers = _names(raw.get("organizer"), "organizer")
    mine = "" if all_day else your_time(str(raw.get("utc_start_date", "") or ""), local=local)
    yours = ""
    if mine and mine != spoken_moment(start):
        yours = f" On your computer's clock it starts {mine}."
    recurring = recurring_words(raw)
    cost = str(raw.get("cost", "") or "")
    status = str(raw.get("status", "") or "")
    return WbRow(
        kind="tribe_event",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"title": title, "when": when, "venue": venue or "no venue", "status": status},
        detail=(
            f"{title}, {when}, {zone}{' (' + abbr + ')' if abbr else ''}."
            f"{yours}{' At ' + venue + '.' if venue else ''}"
            f"{' Cost ' + cost + '.' if cost else ''} {recurring}"
        ).strip(),
        link=str(raw.get("url", "") or ""),
        status=status,
        subkind="recurring" if recurring else "events_calendar",
        raw={
            "title": title,
            "starts": spoken_moment(start, all_day=all_day),
            "ends": spoken_moment(end, all_day=all_day),
            "start_date": start,
            "end_date": end,
            "all_day": "yes" if all_day else "no",
            "time_zone": zone,
            "your_time": mine,
            "venue": venue or "none",
            "venue_id": _first_id(raw.get("venue")),
            "organizers": organizers or "none",
            "cost": cost,
            "website": str(raw.get("website", "") or ""),
            "categories": _names(raw.get("categories"), "name") or "none",
            "featured": "yes" if raw.get("featured") else "no",
            "recurring": recurring or "no",
        },
    )


def _first_id(value: Any) -> int:
    rows = value if isinstance(value, list) else [value]
    for item in rows:
        if isinstance(item, Mapping) and item.get("id"):
            return int(item["id"])
    return 0


def venue_row(raw: Mapping[str, Any], site: str) -> WbRow:
    name = rendered(raw.get("venue")) or "Unnamed venue"
    where = ", ".join(
        str(raw.get(k, "") or "")
        for k in ("address", "city", "stateprovince", "zip", "country")
        if raw.get(k)
    )
    phone = str(raw.get("phone", "") or "")
    return WbRow(
        kind="tribe_venue",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "where": where, "phone": phone},
        detail=f"{name}, a venue{', at ' + where if where else ''}.",
        link=str(raw.get("url", "") or ""),
        status=str(raw.get("status", "") or ""),
        subkind="events_calendar",
        raw={
            "name": name,
            **{k: str(raw.get(k, "") or "") for k in VENUE_FIELDS},
        },
    )


def organizer_row(raw: Mapping[str, Any], site: str) -> WbRow:
    name = rendered(raw.get("organizer")) or "Unnamed organizer"
    phone = str(raw.get("phone", "") or "")
    website = str(raw.get("website", "") or "")
    return WbRow(
        kind="tribe_organizer",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "phone": phone, "website": website},
        detail=f"{name}, an organizer{', ' + phone if phone else ''}.",
        link=str(raw.get("url", "") or ""),
        status=str(raw.get("status", "") or ""),
        subkind="events_calendar",
        raw={"name": name, **{k: str(raw.get(k, "") or "") for k in ORGANIZER_FIELDS}},
    )


# -- New and Edit -----------------------------------------------------------------------


@dataclass(frozen=True)
class EventSpec:
    title: str
    start: str
    end: str
    all_day: bool = False
    timezone: str = ""
    venue_id: int = 0
    organizer_ids: tuple[int, ...] = field(default_factory=tuple)
    cost: str = ""


def event_body(spec: EventSpec, old: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The event in the plugin's names, its dates checked; with *old*, only what changed.

    A new event is a draft. A start after its end is refused here, not by the site.
    """
    if not spec.title.strip():
        raise EventDateError("An event needs a title.")
    start = parse_when(spec.start, label="The start")
    end = parse_when(spec.end, label="The end")
    if end < start:
        raise EventDateError("The event ends before it starts.")
    body: dict[str, Any] = {
        "title": spec.title.strip(),
        "start_date": start,
        "end_date": end,
        "all_day": spec.all_day,
    }
    if spec.timezone.strip():
        body["timezone"] = spec.timezone.strip()
    if spec.venue_id:
        body["venue"] = spec.venue_id
    if spec.organizer_ids:
        body["organizer"] = list(spec.organizer_ids)
    if spec.cost.strip():
        body["cost"] = spec.cost.strip()
    if old is None:
        return {**body, "status": "draft"}
    was = {
        "title": old.get("title"),
        "start_date": old.get("start_date"),
        "end_date": old.get("end_date"),
        "all_day": old.get("all_day") == "yes",
        "timezone": old.get("time_zone"),
        "venue": old.get("venue_id") or None,
        "cost": old.get("cost"),
    }
    return {k: v for k, v in body.items() if k == "organizer" or v != was.get(k)}


def event_preview(
    spec: EventSpec, body: Mapping[str, Any], site: str, *, venue: str = "", new: bool
) -> list[str]:
    when = spoken_span(
        str(body.get("start_date", parse_when(spec.start))),
        str(body.get("end_date", parse_when(spec.end))),
        all_day=spec.all_day,
    )
    zone = spec.timezone.strip() or "the site's own time zone"
    lines = [
        (f"A new event on {site}: " if new else f"{spec.title.strip()} on {site} changes. ")
        + f"{spec.title.strip()}, {when}.",
        f"Times are in {zone}.",
    ]
    if venue:
        lines.append(f"Venue: {venue}.")
    if spec.cost.strip():
        lines.append(f"Cost: {spec.cost.strip()}.")
    if new:
        lines.append("It is made as a draft; Publish or Update makes it public.")
    else:
        changed = ", ".join(k.replace("_", " ") for k in body if k != "organizer") or "nothing"
        lines.append(f"What changes: {changed}. Anyone already told the old time is not told.")
    return lines


VENUE_FIELDS = ("address", "city", "stateprovince", "zip", "country", "phone", "website")
ORGANIZER_FIELDS = ("phone", "website", "email")


@dataclass(frozen=True)
class VenueSpec:
    name: str
    values: Mapping[str, str] = field(default_factory=dict)


OrganizerSpec = VenueSpec


def _place_body(name_key: str, spec: VenueSpec, keys: Sequence[str]) -> dict[str, Any]:
    if not spec.name.strip():
        raise EventDateError(f"A {name_key} needs a name.")
    body: dict[str, Any] = {name_key: spec.name.strip()}
    body.update({k: v.strip() for k, v in spec.values.items() if k in keys and v.strip()})
    return body


def venue_body(spec: VenueSpec) -> dict[str, Any]:
    return _place_body("venue", spec, VENUE_FIELDS)


def organizer_body(spec: OrganizerSpec) -> dict[str, Any]:
    return _place_body("organizer", spec, ORGANIZER_FIELDS)


def place_preview(noun: str, body: Mapping[str, Any], site: str, *, new: bool) -> list[str]:
    name = str(body.get(noun, "") or "")
    parts = [f"{k}: {v}" for k, v in body.items() if k != noun]
    lines = [
        f"{'A new' if new else 'Changes to the'} {noun} on {site}: {name}.",
        *(parts or ["No other details."]),
    ]
    if not new:
        lines.append(f"Events already at this {noun} show the change at once.")
    return lines


def trash_preview(noun: str, name: str, site: str) -> list[str]:
    tail = {
        "event": "It leaves the calendar; restore it from Events > Trash in wp-admin.",
        "venue": "Events at it lose their venue; restore it from Events > Venues > Trash.",
        "organizer": "Events lose this organizer; restore it from Events > Organizers > Trash.",
    }[noun]
    return [f"{name} moves to the Trash on {site}.", tail]


def require_not_recurring(row: WbRow) -> None:
    if row.subkind == "recurring":
        raise WordPressApiError(recurring_words({"recurring": True}))


_EVENT_FILTERS = frozenset({"search", "categories", "tags", "venue", "organizer", "featured"})


def load_events(ctx: Any, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """``upcoming`` or ``past`` events, ``venues`` or ``organizers``, from the plugin's routes."""
    info = getattr(ctx, "info", None)
    if NAMESPACE not in tuple(getattr(info, "namespaces", ()) or ()):
        raise WordPressApiError(
            f"{ctx.name} does not list The Events Calendar's {NAMESPACE} routes in its REST "
            "index, so it has no events QUILL can read."
        )
    if what in ("categories", "tags"):
        from quill.core.wordpress.workbench_event_terms import load_event_terms

        return load_event_terms(ctx, what, query)
    if what in ("venues", "organizers"):
        params = {"search": query["search"]} if query.get("search") else {}
        found = collect(ctx.api, what, params)
        make = venue_row if what == "venues" else organizer_row
        return [make(raw, ctx.name) for raw in found]
    params = {k: v for k, v in query.items() if k in _EVENT_FILTERS and str(v).strip()}
    if query.get("start_date") or query.get("end_date"):  # Events Between Dates
        params.update({k: query[k] for k in ("start_date", "end_date") if query.get(k)})
    elif what == "past":
        params["ends_before"] = "now"
    else:
        params["start_date"] = "now"
    rows = [event_row(raw, ctx.name) for raw in collect(ctx.api, "events", params)]
    return list(reversed(rows)) if what == "past" else rows


def between_params(first: str, last: str) -> dict[str, str]:
    """Events Between Dates: two dates (time optional) as the plugin's start and end filters."""
    start = parse_when(first, label="The first date")
    end = parse_when(
        last if " " in last.strip() else f"{last.strip()} 23:59:59", label="The last date"
    )
    if end < start:
        raise EventDateError("The last date is before the first.")
    return {"start_date": start, "end_date": end}
