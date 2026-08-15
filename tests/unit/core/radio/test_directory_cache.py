"""Tests for the browse-level disk cache (quill/core/radio/directory_cache.py).

No network and no wx: the cache is exercised against a temporary data dir via
QUILL_DATA_DIR (honoured because tests/conftest.py sets _DEV_BUILD).
"""

from __future__ import annotations

import time

import pytest

from quill.core.radio import directory_cache


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    directory_cache.clear()
    yield
    directory_cache.clear()


def test_save_and_load_round_trip() -> None:
    directory_cache.save("k", ["Jazz", "Rock"])
    entry = directory_cache.load("k")
    assert entry is not None
    assert entry.payload == ["Jazz", "Rock"]
    assert entry.complete is True
    assert entry.age_seconds() < 5


def test_missing_key_is_none_not_an_error() -> None:
    assert directory_cache.load("never-written") is None


def test_fresh_cache_short_circuits_the_fetch() -> None:
    calls = []

    def fetch():
        calls.append(1)
        return ["live"]

    first, age = directory_cache.resolve("k", fetch)
    assert first == ["live"] and age is None and len(calls) == 1
    second, age2 = directory_cache.resolve("k", fetch)
    assert second == ["live"] and len(calls) == 1, "a fresh entry must not refetch"
    assert age2 is not None and age2 >= 0


def test_stale_cache_triggers_a_refetch() -> None:
    directory_cache.save("k", ["old"])
    got, age = directory_cache.resolve("k", lambda: ["new"], max_age_seconds=0)
    assert got == ["new"] and age is None


def test_a_failed_fetch_falls_back_to_a_stale_entry_with_its_age() -> None:
    # The rule that matters for a browse tree: a stale answer beats no answer,
    # and the caller is told how stale so it can say so.
    directory_cache.save("k", ["old"])
    entry = directory_cache.load("k")
    assert entry is not None
    directory_cache.save("k", ["old"])

    def boom():
        raise RuntimeError("directory down")

    got, age = directory_cache.resolve("k", boom, max_age_seconds=0)
    assert got == ["old"]
    assert age is not None, "a stale answer must report its age"


def test_a_failed_fetch_with_no_cache_returns_empty_not_an_exception() -> None:
    def boom():
        raise RuntimeError("directory down")

    got, age = directory_cache.resolve("cold", boom, empty=[])
    assert got == [] and age is None


def test_an_empty_live_result_is_not_cached_over_a_good_one() -> None:
    directory_cache.save("k", ["good"])
    got, _age = directory_cache.resolve("k", lambda: [], max_age_seconds=0)
    assert got == ["good"], "an empty refresh must not blank a working branch"


def test_refresh_skips_the_fresh_tier() -> None:
    directory_cache.save("k", ["old"])
    got, age = directory_cache.resolve("k", lambda: ["new"], refresh=True)
    assert got == ["new"] and age is None


def test_incomplete_entries_are_not_served_to_a_caller_needing_everything() -> None:
    directory_cache.save("k", ["head", "only"], complete=False)
    calls = []

    def fetch():
        calls.append(1)
        return ["all", "of", "them"]

    got, _age = directory_cache.resolve("k", fetch, require_complete=True)
    assert got == ["all", "of", "them"] and len(calls) == 1
    # ...but a caller that only wanted a prefix is happy with the cached one.
    directory_cache.save("k", ["head", "only"], complete=False)
    got2, age2 = directory_cache.resolve("k", fetch, require_complete=False)
    assert got2 == ["head", "only"] and age2 is not None


def test_forget_drops_one_key_and_clear_drops_all() -> None:
    directory_cache.save("a", [1])
    directory_cache.save("b", [2])
    directory_cache.forget("a")
    assert directory_cache.load("a") is None
    assert directory_cache.load("b") is not None
    directory_cache.clear()
    assert directory_cache.load("b") is None


def test_corrupt_entry_reads_as_a_miss() -> None:
    directory_cache.save("k", [1])
    path = directory_cache._cache_dir() / directory_cache._safe_name("k")
    path.write_text("{not json", encoding="utf-8")
    assert directory_cache.load("k") is None


def test_key_with_path_characters_cannot_escape_the_cache_dir() -> None:
    directory_cache.save("../../etc/passwd", ["x"])
    written = list(directory_cache._cache_dir().glob("*.json"))
    assert len(written) == 1
    assert written[0].parent == directory_cache._cache_dir()


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (None, ""),
        (5, "just now"),
        (600, "10 minutes ago"),
        (3600 * 2, "2 hours ago"),
        (3600 * 25, "yesterday"),
        (3600 * 24 * 3, "3 days ago"),
    ],
)
def test_spoken_age_is_words_not_a_timestamp(age, expected) -> None:
    assert directory_cache.spoken_age(age) == expected


def test_entry_freshness_uses_an_injectable_now() -> None:
    entry = directory_cache.CacheEntry(payload=[], fetched_at=1000.0)
    assert entry.is_fresh(100, now=1050.0)
    assert not entry.is_fresh(100, now=1200.0)
    assert entry.age_seconds(now=1200.0) == pytest.approx(200.0)
    # A clock that went backwards must not report a negative age.
    assert entry.age_seconds(now=900.0) == 0.0


def test_time_moves_forward_between_saves() -> None:
    directory_cache.save("k", [1])
    first = directory_cache.load("k")
    time.sleep(0.01)
    directory_cache.save("k", [2])
    second = directory_cache.load("k")
    assert first is not None and second is not None
    assert second.fetched_at >= first.fetched_at
