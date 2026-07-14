"""Tests for the iTunes Search podcast discovery client (Safe Mode gate,
parsing) -- no real network calls."""

from __future__ import annotations

import json

import pytest

import quill.core.podcasts.itunes_search as itunes_search
from quill.core.podcasts.itunes_search import (
    ITunesSearchError,
    refuse_in_safe_mode,
    results_from_json,
    search_podcasts,
)


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(ITunesSearchError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_results_from_json_parses_and_skips_junk() -> None:
    data = {
        "results": [
            {
                "collectionName": "Great Show",
                "feedUrl": "https://example.com/feed.xml",
                "artistName": "Jane Doe",
                "artworkUrl600": "https://example.com/art600.png",
                "collectionViewUrl": "https://podcasts.apple.com/show",
            },
            {"collectionName": "", "feedUrl": "https://x"},  # skipped: no title
            {"collectionName": "No Feed"},  # skipped: no feed url
            "junk",  # skipped: not a dict
        ]
    }
    results = results_from_json(data)
    assert len(results) == 1
    result = results[0]
    assert result.title == "Great Show"
    assert result.feed_url == "https://example.com/feed.xml"
    assert result.artist == "Jane Doe"
    assert result.display_name == "Great Show — Jane Doe"


def test_results_from_json_prefers_artwork_600_over_100() -> None:
    data = {
        "results": [
            {
                "collectionName": "X",
                "feedUrl": "https://x/feed.xml",
                "artworkUrl600": "https://x/600.png",
                "artworkUrl100": "https://x/100.png",
            }
        ]
    }
    assert results_from_json(data)[0].artwork_url == "https://x/600.png"


def test_results_from_json_handles_non_dict_payload() -> None:
    assert results_from_json("junk") == []
    assert results_from_json({}) == []


def test_display_name_omits_dash_without_artist() -> None:
    from quill.core.podcasts.itunes_search import PodcastSearchResult

    result = PodcastSearchResult(title="X", feed_url="https://x")
    assert result.display_name == "X"


def test_search_podcasts_refuses_in_safe_mode() -> None:
    with pytest.raises(ITunesSearchError):
        search_podcasts("jazz", safe_mode=True)


def test_search_podcasts_empty_query_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(_url: str) -> object:
        raise AssertionError("should not fetch for an empty query")

    monkeypatch.setattr(itunes_search, "_http_json", fail_if_called)
    assert search_podcasts("   ") == []


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_search_podcasts_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({
        "results": [{"collectionName": "WXYZ", "feedUrl": "https://example.com/feed.xml"}]
    }).encode()
    monkeypatch.setattr(
        itunes_search.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload)
    )
    results = search_podcasts("wxyz")
    assert len(results) == 1 and results[0].title == "WXYZ"


def test_http_json_refuses_non_https() -> None:
    with pytest.raises(ITunesSearchError):
        itunes_search._http_json("http://example.com/search")


def test_http_json_raises_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def always_fail(*_a: object, **_k: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(itunes_search.urllib.request, "urlopen", always_fail)
    with pytest.raises(ITunesSearchError):
        itunes_search._http_json("https://example.com/search")


def test_http_json_raises_on_unparseable_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        itunes_search.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(b"not json")
    )
    with pytest.raises(ITunesSearchError):
        itunes_search._http_json("https://example.com/search")
