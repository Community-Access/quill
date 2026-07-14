"""Tests for podcast chapters: fetch (Safe Mode gate), parsing, and
position-based chapter lookup (no real network)."""

from __future__ import annotations

import json

import pytest

import quill.core.podcasts.chapters as chapters_module
from quill.core.podcasts.chapters import (
    ChaptersError,
    PodcastChapter,
    chapter_at_position,
    fetch_and_parse_chapters,
    next_chapter,
    parse_chapters,
    previous_chapter,
    refuse_in_safe_mode,
)

_SAMPLE = {
    "version": "1.2.0",
    "chapters": [
        {"startTime": 0, "title": "Intro"},
        {"startTime": 90.5, "title": "Segment 2", "img": "https://x/2.png", "url": "https://x/2"},
        {"startTime": 300, "title": "Outro"},
    ],
}


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(ChaptersError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_parse_chapters_extracts_fields_in_order() -> None:
    result = parse_chapters(json.dumps(_SAMPLE).encode())
    assert [c.title for c in result] == ["Intro", "Segment 2", "Outro"]
    assert result[0].start_ms == 0
    assert result[1].start_ms == 90500
    assert result[1].image_url == "https://x/2.png"
    assert result[1].link_url == "https://x/2"


def test_parse_chapters_sorts_out_of_order_entries() -> None:
    data = {
        "chapters": [
            {"startTime": 100, "title": "Second"},
            {"startTime": 0, "title": "First"},
        ]
    }
    result = parse_chapters(json.dumps(data).encode())
    assert [c.title for c in result] == ["First", "Second"]


def test_parse_chapters_skips_junk_entries() -> None:
    data = {
        "chapters": [
            {"startTime": 0, "title": ""},  # no title
            {"title": "No start time"},  # missing startTime
            {"startTime": -5, "title": "Negative"},  # negative start
            "junk",  # not a dict
            {"startTime": 10, "title": "Valid"},
        ]
    }
    result = parse_chapters(json.dumps(data).encode())
    assert [c.title for c in result] == ["Valid"]


def test_parse_chapters_handles_non_dict_or_missing_chapters_key() -> None:
    assert parse_chapters(json.dumps({"version": "1.2.0"}).encode()) == []
    assert parse_chapters(json.dumps([]).encode()) == []


def test_parse_chapters_raises_on_invalid_json() -> None:
    with pytest.raises(ChaptersError):
        parse_chapters(b"not json")


def test_fetch_and_parse_chapters_refuses_in_safe_mode() -> None:
    with pytest.raises(ChaptersError):
        fetch_and_parse_chapters("https://x/chapters.json", safe_mode=True)


def test_fetch_and_parse_chapters_empty_url_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(_url: str) -> bytes:
        raise AssertionError("should not fetch an empty url")

    monkeypatch.setattr(chapters_module, "_fetch_chapters_bytes", fail_if_called)
    assert fetch_and_parse_chapters("") == []


def test_fetch_chapters_bytes_refuses_non_https() -> None:
    with pytest.raises(ChaptersError):
        chapters_module._fetch_chapters_bytes("http://x/chapters.json")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, _n: int = -1) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fetch_and_parse_chapters_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps(_SAMPLE).encode()
    monkeypatch.setattr(
        chapters_module.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload)
    )
    result = fetch_and_parse_chapters("https://x/chapters.json")
    assert len(result) == 3


def test_fetch_chapters_bytes_raises_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def always_fail(*_a: object, **_k: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(chapters_module.urllib.request, "urlopen", always_fail)
    with pytest.raises(ChaptersError):
        chapters_module._fetch_chapters_bytes("https://x/chapters.json")


# -- position-based lookup --------------------------------------------------

_CHAPTERS = [
    PodcastChapter(start_ms=0, title="Intro"),
    PodcastChapter(start_ms=90000, title="Segment 2"),
    PodcastChapter(start_ms=300000, title="Outro"),
]


def test_chapter_at_position_finds_the_containing_chapter() -> None:
    assert chapter_at_position(_CHAPTERS, 0).title == "Intro"
    assert chapter_at_position(_CHAPTERS, 50000).title == "Intro"
    assert chapter_at_position(_CHAPTERS, 90000).title == "Segment 2"
    assert chapter_at_position(_CHAPTERS, 999999).title == "Outro"


def test_chapter_at_position_empty_list_returns_none() -> None:
    assert chapter_at_position([], 0) is None


def test_next_chapter_returns_the_upcoming_one_or_none_at_the_end() -> None:
    assert next_chapter(_CHAPTERS, 0).title == "Segment 2"
    assert next_chapter(_CHAPTERS, 90000).title == "Outro"
    assert next_chapter(_CHAPTERS, 300000) is None


def test_previous_chapter_returns_the_prior_one_or_none_at_the_start() -> None:
    assert previous_chapter(_CHAPTERS, 90000).title == "Intro"
    assert previous_chapter(_CHAPTERS, 300000).title == "Segment 2"
    assert previous_chapter(_CHAPTERS, 0) is None
