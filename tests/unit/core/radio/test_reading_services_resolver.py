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


def test_list_reading_services_unions_curated_bundle_with_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []
    rs.refresh_reading_services(searcher=_fake_searcher(calls))
    assert len(calls) == len(rs._READING_KEYWORDS)

    stations = rs.list_reading_services(searcher=_fake_searcher(calls))

    # No further searcher calls -- discovery served straight from the fresh cache.
    assert len(calls) == len(rs._READING_KEYWORDS)
    bundled = rs.load_reading_services()
    # The curated bundle is always present, plus the one discovered service.
    assert len(stations) == len(bundled) + 1
    urls = {s.stream_url for s in stations}
    assert "https://s/metro-reading" in urls  # the discovered one
    assert all(b.stream_url in urls for b in bundled)  # every curated one survives


def test_list_reading_services_curated_only_when_no_discovery(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)

    # Searcher returns nothing new; the curated bundle still shows in full.
    stations = rs.list_reading_services(searcher=lambda *a, **k: [])

    bundled = rs.load_reading_services()
    assert len(stations) == len(bundled)
    assert {s.stream_url for s in stations} == {b.stream_url for b in bundled}


def test_list_reading_services_dedupes_discovery_against_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    bundled = rs.load_reading_services()
    dup_url = bundled[0].stream_url

    def searcher(keyword, *, safe_mode=False):
        return [
            RadioStation(
                name="Dup Reading Service",
                stream_url=dup_url,  # same stream as a curated service
                tags=("reading service",),
                source="RadioBrowser",
            )
        ]

    stations = rs.list_reading_services(searcher=searcher)
    # The duplicate stream collapses -- no double entry.
    assert len(stations) == len(bundled)


def test_list_reading_services_safe_mode_falls_back_to_bundled_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_cache_dir", lambda: tmp_path)
    calls: list[tuple[str, bool]] = []

    stations = rs.list_reading_services(safe_mode=True, searcher=_fake_searcher(calls))

    assert calls == []
    assert not (tmp_path / "directory.json").exists()
    bundled = rs.load_reading_services()
    assert {s.stream_url for s in stations} == {s.stream_url for s in bundled}
    assert len(stations) == len(bundled)
