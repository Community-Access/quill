"""The schedule says whose clock its times are on.

Reported from Phoenix, 2026-08-25: *"the calendar shows 7:00 AM for the first
event and I think it should be 6:00 AM as I am in Arizona/Phoenix... Is there a
timezone issue going on here?"*

There was not. ACB writes ``DTSTART;TZID=America/Chicago:20260825T090000`` and
labels its own website CDT; 9 am CDT is 7 am in Arizona, which keeps MST all
year. But the window showed a bare "7:00 AM" and never said whose 7 am it was,
which leaves no way to tell a correct conversion from a missing one -- and the
Arizona gap *moves* (two hours behind Central in summer, one in winter), so
nobody should have to do that arithmetic to trust the window.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from quill.core.radio import calendar_actions

_AUGUST = datetime(2026, 8, 25, 14, 0, tzinfo=UTC)  # 9 am CDT
_JANUARY = datetime(2026, 1, 25, 15, 0, tzinfo=UTC)  # 9 am CST


def test_a_reader_on_acbs_own_clock_is_told_nothing() -> None:
    """A sentence saying "these times are in your time" to somebody in Chicago
    is a sentence read out on every reload for nothing."""
    assert calendar_actions.zone_note(_AUGUST, ZoneInfo("America/Chicago")) == ""


def test_arizona_is_told_which_clock_and_whose_the_source_is() -> None:
    note = calendar_actions.zone_note(_AUGUST, ZoneInfo("America/Phoenix"))

    assert "Times are shown in" in note
    assert "Central" in note


def test_arizona_matches_central_in_winter_and_the_note_goes_quiet() -> None:
    """The gap is two hours in summer and one in winter -- but the note is not
    about the size of the gap, it is about whether there is one.

    Arizona is MST all year; Central goes to CST in November. They still differ
    by an hour, so the note stays. Somewhere that genuinely shares the offset is
    what silences it -- which is the point of testing the offset, not the name.
    """
    assert calendar_actions.zone_note(_JANUARY, ZoneInfo("America/Phoenix")) != ""
    assert calendar_actions.zone_note(_JANUARY, ZoneInfo("America/Chicago")) == ""
    # Mountain *Daylight* shares Central's offset in neither season, but
    # Saskatchewan sits on Central's winter clock the whole year round.
    assert calendar_actions.zone_note(_JANUARY, ZoneInfo("America/Regina")) == ""


def test_the_note_reaches_the_summary_a_listener_actually_reads() -> None:
    """Pure helpers nobody wires up are how this was missing in the first place."""
    from quill.core.radio.ics import CalendarEvent

    event = CalendarEvent(
        uid="1",
        summary="ACB Presents the Daily Schedule",
        start=_AUGUST,
        end=None,
        description="",
        categories=("ACB Media 5",),
    )
    said = calendar_actions.summarise_schedule([event], [event], _AUGUST, None)

    # On a Central machine this line is absent by design, so assert the wiring
    # rather than the wording: the summary is whatever zone_note returns here.
    note = calendar_actions.zone_note(_AUGUST)
    assert (note in said) if note else ("Times are shown in" not in said)
