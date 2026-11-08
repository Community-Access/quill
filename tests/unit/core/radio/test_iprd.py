"""IPRD, the open public radio directory: parsing, the branch, paging, search.

Every test serves a small hand-made catalogue through ``iprd._fetch``; nothing
reaches the network, and the day-long cache is bypassed.
"""

from __future__ import annotations

import pytest

from quill.core.radio import (
    browse_sources,
    browse_visibility,
    directory_cache,
    iprd,
    search_sources,
)


def _station(n: int, *, country: str = "Ireland", genres=("Pop",), url: str = "") -> dict:
    return {
        "id": f"s{n}",
        "name": f"Station {n:03d}",
        "country": country,
        "language": [],
        "genres": list(genres),
        "website": f"https://example.org/{n}",
        "streams": [{"url": url or f"https://stream.example/{n}", "format": "MP3", "bitrate": 128}],
    }


CATALOG = {
    "version": "1",
    "stations": [
        _station(1, genres=("Pop", "pop", "Rock")),
        _station(2, country="Andorra", genres=("Hits",)),
        # Two streams: the HTTPS one is kept although it is listed second.
        {
            **_station(3, country="Andorra"),
            "streams": [
                {"url": "http://plain.example/3", "format": "Unknown", "bitrate": 0},
                {"url": "https://secure.example/3", "format": "aac", "bitrate": 64},
            ],
        },
        # A duplicate stream, a station with no name, one with nothing playable.
        _station(4, url="https://stream.example/1"),
        {**_station(5), "name": "  "},
        {**_station(6), "streams": [{"url": "rtsp://nope/6"}]},
    ],
}


@pytest.fixture(autouse=True)
def _served(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    def fetch() -> object:
        calls.append(1)
        return CATALOG

    monkeypatch.setattr(iprd, "_fetch", fetch)
    monkeypatch.setattr(
        directory_cache, "resolve", lambda key, fetch, **kw: (fetch() or kw.get("empty"), None)
    )
    iprd.forget_memo()
    yield calls
    iprd.forget_memo()


def test_trimming_keeps_one_playable_stream_per_station() -> None:
    rows = iprd.trim_catalog(CATALOG)
    assert [r[0] for r in rows] == ["Station 001", "Station 002", "Station 003"]
    assert rows[0][3] == ["pop", "rock"], "genres fold case and repeat once"
    assert rows[2][1] == "https://secure.example/3" and rows[2][4] == "AAC" and rows[2][5] == 64
    assert iprd.trim_catalog({"stations": "nonsense"}) == []
    assert iprd.trim_catalog(None) == []


def test_a_station_plays_and_carries_its_genres() -> None:
    station = iprd.to_station(iprd.catalog()[0])
    assert station.stream_url == "https://stream.example/1"
    assert station.source == "IPRD" and station.country == "Ireland"
    assert station.tags == ("Pop", "Rock") and station.bitrate_kbps == 128


def test_the_branch_offers_countries_and_genres_with_counts() -> None:
    root = browse_sources.browse("iprd")
    assert [n.label for n in root] == ["By Country", "By Genre"]
    countries = browse_sources.browse("iprdcountries")
    assert [(n.label, n.child_count) for n in countries] == [("Andorra", 2), ("Ireland", 1)]
    genres = browse_sources.browse("iprdgenres")
    assert {n.label for n in genres} == {"Hits", "Pop", "Rock"}


def test_a_country_lists_its_stations_without_repeating_the_country() -> None:
    rows = browse_sources.browse("iprdcountry:Andorra")
    assert [r.label for r in rows] == ["Station 002", "Station 003"]
    assert all(r.is_leaf for r in rows)


def test_a_long_list_pages_a_hundred_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    big = {"stations": [_station(n, country="Chile") for n in range(1, 251)]}
    monkeypatch.setattr(iprd, "_fetch", lambda: big)
    iprd.forget_memo()
    first = browse_sources.browse("iprdcountry:Chile")
    assert len(first) == 101 and first[-1].label == "More..."
    assert first[-1].note == "showing 100 of 250"
    second = browse_sources.browse(first[-1].node_id)
    assert second[0].label == "Station 101" and second[-1].note == "showing 200 of 250"
    third = browse_sources.browse(second[-1].node_id)
    assert len(third) == 50 and all(r.is_leaf for r in third)


def test_the_catalogue_is_fetched_once_for_many_folders(_served: list[int]) -> None:
    browse_sources.browse("iprdcountries")
    browse_sources.browse("iprdgenres")
    browse_sources.browse("iprdcountry:Andorra")
    assert len(_served) == 1


def test_opening_the_root_fetches_nothing(_served: list[int]) -> None:
    browse_sources.browse("iprd")
    assert _served == []


def test_search_matches_every_word_and_survives_an_outage(monkeypatch) -> None:
    assert [s.name for s in iprd.search_stations("station 002")] == ["Station 002"]
    assert iprd.search_stations("   ") == []

    def down() -> object:
        raise iprd.IprdError("down")

    monkeypatch.setattr(iprd, "_fetch", down)
    monkeypatch.setattr(directory_cache, "resolve", lambda key, fetch, **kw: (kw["empty"], None))
    iprd.forget_memo()
    assert iprd.search_stations("station") == []


def test_safe_mode_refuses_out_loud() -> None:
    with pytest.raises(iprd.IprdError):
        iprd.catalog(safe_mode=True)
    assert browse_sources.needs_network("iprd")
    assert browse_sources.browse("iprdcountries", safe_mode=True) == []


def test_only_the_published_catalogue_is_ever_named() -> None:
    assert iprd.CATALOG_URL == ("https://iprd-org.github.io/iprd/site_data/metadata/catalog.json")


def test_the_branch_and_search_reach_existing_profiles() -> None:
    assert ("iprd",) in browse_visibility.INTRODUCED_BY_EPOCH.values()
    assert browse_visibility.SOURCES_EPOCH == max(browse_visibility.INTRODUCED_BY_EPOCH)
    assert ("iprd", "networks") in search_sources.INTRODUCED_BY_EPOCH.values()
    assert search_sources.SEARCH_SOURCES_EPOCH == max(search_sources.INTRODUCED_BY_EPOCH)
    assert dict(browse_sources.ROOT_SOURCES)["iprd"] == "IPRD (Public Radio Directory)"
