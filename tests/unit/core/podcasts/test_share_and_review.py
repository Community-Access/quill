"""Sharing a moment, and the year in review.

The share-link cases are mostly about what ``parse_link`` **refuses**: it reads
input handed in from outside the app, and the whole safety argument rests on it
resolving to a feed and a GUID and nothing else.

The streak cases are the calendar edge cases, which is where every streak
feature gets it wrong: 23:59 and 00:01 are two days, two sessions in one day are
one day, and today not having happened yet does not break a run.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from quill.core.podcasts import share_links
from quill.core.podcasts.year_in_review import streaks, year_in_review


class _Session:
    def __init__(self, when: datetime, seconds: float = 600.0, **fields: object) -> None:
        self.date = when.isoformat()
        self.seconds = seconds
        self.speed = 1.0
        self.trimmed_seconds = 0.0
        self.completed = False
        self.key = "show-1"
        for name, value in fields.items():
            setattr(self, name, value)


# -- C7: sharing -------------------------------------------------------------


def test_a_link_round_trips() -> None:
    link = share_links.build_link("https://feeds.example.com/ba", "guid-7", 2_472_000)
    target = share_links.parse_link(link)
    assert target is not None
    assert target.feed_url == "https://feeds.example.com/ba"
    assert target.guid == "guid-7"
    assert target.position_ms == 2_472_000


def test_the_sentence_says_the_same_thing_as_the_link() -> None:
    """A link nobody can open is worse than a sentence anybody can paste."""
    text = share_links.build_text("Blind Abilities", "Episode 214", 2_472_000)
    assert text == "Blind Abilities, Episode 214, at 41 minutes 12 seconds"
    assert "at the start" not in text


def test_from_the_start_is_said_rather_than_zero() -> None:
    assert share_links.build_text("Show", "Episode", 0).endswith("from the start")


def test_both_halves_go_on_the_clipboard_together() -> None:
    payload = share_links.build_share("Show", "Episode", "https://feeds.example.com/x", "g", 60_000)
    sentence, link = payload.split("\n")
    assert sentence.startswith("Show, Episode")
    assert link.startswith("quill-cast://episode?")


def test_a_link_with_no_feed_or_guid_is_not_a_link() -> None:
    assert share_links.build_link("", "guid") == ""
    assert share_links.build_link("https://f", "") == ""


def test_anything_that_is_not_ours_is_refused() -> None:
    for text in (
        "",
        "https://evil.example/x",
        "quill-radio://episode?feed=https://f&guid=g",
        "quill-cast://episode",
        "quill-cast://episode?feed=https://f",
        "quill-cast://episode?guid=g",
    ):
        assert share_links.parse_link(text) is None


def test_a_feed_that_is_not_a_web_address_is_refused() -> None:
    """The one field that reaches the network layer; anything odd here is somebody trying."""
    assert share_links.parse_link("quill-cast://episode?feed=file:///C:/x&guid=g") is None
    assert share_links.parse_link("quill-cast://episode?feed=javascript:alert(1)&guid=g") is None


def test_a_link_that_arrived_wrapped_in_quotes_still_parses() -> None:
    """Shells and chat windows both do this."""
    link = share_links.build_link("https://f.example/x", "g", 0)
    assert share_links.parse_link(f'"{link}"') is not None


def test_a_broken_timestamp_reads_as_the_start_rather_than_failing() -> None:
    target = share_links.parse_link(
        "quill-cast://episode?feed=https%3A%2F%2Ff.example%2Fx&guid=g&t=soon"
    )
    assert target is not None
    assert target.position_ms == 0


def test_positions_are_spoken_as_words() -> None:
    """A screen reader reads 41:12 as a time of day."""
    assert share_links.spoken_position(2_472_000) == "41 minutes 12 seconds"
    assert share_links.spoken_position(0) == "0 seconds"
    assert share_links.spoken_position(3_600_000) == "1 hour"


# -- C8: streaks -------------------------------------------------------------


def _at(days_ago: int, hour: int = 12) -> datetime:
    moment = datetime.now().astimezone().replace(hour=hour, minute=0, second=0, microsecond=0)
    return moment - timedelta(days=days_ago)


def test_a_run_of_days_is_counted() -> None:
    sessions = [_Session(_at(index)) for index in range(3)]
    run = streaks(sessions)
    assert run.current_days == 3
    assert run.longest_days == 3


def test_two_sessions_in_one_day_count_once() -> None:
    sessions = [_Session(_at(0, hour=9)), _Session(_at(0, hour=21))]
    assert streaks(sessions).current_days == 1


def test_two_minutes_either_side_of_midnight_are_two_days() -> None:
    sessions = [_Session(_at(1, hour=23)), _Session(_at(0, hour=0))]
    run = streaks(sessions)
    assert run.current_days == 2
    assert run.longest_days == 2


def test_a_one_day_gap_breaks_the_streak() -> None:
    sessions = [_Session(_at(index)) for index in (0, 1, 3, 4, 5)]
    run = streaks(sessions)
    assert run.current_days == 2
    assert run.longest_days == 3


def test_today_not_having_happened_yet_does_not_break_a_run() -> None:
    """The cruellest possible version of this feature would say it had."""
    sessions = [_Session(_at(index)) for index in (1, 2, 3)]
    assert streaks(sessions).current_days == 3


def test_a_run_that_ended_last_week_is_not_current() -> None:
    sessions = [_Session(_at(index)) for index in (7, 8, 9)]
    run = streaks(sessions)
    assert run.current_days == 0
    assert run.longest_days == 3


def test_no_sessions_is_no_streak_and_says_nothing() -> None:
    run = streaks([])
    assert run.current_days == 0
    assert run.describe() == ""


# -- C8: the year ------------------------------------------------------------


def test_a_year_with_nothing_in_it_reports_nothing() -> None:
    assert year_in_review([], 2026) == ""


def test_the_report_is_sentences_with_the_numbers_the_log_holds() -> None:
    year = datetime.now().astimezone().year
    sessions = [
        _Session(_at(1), seconds=3600, completed=True),
        _Session(_at(2), seconds=1800, speed=1.5),
        _Session(_at(3), seconds=900, key="show-2"),
    ]
    text = year_in_review(sessions, year, {"show-1": "Blind Abilities", "show-2": "Jazz"})
    assert f"Your {year} in listening." in text
    assert "You listened for 1 hour, 45 minutes." in text
    assert "You finished 1 episode." in text
    assert "Blind Abilities" in text
    assert "percent of your year" in text
    assert "faster than normal saved you" in text


def test_a_trim_nobody_measured_is_omitted_rather_than_shown_as_zero() -> None:
    year = datetime.now().astimezone().year
    text = year_in_review([_Session(_at(1), seconds=3600)], year, {"show-1": "A Show"})
    assert "Trimming silence" not in text


def test_a_measured_trim_is_reported() -> None:
    year = datetime.now().astimezone().year
    sessions = [_Session(_at(1), seconds=3600, trimmed_seconds=600.0)]
    assert "Trimming silence saved you" in year_in_review(sessions, year, {})


def test_only_the_chosen_year_counts() -> None:
    year = datetime.now().astimezone().year
    old = datetime(year - 1, 6, 1, 12, 0).astimezone()
    text = year_in_review([_Session(old, seconds=7200)], year, {})
    assert text == ""
    assert year_in_review([_Session(old, seconds=7200)], year - 1, {}) != ""


def test_a_show_no_longer_in_the_library_is_named_honestly() -> None:
    year = datetime.now().astimezone().year
    text = year_in_review([_Session(_at(1), seconds=600)], year, {})
    assert "no longer in your library" in text


def test_the_busiest_month_is_named() -> None:
    year = datetime.now().astimezone().year
    when = datetime(year, 3, 15, 12, 0).astimezone()
    text = year_in_review([_Session(when, seconds=7200)], year, {}, today=date(year, 12, 31))
    assert "Your busiest month was March" in text
