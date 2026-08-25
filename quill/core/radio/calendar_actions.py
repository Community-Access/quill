"""What you can do to a programme in the schedule, and what to say about it.

The verbs on a calendar row (list.md 6.4, 6.6) and everything they need to be
*read out* -- which is where a calendar for a screen-reader user is won or lost.
A week view is a lot of rows; each one has to say what it is in one line, and
each one has to offer the same verbs whether it was reached by mouse, by the
Applications key, or by tabbing to the buttons beside the list.

The verbs, and why each is dimmed rather than absent when it cannot run:

* **Play now** -- needs a stream. An event whose categories name no ACB channel
  has nothing to play, and says so; guessing which of ten channels it meant
  would be worse.
* **Schedule a recording** -- needs a stream *and* a future end. Recording a
  programme that finished on Tuesday is a recording of silence.
* **Set a reminder** -- needs a future start, and turns into *Remove reminder*
  once there is one, because a menu that cannot tell you what you already did
  is a menu you have to remember for.
* **Add to Play Queue** -- needs a stream. Queues the channel, not the
  programme: a live stream is not an episode, and pretending otherwise would
  put a thing in the queue that plays whatever happens to be on when it
  arrives. The label says "channel" for exactly that reason.
* **Copy details** -- always available. There is nothing to be wrong about.

A dimmed verb carries its reason (:mod:`quill.core.dimmed_reason`'s rule, 11.2),
because a dimmed item teaches a state only if it *says* the state.

wx-free, strict-typed, pure. The caller supplies *now*.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Any

from quill.core.radio import acb_calendar
from quill.core.radio.ics import CalendarEvent

PLAY = "calendar.play"
RECORD = "calendar.record"
REMIND = "calendar.remind"
UNREMIND = "calendar.unremind"
QUEUE = "calendar.queue"
COPY = "calendar.copy"
DETAILS = "calendar.details"


@dataclass(frozen=True, slots=True)
class EventAction:
    """One menu item: what it is, what it reads as, and why it is off."""

    action_id: str
    label: str
    enabled: bool = True
    reason: str = ""


def actions_for(
    event: CalendarEvent,
    now: datetime,
    *,
    has_reminder: bool = False,
    playing_stream: str = "",
) -> list[EventAction]:
    """Every verb for one programme, in the order a listener meets them.

    *playing_stream* is the channel the player is on right now, if any. It
    turns Play into **Stop**, which is the whole of 6.5's toggle: pressing Play
    on the channel you are already listening to used to tear the stream down
    and rebuild it -- several seconds of silence, then the same audio, and no
    way to stop from this window at all (reported 2026-08-24). A verb that
    cannot tell it already did its job is a verb that does the wrong one.
    """
    stream = acb_calendar.stream_for(event)
    started = event.start <= now
    finished = (event.end or event.start) <= now
    no_stream = "this programme does not say which channel it is on"
    on_this_channel = acb_calendar.same_stream(stream, playing_stream)

    if on_this_channel:
        play_label = "&Stop"
    elif started:
        play_label = "&Play Now"
    else:
        play_label = "&Play This Channel Now"

    actions = [
        EventAction(
            PLAY,
            play_label,
            enabled=bool(stream),
            reason=no_stream,
        ),
        EventAction(
            RECORD,
            "Schedule a &Recording...",
            enabled=bool(stream) and not finished,
            reason=(no_stream if not stream else "this programme has already finished"),
        ),
    ]
    if has_reminder:
        actions.append(EventAction(UNREMIND, "Remove Re&minder"))
    else:
        actions.append(
            EventAction(
                REMIND,
                "Set a Re&minder...",
                enabled=not started,
                reason="this programme has already started",
            )
        )
    actions += [
        EventAction(
            QUEUE,
            "Add This Channel to the Play &Queue",
            enabled=bool(stream),
            reason=no_stream,
        ),
        EventAction(COPY, "&Copy Details"),
        EventAction(DETAILS, "&Show Notes..."),
    ]
    return actions


# -- what a row says --------------------------------------------------------------


def row_label(event: CalendarEvent, now: datetime) -> str:
    """One line, in the order somebody listening scans for it.

    Time first, because a day's rows are read in time order and the time is
    what places them; then the programme; then the channel, which is what
    decides whether it can be played at all. "On now" comes last and only when
    it is true -- a suffix nobody has to wait through on the other rows.
    """
    parts = [clock(event.start), event.summary]
    stream = acb_calendar.stream_for(event)
    if stream:
        parts.append(stream)
    if event.overlaps(now):
        parts.append("on now")
    return ", ".join(parts)


def clock(moment: datetime) -> str:
    """``7:00 PM`` in the reader's own timezone, unpadded.

    Unpadded because "07:00" reads as "oh seven hundred" to some screen
    readers; built by hand because ``%-I`` is a glibc extension that raises on
    Windows.
    """
    local = moment.astimezone()
    hour = local.hour % 12 or 12
    return f"{hour}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"


def day_label(midnight: datetime, count: int) -> str:
    """A day heading that carries its own count.

    The count is on the heading rather than left for the rows to imply,
    because "Wednesday, nothing scheduled" is an answer and an empty heading
    is a question.
    """
    local = midnight.astimezone()
    name = f"{local.strftime('%A')} {local.day} {local.strftime('%B')}"
    if not count:
        return f"{name}, nothing scheduled"
    return f"{name}, {count} programme{'' if count == 1 else 's'}"


def details_text(event: CalendarEvent) -> str:
    """Copy Details -- everything about one programme, as pasteable text.

    Enough that somebody pasting it into a message has given the whole thing:
    what, when, on which channel, and the description. A title alone is a
    fragment; a title and a time without a channel is a fragment somebody has
    to come back and ask about.
    """
    lines = [event.summary, f"{day_label(event.start, 1).split(',')[0]}, {clock(event.start)}"]
    if event.end is not None:
        lines[-1] += f" to {clock(event.end)}"
    stream = acb_calendar.stream_for(event)
    if stream:
        lines.append(stream)
    if event.description.strip():
        lines += ["", event.description.strip()]
    if event.url.strip():
        lines.append(event.url.strip())
    return "\n".join(lines)


def week_markdown(days: list[tuple[datetime, list[Any]]], *, heading: str = "") -> str:
    """A week as Markdown, for somebody keeping or sharing a listening plan.

    Every day appears, including the empty ones, for the same reason the window
    shows them: a plan with no Wednesday reads as a week with no Wednesday.
    """
    lines = [f"# {heading}" if heading else "# ACB Media schedule", ""]
    for midnight, events in days:
        lines.append(f"## {day_label(midnight, len(events))}")
        lines.append("")
        for event in sorted(events, key=lambda e: e.start):
            stream = acb_calendar.stream_for(event)
            tail = f" -- {stream}" if stream else ""
            lines.append(f"- **{clock(event.start)}** {event.summary}{tail}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def summarise_week(days: list[tuple[datetime, list[Any]]], age_seconds: float | None) -> str:
    """What the window says when a week loads.

    The age is said when there is one, because a schedule read from the cache
    on a train is still useful and a schedule *presented as current* when it is
    three days old is not.
    """
    total = sum(len(events) for _midnight, events in days)
    if not total:
        body = "Nothing is scheduled this week."
    else:
        body = f"{total} programme{'' if total == 1 else 's'} this week."
    from quill.core.radio.directory_cache import spoken_age

    aged = spoken_age(age_seconds)
    return f"{body} {aged}".strip() if aged else body


def nothing_on_now() -> str:
    """Said by the what-is-on-now key when the answer is nothing.

    A key that answers with silence is a key somebody presses twice.
    """
    return "Nothing in the schedule is on right now."


def on_now_sentence(events: list[CalendarEvent]) -> str:
    """What is on across every channel, in one sentence."""
    if not events:
        return nothing_on_now()
    parts = []
    for event in events:
        stream = acb_calendar.stream_for(event)
        parts.append(f"{event.summary} on {stream}" if stream else event.summary)
    return "On now: " + "; ".join(parts) + "."


# -- the flat list (2026-08-24) ---------------------------------------------------
#
# The window used to be a week: seven day headings, Sunday to Saturday, paged
# with Previous/Next. It read as a calendar, and a calendar is the one shape
# this data cannot fill -- ACB publishes a fortnight at a time and then stops,
# so the week containing today is routinely *empty*, and an empty week with a
# heading for each day is indistinguishable from a broken feed. (Confirmed
# twice: on 2026-08-23 and again on 2026-08-24 the published schedule ran out
# at 15 August.) A flat list of everything that *is* published, newest facts
# first in the summary line, cannot lie that way: it either has rows or it says
# in a sentence why it has none.


def full_row_label(event: CalendarEvent, now: datetime) -> str:
    """One programme, with its date, for a list that has no day headings.

    Date first, then time, because the list is sorted that way and a listener
    arrowing through it is tracking where they are in the run of days. "on now"
    and "finished" come last: a suffix nobody has to wait through to hear what
    the programme is.
    """
    local = event.start.astimezone()
    when = f"{local.strftime('%A')} {local.day} {local.strftime('%B')}"
    # Both ends, when the listing gives both. A start time alone answers "when
    # do I tune in" and leaves "how long is this" to be found by opening the
    # row -- and for a schedule you are planning an evening around, the length
    # is half of what you came for. ACB's listings carry DTEND on nearly
    # everything; where they do not, the row says one time rather than
    # inventing a second.
    span = clock(event.start)
    if event.end is not None and event.end > event.start:
        span = f"{span} to {clock(event.end)}"
    parts = [when, span, event.summary]
    stream = acb_calendar.stream_for(event)
    if stream:
        parts.append(stream)
    if event.overlaps(now):
        parts.append("on now")
    # No "finished" marker. It was on every past row, and because ACB publishes
    # a fortnight and stops, that is routinely *every row in the window* -- a
    # word repeated on all forty-nine rows that distinguishes none of them from
    # each other. The date on the front of the row already says it, and "on
    # now" still earns its place because it says something only one row can.
    return ", ".join(parts)


def date_key(moment: datetime) -> str:
    """``2026-08-02`` in the reader's own timezone."""
    return moment.astimezone().strftime("%Y-%m-%d")


def date_choices(events: list[CalendarEvent]) -> list[tuple[str, str]]:
    """``(key, label)`` for every date that actually has a programme.

    Only dates with something on them: a date picker offering 31 days when 14
    of them exist is a picker that mostly answers "nothing", which is the
    failure the week view had.
    """
    counts: dict[str, int] = {}
    first: dict[str, datetime] = {}
    for event in sorted(events, key=lambda e: e.start):
        key = date_key(event.start)
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, event.start)
    out: list[tuple[str, str]] = []
    for key in sorted(counts):
        out.append((key, day_label(first[key], counts[key])))
    return out


def on_date(events: list[CalendarEvent], key: str) -> list[CalendarEvent]:
    """Only this date's programmes; every one when *key* is empty."""
    wanted = str(key or "").strip()
    if not wanted:
        return list(events)
    return [event for event in events if date_key(event.start) == wanted]


def first_upcoming_index(events: list[CalendarEvent], now: datetime) -> int:
    """Where to put the cursor: the next programme, or the last row.

    Opening on row zero puts a listener at the start of a fortnight that may
    have finished a week ago. Opening on the *next* thing is the answer to the
    question they came with.
    """
    for index, event in enumerate(events):
        if (event.end or event.start) > now:
            return index
    return max(0, len(events) - 1)


def published_range(events: list[CalendarEvent]) -> str:
    """``1 August to 16 August``, or empty when nothing is published."""
    if not events:
        return ""
    starts = sorted(event.start for event in events)
    first, last = starts[0].astimezone(), starts[-1].astimezone()
    return f"{first.day} {first.strftime('%B')} to {last.day} {last.strftime('%B')}"


def zone_note(now: datetime, local: tzinfo | None = None) -> str:
    """The "times are shown in..." line, for a reader not on ACB's clock.

    Every time in this window has already been converted to the reader's own
    zone -- ``astimezone()`` on a feed that carries ``TZID=America/Chicago`` --
    and the window never said so, which leaves a listener no way to tell a
    correct conversion from a missing one. Reported from Phoenix on 2026-08-25:
    a 9 am Central programme showing as 7 am read as an hour wrong, and it was
    not (Arizona keeps MST all year, so it is two hours behind Central in
    summer and one in winter -- the gap moves, which is exactly why nobody
    should have to do this arithmetic to trust the window).

    Silent for a reader whose clock already matches Central: a sentence that
    says "these times are in your time" to somebody in Chicago is a sentence
    read out on every reload for nothing. The test is the actual offset at
    *now*, not the zone name, because that is the thing that would make the
    numbers differ.
    """
    try:
        from zoneinfo import ZoneInfo

        central = now.astimezone(ZoneInfo("America/Chicago"))
    except Exception:  # noqa: BLE001 - no tz database is not worth a broken summary
        return ""
    # *local* is the reader's zone; the default is whatever their clock is set
    # to, and a test passes one in rather than moving the machine.
    here = now.astimezone(local) if local is not None else now.astimezone()
    if here.utcoffset() == central.utcoffset():
        return ""
    name = here.strftime("%Z").strip() or "your computer's time zone"
    return f"Times are shown in {name}. ACB publishes in US Central time."


def summarise_schedule(
    shown: list[CalendarEvent],
    everything: list[CalendarEvent],
    now: datetime,
    age_seconds: float | None,
    *,
    filtered: bool = False,
) -> str:
    """What the window says, including the reason it can be empty.

    "Nothing showed up when I arrowed to today" is the single most likely thing
    a listener will meet here, and it is not a bug -- ACB posts a fortnight and
    then stops. So the summary says how far the published schedule runs, every
    time, and says plainly when that is already in the past. A window that
    cannot distinguish "no data yet" from "broken" makes its user do it.
    """
    from quill.core.radio.directory_cache import spoken_age

    aged = spoken_age(age_seconds)
    if not everything:
        return " ".join(
            part for part in ("ACB has published no schedule for this month.", aged) if part
        )

    count = len(shown)
    if filtered:
        body = f"{count} of {len(everything)} programmes match."
    else:
        body = f"{count} programme{'' if count == 1 else 's'} published."

    spread = published_range(everything)
    parts = [body]
    if spread:
        parts.append(f"The published schedule runs {spread}.")
    latest = max((event.end or event.start) for event in everything)
    if latest <= now:
        ends = latest.astimezone()
        parts.append(
            "Nothing is published for today or later -- ACB last posted a "
            f"schedule through {ends.day} {ends.strftime('%B')}."
        )
    note = zone_note(now)
    if note:
        parts.append(note)
    if aged:
        parts.append(aged)
    return " ".join(parts)


def schedule_markdown(events: list[CalendarEvent], *, heading: str = "") -> str:
    """The flat list as Markdown, grouped by the dates that have programmes."""
    lines = [f"# {heading}" if heading else "# ACB Media schedule", ""]
    ordered = sorted(events, key=lambda event: event.start)
    current = ""
    for event in ordered:
        key = date_key(event.start)
        if key != current:
            current = key
            same_day = [e for e in ordered if date_key(e.start) == key]
            if lines[-1] != "":
                lines.append("")
            lines += [f"## {day_label(event.start, len(same_day))}", ""]
        stream = acb_calendar.stream_for(event)
        tail = f" -- {stream}" if stream else ""
        lines.append(f"- **{clock(event.start)}** {event.summary}{tail}")
    return "\n".join(lines).rstrip("\n") + "\n"


__all__ = [
    "COPY",
    "DETAILS",
    "PLAY",
    "QUEUE",
    "RECORD",
    "REMIND",
    "UNREMIND",
    "EventAction",
    "actions_for",
    "clock",
    "date_choices",
    "date_key",
    "day_label",
    "details_text",
    "first_upcoming_index",
    "full_row_label",
    "on_date",
    "nothing_on_now",
    "on_now_sentence",
    "published_range",
    "row_label",
    "schedule_markdown",
    "summarise_schedule",
    "summarise_week",
    "week_markdown",
    "zone_note",
]
