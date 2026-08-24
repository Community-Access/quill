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
from datetime import datetime
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
    event: CalendarEvent, now: datetime, *, has_reminder: bool = False
) -> list[EventAction]:
    """Every verb for one programme, in the order a listener meets them."""
    stream = acb_calendar.stream_for(event)
    started = event.start <= now
    finished = (event.end or event.start) <= now
    no_stream = "this programme does not say which channel it is on"

    actions = [
        EventAction(
            PLAY,
            "&Play Now" if started else "&Play This Channel Now",
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
    "day_label",
    "details_text",
    "nothing_on_now",
    "on_now_sentence",
    "row_label",
    "summarise_week",
    "week_markdown",
]
