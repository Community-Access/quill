"""Tests for the keyless Apple Podcasts browse directory.

Pure parsing plus request-shape checks; `_fetch` is replaced so no network is
touched. The fixtures are trimmed copies of the real documents (including
Apple's own "Explict" typo in the chart feed, which a naive check misses).
"""

from __future__ import annotations

import json

import pytest

from quill.core.podcasts import apple_podcasts as apple
from quill.core.radio import directory_cache


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    directory_cache.clear()
    yield
    directory_cache.clear()


_GENRES = json.dumps({
    "26": {
        "name": "Podcasts",
        "id": "26",
        "subgenres": {
            "1301": {
                "name": "Arts",
                "id": "1301",
                "subgenres": {
                    "1482": {"name": "Books", "id": "1482", "subgenres": {}},
                    "1402": {"name": "Design", "id": "1402", "subgenres": {}},
                },
            },
            "1303": {"name": "Comedy", "id": "1303", "subgenres": {}},
            "9999": {"id": "9999", "subgenres": {}},  # no name -> dropped
        },
    },
    "34": {"name": "Music", "id": "34", "subgenres": {}},  # not podcasts
})

_CHARTS = json.dumps({
    "feed": {
        "title": "Top Podcasts",
        "results": [
            {
                "id": "1200361736",
                "name": "The Daily",
                "artistName": "The New York Times",
                "artworkUrl100": "https://is1.example/100x100.jpg",
                "url": "https://podcasts.apple.com/us/podcast/id1200361736",
                "genres": [{"genreId": "1489", "name": "News"}, {"genreId": "26"}],
                "contentAdvisoryRating": "Explict",
            },
            {
                "id": "1234",
                "name": "Arts Show",
                "artistName": "Someone",
                "genres": [{"genreId": "1301", "name": "Arts"}],
            },
            {"name": "No id, dropped"},
        ],
    }
})

#: Trimmed from Apple's live History chart (itunes.apple.com/us/rss/toppodcasts/
#: limit=200/genre=1487/json, fetched 2026-10-03), plus one incomplete row and
#: one repeat, which the parser must drop.
_GENRE_CHART = json.dumps({
    "feed": {
        "entry": [
            {
                "im:name": {"label": "The Team House"},
                "im:image": [
                    {"label": "https://is1-ssl.mzstatic.com/a/55x55bb.png"},
                    {"label": "https://is1-ssl.mzstatic.com/a/170x170bb.png"},
                ],
                "id": {
                    "label": "https://podcasts.apple.com/us/podcast/the-team-house/id1492797340?uo=2",
                    "attributes": {"im:id": "1492797340"},
                },
                "im:artist": {"label": "dee takos"},
                "category": {"attributes": {"im:id": "1487", "label": "History"}},
                "link": {
                    "attributes": {
                        "href": "https://podcasts.apple.com/us/podcast/the-team-house/id1492797340?uo=2"
                    }
                },
            },
            {
                "im:name": {"label": "The Rest Is History"},
                "id": {"attributes": {"im:id": "1537788786"}},
                "im:artist": {"label": "Goalhanger", "attributes": {"href": "https://x.test"}},
                "category": {"attributes": {"im:id": "1487", "label": "History"}},
            },
            {
                "im:name": {"label": "World War II with Tom Hanks"},
                "id": {"attributes": {"im:id": "1896760409"}},
                "im:artist": {"label": "The HISTORY Channel"},
                "category": {"attributes": {"im:id": "1487", "label": "History"}},
            },
            {"im:name": {"label": "No id, dropped"}},
            {
                "im:name": {"label": "The Rest Is History"},
                "id": {"attributes": {"im:id": "1537788786"}},
            },
        ]
    }
})

_LOOKUP = json.dumps({
    "resultCount": 1,
    "results": [
        {"collectionName": "The Daily", "feedUrl": "https://feeds.simplecast.com/Sl5CSM3S"}
    ],
})


# --- genre tree ---------------------------------------------------------------


def test_parse_genres_walks_only_the_podcasts_root() -> None:
    genres = apple.parse_genres(_GENRES)
    assert [g.name for g in genres] == ["Arts", "Comedy"]  # Music is not a podcast genre
    assert genres[0].genre_id == "1301"


def test_parse_genres_keeps_nested_subgenres() -> None:
    arts = apple.parse_genres(_GENRES)[0]
    assert arts.has_children
    assert [(g.genre_id, g.name) for g in arts.subgenres] == [("1482", "Books"), ("1402", "Design")]
    assert not apple.parse_genres(_GENRES)[1].has_children


def test_parse_genres_tolerates_junk() -> None:
    assert apple.parse_genres("not json") == []
    assert apple.parse_genres("{}") == []
    assert apple.parse_genres(json.dumps({"26": "not a dict"})) == []


def test_genres_in_finds_a_node_at_any_depth() -> None:
    genres = apple.parse_genres(_GENRES)
    assert apple.genres_in(genres, "1482").name == "Books"
    assert apple.genres_in(genres, "1303").name == "Comedy"
    assert apple.genres_in(genres, "nope") is None


# --- charts -------------------------------------------------------------------


def test_parse_charts_reads_rows_and_drops_incomplete_ones() -> None:
    shows = apple.parse_charts(_CHARTS)
    assert [s.name for s in shows] == ["The Daily", "Arts Show"]
    assert shows[0].collection_id == "1200361736"
    assert shows[0].artist == "The New York Times"
    assert shows[0].display_name == "The Daily -- The New York Times"


def test_parse_charts_handles_apples_own_explict_spelling() -> None:
    # Apple's feed really does spell it "Explict"; a naive == "Explicit" misses.
    assert apple.parse_charts(_CHARTS)[0].explicit is True
    assert apple.parse_charts(_CHARTS)[1].explicit is False


def test_parse_charts_tolerates_junk() -> None:
    assert apple.parse_charts("not json") == []
    assert apple.parse_charts(json.dumps({"feed": {}})) == []


def test_a_chart_row_says_what_will_happen_before_activation() -> None:
    show = apple.parse_charts(_CHARTS)[0]
    assert "explicit" in show.spoken_note
    assert "opens its feed" in show.spoken_note


# --- feed resolution ----------------------------------------------------------


def test_parse_feed_url_extracts_the_rss_feed() -> None:
    assert apple.parse_feed_url(_LOOKUP) == "https://feeds.simplecast.com/Sl5CSM3S"


def test_parse_feed_url_is_empty_for_an_unknown_id_not_an_error() -> None:
    assert apple.parse_feed_url(json.dumps({"resultCount": 0, "results": []})) == ""
    assert apple.parse_feed_url("not json") == ""


def test_parse_show_details_carries_artwork_and_homepage() -> None:
    # What lets Subscribe hand Quill Cast a tile and a site link instead of a
    # bare title. Spellings mirror itunes_search: artworkUrl600 preferred,
    # homepage from collectionViewUrl.
    payload = json.dumps({
        "resultCount": 1,
        "results": [
            {
                "feedUrl": "https://feeds.example/daily",
                "artworkUrl100": "https://art.example/100.jpg",
                "artworkUrl600": "https://art.example/600.jpg",
                "collectionViewUrl": "https://podcasts.apple.com/us/podcast/id1",
            }
        ],
    })
    details = apple.parse_show_details(payload)
    assert details.feed_url == "https://feeds.example/daily"
    assert details.artwork_url == "https://art.example/600.jpg"
    assert details.homepage == "https://podcasts.apple.com/us/podcast/id1"
    # 100px fallback when 600 is absent; all-empty for junk, not an error.
    smaller = json.dumps({
        "results": [{"feedUrl": "https://f.example/x", "artworkUrl100": "https://art/1.jpg"}]
    })
    assert apple.parse_show_details(smaller).artwork_url == "https://art/1.jpg"
    assert apple.parse_show_details("not json") == apple.ShowDetails()


def test_resolve_feed_url_makes_one_request_then_caches(monkeypatch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        return _LOOKUP

    monkeypatch.setattr(apple, "_fetch", fake_fetch)
    assert apple.resolve_feed_url("1200361736") == "https://feeds.simplecast.com/Sl5CSM3S"
    assert apple.resolve_feed_url("1200361736") == "https://feeds.simplecast.com/Sl5CSM3S"
    assert len(calls) == 1, "activation must not re-pay for a lookup"
    assert "id=1200361736" in calls[0] and "entity=podcast" in calls[0]


def test_resolve_feed_url_makes_no_request_for_a_blank_id(monkeypatch) -> None:
    monkeypatch.setattr(
        apple, "_fetch", lambda url: (_ for _ in ()).throw(AssertionError("no request"))
    )
    assert apple.resolve_feed_url("  ") == ""


# --- browse wiring ------------------------------------------------------------


def test_fetch_genres_caches_between_opens(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(apple, "_fetch", lambda url: (calls.append(url), _GENRES)[1])
    first = apple.fetch_genres()
    second = apple.fetch_genres()
    assert [g.name for g in first] == [g.name for g in second] == ["Arts", "Comedy"]
    assert len(calls) == 1
    # ...and the nested shape survives the JSON round trip through the cache.
    assert [g.name for g in second[0].subgenres] == ["Books", "Design"]


def test_the_storefront_chart_is_whole_and_unfiltered(monkeypatch) -> None:
    monkeypatch.setattr(apple, "_fetch", lambda url: _CHARTS)
    assert [s.name for s in apple.fetch_charts("us")] == ["The Daily", "Arts Show"]


def test_fetch_charts_requests_the_right_storefront_and_row_count(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(apple, "_fetch", lambda url: (calls.append(url), _CHARTS)[1])
    apple.fetch_charts("ie", count=25)
    assert "/api/v2/ie/podcasts/top/25/podcasts.json" in calls[0]
    apple.fetch_charts("JP", count=9999)
    assert "/api/v2/jp/podcasts/top/100/podcasts.json" in calls[1]


def test_a_genre_asks_apple_for_that_genres_own_chart(monkeypatch) -> None:
    """The 2026-10-03 report: History had four shows and Comedy Fiction none.

    Both came from filtering the storefront's overall top 100 by genre. A genre
    folder now asks for the genre's own chart, 200 rows, and never touches the
    storefront chart or the genre tree to do it.
    """
    calls: list[str] = []
    monkeypatch.setattr(apple, "_fetch", lambda url: (calls.append(url), _GENRE_CHART)[1])

    shows = apple.fetch_charts("us", genre_id="1487")

    assert calls == ["https://itunes.apple.com/us/rss/toppodcasts/limit=200/genre=1487/json"]
    assert [s.name for s in shows] == [
        "The Team House",
        "The Rest Is History",
        "World War II with Tom Hanks",
    ]


def test_each_genre_is_its_own_request_and_each_is_cached(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(apple, "_fetch", lambda url: (calls.append(url), _GENRE_CHART)[1])
    apple.fetch_charts("us", genre_id="1483")  # Fiction
    apple.fetch_charts("us", genre_id="1486")  # Comedy Fiction, a subgenre
    apple.fetch_charts("us", genre_id="1486")
    apple.fetch_charts("gb", genre_id="1486")
    base = "https://itunes.apple.com/{}/rss/toppodcasts/limit=200/genre={}/json"
    assert calls == [
        base.format("us", "1483"),
        base.format("us", "1486"),
        base.format("gb", "1486"),
    ]


def test_storefront_name_falls_back_to_the_code() -> None:
    assert apple.storefront_name("ie") == "Ireland"
    assert apple.storefront_name("JP") == "Japan"
    assert apple.storefront_name("zz") == "ZZ"


def test_safe_mode_refuses_every_network_entry_point(monkeypatch) -> None:
    monkeypatch.setattr(
        apple, "_fetch", lambda url: (_ for _ in ()).throw(AssertionError("no request"))
    )
    with pytest.raises(apple.ApplePodcastsError):
        apple.refuse_in_safe_mode(True)
    with pytest.raises(apple.ApplePodcastsError):
        apple.fetch_genres(safe_mode=True)
    with pytest.raises(apple.ApplePodcastsError):
        apple.fetch_charts("us", safe_mode=True)
    with pytest.raises(apple.ApplePodcastsError):
        apple.resolve_feed_url("123", safe_mode=True)


def test_only_https_is_fetched() -> None:
    with pytest.raises(apple.ApplePodcastsError):
        apple._fetch("http://itunes.apple.com/lookup?id=1")


def test_no_podcast_index_dependency_anywhere_in_the_module() -> None:
    # Jeff's decision 2026-08-13: iTunes for everything, Podcast Index never.
    # A test rather than a comment, so "just add it as an option" fails loudly.
    from pathlib import Path

    source = Path(apple.__file__).read_text(encoding="utf-8").lower()
    assert "podcastindex.org" not in source
    assert "x-auth-key" not in source


def test_parse_genre_chart_reads_apples_per_genre_feed() -> None:
    from quill.core.podcasts import apple_genre_charts as charts

    shows = charts.parse_genre_chart(_GENRE_CHART)
    first = shows[0]
    assert first.collection_id == "1492797340"
    assert first.artist == "dee takos"
    assert first.genre_ids == ("1487",)
    assert first.artwork_url.endswith("170x170bb.png")
    assert first.page_url.startswith("https://podcasts.apple.com/us/podcast/the-team-house/")
    # The incomplete row and the repeated one are dropped, not raised on.
    assert len(shows) == 3


def test_parse_genre_chart_reads_a_one_row_chart_and_junk() -> None:
    from quill.core.podcasts import apple_genre_charts as charts

    one = json.loads(_GENRE_CHART)
    one["feed"]["entry"] = one["feed"]["entry"][0]  # Atom-as-JSON: a lone object
    assert [s.name for s in charts.parse_genre_chart(json.dumps(one))] == ["The Team House"]
    assert charts.parse_genre_chart(json.dumps({"feed": {}})) == []
    assert charts.parse_genre_chart("not json") == []
    assert charts.parse_genre_chart("[]") == []


def test_a_genre_chart_that_fails_is_recorded_not_raised(monkeypatch) -> None:
    from quill.core.radio import browse_failure

    def _down(url: str) -> str:
        raise apple.ApplePodcastsError("Could not reach Apple Podcasts") from TimeoutError()

    monkeypatch.setattr(apple, "_fetch", _down)
    browse_failure.LAST_FAILURE.clear()
    assert apple.fetch_charts("us", genre_id="1487") == []
    assert browse_failure.last_error_was_network()
