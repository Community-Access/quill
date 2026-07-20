import json

from quill.core.radio import reading_services as rs


def test_load_reading_services_reads_one_service(tmp_path, monkeypatch):
    doc = {
        "generated_at": "",
        "services": [
            {
                "name": "WRBH",
                "stream_url": "https://s/wrbh",
                "state": "Louisiana",
                "station_uuid": "abc-123",
                "homepage": "https://wrbh.org/",
                "codec": "MP3",
            }
        ],
    }
    path = tmp_path / "reading_services.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(rs, "reading_services_path", lambda: path)

    stations = rs.load_reading_services()

    assert len(stations) == 1
    assert stations[0].source == "Radio Reading Service"
    assert stations[0].stream_url == "https://s/wrbh"


def test_load_reading_services_missing_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "reading_services_path", lambda: tmp_path / "nope.json")
    assert rs.load_reading_services() == []


def test_load_reading_services_bundled_snapshot():
    stations = rs.load_reading_services()
    assert len(stations) >= 15
    for station in stations:
        assert station.stream_url
        assert station.source == "Radio Reading Service"


def test_load_reading_services_includes_state_in_tags():
    """Verify that state names from the bundled snapshot are in station tags."""
    stations = rs.load_reading_services()
    assert any("Michigan" in s.tags for s in stations)
