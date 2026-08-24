"""What the index says about a show, parsed without asking it.

Every parser here is total: the Podcast Index is somebody else's JSON, and a
field that is missing, null, a string where a number was expected, or a
category map where a list was expected must read as "we do not know that"
rather than as an exception inside a browse tree.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.podcasts import podcast_index_catalog as catalog

FEED = {
    "id": 41504,
    "title": "The Show",
    "author": "A Publisher",
    "description": "About things.",
    "url": "https://feed.test/rss",
    "link": "https://show.test",
    "artwork": "https://art.test/cover.jpg",
    "language": "en-us",
    "categories": {"55": "News", "59": "Politics"},
    "episodeCount": 412,
    "newestItemPubdate": 1_787_500_000,
    "explicit": False,
    "dead": 0,
    "funding": {"url": "https://give.test", "message": "Support the show"},
}

ITEM = {
    "id": 991,
    "title": "Episode One",
    "description": "What happened.",
    "enclosureUrl": "https://media.test/1.mp3",
    "datePublished": 1_787_500_000,
    "duration": 1800,
    "episode": 1,
    "season": 2,
    "episodeType": "full",
    "explicit": 0,
    "image": "https://art.test/1.jpg",
    "link": "https://show.test/1",
    "transcripts": [{"url": "https://text.test/1.srt", "type": "application/srt"}],
    "chaptersUrl": "https://chapters.test/1.json",
}


def test_a_show_carries_the_catalogue_fact_sheet() -> None:
    show = catalog.show_from_json(FEED)

    assert show.title == "The Show"
    assert show.feed_url == "https://feed.test/rss"
    assert show.categories == ("News", "Politics")
    assert show.episode_count == 412
    assert show.language == "en-us"
    assert show.funding_url == "https://give.test"
    assert show.funding_label == "Support the show"
    assert show.dead is False


def test_the_summary_reads_as_one_spoken_line() -> None:
    assert catalog.show_from_json(FEED).summary == "A Publisher, 412 episodes, News, Politics"


def test_a_show_the_index_can_no_longer_read_says_so() -> None:
    show = catalog.show_from_json({**FEED, "dead": 1})

    assert show.dead is True
    assert "no longer read" in show.summary


def test_categories_survive_either_shape() -> None:
    """The API sends a map; a cached round trip brings back a list."""
    as_list = catalog.show_from_json({**FEED, "categories": ["News", "Politics"]})
    assert as_list.categories == ("News", "Politics")
    assert catalog.show_from_json({**FEED, "categories": None}).categories == ()


def test_an_episode_carries_its_podcasting_2_0_links() -> None:
    episode = catalog.episode_from_json(ITEM)

    assert episode.audio_url == "https://media.test/1.mp3"
    assert episode.duration_seconds == 1800
    assert episode.season == 2
    assert episode.transcript_url == "https://text.test/1.srt"
    assert episode.transcript_type == "application/srt"
    assert episode.chapters_url == "https://chapters.test/1.json"


def test_a_transcript_named_the_older_way_is_still_found() -> None:
    older = {**ITEM, "transcripts": None, "transcriptUrl": "https://text.test/old.vtt"}
    assert catalog.episode_from_json(older).transcript_url == "https://text.test/old.vtt"


@pytest.mark.parametrize("junk", [None, 42, "a string", [], {"nothing": "useful"}])
def test_junk_parses_to_an_empty_answer_rather_than_raising(junk: Any) -> None:
    assert catalog.show_from_json(junk).feed_url == ""
    assert catalog.episode_from_json(junk).audio_url == ""
    assert catalog.shows_from_json(junk) == []
    assert catalog.episodes_from_json(junk) == []
    assert catalog.categories_from_json(junk) == []


def test_both_response_shapes_are_read() -> None:
    """``feeds`` for a list, ``feed`` for a single lookup."""
    assert len(catalog.shows_from_json({"feeds": [FEED, FEED]})) == 2
    assert len(catalog.shows_from_json({"feed": FEED})) == 1


def test_a_row_with_neither_a_feed_nor_a_title_is_dropped() -> None:
    assert catalog.shows_from_json({"feeds": [{"id": 1}]}) == []


def test_the_taxonomy_comes_back_in_reading_order() -> None:
    payload = {"feeds": [{"id": 2, "name": "News"}, {"id": 1, "name": "Arts"}]}

    assert [c.name for c in catalog.categories_from_json(payload)] == ["Arts", "News"]


def test_a_cached_show_round_trips_through_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cache entry has been through JSON, so a dataclass comes back a dict."""
    show = catalog.show_from_json(FEED)

    assert catalog.show_from_json(catalog._show_dict(show)) == show


def test_a_cached_episode_round_trips_through_json() -> None:
    episode = catalog.episode_from_json(ITEM)

    assert catalog.episode_from_json(catalog._episode_dict(episode)) == episode


def test_safe_mode_refuses_every_catalogue_call() -> None:
    from quill.core.podcasts.podcast_index import PodcastIndexError

    for call in (
        lambda: catalog.show_facts("https://feed.test/rss", safe_mode=True),
        lambda: catalog.episodes_for_feed("https://feed.test/rss", safe_mode=True),
        lambda: catalog.trending(safe_mode=True),
        lambda: catalog.categories(safe_mode=True),
    ):
        with pytest.raises(PodcastIndexError):
            call()


def test_an_empty_feed_address_asks_nothing() -> None:
    assert catalog.show_facts("") is None
    assert catalog.episodes_for_feed("  ") == []


def test_the_request_limit_is_bounded_both_ways() -> None:
    assert catalog._limit(0) == catalog.CATALOG_LIMIT
    assert catalog._limit(-5) == 1
    assert catalog._limit(10_000) == catalog._MAX_LIMIT
