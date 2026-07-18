"""Tests for the TuneIn/iHeart search-blend helpers (no network; the underlying
directory clients are monkeypatched)."""

from __future__ import annotations

import quill.core.radio.directory_search as ds
from quill.core.radio.iheart import IHeartStation
from quill.core.radio.models import RadioStation
from quill.core.radio.tunein import TuneInResult


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
