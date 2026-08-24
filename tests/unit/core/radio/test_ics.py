"""Reading an iCalendar feed by hand (list.md section 6).

ACB Media publishes its schedule as ICS. Two hundred lines of parser beats a
dependency for a feed this narrow -- but only if the two things that are easy
to get wrong are actually got right, and both of them cost the whole feature
when they are not:

* **Line folding.** RFC 5545 wraps at 75 octets and continues with a leading
  space. Unfolded naively, one long programme title becomes two properties, the
  second of which is not a property.
* **Escapes.** ``\\,`` inside a text value. Read raw, a description truncates at
  its first comma -- and the description is where a programme's content lives.

The third rule is about failure: **a feed that breaks must not break the week.**
An event that cannot be read is skipped; a file that is not ICS at all reads as
no events, which the caller reports as "the schedule could not be read" rather
than as an empty Tuesday.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.radio.ics import CalendarEvent, parse_calendar, parse_timestamp

SAMPLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//My Calendar//EN
BEGIN:VEVENT
UID:acb-1
DTSTAMP:20260820T120000Z
DTSTART:20260824T190000Z
DTEND:20260824T200000Z
SUMMARY:Main Menu
DESCRIPTION:Technology news\\, reviews\\, and interviews.
CATEGORIES:ACB Media 1
END:VEVENT
BEGIN:VEVENT
UID:acb-2
DTSTART:20260825T010000Z
DTEND:20260825T020000Z
SUMMARY:The Sunday Night Blues Hour with a very long name that the feed
  will have folded across two lines
CATEGORIES:ACB Media 4
END:VEVENT
END:VCALENDAR
"""


# -- the ordinary case -----------------------------------------------------------


def test_every_event_is_read() -> None:
    assert len(parse_calendar(SAMPLE)) == 2


def test_events_come_back_earliest_first() -> None:
    events = parse_calendar(SAMPLE)
    assert [event.summary.split(" with")[0] for event in events] == [
        "Main Menu",
        "The Sunday Night Blues Hour",
    ]


def test_the_start_and_end_are_aware_utc() -> None:
    event = parse_calendar(SAMPLE)[0]
    assert event.start == datetime(2026, 8, 24, 19, 0, tzinfo=UTC)
    assert event.end == datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def test_a_category_becomes_the_stream_name() -> None:
    """Categories map to stream names -- the whole of 6.1's second half."""
    assert parse_calendar(SAMPLE)[0].categories == ("ACB Media 1",)


def test_several_categories_are_all_kept() -> None:
    text = _event(categories="ACB Media 1,ACB Media 2")
    assert parse_calendar(text)[0].categories == ("ACB Media 1", "ACB Media 2")


# -- folding ---------------------------------------------------------------------


def test_a_folded_line_is_put_back_together() -> None:
    """Unfolded naively, this title becomes two properties and the second is
    not a property at all."""
    event = parse_calendar(SAMPLE)[1]
    assert event.summary == (
        "The Sunday Night Blues Hour with a very long name that the feed "
        "will have folded across two lines"
    )


def test_a_tab_continues_a_line_as_well_as_a_space() -> None:
    text = SAMPLE.replace("\n  will have", "\n\twill have")
    assert "will have folded" in parse_calendar(text)[1].summary


def test_crlf_line_endings_read_the_same_as_lf() -> None:
    """The wire format is CRLF; a file saved locally may not be."""
    assert parse_calendar(SAMPLE.replace("\n", "\r\n")) == parse_calendar(SAMPLE)


# -- escapes ---------------------------------------------------------------------


def test_an_escaped_comma_survives() -> None:
    """Read raw, this description truncates at its first comma."""
    event = parse_calendar(SAMPLE)[0]
    assert event.description == "Technology news, reviews, and interviews."


def test_an_escaped_newline_becomes_a_newline() -> None:
    text = _event(description="First line\\nSecond line")
    assert parse_calendar(text)[0].description == "First line\nSecond line"


def test_an_escaped_backslash_stays_one_backslash() -> None:
    text = _event(description="A back\\\\slash")
    assert parse_calendar(text)[0].description == "A back\\slash"


def test_an_escaped_semicolon_survives() -> None:
    text = _event(description="Here\\; and there")
    assert parse_calendar(text)[0].description == "Here; and there"


# -- the property line -----------------------------------------------------------


def test_parameters_are_dropped_and_the_value_kept() -> None:
    text = _event(extra="DTSTART;VALUE=DATE-TIME:20260824T190000Z")
    assert parse_calendar(text)[0].start == datetime(2026, 8, 24, 19, 0, tzinfo=UTC)


def test_a_colon_inside_a_quoted_parameter_is_not_the_value_separator() -> None:
    """``DTSTART;TZID="A/B":2026...`` has two colons, and taking the first
    would glue the timezone to the front of the value."""
    text = _event(extra='DTSTART;TZID="America/New_York":20260824T150000')
    assert parse_calendar(text)[0].start == datetime(2026, 8, 24, 15, 0, tzinfo=UTC)


def test_a_url_in_a_value_keeps_its_own_colon() -> None:
    text = _event(extra="URL:https://acbmedia.org/show")
    assert parse_calendar(text)[0].url == "https://acbmedia.org/show"


# -- timestamps ------------------------------------------------------------------


def test_the_three_shapes_a_time_arrives_in() -> None:
    assert parse_timestamp("20260824T190000Z") == datetime(2026, 8, 24, 19, 0, tzinfo=UTC)
    assert parse_timestamp("20260824T190000") == datetime(2026, 8, 24, 19, 0, tzinfo=UTC)
    assert parse_timestamp("20260824") == datetime(2026, 8, 24, 0, 0, tzinfo=UTC)


def test_an_iso_timestamp_is_accepted_too() -> None:
    assert parse_timestamp("2026-08-24T19:00:00+00:00") == datetime(2026, 8, 24, 19, 0, tzinfo=UTC)


def test_an_unreadable_timestamp_is_none_rather_than_a_guess() -> None:
    for junk in ("", "   ", "next Tuesday", "2026-13-45"):
        assert parse_timestamp(junk) is None


def test_a_floating_time_reads_as_utc_rather_than_as_local() -> None:
    """Guessing wrong by five hours is worse than being consistently wrong by
    an amount the caller can see."""
    assert parse_timestamp("20260824T190000").tzinfo is UTC


# -- failure ---------------------------------------------------------------------


def test_an_event_with_no_start_is_skipped_not_placed_somewhere() -> None:
    """Putting it somewhere anyway would invent a time somebody might act on."""
    text = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:x\nSUMMARY:Nowhen\nEND:VEVENT\nEND:VCALENDAR\n"
    assert parse_calendar(text) == []


def test_one_broken_event_does_not_lose_the_others() -> None:
    """A schedule that will not show Tuesday because Thursday is malformed is
    worse than one missing Thursday."""
    text = SAMPLE.replace("DTSTART:20260825T010000Z", "DTSTART:whenever")
    events = parse_calendar(text)
    assert [event.summary for event in events] == ["Main Menu"]


def test_something_that_is_not_a_calendar_reads_as_no_events() -> None:
    for junk in ("", "<html><body>Not found</body></html>", "{}"):
        assert parse_calendar(junk) == []


def test_an_event_with_no_summary_still_has_a_name() -> None:
    """An unnamed row in a week view is a row nobody can act on."""
    text = _event(summary="")
    assert parse_calendar(text)[0].summary == "Untitled programme"


def test_an_event_with_no_uid_gets_one_from_what_it_is() -> None:
    """The uid is how a reminder and a recording find their event again."""
    text = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260824T190000Z\nSUMMARY:X\nEND:VEVENT\n"
    assert parse_calendar(text)[0].uid


def test_an_unterminated_event_is_dropped_rather_than_half_read() -> None:
    text = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260824T190000Z\nSUMMARY:X\n"
    assert parse_calendar(text) == []


# -- what is on now --------------------------------------------------------------


def test_an_event_is_on_between_its_start_and_its_end() -> None:
    event = parse_calendar(SAMPLE)[0]
    assert event.overlaps(datetime(2026, 8, 24, 19, 30, tzinfo=UTC)) is True
    assert event.overlaps(datetime(2026, 8, 24, 18, 59, tzinfo=UTC)) is False
    assert event.overlaps(datetime(2026, 8, 24, 20, 0, tzinfo=UTC)) is False, "end is exclusive"


def test_an_event_with_no_end_is_treated_as_an_hour() -> None:
    """Never and forever are both wrong in a way somebody notices."""
    event = CalendarEvent(uid="x", summary="X", start=datetime(2026, 8, 24, 19, 0, tzinfo=UTC))
    assert event.duration is None
    assert event.overlaps(datetime(2026, 8, 24, 19, 59, tzinfo=UTC)) is True
    assert event.overlaps(datetime(2026, 8, 24, 20, 1, tzinfo=UTC)) is False


def test_a_duration_is_the_gap_between_the_two_ends() -> None:
    assert parse_calendar(SAMPLE)[0].duration.total_seconds() == 3600


def _event(
    *, summary: str = "A Show", description: str = "", categories: str = "", extra: str = ""
) -> str:
    lines = ["BEGIN:VCALENDAR", "BEGIN:VEVENT", "UID:test-1"]
    # An *extra* that is itself a DTSTART replaces the default one; anything
    # else joins it, so an event under test always has a start and is never
    # skipped for a reason the test did not intend.
    if extra.upper().startswith("DTSTART"):
        lines.append(extra)
    else:
        lines.append("DTSTART:20260824T190000Z")
        if extra:
            lines.append(extra)
    lines.append(f"SUMMARY:{summary}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if categories:
        lines.append(f"CATEGORIES:{categories}")
    lines += ["END:VEVENT", "END:VCALENDAR", ""]
    return "\n".join(lines)
