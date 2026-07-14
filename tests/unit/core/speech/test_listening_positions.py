"""Tests for the remembered listening positions store."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.listening_positions import load_position_ms, save_position_ms


def test_round_trip_and_unknown(tmp_path: Path) -> None:
    book = tmp_path / "book.mp3"
    book.write_bytes(b"x" * 10)
    assert load_position_ms(tmp_path, book) == 0
    save_position_ms(tmp_path, book, 123_456)
    assert load_position_ms(tmp_path, book) == 123_456


def test_rebuilt_file_starts_fresh(tmp_path: Path) -> None:
    book = tmp_path / "book.mp3"
    book.write_bytes(b"x" * 10)
    save_position_ms(tmp_path, book, 60_000)
    book.write_bytes(b"y" * 999)  # size changed -> a different book
    assert load_position_ms(tmp_path, book) == 0


def test_broken_store_reads_as_empty(tmp_path: Path) -> None:
    (tmp_path / "listening_positions.json").write_text("junk", encoding="utf-8")
    book = tmp_path / "book.mp3"
    book.write_bytes(b"x")
    assert load_position_ms(tmp_path, book) == 0
    save_position_ms(tmp_path, book, 5_000)  # heals the store
    assert load_position_ms(tmp_path, book) == 5_000
