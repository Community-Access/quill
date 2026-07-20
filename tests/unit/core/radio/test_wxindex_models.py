from quill.core.radio.wxindex_models import (
    parse_states,
    parse_stations,
    to_radio_station,
)

_STATION_JSON = {
    "callsign": "KHB36",
    "frequency": "162.550",
    "city": "Manassas",
    "state_slug": "VA",
    "state_name": "Virginia",
    "wfo": "Sterling VA",
    "wfo_code": "LWX",
    "latitude": 38.75,
    "longitude": -77.48,
    "counties": ["Prince William, VA"],
    "same": ["051153"],
    "feeds": [
        {
            "label": "Primary",
            "source_name": "Example",
            "stream_url": "https://stream.example/khb36",
        }
    ],
}


def test_parse_stations_builds_wxstation():
    [s] = parse_stations([_STATION_JSON])
    assert s.callsign == "KHB36"
    assert s.frequency_mhz == 162.55
    assert s.name == "Manassas"
    assert s.state == "VA"
    assert s.wfo == "LWX"
    assert s.same_codes == ("051153",)
    assert s.feeds == ("https://stream.example/khb36",)


def test_parse_states_reads_counts():
    [st] = parse_states([{"state_slug": "VA", "state_name": "Virginia", "station_count": 42}])
    assert (st.slug, st.name, st.station_count) == ("VA", "Virginia", 42)


def test_to_radio_station_maps_playable_fields():
    rs = to_radio_station(parse_stations([_STATION_JSON])[0])
    assert rs.stream_url == "https://stream.example/khb36"
    assert rs.source == "NOAA Weather Radio"
    assert "KHB36" in rs.name and "162.55" in rs.name


def test_committed_snapshot_parses_real_stations():
    from quill.core.radio.wxindex_snapshot import load_snapshot

    snap = load_snapshot()
    assert len(snap.states) >= 50
    playable = [s for s in snap.stations if s.feeds]
    assert len(playable) >= 100  # ~144 have feeds
    assert all(p.feeds[0].startswith("http") for p in playable[:5])
