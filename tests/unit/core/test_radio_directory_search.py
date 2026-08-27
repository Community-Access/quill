"""Tests for the TuneIn/iHeart/NOAA search-blend helpers (no network; the
underlying directory clients are monkeypatched)."""

from __future__ import annotations

import quill.core.radio.directory_search as ds
from quill.core.radio.iheart import IHeartStation
from quill.core.radio.models import RadioStation
from quill.core.radio.tunein import TuneInResult
from quill.core.radio.wxindex_models import WxStation


def _rs(name: str, url: str, *, country: str = "", source: str = "") -> RadioStation:
    return RadioStation(name=name, stream_url=url, country=country, source=source)


def test_merge_and_rank_dedupes_by_stream_url_first_source_wins() -> None:
    a = [_rs("Jazz FM", "https://s/jazz", source="RadioBrowser")]
    b = [_rs("Jazz FM Copy", "https://s/jazz", source="iHeart")]  # same URL
    merged = ds.merge_and_rank([a, b])
    assert len(merged) == 1
    assert merged[0].source == "RadioBrowser"  # first list wins


def test_merge_and_rank_dedupes_by_name_and_country() -> None:
    a = [_rs("KEXP", "https://a/kexp", country="United States")]
    b = [_rs("kexp", "https://b/kexp", country="United States")]  # same name+country
    c = [_rs("KEXP", "https://c/kexp", country="Canada")]  # different country -> kept
    merged = ds.merge_and_rank([a, b, c])
    assert len(merged) == 2
    assert {s.country for s in merged} == {"United States", "Canada"}


def test_merge_and_rank_absorbs_dropped_duplicate_source() -> None:
    # RadioBrowser lists SomaFM channels itself (source=""), and the SomaFM
    # client returns the same stream URL (source="SomaFM"). The dup is dropped,
    # but the survivor must remember it came from SomaFM too, so the Source
    # filter can still show it under SomaFM.
    rb = [_rs("Groove Salad", "https://ice/gsalad", source="")]
    soma = [_rs("Groove Salad", "https://ice/gsalad", source="SomaFM")]
    merged = ds.merge_and_rank([rb, soma])
    assert len(merged) == 1
    assert ds.station_source_labels(merged[0]) == {"Radio Browser", "SomaFM"}


def test_station_source_labels_defaults_and_maps_blank_to_radio_browser() -> None:
    plain = _rs("KEXP", "https://a", source="")
    assert ds.station_source_labels(plain) == {"Radio Browser"}
    labelled = _rs("WRBH", "https://b", source="Radio Reading Service")
    assert ds.station_source_labels(labelled) == {"Radio Reading Service"}


def test_merge_and_rank_absorbs_name_country_duplicate_source() -> None:
    # Same station, different mount URL (so URL dedup misses) but same
    # name+country: the survivor still absorbs the dropped source.
    a = [_rs("Jazz FM", "https://a/jazz", country="UK", source="")]
    b = [_rs("Jazz FM", "https://b/jazz", country="UK", source="TuneIn")]
    merged = ds.merge_and_rank([a, b])
    assert len(merged) == 1
    assert ds.station_source_labels(merged[0]) == {"Radio Browser", "TuneIn"}


def test_merge_and_rank_floats_exact_name_matches_first() -> None:
    lists = [
        [_rs("Jazz FM Classics", "https://a")],
        [_rs("Jazz FM", "https://b")],  # exact match for the query
        [_rs("Smooth Jazz FM", "https://c")],
    ]
    merged = ds.merge_and_rank(lists, query="jazz fm")
    assert merged[0].name == "Jazz FM"
    # the rest keep their merged order beneath the exact hit
    assert [s.name for s in merged[1:]] == ["Jazz FM Classics", "Smooth Jazz FM"]


def test_merge_and_rank_empty_query_just_dedupes_in_order() -> None:
    lists = [[_rs("A", "https://a")], [_rs("B", "https://b")], [_rs("A", "https://a")]]
    merged = ds.merge_and_rank(lists)
    assert [s.name for s in merged] == ["A", "B"]


def test_tunein_search_resolves_and_stamps_source(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.tunein,
        "search",
        lambda q, *, safe_mode=False: [
            TuneInResult(guide_id="s1", title="BBC Radio 1", is_station=True),
            TuneInResult(guide_id="c9", title="A Category", is_station=False),
            TuneInResult(guide_id="s2", title="No Stream", is_station=True),
        ],
    )

    def fake_resolve(guide_id, *, safe_mode=False):
        return ["https://cdn/one.m3u8"] if guide_id == "s1" else []

    monkeypatch.setattr(ds.tunein, "resolve_station_streams", fake_resolve)
    stations = ds.tunein_search_stations("bbc")
    # The category is skipped and the stream-less station is dropped.
    assert [s.name for s in stations] == ["BBC Radio 1"]
    assert stations[0].source == "TuneIn"
    assert stations[0].stream_url == "https://cdn/one.m3u8"


def test_tunein_search_respects_cap(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.tunein,
        "search",
        lambda q, *, safe_mode=False: [
            TuneInResult(guide_id=f"s{i}", title=f"S{i}", is_station=True) for i in range(10)
        ],
    )
    monkeypatch.setattr(
        ds.tunein, "resolve_station_streams", lambda gid, *, safe_mode=False: ["https://x"]
    )
    assert len(ds.tunein_search_stations("x", cap=3)) == 3


def test_tunein_search_swallows_errors(monkeypatch) -> None:
    def boom(*a, **k):
        raise ds.tunein.TuneInError("offline")

    monkeypatch.setattr(ds.tunein, "search", boom)
    assert ds.tunein_search_stations("x") == []
    assert ds.tunein_search_stations("   ") == []  # empty query, no call


def _index() -> list[IHeartStation]:
    return [
        IHeartStation("4846", "Delilah", "delilah", "https://iheart/live/delilah-4846/"),
        IHeartStation("2804", "973 KBCO", "973-kbco", "https://iheart/live/973-kbco-2804/"),
        IHeartStation("93", "Delight FM", "delight-fm", "https://iheart/live/delight-fm-93/"),
    ]


def test_iheart_search_filters_by_name_and_resolves(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.iheart,
        "resolve_stream",
        lambda url, *, safe_mode=False: f"https://revma/{url.rsplit('-', 1)[-1]}hls.m3u8",
    )
    stations = ds.iheart_search_stations(_index(), "del")  # matches Delilah + Delight FM
    names = [s.name for s in stations]
    assert names == ["Delilah", "Delight FM"]
    assert all(s.source == "iHeart" for s in stations)
    assert stations[0].station_uuid == "iheart:4846"


def test_iheart_search_matches_punctuation_and_id(monkeypatch) -> None:
    # Issue #1156: slug "1031-austin" -> name "1031 Austin"; a search for the
    # branded "103.1 Austin" (with the dot) or the bare station id must find it.
    index = [
        IHeartStation("8403", "1031 Austin", "1031-austin", "https://iheart/live/1031-austin-8403/")
    ]
    monkeypatch.setattr(ds.iheart, "resolve_stream", lambda url, *, safe_mode=False: "https://x")
    for query in ("103.1 Austin", "1031 austin", "8403", "austin"):
        assert [s.name for s in ds.iheart_search_stations(index, query)] == ["1031 Austin"], query
    # A query that shares no token is still rejected.
    assert ds.iheart_search_stations(index, "seattle") == []


def test_iheart_search_respects_cap_and_skips_unresolvable(monkeypatch) -> None:
    def resolve(url, *, safe_mode=False):
        return "" if "delilah" in url else "https://revma/x.m3u8"

    monkeypatch.setattr(ds.iheart, "resolve_stream", resolve)
    # "del" matches Delilah (unresolvable -> dropped) and Delight FM (kept).
    stations = ds.iheart_search_stations(_index(), "del")
    assert [s.name for s in stations] == ["Delight FM"]


def test_iheart_search_empty_name_returns_nothing(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.iheart,
        "resolve_stream",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no resolve")),
    )
    assert ds.iheart_search_stations(_index(), "  ") == []


def test_iheart_search_swallows_resolve_errors(monkeypatch) -> None:
    def boom(url, *, safe_mode=False):
        raise ds.iheart.IHeartError("offline")

    monkeypatch.setattr(ds.iheart, "resolve_stream", boom)
    assert ds.iheart_search_stations(_index(), "del") == []


def test_wxindex_search_adapts_and_stamps_source(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.wxindex,
        "search_stations",
        lambda q, *, safe_mode=False: [
            WxStation("KHB36", 162.55, name="Springfield", feeds=("https://noaa/khb36",))
        ],
    )
    stations = ds.wxindex_search_stations("051153")
    assert len(stations) == 1
    assert stations[0].source == "NOAA Weather Radio"
    assert stations[0].stream_url == "https://noaa/khb36"


def test_wxindex_search_drops_stations_without_feeds(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.wxindex,
        "search_stations",
        lambda q, *, safe_mode=False: [
            WxStation("KHB36", 162.55, feeds=("https://noaa/khb36",)),
            WxStation("WXL99", 162.40, feeds=()),  # no live feed -> nothing playable
        ],
    )
    stations = ds.wxindex_search_stations("wa")
    assert [s.station_uuid for s in stations] == ["wxindex:KHB36"]


def test_wxindex_search_empty_query_returns_nothing(monkeypatch) -> None:
    monkeypatch.setattr(
        ds.wxindex,
        "search_stations",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no call")),
    )
    assert ds.wxindex_search_stations("   ") == []


def test_wxindex_search_swallows_errors(monkeypatch) -> None:
    def boom(q, *, safe_mode=False):
        raise ds.wxindex.WxIndexError("offline")

    monkeypatch.setattr(ds.wxindex, "search_stations", boom)
    assert ds.wxindex_search_stations("051153") == []


# --- the resolution that made search slow now happens all at once ------------
# Reported 2026-08-26: "search is still way too slow, can this not be explored
# further to make it lightning fast?"


def test_tunein_resolves_its_results_at_the_same_time_not_one_by_one() -> None:
    """Ten round trips end to end is ten times the slowest thing on the network."""
    import threading

    from quill.core.radio import directory_search, tunein

    class _Result:
        is_station = True

        def __init__(self, guide_id: str) -> None:
            self.guide_id = guide_id

    results = [_Result(f"s{i}") for i in range(6)]
    in_flight = threading.Semaphore(0)
    hold = threading.Event()

    def _resolve(guide_id, *, safe_mode=False):  # noqa: ARG001
        in_flight.release()
        assert hold.wait(5)
        return ["https://a.example/stream"]

    originals = (tunein.search, tunein.resolve_station_streams, tunein.to_radio_station)
    tunein.search = lambda _q, **_kw: results
    tunein.resolve_station_streams = _resolve
    tunein.to_radio_station = lambda _r, url: RadioStation(name="X", stream_url=url)
    try:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as runner:
            future = runner.submit(directory_search.tunein_search_stations, "jazz")
            # Every result must be in flight before any is allowed to finish;
            # a sequential loop cannot satisfy this and the test times out.
            for _ in results:
                assert in_flight.acquire(timeout=5)
            hold.set()
            rows = future.result(timeout=10)
    finally:
        hold.set()
        tunein.search, tunein.resolve_station_streams, tunein.to_radio_station = originals

    assert len(rows) == len(results)


def test_iheart_resolves_its_matches_at_the_same_time_too() -> None:
    import threading

    from quill.core.radio import directory_search, iheart

    class _Station:
        def __init__(self, page_url: str) -> None:
            self.page_url = page_url

    index = [_Station(f"https://a.example/{i}") for i in range(5)]
    in_flight = threading.Semaphore(0)
    hold = threading.Event()

    def _resolve(page_url, *, safe_mode=False):  # noqa: ARG001
        in_flight.release()
        assert hold.wait(5)
        return "https://a.example/stream"

    originals = (iheart.station_matches, iheart.resolve_stream, iheart.to_radio_station)
    iheart.station_matches = lambda _s, _n: True
    iheart.resolve_stream = _resolve
    iheart.to_radio_station = lambda _s, url: RadioStation(name="X", stream_url=url)
    try:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as runner:
            future = runner.submit(directory_search.iheart_search_stations, index, "kiss")
            for _ in index:
                assert in_flight.acquire(timeout=5)
            hold.set()
            rows = future.result(timeout=10)
    finally:
        hold.set()
        iheart.station_matches, iheart.resolve_stream, iheart.to_radio_station = originals

    assert len(rows) == len(index)


def test_one_result_needs_no_pool_at_all() -> None:
    from quill.core.radio import directory_search

    assert directory_search._in_parallel(lambda x: x * 2, [21]) == [42]
    assert directory_search._in_parallel(lambda x: x, []) == []


def test_a_resolver_that_raises_never_reaches_the_caller() -> None:
    from quill.core.radio import directory_search

    def _boom(_item):
        raise RuntimeError("no")

    assert directory_search._in_parallel(_boom, [1]) == []
