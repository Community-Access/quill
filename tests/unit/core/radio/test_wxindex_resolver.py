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
