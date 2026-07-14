"""Sanity checks for the bundled ACB Media station list (pure; no network)."""

from __future__ import annotations

from quill.core.radio.acb_media import acb_media_stations


def test_returns_ten_stations_with_unique_names_and_https_urls() -> None:
    stations = acb_media_stations()
    assert len(stations) == 10
    names = [s.name for s in stations]
    assert len(set(names)) == 10
    assert names[0] == "ACB Media 1"
    for station in stations:
        assert station.stream_url.startswith("https://streaming.live365.com/")
        assert station.homepage.startswith("https://")
        assert "ACB Media" in station.tags
