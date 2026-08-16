""" "This folder is empty" and "this source is down" must never look alike.

Both failures reached a listener as an empty folder on 2026-08-16, from two
different directions:

* **LibriVox** was down (Cloudflare 522 after a ~19.5 s hold). Its client wraps
  every transport failure in ``LibriVoxError``, and the classifier only matched
  the *outermost* exception type -- so a wrapped outage read as "no data in the
  folder", with nothing to suggest trying again.
* **The Internet Archive's** search backend was down, and it says so with
  **HTTP 200** and ``{"error": "[BACKEND_ERROR] ..."}``. That parsed to zero
  docs, which is a perfectly ordinary answer, so "Radio Programs" reported
  itself empty -- and, because the empty result was a truthy dict, the outage
  got *cached* and outlived the outage.
"""

from __future__ import annotations

import pytest

from quill.core.radio import browse_failure, internet_archive


def test_a_wrapped_transport_failure_still_counts_as_unreachable() -> None:
    from quill.core.media.librivox import LibriVoxError

    cause = TimeoutError("timed out")
    try:
        raise LibriVoxError("LibriVox request failed") from cause
    except LibriVoxError as error:
        assert browse_failure.last_error_was_network(error) is True


def test_an_unwrapped_domain_error_is_still_just_empty() -> None:
    """A source that answers fine and has nothing to show is not an outage."""

    class PlainError(Exception):
        pass

    assert browse_failure.last_error_was_network(PlainError("no matches")) is False


def test_a_service_that_says_it_is_broken_counts_as_unreachable() -> None:
    error = internet_archive.InternetArchiveError("search backend down")
    assert browse_failure.last_error_was_network(error) is True


def test_the_archive_error_body_raises_rather_than_reading_as_empty() -> None:
    body = '{"error":"[BACKEND_ERROR] Invalid or no response from Elasticsearch"}'
    with pytest.raises(internet_archive.InternetArchiveError):
        internet_archive.parse_search(body)


def test_a_real_archive_answer_still_parses() -> None:
    body = (
        '{"response":{"numFound":2,"docs":['
        '{"identifier":"a","title":"A","mediatype":"collection"},'
        '{"identifier":"b","title":"B","mediatype":"audio"}]}}'
    )
    total, items = internet_archive.parse_search(body)
    assert total == 2
    assert [item.identifier for item in items] == ["a", "b"]
    assert items[0].is_collection and not items[1].is_collection


def test_a_swallowed_refresh_failure_is_still_recorded(tmp_path, monkeypatch) -> None:
    """directory_cache never raises into a browse tree -- by design -- but the
    fact of the failure has to survive, or empty and broken merge again."""
    from quill.core.radio import directory_cache

    monkeypatch.setattr(directory_cache, "_cache_dir", lambda: tmp_path)
    browse_failure.LAST_FAILURE.clear()

    def _boom() -> list:
        raise TimeoutError("directory timed out")

    payload, age = directory_cache.resolve("k", _boom, max_age_seconds=60, empty=[])
    assert payload == [] and age is None
    assert browse_failure.last_error_was_network() is True


def test_an_empty_answer_is_never_cached_as_the_listing(tmp_path, monkeypatch) -> None:
    from quill.core.radio import directory_cache

    monkeypatch.setattr(directory_cache, "_cache_dir", lambda: tmp_path)
    directory_cache.resolve("k2", lambda: [], max_age_seconds=60, empty=[])
    assert directory_cache.load("k2") is None
