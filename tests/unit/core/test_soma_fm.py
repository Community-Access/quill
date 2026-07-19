"""Tests for the SomaFM client (Safe Mode gate, parsing, playlist
resolution) -- no real network calls."""

from __future__ import annotations

import json

import pytest

import quill.core.radio.soma_fm as soma_fm
from quill.core.radio.soma_fm import (
    SomaFmError,
    channels_from_json,
    first_stream_url_from_pls,
    refuse_in_safe_mode,
    search_stations,
)

_SAMPLE_PLS = """[playlist]
numberofentries=2
File1=https://ice6.somafm.com/groovesalad-256-mp3
Title1=SomaFM: Groove Salad (#1)
Length1=-1
File2=https://ice2.somafm.com/groovesalad-256-mp3
Title2=SomaFM: Groove Salad (#2)
Length2=-1
Version=2
"""

_SAMPLE_CHANNEL: dict[str, object] = {
    "id": "groovesalad",
    "title": "Groove Salad",
    "description": "A nicely chilled plate of ambient/downtempo beats.",
    "genre": "ambient|electronic",
    "image": "https://api.somafm.com/logos/120/groovesalad120.png",
    "playlists": [
        {"url": "https://api.somafm.com/groovesalad256.pls", "format": "mp3", "quality": "highest"},
        {"url": "https://api.somafm.com/groovesalad130.pls", "format": "aac", "quality": "highest"},
        {"url": "https://api.somafm.com/groovesalad32.pls", "format": "aacp", "quality": "low"},
    ],
}


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(SomaFmError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_first_stream_url_from_pls_parses_file1() -> None:
    assert first_stream_url_from_pls(_SAMPLE_PLS) == "https://ice6.somafm.com/groovesalad-256-mp3"


def test_first_stream_url_from_pls_returns_none_for_junk() -> None:
    assert first_stream_url_from_pls("not a playlist at all") is None


def test_channels_from_json_parses_and_skips_junk() -> None:
    data = {"channels": [_SAMPLE_CHANNEL, "junk", {"no": "title"}]}
    channels = channels_from_json(data)
    assert len(channels) == 2  # the sample channel and the dict without a title
    assert channels[0]["id"] == "groovesalad"


def test_channels_from_json_handles_missing_or_malformed_top_level() -> None:
    assert channels_from_json("not a dict") == []
    assert channels_from_json({"channels": "not a list"}) == []
    assert channels_from_json({}) == []


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _dispatching_urlopen(routes: dict[str, bytes]):
    def _urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        for fragment, payload in routes.items():
            if fragment in url:
                return _FakeResponse(payload)
        raise AssertionError(f"unexpected URL requested: {url}")

    return _urlopen


def test_search_stations_refuses_in_safe_mode() -> None:
    with pytest.raises(SomaFmError):
        search_stations("ambient", safe_mode=True)


def test_search_stations_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()
    routes = {
        "channels.json": channels_payload,
        "groovesalad256.pls": _SAMPLE_PLS.encode(),
    }
    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _dispatching_urlopen(routes))
    stations = search_stations("groove")
    assert len(stations) == 1
    station = stations[0]
    assert station.name == "Groove Salad"
    assert station.stream_url == "https://ice6.somafm.com/groovesalad-256-mp3"
    assert station.station_uuid == ""
    assert station.tags == ("ambient", "electronic", "SomaFM")
    assert station.codec == "MP3"


def test_search_stations_matches_title_description_and_genre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()
    routes = {"channels.json": channels_payload, "groovesalad256.pls": _SAMPLE_PLS.encode()}
    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _dispatching_urlopen(routes))
    assert len(search_stations("chilled")) == 1  # matches description
    assert len(search_stations("electronic")) == 1  # matches genre
    assert len(search_stations("no-such-thing")) == 0


def test_search_stations_matching_ignores_spacing_and_punctuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Kelly's report: a known channel ("Groove Salad") was missed when the query
    # spacing/punctuation did not match the title exactly.
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()
    routes = {"channels.json": channels_payload, "groovesalad256.pls": _SAMPLE_PLS.encode()}
    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _dispatching_urlopen(routes))
    assert len(search_stations("GrooveSalad")) == 1  # no space
    assert len(search_stations("groove-salad")) == 1  # hyphen
    assert len(search_stations("salad groove")) == 1  # tokens, any order
    assert len(search_stations("Groove Salad")) == 1  # exact still works


def test_search_stations_empty_query_returns_every_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()
    routes = {"channels.json": channels_payload, "groovesalad256.pls": _SAMPLE_PLS.encode()}
    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _dispatching_urlopen(routes))
    assert len(search_stations("")) == 1


def test_search_stations_skips_a_channel_whose_playlist_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()

    def _urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if "channels.json" in url:
            return _FakeResponse(channels_payload)
        raise OSError("connection refused")  # every playlist fetch fails

    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _urlopen)
    assert search_stations("groove") == []  # best-effort: no crash, just no results


def test_search_stations_no_matching_channels_skips_network_for_playlists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels_payload = json.dumps({"channels": [_SAMPLE_CHANNEL]}).encode()

    def _urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if "channels.json" in url:
            return _FakeResponse(channels_payload)
        raise AssertionError("should not fetch a playlist when nothing matched")

    monkeypatch.setattr(soma_fm.urllib.request, "urlopen", _urlopen)
    assert search_stations("no-such-genre-at-all") == []
