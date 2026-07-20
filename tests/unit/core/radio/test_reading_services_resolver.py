import pytest

from quill.core.radio import reading_services as rs
from quill.core.radio.models import RadioStation
from quill.core.radio.radio_browser import RadioBrowserError


def _reading_station() -> RadioStation:
    return RadioStation(
        name="Metro Reading Service",
        stream_url="https://s/metro-reading",
        station_uuid="uuid-1",
        tags=("talk", "reading service"),
        source="RadioBrowser",
    )


def _unrelated_station() -> RadioStation:
    return RadioStation(
        name="Classic Rock 101",
        stream_url="https://s/classic-rock",
        station_uuid="uuid-2",
        tags=("rock",),
        source="RadioBrowser",
    )


def _fake_searcher(calls: list[tuple[str, bool]]):
    def searcher(keyword: str, *, safe_mode: bool = False) -> list[RadioStation]:
        calls.append((keyword, safe_mode))
        return [_reading_station(), _unrelated_station()]

    return searcher


def test_refresh_reading_services_filters_and_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []

    result = rs.refresh_reading_services(searcher=_fake_searcher(calls))

    assert result.count == 1
    assert result.generated_at
    # Called once per keyword.
    assert len(calls) == len(rs._READING_KEYWORDS)

    cache_path = tmp_path / "directory.json"
    assert cache_path.exists()

    cached, _age = rs._read_cache()
    assert len(cached) == 1
    assert cached[0].stream_url == "https://s/metro-reading"
    assert cached[0].source == "Radio Reading Service"


def test_refresh_reading_services_refuses_in_safe_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []

    with pytest.raises(RadioBrowserError, match="Safe Mode"):
        rs.refresh_reading_services(safe_mode=True, searcher=_fake_searcher(calls))
    assert calls == []
    assert not (tmp_path / "directory.json").exists()


def test_list_reading_services_serves_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []
    rs.refresh_reading_services(searcher=_fake_searcher(calls))
    assert len(calls) == len(rs._READING_KEYWORDS)

    stations = rs.list_reading_services(searcher=_fake_searcher(calls))

    # No further searcher calls -- served straight from the fresh cache.
    assert len(calls) == len(rs._READING_KEYWORDS)
    assert len(stations) == 1
    assert stations[0].stream_url == "https://s/metro-reading"
    assert stations[0].source == "Radio Reading Service"


def test_list_reading_services_refreshes_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []

    stations = rs.list_reading_services(searcher=_fake_searcher(calls))

    assert len(calls) == len(rs._READING_KEYWORDS)
    assert len(stations) == 1
    assert stations[0].source == "Radio Reading Service"
    assert (tmp_path / "directory.json").exists()


def test_list_reading_services_safe_mode_falls_back_to_bundled_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []

    stations = rs.list_reading_services(safe_mode=True, searcher=_fake_searcher(calls))

    assert calls == []
    assert not (tmp_path / "directory.json").exists()
    bundled = rs.load_reading_services()
    assert [s.stream_url for s in stations] == [s.stream_url for s in bundled]
    assert len(stations) == len(bundled)
