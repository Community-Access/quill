import json

from quill.core.radio import wxindex_snapshot as snap


def test_load_snapshot_reads_states_and_stations(tmp_path, monkeypatch):
    doc = {
        "generated_at": "2026-07-19T00:00:00Z",
        "states": [{"slug": "virginia", "name": "Virginia", "station_count": 1}],
        "stations": [
            {"callsign": "KHB36", "frequency": "162.550", "feeds": [{"url": "https://s/khb36"}]}
        ],
    }
    path = tmp_path / "noaa_directory.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(snap, "snapshot_path", lambda: path)
    s = snap.load_snapshot()
    assert s.states[0].slug == "virginia"
    assert s.stations[0].callsign == "KHB36"


def test_load_snapshot_missing_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(snap, "snapshot_path", lambda: tmp_path / "nope.json")
    s = snap.load_snapshot()
    assert s.states == [] and s.stations == []
