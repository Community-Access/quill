import json

import pytest

from quill.core.radio import wxindex


def _fetcher(mapping):
    return lambda url: mapping[url]


def test_stations_for_state_uses_live_then_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    body = json.dumps([
        {"callsign": "KHB36", "frequency": "162.550", "feeds": [{"url": "https://s/khb36"}]}
    ])
    f = _fetcher({"https://api.wxindex.org/v1/states/virginia/stations": body})
    got = wxindex.stations_for_state("virginia", fetcher=f)
    assert got[0].callsign == "KHB36"
    assert (tmp_path / "state-virginia.json").is_file()  # cached


def test_stations_for_state_falls_back_to_cache_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    (tmp_path / "state-virginia.json").write_text(
        json.dumps([{"callsign": "KZZ99", "frequency": "162.400", "feeds": []}]),
        encoding="utf-8",
    )

    def boom(url):
        raise wxindex.WxIndexError("down")

    got = wxindex.stations_for_state("virginia", fetcher=boom, max_age_seconds=0)
    assert got[0].callsign == "KZZ99"  # served stale cache, no raise


def test_refresh_directory_writes_cache_and_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    f = _fetcher({
        "https://api.wxindex.org/v1/states": json.dumps([{"slug": "virginia", "name": "Virginia"}]),
        "https://api.wxindex.org/v1/stations/all-known": json.dumps([
            {"callsign": "KHB36", "frequency": "162.550", "feeds": []}
        ]),
    })
    res = wxindex.refresh_directory(fetcher=f)
    assert res.station_count == 1 and res.state_count == 1
    assert (tmp_path / "directory.json").is_file()


def test_safe_mode_refuses_live(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    with pytest.raises(wxindex.WxIndexError):
        wxindex.refresh_directory(safe_mode=True, fetcher=lambda url: "[]")


def test_playable_stations_for_state_reads_feeds_from_bundled_snapshot(monkeypatch, tmp_path):
    # No directory.json cache -> falls to the bundled snapshot, which carries
    # feeds (the per-state live endpoint does not, so browse must use this).
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    from quill.core.radio import wxindex_snapshot
    from quill.core.radio.wxindex_models import WxStation
    from quill.core.radio.wxindex_snapshot import Snapshot

    snap = Snapshot(
        stations=[
            WxStation("KHB36", 162.55, state="VA", feeds=("https://s/khb36",)),
            WxStation("KEC99", 162.40, state="VA", feeds=()),  # no feed -> excluded
            WxStation("WXL58", 162.55, state="MD", feeds=("https://s/wxl58",)),  # other state
        ]
    )
    monkeypatch.setattr(wxindex_snapshot, "load_snapshot", lambda: snap)
    monkeypatch.setattr(wxindex, "load_snapshot", lambda: snap)
    got = wxindex.playable_stations_for_state("VA")
    assert [s.callsign for s in got] == ["KHB36"]  # only VA with a feed


def test_playable_stations_for_state_prefers_fresh_directory_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    (tmp_path / "directory.json").write_text(
        json.dumps({
            "stations": [
                {
                    "callsign": "KHB36",
                    "frequency": "162.550",
                    "state_slug": "VA",
                    "feeds": [{"stream_url": "https://fresh/khb36"}],
                }
            ]
        }),
        encoding="utf-8",
    )
    got = wxindex.playable_stations_for_state("VA")
    assert len(got) == 1
    assert got[0].feeds == ("https://fresh/khb36",)


def test_states_with_playable_feeds_match_the_directory_not_the_live_count(monkeypatch) -> None:
    # Regression: NOAA state folders showed a live /v1/states count ("IL 9 items")
    # but expanding them yielded no stations, because the leaves come from the
    # directory tier. The folder count now comes from that same tier.
    from quill.core.radio.wxindex_models import WxState, WxStation

    stations = [
        WxStation("KHB01", 162.55, name="A", state="HI", feeds=("u1",)),
        WxStation("KHB02", 162.40, name="B", state="IL", feeds=("u2",)),
        WxStation("KHB03", 162.45, name="C", state="IL", feeds=("u3",)),
        WxStation("KHB04", 162.50, name="D", state="IL", feeds=()),  # no feed -> not counted
    ]
    monkeypatch.setattr(wxindex, "_directory_stations", lambda **_k: stations)
    monkeypatch.setattr(
        wxindex,
        "list_states",
        lambda **_k: [
            WxState(slug="HI", name="Hawaii", stations_with_feeds=99),  # inflated live count
            WxState(slug="IL", name="Illinois", stations_with_feeds=99),
        ],
    )
    folders = {f.slug: f for f in wxindex.states_with_playable_feeds()}
    assert folders["hi"].stations_with_feeds == 1
    assert folders["il"].stations_with_feeds == 2  # not 99, and not 3 (D has no feed)
    assert folders["hi"].name == "Hawaii"
    # The count equals exactly what expanding the folder will show.
    assert len(wxindex.playable_stations_for_state("IL")) == folders["il"].stations_with_feeds


def test_directory_cache_is_bypassed_when_bundled_snapshot_is_newer(monkeypatch, tmp_path):
    # #1207: after an in-place update, a newer bundled snapshot must win over a
    # still-"fresh" cache written by the previous version, which otherwise keeps
    # shadowing the new listings.
    from quill.core.radio import wxindex_snapshot
    from quill.core.radio.wxindex_models import WxStation
    from quill.core.radio.wxindex_snapshot import Snapshot

    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    (tmp_path / "directory.json").write_text(
        json.dumps({
            "generated_at": "2026-06-01T00:00:00Z",
            "stations": [
                {
                    "callsign": "OLD11",
                    "frequency": "162.400",
                    "state_slug": "VA",
                    "feeds": [{"stream_url": "https://old/11"}],
                }
            ],
        }),
        encoding="utf-8",
    )
    newer_snap = Snapshot(
        generated_at="2026-07-20T00:00:00Z",
        stations=[WxStation("NEW22", 162.55, state="VA", feeds=("https://new/22",))],
    )
    monkeypatch.setattr(wxindex_snapshot, "load_snapshot", lambda: newer_snap)
    monkeypatch.setattr(wxindex, "load_snapshot", lambda: newer_snap)
    got = wxindex.playable_stations_for_state("VA")
    assert [s.callsign for s in got] == ["NEW22"]  # snapshot wins over stale cache


def test_directory_cache_wins_when_it_is_newer_than_the_snapshot(monkeypatch, tmp_path):
    # The inverse: a cache freshly refreshed by the user (newer than the bundled
    # snapshot) is still preferred -- we only reject a cache the snapshot beats.
    from quill.core.radio import wxindex_snapshot
    from quill.core.radio.wxindex_models import WxStation
    from quill.core.radio.wxindex_snapshot import Snapshot

    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    (tmp_path / "directory.json").write_text(
        json.dumps({
            "generated_at": "2026-07-25T00:00:00Z",
            "stations": [
                {
                    "callsign": "FRESH9",
                    "frequency": "162.400",
                    "state_slug": "VA",
                    "feeds": [{"stream_url": "https://fresh/9"}],
                }
            ],
        }),
        encoding="utf-8",
    )
    older_snap = Snapshot(
        generated_at="2026-07-20T00:00:00Z",
        stations=[WxStation("BUNDLED", 162.55, state="VA", feeds=("https://b/1",))],
    )
    monkeypatch.setattr(wxindex_snapshot, "load_snapshot", lambda: older_snap)
    monkeypatch.setattr(wxindex, "load_snapshot", lambda: older_snap)
    got = wxindex.playable_stations_for_state("VA")
    assert [s.callsign for s in got] == ["FRESH9"]  # user's fresher cache wins
