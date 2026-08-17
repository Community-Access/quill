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


def test_fetch_charts_filters_a_storefront_chart_by_genre(monkeypatch) -> None:
    monkeypatch.setattr(apple, "_fetch", lambda url: _CHARTS)
    assert [s.name for s in apple.fetch_charts("us")] == ["The Daily", "Arts Show"]
    assert [s.name for s in apple.fetch_charts("us", genre_id="1301")] == ["Arts Show"]
    assert apple.fetch_charts("us", genre_id="nope") == []


def test_fetch_charts_requests_the_right_storefront_and_row_count(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(apple, "_fetch", lambda url: (calls.append(url), _CHARTS)[1])
    apple.fetch_charts("ie", count=25)
    assert "/api/v2/ie/podcasts/top/25/podcasts.json" in calls[0]
    apple.fetch_charts("JP", count=9999)
    assert "/api/v2/jp/podcasts/top/100/podcasts.json" in calls[1]


def test_one_chart_request_serves_every_genre_in_a_storefront(monkeypatch) -> None:
    # The politeness point: filtering the storefront chart beats one request
    # per genre. The genre tree is fetched once too, and cached for a week.
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        return _GENRES if "MZStoreServices" in url else _CHARTS

    monkeypatch.setattr(apple, "_fetch", fake_fetch)
    apple.fetch_charts("us", genre_id="1301")
    apple.fetch_charts("us", genre_id="1303")
    apple.fetch_charts("us")
    chart_calls = [url for url in calls if "podcasts/top" in url]
    genre_calls = [url for url in calls if "MZStoreServices" in url]
    assert len(chart_calls) == 1, "one chart request must serve every genre"
    assert len(genre_calls) == 1, "the genre tree must be fetched once, then cached"


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


def test_genre_id_set_includes_descendants() -> None:
    arts = apple.parse_genres(_GENRES)[0]
    assert apple.genre_id_set(arts) == frozenset({"1301", "1482", "1402"})
    comedy = apple.parse_genres(_GENRES)[1]
    assert apple.genre_id_set(comedy) == frozenset({"1303"})


def test_filtering_by_a_top_level_genre_matches_rows_tagged_with_its_children(monkeypatch) -> None:
    # The bug the first live run found: a chart row carries its LEAF genre, so
    # matching a top-level id against raw row tags found nothing at all.
    charts = json.dumps({
        "feed": {
            "results": [
                {"id": "1", "name": "A Books Show", "genres": [{"genreId": "1482"}]},
                {"id": "2", "name": "A Comedy Show", "genres": [{"genreId": "1303"}]},
            ]
        }
    })

    def fake_fetch(url: str) -> str:
        return _GENRES if "genres" in url else charts

    monkeypatch.setattr(apple, "_fetch", fake_fetch)
    assert [s.name for s in apple.fetch_charts("us", genre_id="1301")] == ["A Books Show"]
    assert [s.name for s in apple.fetch_charts("us", genre_id="1482")] == ["A Books Show"]
    assert [s.name for s in apple.fetch_charts("us", genre_id="1303")] == ["A Comedy Show"]
