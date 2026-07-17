"""Tests for the TuneIn/iHeart search-blend helpers (no network; the underlying
directory clients are monkeypatched)."""

from __future__ import annotations

import quill.core.radio.directory_search as ds
from quill.core.radio.iheart import IHeartStation
from quill.core.radio.tunein import TuneInResult


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
