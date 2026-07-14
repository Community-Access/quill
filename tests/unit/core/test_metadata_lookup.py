"""Tests for the book-metadata lookup parsers (pure parts; no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.metadata_lookup import (
    LookupError_,
    LookupResult,
    _lucene_escape,
    cover_url,
    fetch_cover,
    results_from_musicbrainz,
    results_from_open_library,
)


def test_lucene_escape_backslash_then_quote() -> None:
    assert _lucene_escape('He said "hi" \\ bye') == 'He said \\"hi\\" \\\\ bye'


def test_results_from_open_library_parses_and_scores() -> None:
    data = {
        "docs": [
            {
                "title": "My Book",
                "author_name": ["Jane Doe"],
                "first_publish_year": 2001,
                "subject": ["Fiction", "Adventure"],
                "series": ["The Saga"],
                "cover_i": 1234567,
            },
            {"title": "Another", "author_name": []},
            "junk",
        ]
    }
    results = results_from_open_library(data, "my book")
    assert results[0].title == "My Book"
    assert results[0].author == "Jane Doe"
    assert results[0].genre == "Fiction"
    assert results[0].year == "2001"
    assert results[0].series_title == "The Saga"
    assert results[0].score == 95  # exact title match
    assert results[0].cover_id == 1234567
    assert results[1].score == 75
    assert results[1].cover_id == 0  # no cover_i in the doc
    assert len(results) == 2  # junk entry skipped


def test_cover_url_shape() -> None:
    assert cover_url(42) == "https://covers.openlibrary.org/b/id/42-L.jpg?default=false"


def test_fetch_cover_rejects_missing_id(tmp_path: Path) -> None:
    with pytest.raises(LookupError_):
        fetch_cover(0, tmp_path / "cover.jpg")


def test_fetch_cover_writes_target_and_rejects_placeholders(tmp_path: Path, monkeypatch) -> None:
    import quill.core.metadata_lookup as ml

    class FakeResponse:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    real = b"\xff\xd8" + b"j" * 5000  # plausible JPEG-sized payload
    monkeypatch.setattr(ml.urllib.request, "urlopen", lambda *a, **k: FakeResponse(real))
    target = tmp_path / "audio" / "cover.jpg"
    written = fetch_cover(99, target)
    assert written == target and target.read_bytes() == real

    tiny = b"x" * 10  # the "no cover" placeholder is never this small a real jacket
    monkeypatch.setattr(ml.urllib.request, "urlopen", lambda *a, **k: FakeResponse(tiny))
    with pytest.raises(LookupError_):
        fetch_cover(99, tmp_path / "cover2.jpg")


def test_results_from_musicbrainz_parses() -> None:
    data = {
        "releases": [
            {
                "title": "My Album",
                "score": 88,
                "date": "1999-05-01",
                "artist-credit": [{"name": "The Band"}],
            }
        ]
    }
    results = results_from_musicbrainz(data)
    assert results == [
        LookupResult(
            title="My Album", author="The Band", year="1999", source="MusicBrainz", score=88
        )
    ]


def test_results_tolerate_empty_payloads() -> None:
    assert results_from_open_library({}, "x") == []
    assert results_from_musicbrainz({"releases": "nope"}) == []


def test_display_reads_as_one_sentence() -> None:
    result = LookupResult(title="My Book", author="Jane", year="2001", source="Open Library")
    assert result.display == "My Book by Jane (2001) — Open Library"


def test_search_merges_best_first(monkeypatch) -> None:
    import quill.core.metadata_lookup as lookup

    monkeypatch.setattr(
        lookup,
        "search_open_library",
        lambda t, a="": [LookupResult(title="Book", author="", source="Open Library", score=95)],
    )
    monkeypatch.setattr(
        lookup,
        "search_musicbrainz",
        lambda t, a="": [LookupResult(title="Album", author="", source="MusicBrainz", score=99)],
    )
    results = lookup.search("x")
    assert [r.title for r in results] == ["Album", "Book"]
