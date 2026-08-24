"""Recurrence, against ACB's own output at last (list.md 6.12).

``ics_recurrence`` handles daily, weekly (with ``BYDAY``), fortnightly, monthly
and yearly, with ``COUNT``, ``UNTIL`` and ``EXDATE``, under 32 tests -- every
one of them against a feed we wrote ourselves. ACB's August export contained no
``RRULE`` at all, so the code had never met a real one, and the item stayed open
on exactly that basis.

It has met one now. The fixture beside this file is three events taken verbatim
from the live feed on **2026-08-24** (``acb-2026-08-recurring.ics``), including
the first genuine recurring entry anybody has published there.

Two things came out of reading it, and both are pinned below.

**The recurrence is handled correctly.** ``RRULE:FREQ=WEEKLY;UNTIL=...`` expands
to exactly one occurrence, because the ``UNTIL`` falls before the second week --
in fact before the event's own end. That is what RFC 5545 says and what we do.
It is almost certainly not what whoever added the entry meant, and that is worth
knowing about rather than papering over: an app that "helpfully" ignored an
``UNTIL`` it thought looked wrong would show a weekly programme that does not
exist.

**Every event in the feed carries ``TZID=America/Chicago``**, and the parser
read those as UTC. Rendered back through ``calendar_actions.clock``, which
converts to the reader's own zone, that put the entire ACB schedule five hours
early on any machine not running on UTC. Nobody had reported it, because a
schedule that is consistently wrong still looks like a schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quill.core.radio import ics, ics_recurrence

FIXTURE = Path(__file__).parent / "fixtures" / "acb-2026-08-recurring.ics"
FEED = FIXTURE.read_text(encoding="utf-8")


def _events() -> list[ics.CalendarEvent]:
    return ics.parse_calendar(FEED)


def test_the_real_feed_parses() -> None:
    events = _events()

    assert len(events) == 3
    assert all(event.summary for event in events)


def test_the_recurring_entry_is_found_and_carries_its_rule() -> None:
    """Carried rather than resolved at parse time: expanding a series needs a
    window, and the parser has no idea which week anybody is looking at."""
    recurring = [event for event in _events() if event.rrule]

    assert len(recurring) == 1
    assert recurring[0].rrule == "FREQ=WEEKLY;UNTIL=20260801T000000Z"
    assert recurring[0].summary == "Flight 93 National Memorial visitors center"


def test_the_real_rule_expands_to_what_the_rule_actually_says() -> None:
    """One occurrence, because ``UNTIL`` is before the second week.

    Probably not what its author intended -- an ``UNTIL`` nineteen minutes
    after a weekly event's start makes the "weekly" part do nothing -- but
    reading it any other way would invent a programme. If ACB fixes the entry,
    this test is what proves we start showing the repeats.
    """
    event = next(e for e in _events() if e.rrule)
    window_start, window_end = ics_recurrence.window_for(datetime(2026, 7, 27, tzinfo=UTC))

    occurrences = ics_recurrence.expand(
        event,
        event.rrule,
        window_start=window_start,
        window_end=window_end,
        exdates=event.exdates,
    )

    assert len(occurrences) == 1
    assert occurrences[0].start == datetime(2026, 8, 1, 4, 41, tzinfo=UTC)


def test_a_window_after_the_series_ends_shows_nothing() -> None:
    """The other half of ``UNTIL``: a finished series must not keep appearing."""
    event = next(e for e in _events() if e.rrule)
    window_start, window_end = ics_recurrence.window_for(datetime(2026, 9, 15, tzinfo=UTC))

    occurrences = ics_recurrence.expand(
        event, event.rrule, window_start=window_start, window_end=window_end
    )

    assert occurrences == []


def test_the_feeds_times_are_read_in_chicago_where_they_were_written() -> None:
    """The bug this fixture found. 11:41 pm Central is 4:41 am UTC, not 11:41
    pm UTC -- and the difference is what a listener sees on the row."""
    event = next(e for e in _events() if e.rrule)

    assert event.start == datetime(2026, 8, 1, 4, 41, tzinfo=UTC)
    assert event.end == datetime(2026, 8, 1, 6, 39, tzinfo=UTC)


def test_the_daily_schedule_lands_at_nine_in_the_morning_central() -> None:
    """A sanity check anybody can verify by looking at the feed: ACB Presents
    the Daily Schedule is a 9 am Central programme. If this ever reads 2 pm,
    the timezone has been dropped again."""
    from zoneinfo import ZoneInfo

    daily = [e for e in _events() if "Daily Schedule" in e.summary]
    assert daily

    central = daily[0].start.astimezone(ZoneInfo("America/Chicago"))
    assert (central.hour, central.minute) == (9, 0)


def test_the_feed_is_still_double_spaced_and_that_is_fine() -> None:
    """ACB's export writes a blank line between every property. The parser
    drops empty lines, and this pins the fixture as *verbatim* -- a fixture
    somebody has tidied up is no longer evidence of what arrives."""
    assert "\n\n" in FEED
    assert FEED.startswith("BEGIN:VCALENDAR")
