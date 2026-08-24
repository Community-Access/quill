"""The ACB Media schedule: a week of programmes, and what you can do to one.

ACB publishes its schedule through WordPress's My Calendar plugin. Its REST API
is switched off, so the **ICS feed is the data path** -- read by
:mod:`quill.core.radio.ics`, which is a parser and not a dependency.

Everything here is pure except one fetch, and the fetch goes through
``directory_cache.resolve``, which already does the three things this feature
needs and would otherwise have grown its own worse versions of:

* **fresh cache, then network, then stale cache** -- so a week opens instantly
  on a second visit and still opens on a train with no signal;
* **a failure is recorded rather than raised** -- a schedule that will not load
  must not take the window with it, and the reason lands in Recent Problems,
  which is where somebody looks when the week comes back empty;
* **the age comes back with the payload**, so the window can say "as of
  yesterday" instead of implying it is current.

**No background timer.** The schedule refreshes when the window opens if the
cache has aged out, and whenever Refresh is pressed. That is the same rule the
subscribed-feed check follows and for the same reason: an app that reaches the
network on a schedule nobody chose is spending somebody else's data allowance.

**A category is a stream.** My Calendar's categories are the ACB Media channel
names ("ACB Media 1"..."ACB Media 10"), which is what lets an event know what
to play -- the whole of 6.5. An event with no recognised category is still a
real event; it simply has no Play verb, and says so rather than offering one
that would guess.

wx-free, strict-typed. The querying is pure; the caller supplies *now*.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.radio.ics import CalendarEvent, parse_calendar

#: ACB's My Calendar ICS export (confirmed against acbmedia.org, 2026-08-24).
#:
#: **The month is part of the address**, which is the whole reason this is a
#: template rather than a constant: My Calendar serves a *window*, not the
#: whole calendar, and ``month``/``yr`` say which. A hardcoded month would work
#: perfectly until the first of September and then return last month's
#: listings for ever -- the kind of failure that looks like a quiet schedule
#: rather than a bug.
#:
#: ``nmonth``/``nyr`` name the following month, so each fetch covers two: a
#: week that straddles the 31st is one request, not two.
#:
#: ``mcat`` is My Calendar's category filter, and the list is ACB's own
#: published set. Passing every id rather than omitting the parameter is
#: deliberate -- omitting it returns the site's *default* categories, which is
#: a subset somebody chose in WordPress and could change without warning.
ICS_URL_TEMPLATE = (
    "https://www.acbmedia.org/feed/my-calendar-ics/"
    "?dy=1&format=list&mcat={categories}"
    "&month={month}&nmonth={next_month}&nyr={next_year}&time=month&yr={year}"
)

#: ACB's category ids, as published on their own schedule page. Numbers rather
#: than names because that is what the feed takes; the *names* come back in
#: each event's CATEGORIES, which is what maps a programme to a channel.
_CATEGORY_IDS = (
    "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,28,29,32,34,36,38,40,56,57,58"
)

#: How long a cached schedule stays fresh. An hour: programme listings change
#: on the order of days, and a week somebody opens twice in a morning should
#: not cost two fetches.
MAX_AGE_SECONDS = 3600.0

#: One cache entry per month, for the same reason the URL carries one: a
#: single key would serve August's listings for October, from disk, silently.
CACHE_KEY_PREFIX = "acb-media-calendar"


def ics_url(moment: datetime) -> str:
    """The feed address for the month containing *moment*, plus the next one."""
    year, month = moment.year, moment.month
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)
    return ICS_URL_TEMPLATE.format(
        categories=_CATEGORY_IDS,
        month=month,
        year=year,
        next_month=next_month,
        next_year=next_year,
    )


def cache_key(moment: datetime) -> str:
    """The cache entry for that month."""
    return f"{CACHE_KEY_PREFIX}-{moment.year:04d}-{moment.month:02d}"


#: Named, because a server that logs its callers should be able to tell who
#: this is -- and because an unattributed reader is the kind a site blocks.
_USER_AGENT = "QuillRadio/3.0 (+https://github.com/Community-Access/quill)"

#: Twenty seconds. A calendar is not urgent, but a window waiting on one is.
_TIMEOUT_SECONDS = 20.0

#: Matches "ACB Media 4" however the feed spaces or cases it.
_STREAM_RE = re.compile(r"acb\s*media\s*(\d{1,2})", re.IGNORECASE)


def fetch_schedule(
    *, when: datetime | None = None, refresh: bool = False, safe_mode: bool = False
) -> tuple[list[Any], Any]:
    """The schedule around *when*, and how old it is. Never raises.

    Returns ``(events, age_seconds_or_None)`` -- ``None`` means it came off the
    network just now. Safe Mode answers with the cache alone and no fetch,
    because Safe Mode's promise is that nothing reaches out.

    *when* decides which month is asked for and which cache entry answers, so
    stepping forward a week near the end of a month fetches the next month
    rather than re-reading a cached one that cannot contain it.

    Runs on a worker thread. Nothing here touches wx.
    """
    from quill.core.radio import directory_cache

    moment = when or datetime.now(UTC)
    key = cache_key(moment)

    if safe_mode:
        entry = directory_cache.load(key)
        return (_events_from(entry.payload) if entry is not None else [], _age(entry))

    payload, age = directory_cache.resolve(
        key,
        lambda: _fetch_ics(moment),
        max_age_seconds=MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    return (_events_from(payload), age)


def _fetch_ics(moment: datetime) -> list[dict[str, Any]]:
    """Read the feed and return events as JSON-safe rows.

    Rows rather than dataclasses because the cache is a JSON file: a
    ``CalendarEvent`` stored whole comes back a dict anyway, and pretending
    otherwise is how a cache round trip quietly changes a type.
    """
    import ssl
    import urllib.request

    request = urllib.request.Request(
        ics_url(moment),
        headers={"User-Agent": _USER_AGENT, "Accept": "text/calendar, text/plain"},
    )
    with urllib.request.urlopen(  # noqa: S310 - literal HTTPS constant, no user input
        request, timeout=_TIMEOUT_SECONDS, context=ssl.create_default_context()
    ) as response:
        raw = response.read()
    # errors="replace" rather than strict: a schedule with one bad byte in a
    # programme title should lose that character, not the week.
    text = raw.decode("utf-8", errors="replace")
    return [_to_row(event) for event in parse_calendar(text)]


# -- the querying (pure) ----------------------------------------------------------


def week_start(day: datetime) -> datetime:
    """The Sunday at or before *day*, at midnight.

    Sunday because that is how ACB publishes its week and how North American
    radio schedules read; a listener comparing the window to the website should
    not have to translate.
    """
    midnight = day.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monday is 0 in Python; Sunday is 6. (weekday() + 1) % 7 is days since
    # Sunday, which is the number to step back.
    return midnight - timedelta(days=(midnight.weekday() + 1) % 7)


def week_of(events: list[CalendarEvent], day: datetime) -> list[CalendarEvent]:
    """Every programme in the Sunday-to-Saturday week containing *day*."""
    start = week_start(day)
    finish = start + timedelta(days=7)
    return [event for event in events if start <= event.start < finish]


def days_of(events: list[CalendarEvent], day: datetime) -> list[tuple[datetime, list[Any]]]:
    """The week as seven ``(midnight, programmes)`` pairs, Sunday first.

    Seven pairs always, including the empty ones: a week view that silently
    omitted Wednesday would read as a week with no Wednesday, and "nothing on"
    is information a listener wants rather than a row to hide.
    """
    start = week_start(day)
    out: list[tuple[datetime, list[Any]]] = []
    for offset in range(7):
        midnight = start + timedelta(days=offset)
        nightfall = midnight + timedelta(days=1)
        out.append((
            midnight,
            [event for event in events if midnight <= event.start < nightfall],
        ))
    return out


def search(events: list[CalendarEvent], query: str) -> list[CalendarEvent]:
    """Programmes whose title, description or stream matches *query*.

    Every word has to appear somewhere, in any order and any field: "blues
    tuesday" finds the Tuesday blues show without anybody having to know which
    field holds which word.
    """
    words = [word for word in str(query or "").lower().split() if word]
    if not words:
        return list(events)
    found = []
    for event in events:
        haystack = " ".join((
            event.summary,
            event.description,
            event.location,
            " ".join(event.categories),
        )).lower()
        if all(word in haystack for word in words):
            found.append(event)
    return found


def on_now(events: list[CalendarEvent], now: datetime) -> list[CalendarEvent]:
    """Everything on the air at *now*, across every stream."""
    return [event for event in events if event.overlaps(now)]


def upcoming(events: list[CalendarEvent], now: datetime, *, limit: int = 20) -> list[CalendarEvent]:
    """The next *limit* programmes that have not started yet, soonest first."""
    ahead = [event for event in events if event.start > now]
    return sorted(ahead, key=lambda event: event.start)[: max(0, limit)]


def stream_names(events: list[CalendarEvent]) -> list[str]:
    """Every stream the schedule mentions, in ACB's numeric order.

    Numeric rather than alphabetical, because "ACB Media 10" sorts between 1
    and 2 as text and a listener reading a filter list should not have to
    think about that.
    """
    names = {name for event in events for name in event.categories if _stream_number(name)}
    return sorted(names, key=lambda name: _stream_number(name) or 0)


def stream_for(event: CalendarEvent) -> str:
    """Which ACB Media stream this programme is on, or ``""``.

    Empty for an event whose categories name no stream. That event is still
    real and still listed; what it does not get is a Play verb, because
    guessing which of ten streams it meant would be worse than saying so.
    """
    for name in event.categories:
        if _stream_number(name):
            return name
    return ""


def by_stream(events: list[CalendarEvent], name: str) -> list[CalendarEvent]:
    """Only this stream's programmes; every one when *name* is empty."""
    wanted = str(name or "").strip().lower()
    if not wanted:
        return list(events)
    return [event for event in events if stream_for(event).lower() == wanted]


def station_for(event: CalendarEvent) -> Any:
    """The playable station this programme is on, or ``None`` (6.5).

    Resolved through :mod:`quill.core.radio.acb_media`, which already holds the
    ten streams and their addresses -- so the calendar never learns a URL and
    the two can never disagree about what "ACB Media 4" is.
    """
    name = stream_for(event)
    if not name:
        return None
    from quill.core.radio.acb_media import acb_media_stations

    number = _stream_number(name)
    for station in acb_media_stations():
        if _stream_number(station.name) == number:
            return station
    return None


def _stream_number(name: object) -> int | None:
    match = _STREAM_RE.search(str(name or ""))
    return int(match.group(1)) if match else None


# -- the cache round trip ---------------------------------------------------------


def _to_row(event: CalendarEvent) -> dict[str, Any]:
    return {
        "uid": event.uid,
        "summary": event.summary,
        "start": event.start.isoformat(),
        "end": event.end.isoformat() if event.end is not None else "",
        "description": event.description,
        "location": event.location,
        "categories": list(event.categories),
        "url": event.url,
    }


def _events_from(payload: object) -> list[CalendarEvent]:
    """Rows back into events, skipping anything unreadable.

    A cache written by an older build, or half-written by a crash, must read as
    fewer events rather than as an exception on the way into a window.
    """
    if not isinstance(payload, list):
        return []
    events: list[CalendarEvent] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        start = _moment(row.get("start"))
        if start is None:
            continue
        events.append(
            CalendarEvent(
                uid=str(row.get("uid", "") or ""),
                summary=str(row.get("summary", "") or "Untitled programme"),
                start=start,
                end=_moment(row.get("end")),
                description=str(row.get("description", "") or ""),
                location=str(row.get("location", "") or ""),
                categories=tuple(
                    str(name) for name in row.get("categories", []) if isinstance(name, str)
                ),
                url=str(row.get("url", "") or ""),
            )
        )
    return deduplicate(sorted(events, key=lambda event: event.start))


def deduplicate(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Drop programmes the feed published twice (pure).

    **ACB's feed really does this.** Confirmed against the live August 2026
    export: 20 of 69 events were exact repeats -- same title, same start, same
    end, same channel -- carrying *different* uids (``105795-4440`` and
    ``105842-4487`` for the same Daily Schedule). So the uid cannot be the
    identity, and a week view that trusted it showed every affected programme
    twice.

    Identity is what a listener would call the same programme: when it starts,
    when it ends, what it is called, and which channel it is on. The first one
    in file order wins, and the sort above is stable, so the surviving uid is
    the same on every load -- which matters because a reminder targets a uid
    and would otherwise attach itself to a row that vanished next week.
    """
    seen: set[tuple[str, str, str, tuple[str, ...]]] = set()
    kept: list[CalendarEvent] = []
    for event in events:
        key = (
            event.start.isoformat(),
            event.end.isoformat() if event.end is not None else "",
            event.summary.strip().casefold(),
            tuple(sorted(name.strip().casefold() for name in event.categories)),
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(event)
    return kept


def _moment(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _age(entry: Any) -> float | None:
    return entry.age_seconds() if entry is not None else None


__all__ = [
    "CACHE_KEY_PREFIX",
    "ICS_URL_TEMPLATE",
    "MAX_AGE_SECONDS",
    "cache_key",
    "ics_url",
    "by_stream",
    "days_of",
    "deduplicate",
    "fetch_schedule",
    "on_now",
    "search",
    "station_for",
    "stream_for",
    "stream_names",
    "upcoming",
    "week_of",
    "week_start",
]
