"""Reading an iCalendar feed, by hand, because the alternative is worse.

ACB Media publishes its schedule as ICS (the WordPress My Calendar plugin; its
REST API is switched off, so the ICS feed is the data path). Parsing it needs
about two hundred lines and no dependency at all, and that is the trade this
module takes:

* **Recurrence is carried, not resolved.** A ``VEVENT`` with an ``RRULE`` means
  many programmes, but expanding it needs a window to be bounded by and only
  the caller knows which one. The rule rides on the event;
  :mod:`quill.core.radio.ics_recurrence` does the expanding.
* **No new dependency.** ``icalendar`` would be a wheel in every installer, a
  line in the egress-free dependency audit, and a thing to update, in exchange
  for RFC 5545 coverage this feed does not use -- no alarms, no journals, no
  timezone *definitions* beyond a name, and only the handful of recurrence
  parts a programme listing actually writes.
* **What is actually in the feed is narrow.** ``VEVENT`` records with a
  summary, a start, an end, a category, sometimes a description, and sometimes
  a repeat rule. The rest of RFC 5545 is not there to be got wrong.
* **A feed that breaks must not break the week.** Every field is optional, an
  event that cannot be read is skipped rather than fatal, and a file that is
  not ICS at all reads as no events -- which the caller reports as "the
  schedule could not be read", never as an empty Tuesday.

Two details that are easy to get wrong and cost the whole feature when you do:

**Line folding.** RFC 5545 wraps long lines at 75 octets and continues them
with a leading space or tab. Unfolded naively, a show called "The Sunday Night
Blues Hour with..." becomes two properties, one of which is nonsense. Folding
is undone before anything else looks at a line.

**Escapes.** ``\\,`` ``\\;`` ``\\n`` and ``\\\\`` are escaped inside text
values. A description with a comma in it, read raw, truncates at the comma --
and descriptions are where a programme's actual content lives.

wx-free, strict-typed, pure. No network: the caller fetches, this reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, tzinfo

#: Properties whose value is text and therefore carries escapes.
_TEXT_PROPERTIES = frozenset({"SUMMARY", "DESCRIPTION", "LOCATION", "CATEGORIES", "COMMENT"})


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """One programme in the schedule.

    Times are stored as timezone-aware UTC. A feed that gives a floating local
    time (no ``Z``, no ``TZID``) is read as UTC rather than as the reader's
    local time: guessing wrong by five hours is worse than being consistently
    wrong by an amount the caller can see and correct, and ACB's feed is
    stamped.
    """

    uid: str
    summary: str
    start: datetime
    end: datetime | None = None
    description: str = ""
    location: str = ""
    categories: tuple[str, ...] = field(default_factory=tuple)
    url: str = ""
    #: The raw ``RRULE`` and ``EXDATE``, carried rather than acted on here:
    #: expanding a series needs a *window* to be bounded by, and only the
    #: caller knows which fortnight it is about to show. See
    #: :mod:`quill.core.radio.ics_recurrence`. Empty for the ordinary case,
    #: which is what ACB's own export writes today.
    rrule: str = ""
    exdates: str = ""

    @property
    def duration(self) -> timedelta | None:
        return (self.end - self.start) if self.end is not None else None

    def overlaps(self, moment: datetime) -> bool:
        """Whether this programme is on at *moment*.

        An event with no end is treated as on for an hour: the alternative --
        never, or forever -- is wrong in a way somebody notices, and an hour
        is what an unstated programme slot almost always is.
        """
        finish = self.end or (self.start + timedelta(hours=1))
        return self.start <= moment < finish


def parse_calendar(text: str) -> list[CalendarEvent]:
    """Every readable ``VEVENT`` in *text*, earliest first.

    An unreadable event is skipped, never fatal: a schedule that will not show
    Tuesday because Thursday is malformed is worse than one missing Thursday.
    """
    events: list[CalendarEvent] = []
    current: dict[str, str] | None = None
    for line in _unfolded(text):
        upper = line.upper()
        if upper.startswith("BEGIN:VEVENT"):
            current = {}
            continue
        if upper.startswith("END:VEVENT"):
            if current is not None:
                event = _event_from(current)
                if event is not None:
                    events.append(event)
            current = None
            continue
        if current is None:
            continue
        name, value = _split_property(line)
        if not name:
            continue
        # Keep the zone a start or end was written in. Every event in ACB's
        # feed carries TZID=America/Chicago, and reading those as UTC put the
        # whole schedule five hours early for anybody whose clock is not UTC
        # (found 2026-08-24 against the live feed).
        if name in ("DTSTART", "DTEND"):
            zone = _tzid_of(line)
            if zone:
                current[f"{name}#TZID"] = zone
        if name == "EXDATE" and current.get("EXDATE"):
            # A cancelled week is one EXDATE line; three cancelled weeks are
            # three, and keeping only the last would quietly restore two of
            # them. Joined, because that is how the value already reads when a
            # feed puts them on one line.
            current["EXDATE"] = f"{current['EXDATE']},{value}"
        else:
            current[name] = value
    return sorted(events, key=lambda event: event.start)


def _unfolded(text: str) -> list[str]:
    """Undo RFC 5545 line folding.

    A continuation line starts with a space or a tab and belongs to the line
    before it. Missing this turns one long programme title into two properties,
    the second of which is not a property at all.
    """
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return [line for line in lines if line.strip()]


def _split_property(line: str) -> tuple[str, str]:
    """``NAME;PARAM=X:value`` -> ``("NAME", "value")``, parameters dropped.

    ``TZID`` is the exception and is kept, by the caller, under a name of its
    own -- see :func:`_tzid_of`. It is the one parameter whose absence changes
    what the value *means*.

    The colon that ends the name is the first one *outside* a quoted
    parameter: ``DTSTART;TZID="America/New_York":2026...`` has two, and taking
    the first would leave the timezone glued to the front of the value.
    """
    in_quotes = False
    for index, character in enumerate(line):
        if character == '"':
            in_quotes = not in_quotes
        elif character == ":" and not in_quotes:
            head, value = line[:index], line[index + 1 :]
            name = head.split(";", 1)[0].strip().upper()
            return (name, _unescape(value) if name in _TEXT_PROPERTIES else value.strip())
    return ("", "")


def _unescape(value: str) -> str:
    r"""Undo RFC 5545 text escaping (``\,`` ``\;`` ``\n`` ``\\``).

    Read raw, a description containing a comma truncates at it -- and the
    description is where a programme's actual content lives.
    """
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            nxt = value[index + 1]
            out.append({"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}.get(nxt, nxt))
            index += 2
            continue
        out.append(char)
        index += 1
    return _decode_entities("".join(out).strip())


def _decode_entities(value: str) -> str:
    """Turn HTML entities in a calendar's text back into characters.

    ACB's feed is generated from WordPress post content, and it arrives
    **double-encoded**: a curly apostrophe reaches us as ``&amp;#8217;``, which
    a screen reader reads out as "ampersand hash eight two one seven
    semicolon" in the middle of a programme title. One pass gives ``&#8217;``,
    which is no better; two give the apostrophe.

    Bounded at three passes and stopped as soon as it settles, because
    unescaping until nothing changes is how a title that legitimately contains
    ``&amp;amp;`` gets eaten -- and because an unbounded loop on hostile input
    is not something a calendar needs to own.
    """
    if "&" not in value:
        return value
    import html

    text = value
    for _pass in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    return text


def _tzid_of(line: str) -> str:
    """The ``TZID`` parameter on a property line, or "".

    Quoted or bare -- ``TZID="America/New_York"`` and ``TZID=America/Chicago``
    are both legal and ACB writes the second.
    """
    head = line.split(":", 1)[0]
    for parameter in head.split(";")[1:]:
        name, _, value = parameter.partition("=")
        if name.strip().upper() == "TZID":
            return value.strip().strip('"')
    return ""


def _zone(tzid: str) -> tzinfo | None:
    """*tzid* as a real timezone, or ``None`` when this machine has no such zone.

    ``None`` rather than an exception: a feed naming a zone the tz database
    does not carry should cost the *offset*, which the caller can see and
    correct, never the programme.
    """
    if not tzid:
        return None
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:  # pragma: no cover - zoneinfo is stdlib on 3.9+
        return None
    try:
        return ZoneInfo(tzid)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def parse_timestamp(value: str, *, tzid: str = "") -> datetime | None:
    """An ICS date-time as aware UTC, or None when it cannot be read.

    Handles ``20260824T193000Z``, ``20260824T193000`` (floating) and
    ``20260824`` (a whole day, read as its midnight). Anything else is None,
    which the caller turns into a skipped event rather than a crash.

    *tzid* is the property's ``TZID`` parameter, and it is the difference
    between a right answer and a wrong one. **Every** event in ACB's feed is
    written ``DTSTART;TZID=America/Chicago:...``; reading those as UTC and
    then rendering them in the reader's own zone (which ``calendar_actions``
    does) put the entire schedule five hours early. A genuinely floating time
    -- no ``Z``, no ``TZID`` -- is still read as UTC, because guessing the
    reader's zone would be wrong by a different amount on every machine.
    """
    text = str(value or "").strip()
    if not text:
        return None
    trailing_z = text.endswith(("Z", "z"))
    body = text[:-1] if trailing_z else text
    zone = None if trailing_z else _zone(tzid)
    for pattern in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            moment = datetime.strptime(body, pattern)
        except ValueError:
            continue
        if zone is not None:
            return moment.replace(tzinfo=zone).astimezone(UTC)
        return moment.replace(tzinfo=UTC)
    try:
        moment = datetime.fromisoformat(body)
    except ValueError:
        return None
    if moment.tzinfo is not None:
        return moment.astimezone(UTC)
    if zone is not None:
        return moment.replace(tzinfo=zone).astimezone(UTC)
    return moment.replace(tzinfo=UTC)


def _event_from(fields: dict[str, str]) -> CalendarEvent | None:
    """One ``VEVENT``'s fields as an event, or None when it has no start.

    A start is the only genuinely required part: an event with no beginning
    cannot be placed in a week, and putting it somewhere anyway would be
    inventing a time somebody might act on.
    """
    start = parse_timestamp(fields.get("DTSTART", ""), tzid=fields.get("DTSTART#TZID", ""))
    if start is None:
        return None
    summary = fields.get("SUMMARY", "").strip()
    categories = tuple(
        part.strip() for part in fields.get("CATEGORIES", "").split(",") if part.strip()
    )
    return CalendarEvent(
        uid=fields.get("UID", "").strip() or f"{start.isoformat()}|{summary}",
        summary=summary or "Untitled programme",
        start=start,
        end=parse_timestamp(fields.get("DTEND", ""), tzid=fields.get("DTEND#TZID", "")),
        description=fields.get("DESCRIPTION", "").strip(),
        location=fields.get("LOCATION", "").strip(),
        categories=categories,
        url=fields.get("URL", "").strip(),
        rrule=fields.get("RRULE", "").strip(),
        exdates=fields.get("EXDATE", "").strip(),
    )


__all__ = ["CalendarEvent", "parse_calendar", "parse_timestamp"]
