"""Tests for the Audio Studio chapter play queue store (Phase 2 port-in)."""

from __future__ import annotations

from pathlib import Path

from quill.core.audio_studio.play_queue import (
    PlayQueue,
    QueueEntry,
    add,
    at,
    clear,
    load_queue,
    next_entry,
    remove,
    save_queue,
)


def test_add_append_dedup() -> None:
    q = PlayQueue()
    add(q, QueueEntry("a", "A"))
    add(q, QueueEntry("a", "A"))  # dup
    add(q, QueueEntry("b", "B"))
    assert [e.path for e in q.entries] == ["a", "b"]


def test_next_advances_and_wraps() -> None:
    q = PlayQueue(current_index=-1)
    add(q, QueueEntry("a", "A"))
    add(q, QueueEntry("b", "B"))
    assert next_entry(q).path == "a"
    assert next_entry(q).path == "b"
    assert next_entry(q).path == "a"  # wrap


def test_next_on_empty_returns_none() -> None:
    q = PlayQueue()
    assert next_entry(q) is None


def test_at_out_of_range_returns_none() -> None:
    q = PlayQueue()
    add(q, QueueEntry("a", "A"))
    assert at(q, 5) is None
    assert at(q, 0).path == "a"


def test_remove_and_clear_and_round_trip(tmp_path: Path) -> None:
    q = PlayQueue()
    add(q, QueueEntry("a", "A"))
    add(q, QueueEntry("b", "B"))
    remove(q, "a")
    assert [e.path for e in q.entries] == ["b"]
    clear(q)
    assert q.is_empty
    add(q, QueueEntry("c", "C"))
    save_queue(tmp_path, q)
    assert load_queue(tmp_path).entries[0].path == "c"


def test_round_trip_preserves_current_index(tmp_path: Path) -> None:
    q = PlayQueue()
    add(q, QueueEntry("a", "A"))
    add(q, QueueEntry("b", "B"))
    next_entry(q)
    next_entry(q)  # current_index == 1
    save_queue(tmp_path, q)
    got = load_queue(tmp_path)
    assert got.current_index == 1
    assert got.entries[1].path == "b"


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    got = load_queue(tmp_path)
    assert got.is_empty
    assert got.current_index == -1


def test_load_broken_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "audio_studio_play_queue.json").write_text("{bad", encoding="utf-8")
    assert load_queue(tmp_path).is_empty
