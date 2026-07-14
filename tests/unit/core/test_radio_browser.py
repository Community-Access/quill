"""Tests for the RadioBrowser client (Safe Mode gate, parsing, mirror
failover) -- no real network calls."""

from __future__ import annotations

import json

import pytest

import quill.core.radio.radio_browser as rb
from quill.core.radio.radio_browser import (
    RadioBrowserError,
    list_countries,
    list_tags,
    refuse_in_safe_mode,
    register_click,
    search_stations,
    stations_from_json,
)


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(RadioBrowserError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_stations_from_json_parses_and_skips_junk() -> None:
    data = [
        {
            "name": "WXYZ",
            "url_resolved": "https://example.com/stream",
            "stationuuid": "abc-123",
            "homepage": "https://example.com",
            "favicon": "",
            "country": "Canada",
            "language": "English",
            "tags": "jazz, smooth",
            "codec": "MP3",
            "bitrate": 128,
            "votes": 42,
        },
        {"name": "", "url": "https://example.com/no-name"},  # skipped: no name
        {"name": "No URL"},  # skipped: no stream url
        "junk",  # skipped: not a dict
    ]
    stations = stations_from_json(data)
    assert len(stations) == 1
    station = stations[0]
    assert station.name == "WXYZ"
    assert station.stream_url == "https://example.com/stream"
    assert station.tags == ("jazz", "smooth")
    assert station.bitrate_kbps == 128
    assert station.votes == 42


def test_stations_from_json_prefers_url_resolved_over_url() -> None:
    data = [{"name": "X", "url": "https://raw", "url_resolved": "https://resolved"}]
    assert stations_from_json(data)[0].stream_url == "https://resolved"


def test_stations_from_json_falls_back_to_url() -> None:
    data = [{"name": "X", "url": "https://raw"}]
    assert stations_from_json(data)[0].stream_url == "https://raw"


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _reset_mirror_cache() -> None:
    rb._cached_mirrors = None
    yield
    rb._cached_mirrors = None


def _stub_mirrors(monkeypatch: pytest.MonkeyPatch, hosts: list[str]) -> None:
    monkeypatch.setattr(rb, "_resolve_mirrors", lambda: hosts)


def test_search_stations_refuses_in_safe_mode() -> None:
    with pytest.raises(RadioBrowserError):
        search_stations("jazz", safe_mode=True)


def test_search_stations_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_mirrors(monkeypatch, ["mirror1.example.com"])
    payload = json.dumps([{"name": "WXYZ", "url": "https://example.com/stream"}]).encode()
    monkeypatch.setattr(rb.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))
    stations = search_stations("wxyz")
    assert len(stations) == 1 and stations[0].name == "WXYZ"


def test_http_json_fails_over_to_next_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_mirrors(monkeypatch, ["bad.example.com", "good.example.com"])
    payload = json.dumps([{"name": "OK", "url": "https://example.com/stream"}]).encode()

    def fake_urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if "bad.example.com" in url:
            raise OSError("connection refused")
        return _FakeResponse(payload)

    monkeypatch.setattr(rb.urllib.request, "urlopen", fake_urlopen)
    stations = search_stations("ok")
    assert stations[0].name == "OK"


def test_http_json_raises_after_every_mirror_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_mirrors(monkeypatch, ["bad1.example.com", "bad2.example.com"])

    def always_fail(*_a: object, **_k: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(rb.urllib.request, "urlopen", always_fail)
    with pytest.raises(RadioBrowserError):
        search_stations("anything")


def test_list_tags_and_countries_extract_names(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_mirrors(monkeypatch, ["mirror1.example.com"])
    payload = json.dumps([{"name": "jazz"}, {"name": "rock"}, {"no_name": True}]).encode()
    monkeypatch.setattr(rb.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))
    assert list_tags() == ["jazz", "rock"]
    assert list_countries() == ["jazz", "rock"]


def test_register_click_refuses_in_safe_mode() -> None:
    with pytest.raises(RadioBrowserError):
        register_click("some-uuid", safe_mode=True)


def test_register_click_noop_without_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_a: object, **_k: object) -> None:
        raise AssertionError("should not fetch without a uuid")

    monkeypatch.setattr(rb, "_http_json", fail_if_called)
    register_click("")  # no raise, no network call
