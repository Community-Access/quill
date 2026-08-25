"""What a calendar row offers and how it reads (6.4, 6.6).

A week view is a lot of rows, and a row that cannot be understood from one
spoken line is a row somebody has to open to identify. So the ordering in
:func:`row_label` is not cosmetic -- time first because the day is read in time
order, then the programme, then the channel, which is what decides whether it
can be played at all.

The verbs are dimmed rather than absent when they cannot run, and each carries
its reason: a dimmed item teaches a state only if it *says* the state. The two
that dim are the two that can genuinely be impossible -- a programme on no
named channel, and a programme that has already been and gone.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.radio import calendar_actions as ca
from quill.core.radio.ics import CalendarEvent

NOW = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
SHOWTIME = datetime(2026, 8, 26, 19, 0, tzinfo=UTC)


def _event(
    *,
    stream: str = "ACB Media 1",
    start: datetime = SHOWTIME,
    hours: int = 1,
    description: str = "",
) -> CalendarEvent:
    return CalendarEvent(
        uid="uid-1",
        summary="Main Menu",
        start=start,
        end=start + timedelta(hours=hours) if hours else None,
        categories=(stream,) if stream else (),
        description=description,
    )


def _by_id(actions) -> dict:
    return {action.action_id: action for action in actions}


# -- which verbs ------------------------------------------------------------------


def test_every_verb_is_on_every_row() -> None:
    """Dimmed, not absent: a verb that comes and goes reads as a feature that
    comes and goes."""
    actions = _by_id(ca.actions_for(_event(stream=""), NOW))
    assert set(actions) >= {ca.PLAY, ca.RECORD, ca.REMIND, ca.QUEUE, ca.COPY, ca.DETAILS}


def test_a_programme_on_no_named_channel_cannot_be_played_and_says_why() -> None:
    actions = _by_id(ca.actions_for(_event(stream=""), NOW))

    assert actions[ca.PLAY].enabled is False
    assert "does not say which channel" in actions[ca.PLAY].reason
    assert actions[ca.QUEUE].enabled is False
    assert actions[ca.RECORD].enabled is False


def test_a_finished_programme_cannot_be_recorded() -> None:
    """Recording a programme that finished on Tuesday is a recording of
    silence."""
    over = _event(start=NOW - timedelta(hours=3))
    actions = _by_id(ca.actions_for(over, NOW))

    assert actions[ca.RECORD].enabled is False
    assert "already finished" in actions[ca.RECORD].reason


def test_a_programme_still_running_can_still_be_recorded() -> None:
    running = _event(start=NOW - timedelta(minutes=10))
    assert _by_id(ca.actions_for(running, NOW))[ca.RECORD].enabled is True


def test_a_started_programme_cannot_be_reminded_about() -> None:
    started = _event(start=NOW - timedelta(minutes=5))
    actions = _by_id(ca.actions_for(started, NOW))

    assert actions[ca.REMIND].enabled is False
    assert "already started" in actions[ca.REMIND].reason


def test_a_row_that_already_has_a_reminder_offers_to_remove_it() -> None:
    """A menu that cannot tell you what you already did is a menu you have to
    remember for."""
    actions = _by_id(ca.actions_for(_event(), NOW, has_reminder=True))

    assert ca.UNREMIND in actions
    assert ca.REMIND not in actions


def test_copy_details_is_never_dimmed() -> None:
    """There is nothing about it to be wrong."""
    for event in (_event(), _event(stream=""), _event(start=NOW - timedelta(days=2))):
        assert _by_id(ca.actions_for(event, NOW))[ca.COPY].enabled is True


def test_every_verb_advertises_a_keyboard_letter_nobody_else_claims() -> None:
    labels = [action.label for action in ca.actions_for(_event(), NOW)]
    letters = [label.split("&", 1)[1][0].lower() for label in labels if "&" in label]

    assert len(letters) == len(labels), "every verb has a mnemonic"
    assert len(letters) == len(set(letters)), "and no two share one"


def test_every_dimmed_verb_carries_a_reason() -> None:
    """11.2: a dimmed item teaches a state only if it says the state."""
    for event in (_event(stream=""), _event(start=NOW - timedelta(days=2))):
        for action in ca.actions_for(event, NOW):
            if not action.enabled:
                assert action.reason.strip(), action.action_id


# -- how a row reads --------------------------------------------------------------


def test_a_row_leads_with_the_time() -> None:
    """A day's rows are read in time order, and the time is what places them."""
    row = ca.row_label(_event(), NOW)
    assert row.split(",")[0].endswith(("AM", "PM"))


def test_a_row_names_the_programme_and_its_channel() -> None:
    row = ca.row_label(_event(), NOW)
    assert "Main Menu" in row
    assert "ACB Media 1" in row


def test_a_row_says_on_now_only_when_it_is() -> None:
    """A suffix nobody has to wait through on the other rows."""
    running = _event(start=NOW - timedelta(minutes=10))
    assert ca.row_label(running, NOW).endswith("on now")
    assert not ca.row_label(_event(), NOW).endswith("on now")


def test_a_clock_is_unpadded_and_needs_no_glibc() -> None:
    """ "07:00" reads as "oh seven hundred"; ``%-I`` raises on Windows.

    Built in the *local* zone, because that is what ``clock`` renders in and a
    fixed UTC hour would make this test say different things in Denver and in
    Berlin."""
    assert ca.clock(_local(7, 5)) == "7:05 AM"


def test_midnight_reads_as_twelve_not_zero() -> None:
    assert ca.clock(_local(0, 0)) == "12:00 AM"


def test_noon_reads_as_twelve_pm() -> None:
    assert ca.clock(_local(12, 0)) == "12:00 PM"


def _local(hour: int, minute: int) -> datetime:
    """A moment that is *hour:minute* where the reader is."""
    zone = datetime.now().astimezone().tzinfo
    return datetime(2026, 8, 26, hour, minute, tzinfo=zone)


def test_a_day_heading_carries_its_own_count() -> None:
    assert "3 programmes" in ca.day_label(SHOWTIME, 3)
    assert "1 programme," in ca.day_label(SHOWTIME, 1) + ","


def test_an_empty_day_says_nothing_scheduled_rather_than_nothing() -> None:
    """An empty heading is a question; "nothing scheduled" is an answer."""
    assert "nothing scheduled" in ca.day_label(SHOWTIME, 0)


# -- copy details -----------------------------------------------------------------


def test_details_carry_what_when_where_and_the_description() -> None:
    text = ca.details_text(_event(description="Tech news and interviews."))

    assert "Main Menu" in text
    assert "ACB Media 1" in text
    assert "Tech news and interviews." in text
    assert " to " in text, "the end time as well as the start"


def test_details_leave_out_what_the_feed_did_not_give() -> None:
    text = ca.details_text(_event(stream="", hours=0))
    assert "ACB Media" not in text
    assert " to " not in text


# -- the week, exported -----------------------------------------------------------


def test_the_export_keeps_every_day_including_the_empty_ones() -> None:
    """A plan with no Wednesday reads as a week with no Wednesday."""
    days = [(SHOWTIME.replace(hour=0), [_event()]), (SHOWTIME.replace(hour=0), [])]
    text = ca.week_markdown(days)

    assert text.count("## ") == 2
    assert "nothing scheduled" in text


def test_the_export_names_the_programme_its_time_and_its_channel() -> None:
    text = ca.week_markdown([(SHOWTIME.replace(hour=0), [_event()])])
    assert "Main Menu" in text
    assert "ACB Media 1" in text


def test_the_export_takes_a_heading() -> None:
    text = ca.week_markdown([], heading="ACB Media schedule, week of 23 August 2026")
    assert text.startswith("# ACB Media schedule, week of 23 August 2026")


# -- what the window says ---------------------------------------------------------


def test_an_empty_week_says_so() -> None:
    assert "Nothing is scheduled" in ca.summarise_week([(SHOWTIME, [])], None)


def test_a_week_counts_its_programmes() -> None:
    said = ca.summarise_week([(SHOWTIME, [_event(), _event()])], None)
    assert said.startswith("2 programmes")


def test_a_cached_week_says_how_old_it_is() -> None:
    """A schedule presented as current when it is three days old is not."""
    said = ca.summarise_week([(SHOWTIME, [_event()])], 86400 * 3)
    assert said != ca.summarise_week([(SHOWTIME, [_event()])], None)


def test_on_now_names_each_programme_and_its_channel() -> None:
    said = ca.on_now_sentence([_event(), _event(stream="ACB Media 4")])
    assert said.startswith("On now:")
    assert "ACB Media 1" in said and "ACB Media 4" in said


def test_on_now_with_nothing_on_still_answers() -> None:
    assert ca.on_now_sentence([]) == ca.nothing_on_now()
    assert "Nothing" in ca.nothing_on_now()


# -- the flat list (2026-08-24) --------------------------------------------------
#
# The window was a week and is now one list. These pin the part the week got
# wrong: an empty view has to say WHY it is empty, because ACB publishes a
# fortnight and then stops, and "I arrowed to today and there was nothing" is
# the first thing anybody meets.


def _at(day: int, hour: int = 12, *, summary: str = "Programme") -> CalendarEvent:
    start = datetime(2026, 8, day, hour, tzinfo=UTC)
    return CalendarEvent(
        uid=f"uid-{day}-{hour}",
        summary=summary,
        start=start,
        end=start + timedelta(hours=1),
        categories=("ACB Media 5",),
    )


def test_the_summary_says_how_far_the_published_schedule_runs() -> None:
    events = [_at(2), _at(15)]

    said = ca.summarise_schedule(events, events, datetime(2026, 8, 10, tzinfo=UTC), None)

    assert "2 August to 15 August" in said


def test_an_empty_today_is_explained_rather_than_left_silent() -> None:
    """The whole reason the week view was replaced."""
    events = [_at(2), _at(15)]

    said = ca.summarise_schedule(events, events, datetime(2026, 8, 24, tzinfo=UTC), None)

    assert "Nothing is published for today or later" in said
    assert "15 August" in said


def test_a_schedule_that_reaches_past_now_does_not_claim_to_be_stale() -> None:
    events = [_at(2), _at(28)]

    said = ca.summarise_schedule(events, events, datetime(2026, 8, 24, tzinfo=UTC), None)

    assert "Nothing is published" not in said


def test_no_schedule_at_all_says_ACB_published_none() -> None:
    said = ca.summarise_schedule([], [], datetime(2026, 8, 24, tzinfo=UTC), None)

    assert "ACB has published no schedule" in said


def test_a_filtered_list_says_how_many_of_how_many() -> None:
    events = [_at(2), _at(3), _at(4)]

    said = ca.summarise_schedule(
        events[:1], events, datetime(2026, 8, 1, tzinfo=UTC), None, filtered=True
    )

    assert "1 of 3 programmes match" in said


def test_the_date_picker_offers_only_dates_that_have_programmes() -> None:
    """A picker that mostly answers "nothing" is the calendar this replaced."""
    choices = ca.date_choices([_at(2), _at(2, 15), _at(5)])

    assert [key for key, _label in choices] == ["2026-08-02", "2026-08-05"]
    assert "2 programmes" in choices[0][1]


def test_a_date_filters_to_that_date() -> None:
    events = [_at(2), _at(5)]

    assert ca.on_date(events, "2026-08-05") == [events[1]]
    assert ca.on_date(events, "") == events


def test_the_list_opens_on_the_next_programme_still_to_come() -> None:
    events = [_at(2), _at(20), _at(28)]

    index = ca.first_upcoming_index(events, datetime(2026, 8, 24, tzinfo=UTC))

    assert index == 2


def test_a_wholly_finished_schedule_opens_on_its_last_row() -> None:
    events = [_at(2), _at(15)]

    index = ca.first_upcoming_index(events, datetime(2026, 8, 24, tzinfo=UTC))

    assert index == 1


def test_every_row_carries_its_own_date_because_there_are_no_day_headings() -> None:
    row = ca.full_row_label(_at(4, 9), datetime(2026, 8, 24, tzinfo=UTC))

    assert row.startswith("Tuesday 4 August, ")
    assert "ACB Media 5" in row


def test_a_row_says_both_ends_of_the_programme() -> None:
    """How long it runs is half of what a schedule is read for."""
    row = ca.full_row_label(_at(4, 9), datetime(2026, 8, 24, tzinfo=UTC))

    assert " to " in row, row


def test_a_listing_with_no_end_says_one_time_rather_than_inventing_a_second() -> None:
    from datetime import timedelta as _td

    start = datetime(2026, 8, 4, 9, tzinfo=UTC)
    open_ended = CalendarEvent(uid="u", summary="Programme", start=start, end=None)

    row = ca.full_row_label(open_ended, start + _td(days=1))

    assert " to " not in row


def test_a_past_programme_is_not_labelled_finished_on_every_row() -> None:
    """ACB publishes a fortnight and stops, so "finished" was on all 49 rows --
    a word repeated everywhere distinguishes nothing, and the date already
    says it."""
    row = ca.full_row_label(_at(4, 9), datetime(2026, 8, 24, tzinfo=UTC))

    assert "finished" not in row


def test_the_one_programme_on_air_still_says_so() -> None:
    """ "on now" earns its place: only one row can say it."""
    row = ca.full_row_label(_at(24, 12), datetime(2026, 8, 24, 12, 30, tzinfo=UTC))

    assert row.endswith("on now")


def test_the_markdown_export_groups_the_flat_list_by_date() -> None:
    text = ca.schedule_markdown([_at(2), _at(2, 15), _at(5)])

    assert text.count("## ") == 2
    assert text.startswith("# ACB Media schedule")
