"""NOAA Weather Radio resolver used by the Weather menu's "Listen to your
Local NOAA Weather Radio" command (task 8): a pure, wx-free adapter over
``wxindex.local_stations`` -> ``to_radio_station``, testable with no wx and
no network."""

from __future__ import annotations

from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import WxStation, local_noaa_radio_station


def test_local_noaa_station_for_location(monkeypatch):
    monkeypatch.setattr(
        wxindex,
        "local_stations",
        lambda lat, lon, county="", **k: [WxStation("KHB36", 162.55, feeds=("https://s/k",))],
    )
    rs = local_noaa_radio_station(latitude=38.75, longitude=-77.48, county="Prince William, VA")
    assert rs is not None
    assert rs.source == "NOAA Weather Radio"
    assert rs.stream_url == "https://s/k"
    assert "KHB36" in rs.name


def test_local_noaa_none_when_no_stations(monkeypatch):
    monkeypatch.setattr(wxindex, "local_stations", lambda *a, **k: [])
    assert local_noaa_radio_station(latitude=0.0, longitude=0.0) is None
