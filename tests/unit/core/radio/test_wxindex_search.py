import json

from quill.core.radio import wxindex


def test_search_routes_same_code():
    seen = {}

    def f(url):
        seen["url"] = url
        return json.dumps([{"callsign": "KHB36", "frequency": "162.550", "feeds": []}])

    out = wxindex.search_stations("051153", fetcher=f)
    assert "same=051153" in seen["url"] and out[0].callsign == "KHB36"


def test_search_routes_callsign():
    seen = {}

    def f(url):
        seen["url"] = url
        return json.dumps({"callsign": "KHB36", "frequency": "162.550", "feeds": []})

    out = wxindex.search_stations("KHB36", fetcher=f)
    assert "/v1/stations/KHB36" in seen["url"] and out[0].callsign == "KHB36"


def test_search_routes_county_state():
    seen = {}

    def f(url):
        seen["url"] = url
        return json.dumps([{"callsign": "KHB36", "frequency": "162.550", "feeds": []}])

    out = wxindex.search_stations("Fairfax, VA", fetcher=f)
    assert "c=Fairfax" in seen["url"] and "s=VA" in seen["url"] and out[0].callsign == "KHB36"


def test_search_routes_free_text_to_state_query():
    seen = {}

    def f(url):
        seen["url"] = url
        return json.dumps([{"callsign": "KHB36", "frequency": "162.550", "feeds": []}])

    out = wxindex.search_stations("virginia", fetcher=f)
    assert "s=virginia" in seen["url"] and out[0].callsign == "KHB36"


def test_search_empty_query_returns_empty():
    assert wxindex.search_stations("   ") == []


def test_search_falls_back_to_snapshot_on_failure(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap
    from quill.core.radio.wxindex_models import WxStation

    monkeypatch.setattr(
        wxindex,
        "load_snapshot",
        lambda: snap.Snapshot(stations=[WxStation("KHB36", 162.55, state="VA")]),
    )

    def boom(url):
        raise wxindex.WxIndexError("down")

    out = wxindex.search_stations("khb36", fetcher=boom)
    assert out[0].callsign == "KHB36"


def test_station_detail_returns_station():
    def f(url):
        return json.dumps({"callsign": "KHB36", "frequency": "162.550", "feeds": []})

    got = wxindex.station_detail("KHB36", fetcher=f)
    assert got is not None and got.callsign == "KHB36"


def test_station_detail_falls_back_to_snapshot(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap
    from quill.core.radio.wxindex_models import WxStation

    monkeypatch.setattr(
        wxindex,
        "load_snapshot",
        lambda: snap.Snapshot(stations=[WxStation("KHB36", 162.55, state="VA")]),
    )

    def boom(url):
        raise wxindex.WxIndexError("down")

    got = wxindex.station_detail("khb36", fetcher=boom)
    assert got is not None and got.callsign == "KHB36"


def test_station_detail_unknown_returns_none(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap

    monkeypatch.setattr(wxindex, "load_snapshot", lambda: snap.Snapshot(stations=[]))

    def boom(url):
        raise wxindex.WxIndexError("down")

    assert wxindex.station_detail("ZZZ99", fetcher=boom) is None


def test_local_stations_nearest_by_coordinate(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap
    from quill.core.radio.wxindex_models import WxStation

    monkeypatch.setattr(
        wxindex,
        "load_snapshot",
        lambda: snap.Snapshot(
            stations=[
                WxStation("A", 162.4, latitude=38.0, longitude=-77.0),
                WxStation("B", 162.5, latitude=48.0, longitude=-100.0),
            ]
        ),
    )
    got = wxindex.local_stations(38.1, -77.1)  # no network; snapshot fallback
    assert got[0].callsign == "A"


def test_local_stations_county_match_first(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap
    from quill.core.radio.wxindex_models import WxStation

    monkeypatch.setattr(
        wxindex,
        "load_snapshot",
        lambda: snap.Snapshot(
            stations=[
                WxStation("A", 162.4, latitude=38.0, longitude=-77.0),
                WxStation("B", 162.5, latitude=48.0, longitude=-100.0),
            ]
        ),
    )

    def f(url):
        return json.dumps([{"callsign": "B", "frequency": "162.500", "feeds": []}])

    got = wxindex.local_stations(38.0, -77.0, county="Some County, ND", fetcher=f)
    assert got[0].callsign == "B"
