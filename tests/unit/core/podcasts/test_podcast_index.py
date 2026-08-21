"""Podcast Index: the signature, the parse, the refusals, and the merge.

The two that carry weight are the signature -- it is the only part that cannot
be corrected after the fact without a round trip to the server -- and the rule
that one directory failing is not the search failing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from quill.core.podcasts import directory_search, podcast_index
from quill.core.podcasts.itunes_search import PodcastSearchResult

_PAYLOAD = {
    "status": "true",
    "feeds": [
        {
            "id": 75075,
            "title": "Blind Abilities",
            "url": "https://feeds.example.com/blindabilities",
            "author": "Blind Abilities Team",
            "artwork": "https://example.com/art.jpg",
            "link": "https://blindabilities.com",
        },
        {"title": "No feed url here", "url": ""},
        "not a dict at all",
    ],
}


# -- the signature -----------------------------------------------------------


def test_the_authorization_header_is_the_published_signature() -> None:
    """SHA-1 of key + secret + unix seconds. The server checks this exact value."""
    headers = podcast_index.auth_headers("KEY123", "SECRET456", now=1_755_000_000)
    expected = hashlib.sha1(b"KEY123SECRET4561755000000").hexdigest()  # noqa: S324
    assert headers["Authorization"] == expected
    assert headers["X-Auth-Key"] == "KEY123"
    assert headers["X-Auth-Date"] == "1755000000"


def test_the_signature_changes_with_the_clock() -> None:
    first = podcast_index.auth_headers("k", "s", now=1_000)
    second = podcast_index.auth_headers("k", "s", now=1_001)
    assert first["Authorization"] != second["Authorization"]


# -- refusals ----------------------------------------------------------------


def test_safe_mode_refuses_before_anything_is_formed() -> None:
    with pytest.raises(podcast_index.PodcastIndexError):
        podcast_index.refuse_in_safe_mode(True)
    with pytest.raises(podcast_index.PodcastIndexError):
        podcast_index.search_podcasts("news", key="k", secret="s", safe_mode=True)


def test_missing_credentials_are_a_sentence_not_a_server_error() -> None:
    with pytest.raises(podcast_index.PodcastIndexError) as caught:
        podcast_index.search_podcasts("news", key="", secret="")
    assert "Podcast Settings" in str(caught.value)


def test_a_non_https_url_is_refused() -> None:
    with pytest.raises(podcast_index.PodcastIndexError):
        podcast_index._http_json("http://api.podcastindex.org/x", {})


# -- parsing -----------------------------------------------------------------


def test_a_captured_payload_parses_into_the_shared_result_type() -> None:
    """The same type iTunes returns, so nothing downstream can tell them apart."""
    results = podcast_index.results_from_json(json.loads(json.dumps(_PAYLOAD)))
    assert len(results) == 1
    row = results[0]
    assert isinstance(row, PodcastSearchResult)
    assert row.title == "Blind Abilities"
    assert row.feed_url == "https://feeds.example.com/blindabilities"
    assert row.artist == "Blind Abilities Team"
    # Podcast Index's id is not an iTunes collection id and must not pose as one.
    assert row.collection_id == ""


def test_junk_is_skipped_rather_than_raising() -> None:
    assert podcast_index.results_from_json({"feeds": "nonsense"}) == []
    assert podcast_index.results_from_json(None) == []


# -- merging -----------------------------------------------------------------


def _result(title: str, url: str) -> PodcastSearchResult:
    return PodcastSearchResult(title=title, feed_url=url)


def test_the_same_feed_from_both_directories_appears_once() -> None:
    merged = podcast_index.merge_results(
        [_result("From iTunes", "https://feeds.example.com/ba")],
        [_result("From Podcast Index", "https://feeds.example.com/ba/")],
    )
    assert [row.title for row in merged] == ["From iTunes"]


def test_two_genuinely_different_feeds_both_survive() -> None:
    merged = podcast_index.merge_results(
        [_result("One", "https://a.example.com/feed")],
        [_result("Two", "https://b.example.com/feed")],
    )
    assert len(merged) == 2


# -- the coordinator ---------------------------------------------------------


def test_one_directory_failing_is_not_the_search_failing(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.itunes_search.search_podcasts",
        lambda *_a, **_k: [_result("From iTunes", "https://a/feed")],
    )

    def _boom(*_a: object, **_k: object) -> list[PodcastSearchResult]:
        raise podcast_index.PodcastIndexError("the index is down")

    monkeypatch.setattr("quill.core.podcasts.podcast_index.search_podcasts", _boom)

    found = directory_search.search("news", source="both", key="k", secret="s")
    assert [row.title for row in found.results] == ["From iTunes"]
    assert found.problems
    said = found.summary()
    assert "1 result" in said
    assert "Podcast Index did not answer" in said


def test_asking_for_itunes_never_touches_the_other(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.itunes_search.search_podcasts",
        lambda *_a, **_k: [_result("One", "https://a/feed")],
    )

    def _never(*_a: object, **_k: object) -> list[PodcastSearchResult]:
        raise AssertionError("Podcast Index must not be asked")

    monkeypatch.setattr("quill.core.podcasts.podcast_index.search_podcasts", _never)
    assert len(directory_search.search("news", source="itunes").results) == 1


def test_an_unknown_source_reads_as_itunes(monkeypatch: Any) -> None:
    """A settings file with a typo should behave like one with nothing in it."""
    monkeypatch.setattr(
        "quill.core.podcasts.itunes_search.search_podcasts",
        lambda *_a, **_k: [_result("One", "https://a/feed")],
    )
    monkeypatch.setattr(
        "quill.core.podcasts.podcast_index.search_podcasts",
        lambda *_a, **_k: [_result("Two", "https://b/feed")],
    )
    assert len(directory_search.search("news", source="carrier pigeon").results) == 1


def test_both_directories_are_named_in_the_status_line(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.itunes_search.search_podcasts",
        lambda *_a, **_k: [_result("One", "https://a/feed")],
    )
    monkeypatch.setattr(
        "quill.core.podcasts.podcast_index.search_podcasts",
        lambda *_a, **_k: [_result("Two", "https://b/feed")],
    )
    said = directory_search.search("news", source="both", key="k", secret="s").summary()
    assert "iTunes" in said and "Podcast Index" in said


def test_nothing_found_says_so_rather_than_reading_as_broken(monkeypatch: Any) -> None:
    monkeypatch.setattr("quill.core.podcasts.itunes_search.search_podcasts", lambda *_a, **_k: [])
    assert directory_search.search("zzz", source="itunes").summary() == "No podcasts matched that."


# -- the credentials never reach a crash bundle ------------------------------


def test_the_secret_does_not_survive_redaction() -> None:
    """A crash bundle is the one place these could leak without being sent."""
    from quill.stability.redaction import redact_text_for_bundle

    secret = "s3cr3t-podcastindex-value-0123456789"
    scrubbed = redact_text_for_bundle(f"podcastindex_secret={secret}")
    assert secret not in scrubbed
    scrubbed = redact_text_for_bundle(f"X-Auth-Key: {secret}")
    assert secret not in scrubbed
