"""Unit tests for the LibriVox provider (parsing only; no network)."""

from __future__ import annotations

import json

import pytest

from quill.core.media.librivox import LibriVoxError, search

_RESPONSE = json.dumps({
    "books": [
        {
            "id": "42",
            "title": "Pride and Prejudice",
            "totaltime": "11:35:04",
            "authors": [{"first_name": "Jane", "last_name": "Austen"}],
            "sections": [
                {"title": "Chapter 1", "listen_url": "https://ex.test/pp01.mp3"},
                {"title": "Chapter 2", "listen_url": "https://ex.test/pp02.mp3"},
                {"title": "No audio", "listen_url": ""},
            ],
        },
        {"id": "7", "title": "No Sections", "authors": [], "sections": []},
    ]
})


def test_search_parses_books_and_sections() -> None:
    books = search("pride", fetch=lambda url: _RESPONSE.encode())
    assert len(books) == 2
    book = books[0]
    assert book.title == "Pride and Prejudice"
    assert book.authors == "Jane Austen"
    assert book.total_time == "11:35:04"
    assert [s.url for s in book.sections] == [
        "https://ex.test/pp01.mp3",
        "https://ex.test/pp02.mp3",
    ]
    assert book.has_audio is True
    assert books[1].has_audio is False


def test_search_builds_expected_url() -> None:
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return b'{"books": []}'

    search("jane eyre", limit=5, fetch=fetch)
    assert "title=^jane%20eyre" in seen[0]
    assert "extended=1" in seen[0]
    assert "limit=5" in seen[0]


def test_empty_query_returns_empty() -> None:
    assert search("   ", fetch=lambda url: b"") == []


def test_transport_failure_raises() -> None:
    def boom(url: str) -> bytes:
        raise OSError("network down")

    with pytest.raises(LibriVoxError):
        search("x", fetch=boom)


def test_bad_json_raises() -> None:
    with pytest.raises(LibriVoxError):
        search("x", fetch=lambda url: b"not json {{{")
