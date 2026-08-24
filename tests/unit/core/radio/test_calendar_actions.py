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
