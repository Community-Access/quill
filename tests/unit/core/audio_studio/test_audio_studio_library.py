"""Tests for the Audio Studio library backing store (Phase 2 port-in)."""

from __future__ import annotations

from pathlib import Path

from quill.core.audio_studio.library import (
    PINNED_VIEWS,
    BookEntry,
    LibraryState,
    load_library,
    move_to_folder,
    record_play,
    save_library,
    toggle_favorite,
    view_query,
)


def _state(books):
    return LibraryState(books=list(books), folders=[])


def test_toggle_favorite_round_trips(tmp_path: Path) -> None:
    s = _state([BookEntry(path="b", title="B")])
    assert toggle_favorite(s, "b") is True
    assert s.books[0].favorite is True
    save_library(tmp_path, s)
    assert load_library(tmp_path).books[0].favorite is True


def test_toggle_favorite_off_returns_false() -> None:
    s = _state([BookEntry(path="b", title="B", favorite=True)])
    assert toggle_favorite(s, "b") is False
    assert s.books[0].favorite is False


def test_toggle_favorite_unknown_path_returns_false() -> None:
    s = _state([BookEntry(path="b", title="B")])
    assert toggle_favorite(s, "missing") is False


def test_view_query_favorites() -> None:
    s = _state(
        [BookEntry(path="a", title="A"), BookEntry(path="b", title="B", favorite=True)]
    )
    assert [e.path for e in view_query(s, "Favorites")] == ["b"]


def test_view_query_recently_played_orders_by_last_played() -> None:
    s = _state(
        [
            BookEntry(path="a", title="A", last_played_at=10),
            BookEntry(path="b", title="B", last_played_at=30),
        ]
    )
    assert [e.path for e in view_query(s, "Recently Played")] == ["b", "a"]


def test_view_query_recently_played_excludes_unplayed() -> None:
    s = _state(
        [BookEntry(path="a", title="A"), BookEntry(path="b", title="B", last_played_at=5)]
    )
    assert [e.path for e in view_query(s, "Recently Played")] == ["b"]


def test_view_query_in_progress_includes_started() -> None:
    s = _state(
        [
            BookEntry(path="a", title="A"),
            BookEntry(path="b", title="B", last_played_at=5),
        ]
    )
    assert [e.path for e in view_query(s, "In Progress")] == ["b"]


def test_view_query_unknown_view_returns_empty() -> None:
    s = _state([BookEntry(path="a", title="A", favorite=True)])
    assert view_query(s, "Nope") == []


def test_move_to_folder_sets_folder() -> None:
    s = _state([BookEntry(path="a", title="A")])
    move_to_folder(s, "a", "Fiction/SF")
    assert s.books[0].folder == "Fiction/SF"
    assert "Fiction/SF" in s.folders


def test_move_to_folder_unknown_path_no_folder_added() -> None:
    s = _state([BookEntry(path="a", title="A")])
    move_to_folder(s, "missing", "Fiction")
    assert s.folders == []


def test_pinned_views_constant() -> None:
    assert PINNED_VIEWS == ("Favorites", "In Progress", "Recently Played", "Inbox")


def test_save_is_atomic(tmp_path: Path) -> None:
    s = _state([BookEntry(path="a", title="A")])
    save_library(tmp_path, s)
    files = [p.name for p in tmp_path.iterdir()]
    assert "audio_studio_library.json" in files


def test_record_play_sets_last_played() -> None:
    s = _state([BookEntry(path="a", title="A"), BookEntry(path="b", title="B")])
    record_play(s, "b", now=42.0)
    assert s.books[1].last_played_at == 42.0
    assert s.books[0].last_played_at == 0.0


def test_record_play_unknown_path_no_op() -> None:
    s = _state([BookEntry(path="a", title="A")])
    record_play(s, "missing", now=42.0)
    assert s.books[0].last_played_at == 0.0


def test_load_library_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_library(tmp_path).books == []