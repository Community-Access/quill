"""Tests for the Audio Studio recently-played history store (Phase 2 port-in)."""

from __future__ import annotations

from pathlib import Path

from quill.core.audio_studio.history import (
    AudioStudioHistory,
    PlayedBook,
    load_history,
    save_history,
)


def test_record_moves_to_front_and_dedups() -> None:
    h = AudioStudioHistory()
    h.record("a", title="A", position_ms=100, chapter=1)
    h.record("b", title="B", position_ms=200, chapter=0)
    h.record("a", title="A", position_ms=300, chapter=2)
    assert [b.path for b in h.books] == ["a", "b"]
    assert h.books[0].position_ms == 300 and h.books[0].chapter == 2


def test_cap_at_15() -> None:
    h = AudioStudioHistory()
    for i in range(20):
        h.record(f"b{i}", title=f"T{i}", position_ms=0, chapter=0)
    assert len(h.books) == 15
    # Most recent first: b19 should be at the front.
    assert h.books[0].path == "b19"


def test_last_played() -> None:
    h = AudioStudioHistory()
    assert h.last_played is None
    h.record("a", title="A", position_ms=0, chapter=0)
    assert h.last_played is not None
    assert h.last_played.path == "a"


def test_resume_on_launch_defaults_true() -> None:
    assert AudioStudioHistory().resume_on_launch is True


def test_round_trip(tmp_path: Path) -> None:
    h = AudioStudioHistory(resume_on_launch=False)
    h.record("a", title="A", position_ms=50, chapter=3)
    save_history(tmp_path, h)
    got = load_history(tmp_path)
    assert got.resume_on_launch is False
    assert got.last_played is not None
    assert got.last_played.path == "a" and got.last_played.chapter == 3
    assert got.last_played.position_ms == 50


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    got = load_history(tmp_path)
    assert got.books == []
    assert got.resume_on_launch is True  # default


def test_load_broken_file_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "audio_studio_history.json").write_text("{not json", encoding="utf-8")
    got = load_history(tmp_path)
    assert got.books == []


def test_played_book_from_dict_rejects_missing_path() -> None:
    assert PlayedBook.from_dict({"title": "x"}) is None
    assert PlayedBook.from_dict("nope") is None


def test_record_ignores_empty_path() -> None:
    h = AudioStudioHistory()
    h.record("", title="", position_ms=0, chapter=0)
    assert h.books == []
