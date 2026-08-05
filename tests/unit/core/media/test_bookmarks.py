"""Unit tests for ``quill.core.media.bookmarks`` (per-book bookmark store)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.media.bookmarks import (
    BookmarkStore,
    MediaBookmark,
    bookmarks_to_markdown,
    format_bookmark_line,
)


@pytest.fixture
def store(tmp_path: Path) -> BookmarkStore:
    return BookmarkStore(tmp_path / "media_bookmarks.json")


def test_empty(store: BookmarkStore) -> None:
    assert store.list("book-1") == []


def test_add_and_list_sorted(store: BookmarkStore) -> None:
    store.add("book-1", 120_000, label="Later")
    store.add("book-1", 30_000, label="Earlier", note="a note")
    marks = store.list("book-1")
    assert [m.position_ms for m in marks] == [30_000, 120_000]
    assert marks[0].label == "Earlier"
    assert marks[0].note == "a note"


def test_add_same_position_replaces(store: BookmarkStore) -> None:
    store.add("book-1", 30_000, label="First")
    store.add("book-1", 30_000, label="Updated")
    marks = store.list("book-1")
    assert len(marks) == 1
    assert marks[0].label == "Updated"


def test_remove(store: BookmarkStore) -> None:
    store.add("book-1", 30_000)
    assert store.remove("book-1", 30_000) is True
    assert store.remove("book-1", 30_000) is False
    assert store.list("book-1") == []


def test_rename(store: BookmarkStore) -> None:
    store.add("book-1", 30_000, label="Old", note="keep")
    assert store.rename("book-1", 30_000, "New") is True
    mark = store.list("book-1")[0]
    assert mark.label == "New"
    assert mark.note == "keep"  # note preserved
    assert store.rename("book-1", 999, "x") is False


def test_isolation_between_books(store: BookmarkStore) -> None:
    store.add("book-1", 1_000)
    store.add("book-2", 2_000)
    store.clear("book-1")
    assert store.list("book-1") == []
    assert [m.position_ms for m in store.list("book-2")] == [2_000]


def test_clear_returns_count(store: BookmarkStore) -> None:
    store.add("book-1", 1_000)
    store.add("book-1", 2_000)
    assert store.clear("book-1") == 2
    assert store.clear("book-1") == 0


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "media_bookmarks.json"
    BookmarkStore(path).add("book-1", 42_000, label="Kept")
    reopened = BookmarkStore(path).list("book-1")
    assert reopened == [MediaBookmark(position_ms=42_000, label="Kept")]


def test_format_bookmark_line() -> None:
    assert format_bookmark_line(5_025_000, note="the twist", title="A Book") == (
        "[1:23:45] the twist — A Book"
    )
    assert format_bookmark_line(5_025_000) == "[1:23:45]"
    assert format_bookmark_line(65_000, note="here") == "[0:01:05] here"


def test_bookmarks_to_markdown() -> None:
    marks = [MediaBookmark(120_000, note="later"), MediaBookmark(30_000, label="Earlier")]
    md = bookmarks_to_markdown("My Book", marks)
    assert md.startswith("# Bookmarks — My Book")
    # sorted by position; note/label rendered
    assert md.index("0:00:30") < md.index("0:02:00")
    assert "Earlier" in md and "later" in md


def test_export_and_merge_bundle(tmp_path: Path) -> None:
    src = BookmarkStore(tmp_path / "a.json")
    src.add("book-1", 1_000, note="one")
    src.add("book-2", 2_000)
    bundle = src.export_bundle()
    assert bundle["version"] == 1

    dst = BookmarkStore(tmp_path / "b.json")
    dst.add("book-1", 1_000, note="already here")  # duplicate position -> skipped
    added = dst.merge_bundle(bundle)
    assert added == 1  # only book-2's new bookmark
    assert [m.position_ms for m in dst.list("book-2")] == [2_000]
    # existing book-1 bookmark not duplicated
    assert len(dst.list("book-1")) == 1
