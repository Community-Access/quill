"""What a feed read does to a podcast's record (check.md bugs 2, 3, 8, 9 and 17).

The shapes come from the 2026-10-04 Downcast import test: a show imported from
an OPML file with no episodes, whose newest episode is from April 2018 (The
Mayan Crystal); a feed the publisher emptied (ReMade); a feed that answers
"not modified". Driven through ``feed_read.record_success`` -- the function
Cast's refresh calls -- with no network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts import check_state, feed_health, feed_problems, feed_read, settings_catalog
from quill.core.podcasts.feed_reader import FeedInfo, FeedReaderError, FetchNotes
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.settings_resolver import set_value
from quill.core.podcasts.settings_types import LEVEL_SHOW
from quill.core.podcasts.subscriptions import PodcastLibrary

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _episode(guid: str, published: str, title: str = "") -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=title or guid,
        audio_url=f"https://art19.example/{guid}.mp3",
        published=published,
    )


def _info(*episodes: PodcastEpisode, **kwargs: object) -> FeedInfo:
    return FeedInfo(
        title="The Mayan Crystal",
        homepage="",
        artwork_url="",
        episodes=list(episodes),
        **kwargs,  # type: ignore[arg-type]
    )


def _imported() -> tuple[PodcastLibrary, PodcastShow]:
    show = PodcastShow(
        id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/mayan-crystal"
    )
    return PodcastLibrary(shows=[show]), show


def _back_catalogue() -> list[PodcastEpisode]:
    """Fresh objects every time: a read marks and merges them in place."""
    return [
        _episode("e1", "Mon, 02 Apr 2018 08:00:00 GMT"),
        _episode("e2", "Mon, 09 Apr 2018 08:00:00 GMT"),
        _episode("e3", "Mon, 16 Apr 2018 08:00:00 GMT"),
    ]


# -- bug 2: the first read is a starting point -------------------------------------


def test_an_imported_shows_first_read_brings_nothing_new() -> None:
    library, show = _imported()

    read = feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)

    assert read.baseline is True
    assert read.arrived == []  # nothing for Episode Filters, routing or notices
    assert len(show.episodes) == 3  # ...but the episodes are all there


def test_last_published_is_the_newest_episodes_own_date_not_the_clock() -> None:
    library, show = _imported()

    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)

    published = check_state.last_published(library, show)
    assert published == datetime(2018, 4, 16, 8, 0, tzinfo=UTC)
    row = feed_health.rows(library, now=NOW)[0]
    assert row.status.startswith("Quiet, nothing new for")
    assert row.published_ago == "8 years ago"


def test_a_clock_stamp_from_an_older_cast_is_healed_by_the_next_read() -> None:
    library, show = _imported()
    show.episodes = _back_catalogue()
    check_state.record_success(library, show, new_episodes=3, now=NOW - timedelta(hours=1))
    assert check_state.last_published(library, show) == NOW - timedelta(hours=1)

    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)

    assert check_state.last_published(library, show) == datetime(2018, 4, 16, 8, 0, tzinfo=UTC)


def test_the_second_read_reports_only_what_is_genuinely_new() -> None:
    library, show = _imported()
    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)
    fresh = _episode("e4", "Sat, 03 Oct 2026 08:00:00 GMT")

    read = feed_read.record_success(library, show, _info(*_back_catalogue(), fresh), now=NOW)

    assert read.baseline is False
    assert [episode.guid for episode in read.arrived] == ["e4"]
    assert check_state.last_published(library, show) == datetime(2026, 10, 3, 8, 0, tzinfo=UTC)


def test_the_first_read_collects_only_what_the_back_catalogue_setting_asks_for() -> None:
    library, show = _imported()
    definition = settings_catalog.definition("backfill_mode")
    count = settings_catalog.definition("backfill_count")
    assert definition is not None and count is not None
    set_value(library, definition, "newest", level=LEVEL_SHOW, scope_id=show.id)
    set_value(library, count, 1, level=LEVEL_SHOW, scope_id=show.id)

    read = feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)

    assert read.backfilled == 1
    marked = [episode.guid for episode in show.episodes if episode.mode_override == "download"]
    assert marked == ["e3"]


def test_with_the_default_setting_the_first_read_collects_nothing() -> None:
    library, show = _imported()
    read = feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)
    assert read.backfilled == 0
    assert all(episode.mode_override != "download" for episode in show.episodes)


# -- bug 3: an empty feed has a status of its own ----------------------------------


def test_an_emptied_feed_is_reported_as_empty_not_ok() -> None:
    library, show = _imported()

    read = feed_read.record_success(library, show, _info(), now=NOW)

    assert read.empty is True
    row = feed_health.rows(library, now=NOW)[0]
    assert row.status == "Empty: the feed has no episodes"
    assert row.rank == feed_health.EMPTY_RANK
    assert row.worth_a_search is True
    assert feed_health.summary([row]) == "1 podcast, 1 empty. Worst first."


def test_an_empty_feeds_first_episode_is_news() -> None:
    library, show = _imported()
    feed_read.record_success(library, show, _info(), now=NOW)

    read = feed_read.record_success(library, show, _info(_back_catalogue()[0]), now=NOW)

    assert read.baseline is False
    assert [episode.guid for episode in read.arrived] == ["e1"]
    assert check_state.is_empty(library, show) is False


# -- bug 9: validators and "not modified" ------------------------------------------


def test_validators_are_kept_and_sent_only_once_the_show_has_episodes() -> None:
    library, show = _imported()
    assert feed_read.notes_for(library, show).etag == ""
    notes = FetchNotes(etag='"v1"', last_modified="Sat, 03 Oct 2026 10:00:00 GMT")

    feed_read.record_success(library, show, _info(*_back_catalogue()), notes, now=NOW)

    again = feed_read.notes_for(library, show)
    assert (again.etag, again.last_modified) == ('"v1"', "Sat, 03 Oct 2026 10:00:00 GMT")
    show.feed_url = "https://elsewhere.example/feed"
    assert feed_read.notes_for(library, show).etag == ""  # tied to the address


def test_not_modified_is_a_success_with_nothing_new() -> None:
    library, show = _imported()
    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)
    check_state.record_failure(library, show, now=NOW, reason="x", kind=feed_problems.TIMEOUT)

    read = feed_read.record_success(library, show, _info(not_modified=True), now=NOW)

    assert read.not_modified is True
    assert read.arrived == []
    assert len(show.episodes) == 3
    assert check_state.failure_run(library, show) == 0
    assert check_state.last_published(library, show) == datetime(2018, 4, 16, 8, 0, tzinfo=UTC)


# -- bugs 7 and 8: the reason is kept and said -------------------------------------


def test_a_failure_keeps_its_plain_reason_for_feed_check() -> None:
    library, show = _imported()
    error = FeedReaderError(
        "The host no longer has a feed at this address.", kind=feed_problems.GONE
    )

    problem = feed_read.record_failure(library, show, error, now=NOW)

    assert problem.kind == feed_problems.GONE
    row = feed_health.rows(library, now=NOW)[0]
    assert row.status == (
        "Failing, 1 check in a row: The host no longer has a feed at this address "
        "(Cast is still trying)"
    )
    assert row.worth_a_search is True


def test_a_slow_host_is_not_offered_a_search_for_a_new_feed() -> None:
    library, show = _imported()
    feed_read.record_failure(library, show, TimeoutError("timed out"), now=NOW)
    row = feed_health.rows(library, now=NOW)[0]
    assert "The host took too long to answer" in row.status
    assert row.worth_a_search is False


def test_the_spoken_notice_says_why_and_only_suggests_a_search_when_it_helps() -> None:
    library, show = _imported()
    definition = settings_catalog.definition("failed_check_notice")
    assert definition is not None
    set_value(library, definition, 1, level=LEVEL_SHOW, scope_id=show.id)
    feed_read.record_failure(library, show, TimeoutError("timed out"), now=NOW)
    said = check_state.failure_notice(library, show)
    assert "The host took too long to answer." in said
    assert "address may have changed" not in said
    assert "New Feed" not in said

    library2, show2 = _imported()
    set_value(library2, definition, 1, level=LEVEL_SHOW, scope_id=show2.id)
    feed_read.record_failure(
        library2, show2, FeedReaderError("gone", kind=feed_problems.REMOVED), now=NOW
    )
    said2 = check_state.failure_notice(library2, show2)
    assert "removed for good" in said2
    assert "Find This Show's New Feed" in said2


def test_a_success_clears_the_reason() -> None:
    library, show = _imported()
    feed_read.record_failure(library, show, TimeoutError("timed out"), now=NOW)
    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)
    assert check_state.failure_reason(library, show) == ""


# -- bug 17: a refresh heals a title escaped twice ---------------------------------


def test_a_refresh_heals_a_title_left_escaped_by_an_older_import() -> None:
    library, show = _imported()
    show.title = "We&apos;re Alive"
    feed_read.record_success(library, show, _info(*_back_catalogue()), now=NOW)
    assert show.title == "We're Alive"
