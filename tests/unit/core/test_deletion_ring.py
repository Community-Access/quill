from __future__ import annotations

from quill.core.deletion_ring import DeletionRing, removed_span


def test_removed_span_finds_contiguous_deletion() -> None:
    assert removed_span("hello world", "ho world") == "ell"
    assert removed_span("hello world", "hello") == " world"
    assert removed_span("hello world", " world") == "hello"


def test_removed_span_handles_no_change_and_insertions() -> None:
    assert removed_span("abc", "abc") == ""
    assert removed_span("abc", "abXc") == ""  # insertion, not a deletion
    assert removed_span("", "") == ""


def test_removed_span_whole_string() -> None:
    assert removed_span("gone", "") == "gone"


def test_ring_newest_first_and_capped() -> None:
    ring = DeletionRing(max_entries=3)
    ring.record("one")
    ring.record("two")
    ring.record("three")
    ring.record("four")
    assert ring.entries() == ["four", "three", "two"]
    assert ring.most_recent() == "four"


def test_ring_ignores_empty_and_collapses_repeats() -> None:
    ring = DeletionRing()
    ring.record("")
    assert ring.is_empty()
    ring.record("x")
    ring.record("x")
    assert ring.entries() == ["x"]


def test_ring_clear() -> None:
    ring = DeletionRing()
    ring.record("a")
    ring.clear()
    assert ring.is_empty()
    assert ring.most_recent() is None
