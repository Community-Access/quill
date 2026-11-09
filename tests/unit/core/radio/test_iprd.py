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


def test_a_slow_fetch_never_stalls_a_reader_that_has_a_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    rows = iprd.catalog()
    monkeypatch.setattr(iprd, "_memo", (time.monotonic() - 10_000, rows))
    assert iprd._fetch_lock.acquire(blocking=False), "as if another folder were fetching"
    try:
        started = time.monotonic()
        assert iprd.catalog() == rows, "the older copy, at once"
        assert time.monotonic() - started < 1.0
    finally:
        iprd._fetch_lock.release()


def test_callers_waiting_on_a_failed_fetch_do_not_each_fetch_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading

    calls: list[int] = []
    started = threading.Event()
    gate = threading.Event()

    def slow_and_down(key, fetch, **kw):
        calls.append(1)
        started.set()
        gate.wait(5)
        return kw["empty"], None

    monkeypatch.setattr(directory_cache, "resolve", slow_and_down)
    results: list[object] = []
    first = threading.Thread(target=lambda: results.append(iprd.catalog()))
    first.start()
    assert started.wait(5)
    second = threading.Thread(target=lambda: results.append(iprd.catalog()))
    second.start()
    second.join(0.2)
    gate.set()
    first.join(5)
    second.join(5)
    assert results == [[], []]
    assert len(calls) == 1, "the waiter shared the outcome instead of a second 30 s wait"


def test_a_packed_catalogue_is_inflated_only_up_to_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gzip

    monkeypatch.setattr(iprd, "_MAX_BYTES", 1000)
    assert iprd._inflate(gzip.compress(b"x" * 1000)) == b"x" * 1000
    with pytest.raises(iprd.IprdError):
        iprd._inflate(gzip.compress(b"x" * 100_000))


def test_odd_bitrates_and_shapes_are_skipped_not_raised() -> None:
    payload = {
        "stations": [
            {**_station(1), "streams": [{"url": "https://a.example/1", "bitrate": float("inf")}]},
            {**_station(2), "streams": [{"url": "https://a.example/2", "bitrate": float("nan")}]},
            {**_station(3), "streams": [{"url": "https://a.example/3", "bitrate": "128"}]},
            {**_station(4), "streams": 7, "genres": 3},
            {**_station(5), "genres": 9},
        ]
    }
    rows = iprd.trim_catalog(payload)
    assert [row[5] for row in rows] == [0, 0, 0, 128]
    assert rows[-1][3] == []
