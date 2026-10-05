"""Podcast directory folders that fail must say why, never "Nothing in here".

The 2026-10-03 report: Podcast Index categories "do not load at all", and Apple
subgenres opened onto "nothing in here". An empty folder is a true answer only
when the source answered with nothing. A source that could not answer -- no key,
a key refused, a refusal sent as HTTP 200 -- has a sentence to say, and these
tests pin that it reaches the folder. No network: the fetch is replaced.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts import podcast_index, podcast_index_catalog
from quill.core.radio import browse_failure, browse_sources, directory_cache
from quill.ui.radio import browse_feedback


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    directory_cache.clear()
    browse_failure.LAST_FAILURE.clear()
    yield
    directory_cache.clear()
    browse_failure.LAST_FAILURE.clear()


def test_with_no_key_the_category_folder_says_how_to_add_one(monkeypatch) -> None:
    monkeypatch.setattr(podcast_index_catalog, "credentials", lambda: ("", ""))

    children = browse_sources.browse("picategories")
    network_failed, reason = browse_feedback.empty_verdict(children)

    assert children == []
    assert network_failed is False, "a missing key is not the network"
    assert reason == podcast_index.NO_KEY_SENTENCE
    assert "Podcast Index Credentials" in reason


def test_a_refusal_sent_as_a_success_is_not_an_empty_taxonomy(monkeypatch) -> None:
    """The index answers some refusals with HTTP 200 and ``status: "false"``."""
    monkeypatch.setattr(podcast_index_catalog, "credentials", lambda: ("k", "s"))
    monkeypatch.setattr(
        podcast_index_catalog,
        "_http_json",
        lambda url, headers: {"status": "false", "description": "Invalid authorization"},
    )

    children = browse_sources.browse("picategories")
    network_failed, reason = browse_feedback.empty_verdict(children)

    assert children == []
    assert network_failed is False
    assert "Invalid authorization" in reason


def test_a_working_taxonomy_loads_every_category(monkeypatch) -> None:
    rows = [{"id": index, "name": f"Category {index:03d}"} for index in range(1, 113)]
    monkeypatch.setattr(podcast_index_catalog, "credentials", lambda: ("k", "s"))
    monkeypatch.setattr(
        podcast_index_catalog,
        "_http_json",
        lambda url, headers: {"status": "true", "feeds": rows, "count": 112},
    )

    children = browse_sources.browse("picategories")

    assert len(children) == 112
    assert browse_feedback.empty_verdict(children) == (False, "")


def test_the_categories_request_has_no_dangling_query_mark(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(podcast_index_catalog, "credentials", lambda: ("k", "s"))
    monkeypatch.setattr(
        podcast_index_catalog,
        "_http_json",
        lambda url, headers: (seen.append(url), {"status": "true", "feeds": []})[1],
    )
    podcast_index_catalog.categories(refresh=True)
    assert seen == ["https://api.podcastindex.org/api/1.0/categories/list"]


def test_refusal_in_reads_only_a_real_refusal() -> None:
    assert podcast_index_catalog.refusal_in({"status": "true", "feeds": []}) == ""
    assert podcast_index_catalog.refusal_in({"feeds": []}) == ""
    assert podcast_index_catalog.refusal_in([]) == ""
    assert podcast_index_catalog.refusal_in({"status": "false", "description": "No"}) == "No"
    assert podcast_index_catalog.refusal_in({"status": False})


def test_the_network_keeps_its_own_sentence() -> None:
    """A transport failure says "could not be reached", not its raw text."""
    try:
        raise podcast_index.PodcastIndexError("Could not reach Podcast Index") from TimeoutError()
    except podcast_index.PodcastIndexError as error:
        browse_failure.remember_failure(error)
    assert browse_feedback.empty_verdict([]) == (True, "")


def test_an_ordinary_error_has_no_listener_sentence() -> None:
    browse_failure.remember_failure(ValueError("int() got junk"))
    assert browse_feedback.empty_verdict([]) == (False, "")


def test_rows_mean_no_verdict_at_all() -> None:
    browse_failure.remember_failure(podcast_index.PodcastIndexError("stale"))
    assert browse_feedback.empty_verdict([object()]) == (False, "")
