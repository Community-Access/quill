"""The ACB Media schedule: a week, a search, and what an event is on (6.1-6.5).

The querying is pure and the fetch goes through ``directory_cache``, so
everything here runs without a network. Three properties are the point:

* **A week is Sunday to Saturday and always has seven days**, including the
  empty ones. A week view that silently omitted Wednesday would read as a week
  with no Wednesday, and "nothing on" is information rather than a row to hide.
* **A category is a stream** (6.5). My Calendar's categories are ACB's channel
  names, which is the whole mechanism by which an event knows what to play --
  and an event whose category names no stream is still a real event, with no
  Play verb rather than a guessed one.
* **Nothing here raises.** A schedule that will not load must not take the
  window with it; the cache answers instead, and the failure goes to Recent
  Problems.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.radio import acb_calendar
from quill.core.radio.ics import CalendarEvent

# 2026-08-26 is a Wednesday; the Sunday of its week is 2026-08-23.
WEDNESDAY = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
SUNDAY = datetime(2026, 8, 23, 0, 0, tzinfo=UTC)


def _event(
    summary: str = "Main Menu",
    *,
    days: int = 0,
    hour: int = 19,
    stream: str = "ACB Media 1",
    description: str = "",
) -> CalendarEvent:
    start = SUNDAY + timedelta(days=days, hours=hour)
    return CalendarEvent(
        uid=f"{summary}-{days}-{hour}",
        summary=summary,
        start=start,
        end=start + timedelta(hours=1),
        description=description,
        categories=(stream,) if stream else (),
    )


# -- the week ---------------------------------------------------------------------


def test_the_week_starts_on_sunday() -> None:
    """ACB publishes Sunday-first, and a listener comparing the window to the
    website should not have to translate."""
    assert acb_calendar.week_start(WEDNESDAY) == SUNDAY


def test_a_sunday_is_its_own_week_start() -> None:
    assert acb_calendar.week_start(SUNDAY + timedelta(hours=23)) == SUNDAY


def test_a_saturday_belongs_to_the_week_that_began_six_days_earlier() -> None:
    saturday = SUNDAY + timedelta(days=6, hours=20)
    assert acb_calendar.week_start(saturday) == SUNDAY


def test_only_this_week_is_in_this_week() -> None:
    events = [_event("Now", days=3), _event("Next week", days=8), _event("Last week", days=-2)]
    assert [e.summary for e in acb_calendar.week_of(events, WEDNESDAY)] == ["Now"]


def test_the_week_is_always_seven_days_including_the_empty_ones() -> None:
    """A week view that omitted Wednesday would read as a week with no
    Wednesday."""
    days = acb_calendar.days_of([_event(days=3)], WEDNESDAY)

    assert len(days) == 7
    assert [midnight.weekday() for midnight, _rows in days] == [6, 0, 1, 2, 3, 4, 5]
    assert sum(len(rows) for _midnight, rows in days) == 1


def test_each_day_holds_only_its_own_programmes() -> None:
    events = [_event("A", days=0, hour=1), _event("B", days=0, hour=23), _event("C", days=1)]
    days = acb_calendar.days_of(events, WEDNESDAY)

    assert [e.summary for e in days[0][1]] == ["A", "B"]
    assert [e.summary for e in days[1][1]] == ["C"]


# -- search (6.3) -----------------------------------------------------------------


def test_search_matches_the_title() -> None:
    events = [_event("Main Menu"), _event("Sound Off")]
    assert [e.summary for e in acb_calendar.search(events, "sound")] == ["Sound Off"]


def test_search_matches_the_description_too() -> None:
    events = [_event("A", description="Interviews about braille displays")]
    assert acb_calendar.search(events, "braille") == events


def test_search_matches_the_stream_name() -> None:
    events = [_event("A", stream="ACB Media 4"), _event("B", stream="ACB Media 1")]
    assert [e.summary for e in acb_calendar.search(events, "media 4")] == ["A"]


def test_every_word_has_to_appear_somewhere_in_any_field() -> None:
    """ "blues tuesday" should find it without anybody knowing which field holds
    which word."""
    events = [_event("Blues Hour", days=2, description="Every Tuesday evening")]
    assert acb_calendar.search(events, "blues tuesday") == events
    assert acb_calendar.search(events, "blues thursday") == []


def test_an_empty_query_is_everything_rather_than_nothing() -> None:
    events = [_event("A"), _event("B")]
    assert acb_calendar.search(events, "") == events
    assert acb_calendar.search(events, "   ") == events


def test_search_ignores_case() -> None:
    assert acb_calendar.search([_event("Main Menu")], "MAIN") != []


# -- what is on now, and what is next ---------------------------------------------


def test_on_now_is_what_is_on_the_air() -> None:
    events = [_event("A", days=0, hour=19), _event("B", days=0, hour=21)]
    moment = SUNDAY + timedelta(days=0, hours=19, minutes=30)

    assert [e.summary for e in acb_calendar.on_now(events, moment)] == ["A"]


def test_on_now_can_answer_with_several_streams_at_once() -> None:
    events = [
        _event("A", hour=19, stream="ACB Media 1"),
        _event("B", hour=19, stream="ACB Media 4"),
    ]
    moment = SUNDAY + timedelta(hours=19, minutes=5)

    assert len(acb_calendar.on_now(events, moment)) == 2


def test_upcoming_is_soonest_first_and_excludes_what_has_started() -> None:
    events = [
        _event("Later", days=1),
        _event("Soon", days=0, hour=23),
        _event("Past", days=0, hour=1),
    ]
    moment = SUNDAY + timedelta(hours=12)

    assert [e.summary for e in acb_calendar.upcoming(events, moment)] == ["Soon", "Later"]


def test_upcoming_respects_its_limit() -> None:
    events = [_event(f"E{n}", days=n % 7, hour=n % 24) for n in range(30)]
    assert len(acb_calendar.upcoming(events, SUNDAY, limit=5)) == 5


# -- a category is a stream (6.5) -------------------------------------------------


def test_an_event_knows_which_stream_it_is_on() -> None:
    assert acb_calendar.stream_for(_event(stream="ACB Media 4")) == "ACB Media 4"


def test_a_stream_name_is_matched_however_the_feed_spells_it() -> None:
    for spelling in ("ACB Media 4", "acb media 4", "ACBMedia4", "ACB  Media  4"):
        assert acb_calendar.stream_for(_event(stream=spelling)) == spelling


def test_an_event_with_no_stream_has_none_rather_than_a_guess() -> None:
    """Guessing which of ten channels it meant would be worse than saying so."""
    assert acb_calendar.stream_for(_event(stream="")) == ""
    assert acb_calendar.stream_for(_event(stream="Community News")) == ""


def test_an_event_resolves_to_a_playable_station() -> None:
    """The whole of 6.5 -- and the address comes from acb_media, so the two
    can never disagree about what "ACB Media 4" is."""
    station = acb_calendar.station_for(_event(stream="ACB Media 4"))

    assert station is not None
    assert station.name == "ACB Media 4"
    assert station.stream_url.startswith("https://")


def test_an_event_with_no_stream_resolves_to_nothing() -> None:
    assert acb_calendar.station_for(_event(stream="")) is None


def test_stream_names_read_back_in_acbs_numeric_order() -> None:
    """ "ACB Media 10" sorts between 1 and 2 as text, and a listener reading a
    filter list should not have to think about that."""
    events = [_event(stream=f"ACB Media {n}") for n in (10, 2, 1)]
    assert acb_calendar.stream_names(events) == ["ACB Media 1", "ACB Media 2", "ACB Media 10"]


def test_filtering_by_stream_keeps_only_that_stream() -> None:
    events = [_event("A", stream="ACB Media 1"), _event("B", stream="ACB Media 4")]
    assert [e.summary for e in acb_calendar.by_stream(events, "ACB Media 4")] == ["B"]


def test_filtering_by_nothing_is_everything() -> None:
    events = [_event("A"), _event("B")]
    assert acb_calendar.by_stream(events, "") == events


# -- fetching, cache and failure (6.8) --------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)


def test_a_schedule_that_will_not_load_is_no_events_rather_than_a_crash(monkeypatch) -> None:
    """A browse window that throws takes the window with it."""

    def _boom(_when) -> list:
        raise OSError("acbmedia.org is unreachable")

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _boom)

    events, age = acb_calendar.fetch_schedule()

    assert events == []
    assert age is None


def test_a_fetched_schedule_comes_back_live_and_is_cached(monkeypatch) -> None:
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [_row("Main Menu")])

    events, age = acb_calendar.fetch_schedule()
    assert [e.summary for e in events] == ["Main Menu"]
    assert age is None, "None means it came off the network just now"

    # Second call inside the freshness window must not fetch again.
    monkeypatch.setattr(acb_calendar, "_fetch_ics", _never)
    again, cached_age = acb_calendar.fetch_schedule()
    assert [e.summary for e in again] == ["Main Menu"]
    assert cached_age is not None, "and a number means it came from the cache"


def test_refresh_goes_past_a_fresh_cache(monkeypatch) -> None:
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [_row("Old")])
    acb_calendar.fetch_schedule()

    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [_row("New")])
    events, age = acb_calendar.fetch_schedule(refresh=True)

    assert [e.summary for e in events] == ["New"]
    assert age is None


def test_a_dead_network_falls_back_to_the_cache(monkeypatch) -> None:
    """Works offline from the cache -- the second half of 6.8."""
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [_row("Main Menu")])
    acb_calendar.fetch_schedule()

    def _boom(_when) -> list:
        raise OSError("no network")

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _boom)
    events, age = acb_calendar.fetch_schedule(refresh=True)

    assert [e.summary for e in events] == ["Main Menu"]
    assert age is not None, "and it says how old it is, rather than implying it is current"


def test_safe_mode_reads_the_cache_and_never_reaches_out(monkeypatch) -> None:
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [_row("Main Menu")])
    acb_calendar.fetch_schedule()

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _never)
    events, _age = acb_calendar.fetch_schedule(safe_mode=True)

    assert [e.summary for e in events] == ["Main Menu"]


def test_safe_mode_with_no_cache_is_empty_rather_than_an_error(monkeypatch) -> None:
    monkeypatch.setattr(acb_calendar, "_fetch_ics", _never)
    assert acb_calendar.fetch_schedule(safe_mode=True) == ([], None)


def test_a_cache_written_by_an_older_build_reads_as_fewer_events(monkeypatch) -> None:
    """Half-written, or written by a version that spelled a field differently:
    fewer events, never an exception on the way into a window."""
    monkeypatch.setattr(
        acb_calendar,
        "_fetch_ics",
        lambda _when: [_row("Good"), {"summary": "No start"}, "not a row", {"start": "whenever"}],
    )
    events, _age = acb_calendar.fetch_schedule()

    assert [e.summary for e in events] == ["Good"]


def test_the_cache_round_trip_keeps_every_field(monkeypatch) -> None:
    row = _row("Main Menu")
    row["description"] = "Technology news, reviews, and interviews."
    row["url"] = "https://acbmedia.org/show"
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [row])
    acb_calendar.fetch_schedule()

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _never)
    events, _age = acb_calendar.fetch_schedule()
    event = events[0]

    assert event.description == "Technology news, reviews, and interviews."
    assert event.url == "https://acbmedia.org/show"
    assert event.categories == ("ACB Media 1",)
    assert event.end is not None


def _row(summary: str) -> dict:
    start = SUNDAY + timedelta(hours=19)
    return {
        "uid": f"uid-{summary}",
        "summary": summary,
        "start": start.isoformat(),
        "end": (start + timedelta(hours=1)).isoformat(),
        "description": "",
        "location": "",
        "categories": ["ACB Media 1"],
        "url": "",
    }


def _never(_when=None) -> list:
    raise AssertionError("the network must not be reached here")


# -- the month is part of the address ---------------------------------------------


def test_the_feed_address_carries_the_month_being_looked_at() -> None:
    """A hardcoded month works perfectly until the first of September, and
    then serves last month's listings for ever."""
    august = acb_calendar.ics_url(datetime(2026, 8, 24, tzinfo=UTC))

    assert "month=8" in august
    assert "yr=2026" in august
    assert "nmonth=9" in august and "nyr=2026" in august


def test_december_rolls_the_following_month_into_the_next_year() -> None:
    december = acb_calendar.ics_url(datetime(2026, 12, 3, tzinfo=UTC))

    assert "month=12" in december and "yr=2026" in december
    assert "nmonth=1" in december and "nyr=2027" in december


def test_the_address_asks_for_every_category_rather_than_the_site_default() -> None:
    """Omitting mcat returns whatever subset somebody chose in WordPress, which
    can change without warning."""
    assert "mcat=1,2,3" in acb_calendar.ics_url(datetime(2026, 8, 24, tzinfo=UTC))


def test_each_month_gets_its_own_cache_entry() -> None:
    """One key would serve August's listings for October, from disk, silently."""
    august = acb_calendar.cache_key(datetime(2026, 8, 24, tzinfo=UTC))
    october = acb_calendar.cache_key(datetime(2026, 10, 1, tzinfo=UTC))

    assert august != october
    assert august == "acb-media-calendar-2026-08"


def test_a_different_month_is_a_different_fetch(monkeypatch) -> None:
    asked: list[int] = []

    def _fetch(when):
        asked.append(when.month)
        return [_row(f"Month {when.month}")]

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _fetch)

    acb_calendar.fetch_schedule(when=datetime(2026, 8, 24, tzinfo=UTC))
    acb_calendar.fetch_schedule(when=datetime(2026, 9, 24, tzinfo=UTC))
    acb_calendar.fetch_schedule(when=datetime(2026, 8, 25, tzinfo=UTC))

    assert asked == [8, 9], "the third is August again, and comes from the cache"


# -- the feed publishes some programmes twice -------------------------------------


def test_a_programme_published_twice_is_listed_once() -> None:
    """ACB's feed really does this. Confirmed against the live August 2026
    export: 20 of 69 events were exact repeats -- same title, same start, same
    end, same channel -- carrying *different* uids. A week view that trusted
    the uid showed every affected programme twice."""
    first = _event("The Daily Schedule")
    twin = CalendarEvent(
        uid="105842-4487",
        summary=first.summary,
        start=first.start,
        end=first.end,
        categories=first.categories,
    )

    assert acb_calendar.deduplicate([first, twin]) == [first]


def test_the_first_one_wins_so_a_reminder_keeps_its_target() -> None:
    """A reminder targets a uid. If the survivor changed between loads, the
    reminder would attach itself to a row that vanished next week."""
    first = _event("The Daily Schedule")
    twin = CalendarEvent(
        uid="zzz-later",
        summary=first.summary,
        start=first.start,
        end=first.end,
        categories=first.categories,
    )

    assert acb_calendar.deduplicate([first, twin])[0].uid == first.uid
    assert acb_calendar.deduplicate([first, twin])[0].uid == first.uid


def test_two_genuinely_different_programmes_both_survive() -> None:
    assert len(acb_calendar.deduplicate([_event("A"), _event("B")])) == 2


def test_the_same_title_at_a_different_time_is_a_different_programme() -> None:
    """A daily show is not a duplicate of itself."""
    monday = _event("Main Menu", days=1)
    tuesday = _event("Main Menu", days=2)

    assert len(acb_calendar.deduplicate([monday, tuesday])) == 2


def test_the_same_title_on_a_different_channel_is_a_different_programme() -> None:
    assert (
        len(
            acb_calendar.deduplicate([
                _event("Simulcast", stream="ACB Media 1"),
                _event("Simulcast", stream="ACB Media 4"),
            ])
        )
        == 2
    )


def test_a_repeat_that_differs_only_by_case_or_spacing_is_still_a_repeat() -> None:
    first = _event("Main Menu")
    twin = CalendarEvent(
        uid="other",
        summary="  main menu ",
        start=first.start,
        end=first.end,
        categories=("acb media 1",),
    )

    assert len(acb_calendar.deduplicate([first, twin])) == 1


def test_deduplication_happens_on_the_way_out_of_the_cache_too(monkeypatch) -> None:
    """A cache written before this existed must not replay the duplicates."""
    row = _row("Twice")
    monkeypatch.setattr(acb_calendar, "_fetch_ics", lambda _when: [row, dict(row, uid="other")])

    events, _age = acb_calendar.fetch_schedule()

    assert [e.summary for e in events] == ["Twice"]


def test_an_unpublished_month_falls_back_to_the_one_before(monkeypatch) -> None:
    """ACB posts a fortnight and stops, so on the 1st the only schedule that
    exists is last month's. A window that answers "nothing" when a schedule
    demonstrably exists is the failure this feature is for; the summary line is
    what keeps the older month from being presented as current."""
    asked: list[tuple[int, int]] = []

    def _by_month(when):
        asked.append((when.year, when.month))
        return [_row("July programme")] if when.month == 7 else []

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _by_month)

    events, _age = acb_calendar.fetch_schedule(when=datetime(2026, 8, 1, tzinfo=UTC))

    assert [e.summary for e in events] == ["July programme"]
    assert asked == [(2026, 8), (2026, 7)]


def test_a_month_that_has_listings_never_reaches_for_the_one_before(monkeypatch) -> None:
    asked: list[tuple[int, int]] = []

    def _by_month(when):
        asked.append((when.year, when.month))
        return [_row("August programme")]

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _by_month)

    events, _age = acb_calendar.fetch_schedule(when=datetime(2026, 8, 24, tzinfo=UTC))

    assert [e.summary for e in events] == ["August programme"]
    assert asked == [(2026, 8)]
