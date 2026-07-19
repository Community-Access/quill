from __future__ import annotations

from quill.core.radio.nfb_media import CATEGORY_LABEL, nfb_media_stations


def test_nfb_media_stations_returns_the_nfbrn_stream() -> None:
    stations = nfb_media_stations()
    assert len(stations) == 1
    station = stations[0]
    assert "NFBRN" in station.name
    assert station.stream_url == "http://cast.az-streamingserver.com:8590/live"
    assert CATEGORY_LABEL in station.tags
    assert station.country == "United States"
    assert station.codec == "MP3"
    assert station.homepage.startswith("https://nfb.org")
