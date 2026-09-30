"""The Feed Check report (ear.md R2): worst first, and never says it gave up.

The report is built from bookkeeping ``check_state`` already keeps, so the tests
here are about the two things the report adds and the bookkeeping does not: an
**order** a listener can rely on, and **wording** that does not send somebody off
to re-subscribe to a podcast that is merely having a bad week.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts import feed_health
from quill.core.podcasts.check_state import record_failure, record_success
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _show(show_id: str, title: str, *, feed: str = "https://e/f.xml", **kwargs) -> PodcastShow:
    return PodcastShow(id=show_id, title=title, feed_url=feed, **kwargs)


def _library(*shows: PodcastShow) -> PodcastLibrary:
    return PodcastLibrary(shows=list(shows))


def _ok(library: PodcastLibrary, show: PodcastShow, *, ago: timedelta) -> None:
    record_success(library, show, new_episodes=1, now=NOW - ago)


# -- the order ---------------------------------------------------------------- #


def test_failing_feeds_come_first_and_the_worst_of_them_first() -> None:
    """A report sorted by title is one you read all of. A screen-reader user
    pays for every row, so trouble goes to the top."""
    bad, worse, fine = _show("1", "Bad"), _show("2", "Worse"), _show("3", "Fine")
    library = _library(bad, worse, fine)
    _ok(library, fine, ago=timedelta(hours=1))
    for _ in range(2):
        record_failure(library, bad, now=NOW)
    for _ in range(9):
        record_failure(library, worse, now=NOW)

    report = feed_health.rows(library, now=NOW)
    assert [row.title for row in report] == ["Worse", "Bad", "Fine"]
    assert report[0].failures == 9


def test_the_order_is_stable_between_two_openings() -> None:
    """A list that reshuffles under a screen-reader cursor is unusable, and two
    feeds failing the same number of times is the common case."""
    first, second = _show("1", "Beta"), _show("2", "Alpha")
    library = _library(first, second)
    for show in (first, second):
        record_failure(library, show, now=NOW)

    once = [row.title for row in feed_health.rows(library, now=NOW)]
    twice = [row.title for row in feed_health.rows(library, now=NOW)]
    assert once == twice == ["Alpha", "Beta"]


def test_never_checked_outranks_quiet_which_outranks_healthy() -> None:
    fresh, quiet, healthy = _show("1", "Fresh"), _show("2", "Quiet"), _show("3", "Healthy")
    library = _library(healthy, quiet, fresh)
    _ok(library, healthy, ago=timedelta(hours=2))
    _ok(library, quiet, ago=timedelta(days=200))
    record_success(library, quiet, new_episodes=0, now=NOW)

    report = feed_health.rows(library, now=NOW)
    assert [row.title for row in report] == ["Fresh", "Quiet", "Healthy"]


def test_a_local_show_is_reported_as_not_broken() -> None:
    """Somebody scanning for problems should meet it once and learn it is not one."""
    library = _library(_show("1", "My Recordings", feed="", is_local=True))
    row = feed_health.rows(library, now=NOW)[0]
    assert row.is_local
    assert "no feed to check" in row.status
    assert not row.is_failing


# -- the wording -------------------------------------------------------------- #


def test_a_failing_feed_is_never_described_as_abandoned() -> None:
    """ "This feed has failed eleven times" reads as "and I gave up", which is
    not what happens -- and would send somebody off to re-subscribe."""
    show = _show("1", "Struggling")
    library = _library(show)
    for _ in range(11):
        record_failure(library, show, now=NOW)

    row = feed_health.rows(library, now=NOW)[0]
    assert "11 checks in a row" in row.status
    assert "still trying" in row.status


def test_a_row_leads_with_the_status_not_with_four_dates() -> None:
    """Context read before the thing it is context for makes somebody wait
    through four dates to find out whether the row needed them at all."""
    show = _show("1", "The Daily")
    library = _library(show)
    _ok(library, show, ago=timedelta(hours=3))

    spoken = feed_health.rows(library, now=NOW)[0].row()
    assert spoken.startswith("The Daily, OK,")
    assert "last checked 3 hours ago" in spoken


def test_never_checked_reads_as_never_not_as_a_date() -> None:
    library = _library(_show("1", "Brand New"))
    row = feed_health.rows(library, now=NOW)[0]
    assert "last checked never" in row.row()
    assert row.status == "Never checked yet"


def test_the_good_summary_is_a_sentence_not_a_count_of_zero() -> None:
    """ "0 failing" makes the listener work out that zero is the good number."""
    show = _show("1", "The Daily")
    library = _library(show)
    _ok(library, show, ago=timedelta(minutes=10))

    assert feed_health.summary(feed_health.rows(library, now=NOW)) == (
        "1 podcast, all checking normally."
    )


def test_the_bad_summary_counts_both_kinds_of_trouble() -> None:
    bad, quiet, fine = _show("1", "Bad"), _show("2", "Quiet"), _show("3", "Fine")
    library = _library(bad, quiet, fine)
    record_failure(library, bad, now=NOW)
    _ok(library, quiet, ago=timedelta(days=100))
    record_success(library, quiet, new_episodes=0, now=NOW)
    _ok(library, fine, ago=timedelta(hours=1))

    text = feed_health.summary(feed_health.rows(library, now=NOW))
    assert "3 podcasts" in text
    assert "1 failing" in text
    assert "1 gone quiet" in text
    assert "Worst first" in text


def test_an_empty_library_says_so_rather_than_counting_nothing() -> None:
    assert feed_health.summary(feed_health.rows(_library(), now=NOW)) == "No podcasts yet."


# -- Retry All Failed acts on failures only ---------------------------------- #


def test_retry_all_failed_leaves_a_quiet_feed_alone() -> None:
    """A quiet feed is working perfectly; retrying it would say "nothing new"
    and teach the listener that the button does nothing."""
    bad, quiet = _show("1", "Bad"), _show("2", "Quiet")
    library = _library(bad, quiet)
    record_failure(library, bad, now=NOW)
    _ok(library, quiet, ago=timedelta(days=90))
    record_success(library, quiet, new_episodes=0, now=NOW)

    failing = feed_health.failing_rows(feed_health.rows(library, now=NOW))
    assert [row.title for row in failing] == ["Bad"]


def test_reading_the_report_checks_nothing() -> None:
    """No new network code: the report is bookkeeping, and a retry is the
    refresh Cast already has."""
    show = _show(
        "1",
        "The Daily",
        episodes=[
            PodcastEpisode(guid="g", title="t", audio_url="https://e/a.mp3", published="2026-09-01")
        ],
    )
    library = _library(show)
    before = dict(library.show_check_state)
    feed_health.rows(library, now=NOW)
    assert library.show_check_state == before
