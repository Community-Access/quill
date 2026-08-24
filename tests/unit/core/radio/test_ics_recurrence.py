"""One VEVENT that means twenty (list.md 6.10).

ACB's August 2026 export wrote every occurrence out separately, so the calendar
read it correctly by ignoring recurrence entirely. That is a fact about one
month, not about the format: the day My Calendar emits an ``RRULE``, a weekly
programme appears **once** instead of every week -- and that failure reads as a
thin schedule rather than as a bug, so nobody reports it.

Three properties carry the expansion, and each is a way it could hang or lie:

* **It is always bounded.** An ``RRULE`` with no ``COUNT`` and no ``UNTIL`` is
  legal and infinite. Expansion is bounded by the window, by ``UNTIL``, and --
  because neither of those survives a malformed rule -- by a hard ceiling.
* **Unsupported parts are ignored, never guessed.** A programme placed on a
  guessed day is worse than one that only appears where the feed put it.
* **Every occurrence keeps its own identity.** A reminder set on next Tuesday
  must attach to next Tuesday, not to the series -- and two occurrences must
  never look like a duplicate of each other to the de-duplication pass.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.radio import ics_recurrence as rec
from quill.core.radio.ics import CalendarEvent

# 2026-08-03 is a Monday.
MONDAY = datetime(2026, 8, 3, 19, 0, tzinfo=UTC)
WINDOW = (datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC))


def _event(start: datetime = MONDAY, *, hours: int = 1) -> CalendarEvent:
    return CalendarEvent(
        uid="series-1",
        summary="Sports Roundtable",
        start=start,
        end=start + timedelta(hours=hours),
        categories=("ACB Media 5",),
    )


def _expand(rule: str, *, exdates: str = "", event: CalendarEvent | None = None) -> list:
    return rec.expand(
        event or _event(), rule, window_start=WINDOW[0], window_end=WINDOW[1], exdates=exdates
    )


def _days(events: list) -> list[str]:
    return [event.start.strftime("%Y-%m-%d %H:%M") for event in events]


# -- the rule itself --------------------------------------------------------------


def test_a_rule_reads_as_its_parts() -> None:
    assert rec.parse_rule("FREQ=WEEKLY;BYDAY=MO,WE;INTERVAL=2") == {
        "FREQ": "WEEKLY",
        "BYDAY": "MO,WE",
        "INTERVAL": "2",
    }


def test_a_lower_case_key_still_reads() -> None:
    assert rec.parse_rule("freq=daily")["FREQ"] == "daily"


def test_junk_reads_as_no_rule() -> None:
    assert rec.parse_rule("") == {}
    assert rec.parse_rule("this is not a rule") == {}


# -- no rule, or one this does not support ----------------------------------------


def test_an_event_with_no_rule_comes_back_alone() -> None:
    assert _expand("") == [_event()]


def test_an_unsupported_frequency_loses_the_repeats_never_the_programme() -> None:
    """A feed that grows a part nobody anticipated must still show the show."""
    out = _expand("FREQ=HOURLY;INTERVAL=3")
    assert out == [_event()]


def test_an_unreadable_rule_comes_back_as_the_one_event() -> None:
    assert _expand("FREQ=;INTERVAL=x") == [_event()]


# -- daily ------------------------------------------------------------------------


def test_a_daily_rule_produces_a_programme_a_day() -> None:
    out = _expand("FREQ=DAILY;COUNT=4")
    assert _days(out) == [
        "2026-08-03 19:00",
        "2026-08-04 19:00",
        "2026-08-05 19:00",
        "2026-08-06 19:00",
    ]


def test_an_interval_skips_days() -> None:
    out = _expand("FREQ=DAILY;INTERVAL=3;COUNT=3")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-06 19:00", "2026-08-09 19:00"]


def test_until_ends_the_series() -> None:
    out = _expand("FREQ=DAILY;UNTIL=20260805T235959Z")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-04 19:00", "2026-08-05 19:00"]


# -- weekly -----------------------------------------------------------------------


def test_a_weekly_rule_produces_the_same_weekday() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=3")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-10 19:00", "2026-08-17 19:00"]


def test_by_day_produces_several_programmes_a_week() -> None:
    """FREQ=WEEKLY;BYDAY=MO,WE,FR is three a week, not one."""
    out = _expand("FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=6")
    assert _days(out) == [
        "2026-08-03 19:00",
        "2026-08-05 19:00",
        "2026-08-07 19:00",
        "2026-08-10 19:00",
        "2026-08-12 19:00",
        "2026-08-14 19:00",
    ]


def test_a_fortnightly_rule_keeps_all_its_days_in_the_weeks_it_runs() -> None:
    """INTERVAL=2 means the same days every other week, not every other day."""
    out = _expand("FREQ=WEEKLY;BYDAY=MO,WE;INTERVAL=2;COUNT=4")
    assert _days(out) == [
        "2026-08-03 19:00",
        "2026-08-05 19:00",
        "2026-08-17 19:00",
        "2026-08-19 19:00",
    ]


def test_the_time_of_day_follows_the_anchor() -> None:
    out = _expand("FREQ=WEEKLY;BYDAY=SA;COUNT=1")
    assert out[0].start.hour == MONDAY.hour and out[0].start.minute == MONDAY.minute


def test_an_ordinal_weekday_reads_as_the_weekday() -> None:
    """ "2FR" belongs to a monthly form this does not support. Dropping the
    number produces *more* occurrences, which a listener can see and
    disbelieve -- a missing programme is invisible."""
    out = _expand("FREQ=WEEKLY;BYDAY=2FR;COUNT=2")
    assert [event.start.weekday() for event in out] == [4, 4]


def test_a_nonsense_weekday_is_ignored_rather_than_guessed() -> None:
    out = _expand("FREQ=WEEKLY;BYDAY=XX;COUNT=2")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-10 19:00"]


# -- monthly and yearly -----------------------------------------------------------


def test_a_monthly_rule_lands_on_the_same_date() -> None:
    out = _expand("FREQ=MONTHLY;COUNT=2")
    assert _days(out) == ["2026-08-03 19:00", "2026-09-03 19:00"]


def test_a_monthly_rule_on_the_31st_clamps_rather_than_rolling_over() -> None:
    """The 31st plus one month is the end of that month, not the 1st of the
    next -- a monthly programme on the 31st means "the end of the month"."""
    out = rec.expand(
        _event(datetime(2026, 8, 31, 19, 0, tzinfo=UTC)),
        "FREQ=MONTHLY;COUNT=2",
        window_start=WINDOW[0],
        window_end=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert _days(out) == ["2026-08-31 19:00", "2026-09-30 19:00"]


def test_a_yearly_rule_steps_a_year() -> None:
    out = rec.expand(
        _event(),
        "FREQ=YEARLY;COUNT=2",
        window_start=WINDOW[0],
        window_end=datetime(2028, 1, 1, tzinfo=UTC),
    )
    assert _days(out) == ["2026-08-03 19:00", "2027-08-03 19:00"]


# -- exclusions -------------------------------------------------------------------


def test_an_excluded_date_is_a_cancelled_week() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=4", exdates="20260810T190000Z")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-17 19:00", "2026-08-24 19:00"]


def test_several_exclusions_all_take() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=4", exdates="20260810T190000Z,20260824T190000Z")
    assert _days(out) == ["2026-08-03 19:00", "2026-08-17 19:00"]


def test_an_unreadable_exclusion_is_ignored_not_fatal() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=2", exdates="whenever")
    assert len(out) == 2


# -- bounds -----------------------------------------------------------------------


def test_nothing_before_the_window_is_produced() -> None:
    """A series that began in March, seen in August, starts in August."""
    out = rec.expand(
        _event(datetime(2026, 3, 2, 19, 0, tzinfo=UTC)),
        "FREQ=WEEKLY",
        window_start=WINDOW[0],
        window_end=datetime(2026, 8, 15, tzinfo=UTC),
    )
    assert _days(out) == ["2026-08-03 19:00", "2026-08-10 19:00"]


def test_nothing_after_the_window_is_produced() -> None:
    out = _expand("FREQ=DAILY")
    assert all(event.start < WINDOW[1] for event in out)


def test_an_unbounded_rule_terminates() -> None:
    """No COUNT and no UNTIL is legal, and infinite. A parser that honoured it
    literally would hang on a feed."""
    out = rec.expand(
        _event(),
        "FREQ=DAILY",
        window_start=WINDOW[0],
        window_end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    assert 0 < len(out) <= rec.MAX_OCCURRENCES


def test_a_zero_interval_cannot_loop_for_ever() -> None:
    """The guard is on the count rather than the arithmetic, so one malformed
    number cannot defeat it."""
    out = rec.expand(
        _event(),
        "FREQ=DAILY;INTERVAL=0",
        window_start=WINDOW[0],
        window_end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    assert len(out) <= rec.MAX_OCCURRENCES


def test_count_is_over_the_series_not_over_the_window() -> None:
    """A rule with COUNT=4 that began in March has produced its four by
    August; a window-relative count would resurrect them."""
    out = rec.expand(
        _event(datetime(2026, 3, 2, 19, 0, tzinfo=UTC)),
        "FREQ=WEEKLY;COUNT=4",
        window_start=WINDOW[0],
        window_end=WINDOW[1],
    )
    assert out == []


# -- identity ---------------------------------------------------------------------


def test_each_occurrence_gets_its_own_uid() -> None:
    """A reminder set on next Tuesday must attach to next Tuesday, and two
    occurrences must not look like a duplicate of each other."""
    out = _expand("FREQ=WEEKLY;COUNT=3")
    uids = [event.uid for event in out]

    assert len(set(uids)) == 3
    assert all(uid.startswith("series-1@") for uid in uids)


def test_an_occurrence_keeps_the_programme_it_came_from() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=2")
    assert all(event.summary == "Sports Roundtable" for event in out)
    assert all(event.categories == ("ACB Media 5",) for event in out)


def test_an_occurrence_keeps_the_length_not_the_end_time() -> None:
    out = _expand("FREQ=WEEKLY;COUNT=2")
    assert all(event.duration == timedelta(hours=1) for event in out)
    assert out[1].end == out[1].start + timedelta(hours=1)


def test_an_event_with_no_end_produces_occurrences_with_no_end() -> None:
    open_ended = CalendarEvent(uid="x", summary="X", start=MONDAY)
    out = rec.expand(
        open_ended, "FREQ=WEEKLY;COUNT=2", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    assert all(event.end is None for event in out)


# -- the window helper ------------------------------------------------------------


def test_the_window_is_this_month_and_the_next() -> None:
    """The same two months the feed's own address asks for, so a rule cannot
    produce occurrences the calendar has nowhere to show."""
    start, end = rec.window_for(datetime(2026, 8, 24, tzinfo=UTC))

    assert start == datetime(2026, 8, 1, tzinfo=UTC)
    assert end == datetime(2026, 10, 1, tzinfo=UTC)


def test_the_window_rolls_across_a_year_end() -> None:
    start, end = rec.window_for(datetime(2026, 12, 3, tzinfo=UTC))

    assert start == datetime(2026, 12, 1, tzinfo=UTC)
    assert end == datetime(2027, 2, 1, tzinfo=UTC)


# -- DTSTART is always an instance (found against the live ACB feed) -------------


def test_an_until_before_the_event_still_shows_the_event_once() -> None:
    """RFC 5545: DTSTART is the first instance of a recurrence set, whatever
    the rule says afterwards.

    The first real RRULE ACB published carries ``UNTIL=20260801T000000Z`` on an
    event that starts at 04:41 on 1 August -- the UNTIL is before the event it
    is attached to. Read strictly, the series is empty and the programme
    disappears from the schedule. A schedule that quietly omits a published
    programme is the worst failure this app has, and every other calendar shows
    this entry once.
    """
    event = _event(datetime(2026, 8, 1, 4, 41, tzinfo=UTC))

    out = rec.expand(
        event,
        "FREQ=WEEKLY;UNTIL=20260801T000000Z",
        window_start=datetime(2026, 7, 1, tzinfo=UTC),
        window_end=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert [o.start for o in out] == [event.start]


def test_a_count_of_zero_occurrences_still_shows_the_event_once() -> None:
    """Same rule from the other direction: a bound that excludes everything
    must not exclude the programme itself."""
    event = _event(datetime(2026, 8, 10, 19, 0, tzinfo=UTC))

    out = rec.expand(
        event,
        "FREQ=DAILY;UNTIL=20260101T000000Z",
        window_start=datetime(2026, 8, 1, tzinfo=UTC),
        window_end=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert len(out) == 1


def test_an_anchor_outside_the_window_is_not_dragged_into_it() -> None:
    """The limit of the rule above. A series that ended in March must not
    reappear in August just because its bounds excluded everything."""
    event = _event(datetime(2026, 3, 2, 19, 0, tzinfo=UTC))

    out = rec.expand(
        event,
        "FREQ=WEEKLY;UNTIL=20260301T000000Z",
        window_start=datetime(2026, 8, 1, tzinfo=UTC),
        window_end=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert out == []


def test_an_exdate_naming_the_first_instance_still_cancels_it() -> None:
    """The other limit: somebody saying "not that one" explicitly outranks the
    courtesy above."""
    event = _event(datetime(2026, 8, 10, 19, 0, tzinfo=UTC))

    out = rec.expand(
        event,
        "FREQ=WEEKLY;UNTIL=20260801T000000Z",
        window_start=datetime(2026, 8, 1, tzinfo=UTC),
        window_end=datetime(2026, 9, 1, tzinfo=UTC),
        exdates="20260810T190000Z",
    )

    assert out == []
