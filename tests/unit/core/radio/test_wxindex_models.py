from quill.core.radio.wxindex_models import (
    parse_states,
    parse_stations,
    to_radio_station,
)

_STATION_JSON = {
    "callsign": "KHB36",
    "frequency": "162.550",
    "name": "Manassas",
    "state": "VA",
    "wfo": "LWX",
    "latitude": 38.75,
    "longitude": -77.48,
    "counties": ["Prince William, VA"],
    "same": ["051153"],
    "feeds": [{"url": "https://stream.example/khb36"}],
}


def test_parse_stations_builds_wxstation():
    [s] = parse_stations([_STATION_JSON])
    assert s.callsign == "KHB36"
    assert s.frequency_mhz == 162.55
    assert s.same_codes == ("051153",)
    assert s.feeds == ("https://stream.example/khb36",)


def test_parse_states_reads_counts():
    [st] = parse_states([{"slug": "virginia", "name": "Virginia", "station_count": 42}])
    assert (st.slug, st.name, st.station_count) == ("virginia", "Virginia", 42)


def test_to_radio_station_maps_playable_fields():
    rs = to_radio_station(parse_stations([_STATION_JSON])[0])
    assert rs.stream_url == "https://stream.example/khb36"
    assert rs.source == "NOAA Weather Radio"
    assert "KHB36" in rs.name and "162.55" in rs.name
