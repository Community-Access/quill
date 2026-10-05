"""Local Media's store: round trip, migration, missing files, and its edits.

The store keeps paths and the tags read from them, never file contents; a
missing file stays in its place and is said to be missing. The edits are pure
list arithmetic and are pinned here row by row, because "move a gapped block
down" is exactly the kind of thing that is easy to get subtly wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.radio import local_media
from quill.core.radio import local_media_edit as edit
from quill.core.radio.local_media import (
    SCHEMA_VERSION,
    LocalMediaLibrary,
    load_library,
    save_library,
    summary,
)
from quill.core.radio.play_queue import PlayQueue


def _library(tmp_path: Path, count: int = 4) -> LocalMediaLibrary:
    library = LocalMediaLibrary()
    playlist = library.add_playlist("Road Trip", now=1.0)
    for index in range(1, count + 1):
        path = tmp_path / f"{index:02d} Song {index}.mp3"
        path.write_bytes(b"x")
        playlist.items.append(
            playlist.make_item(path, title=f"Song {index}", duration_seconds=60, now=float(index))
        )
    return library


def test_round_trip_keeps_order_tags_and_switches(tmp_path: Path) -> None:
    library = _library(tmp_path)
    playlist = library.playlists[0]
    playlist.shuffle, playlist.repeat, playlist.last_item_id = True, "all", 3
    playlist.items[0].artist = "The Band"
    save_library(library, tmp_path)
    raw = json.loads((tmp_path / local_media.FILE_NAME).read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    assert "contents" not in json.dumps(raw), "paths and tags only, never file bytes"
    read = load_library(tmp_path).playlists[0]
    assert [item.title for item in read.items] == ["Song 1", "Song 2", "Song 3", "Song 4"]
    assert read.items[0].artist == "The Band"
    assert (read.shuffle, read.repeat, read.last_item_id) == (True, "all", 3)
    assert read.next_item_id == 5


def test_a_pre_release_file_migrates_once_with_a_backup(tmp_path: Path, quill_data_dir) -> None:
    legacy = {
        "playlists": [
            {"name": "Old", "files": [str(tmp_path / "a.mp3"), str(tmp_path / "b.flac")]},
            {"name": "Odd", "items": [{"id": 3, "path": "c.mp3"}, {"id": 3, "path": "d.mp3"}]},
        ]
    }
    store = tmp_path / local_media.FILE_NAME
    store.write_text(json.dumps(legacy), encoding="utf-8")
    library = load_library(tmp_path)
    old, odd = library.playlists
    assert [item.file_name for item in old.items] == ["a.mp3", "b.flac"]
    assert [item.id for item in old.items] == [1, 2]
    assert len({item.id for item in odd.items}) == 2, "a duplicate id is given a fresh one"
    rewritten = json.loads(store.read_text(encoding="utf-8"))
    assert rewritten["schema_version"] == SCHEMA_VERSION


def test_a_newer_file_is_read_but_never_downgraded(tmp_path: Path) -> None:
    newer = {"schema_version": SCHEMA_VERSION + 1, "playlists": [{"name": "X", "items": []}]}
    store = tmp_path / local_media.FILE_NAME
    store.write_text(json.dumps(newer), encoding="utf-8")
    assert load_library(tmp_path).playlists[0].name == "X"
    assert json.loads(store.read_text(encoding="utf-8")) == newer


def test_a_missing_file_stays_in_place_and_is_said(tmp_path: Path) -> None:
    library = _library(tmp_path)
    playlist = library.playlists[0]
    (tmp_path / "02 Song 2.mp3").unlink()
    assert [item.title for item in playlist.missing()] == ["Song 2"]
    assert playlist.items[1].title == "Song 2", "never dropped from its place"
    assert summary(playlist) == "4 items, 4 minutes, 1 missing"


def test_names_are_unique_and_files_are_recognised() -> None:
    library = LocalMediaLibrary()
    library.add_playlist("Jazz")
    assert library.add_playlist("jazz").name == "jazz 2"
    assert local_media.is_media_file("x.FLAC") and local_media.is_media_file("film.mkv")
    assert not local_media.is_media_file("notes.txt")
    assert local_media.title_from_filename("03_my-song.mp3") == "03 my-song"


# --- edits --------------------------------------------------------------------------


ROWS = ["a", "b", "c", "d", "e", "f"]


def test_move_by_moves_a_block_and_stops_at_the_ends() -> None:
    assert edit.move_by(ROWS, [1], -1) == (["b", "a", "c", "d", "e", "f"], [0])
    assert edit.move_by(ROWS, [0], -1) == (ROWS, [0]), "already at the top"
    assert edit.move_by(ROWS, [1, 2], 1) == (["a", "d", "b", "c", "e", "f"], [2, 3])
    assert edit.move_by(ROWS, [4, 5], 1) == (ROWS, [4, 5]), "already at the bottom"


def test_a_gapped_selection_closes_up_as_it_moves() -> None:
    moved, rows = edit.move_by(ROWS, [1, 4], 1)
    assert moved == ["a", "c", "b", "e", "d", "f"]
    assert rows == [2, 3]


def test_move_to_top_bottom_and_a_position() -> None:
    assert edit.move_to(ROWS, [3, 4], 0) == (["d", "e", "a", "b", "c", "f"], [0, 1])
    assert edit.move_to(ROWS, [0], 10**9) == (["b", "c", "d", "e", "f", "a"], [5])
    assert edit.move_to(ROWS, [5], 2) == (["a", "b", "f", "c", "d", "e"], [2])


def test_insert_before_and_after_and_remove() -> None:
    assert edit.insert_at(ROWS, ["x", "y"], 2) == (["a", "b", "x", "y", "c", "d", "e", "f"], [2, 3])
    assert edit.insert_at(ROWS, ["x"], 6) == ([*ROWS, "x"], [6]), "after the last"
    kept, removed = edit.remove_at(ROWS, [4, 1, 1, 99])
    assert kept == ["a", "c", "d", "f"]
    assert removed == [(1, "b"), (4, "e")]


def test_restore_order_keeps_items_added_since(tmp_path: Path) -> None:
    playlist = _library(tmp_path).playlists[0]
    before = playlist.ids()
    playlist.items = edit.sort_items(playlist.items, "title")[::-1]
    playlist.items.append(playlist.make_item(tmp_path / "new.mp3"))
    restored = edit.restore_order(playlist.items, before)
    assert [item.id for item in restored] == [1, 2, 3, 4, 5]


def test_sorts_are_stable_and_unknown_lengths_go_last(tmp_path: Path) -> None:
    playlist = _library(tmp_path).playlists[0]
    playlist.items[0].duration_seconds = 0
    playlist.items[3].duration_seconds = 10
    by_length = edit.sort_items(playlist.items, "length")
    assert [item.title for item in by_length] == ["Song 4", "Song 2", "Song 3", "Song 1"]
    shuffled = edit.sort_items(playlist.items, "random", shuffler=lambda rows: rows.reverse())
    assert [item.title for item in shuffled] == ["Song 4", "Song 3", "Song 2", "Song 1"]


def test_the_moved_sentence_counts_from_one() -> None:
    assert edit.moved_sentence([2], 12) == "Moved to 3 of 12."
    assert edit.moved_sentence([3, 4, 5], 12) == "Moved 3 items to 4 to 6 of 12."


# --- the shared queue, following an edited list ---------------------------------------


def test_follow_keeps_the_shuffled_order_through_an_edit() -> None:
    queue = PlayQueue(shuffle=True)
    queue.set_rows([1, 2, 3, 4], shuffler=lambda rows: rows.reverse())
    assert queue.order == [4, 3, 2, 1]
    queue.follow([2, 1, 3, 4, 5], shuffler=lambda rows: None)  # a move, and an add
    assert queue.order == [4, 3, 2, 1, 5], "stable until reshuffled; new ones join the end"
    queue.follow([1, 3, 5])
    assert queue.order == [3, 1, 5]


def test_follow_with_shuffle_off_is_the_list_order() -> None:
    queue = PlayQueue()
    queue.follow([3, 1, 2])
    assert queue.order == [3, 1, 2]
