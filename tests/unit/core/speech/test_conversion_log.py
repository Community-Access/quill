"""Tests for the wx-free batch conversion log and the word-count helper."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from quill.core.speech.batch_export import count_document_words, count_words
from quill.core.speech.conversion_log import (
    NullConversionLog,
    default_log_path,
    open_conversion_log,
)


def test_default_log_path_is_timestamped_inside_folder(tmp_path: Path) -> None:
    when = datetime(2026, 6, 26, 9, 5, 30)
    path = default_log_path(tmp_path, now=when)
    assert path.parent == tmp_path
    assert path.name == "quill-batch-speech-20260626-090530.log"


def test_open_conversion_log_creates_folder_and_writes_header(tmp_path: Path) -> None:
    out = tmp_path / "book"  # does not exist yet
    log = open_conversion_log(out, title="Batch export to speech")
    try:
        assert out.is_dir()  # the folder is created before conversion
        assert log.path.is_file()
        log.log("first document")
    finally:
        log.close()
    text = log.path.read_text(encoding="utf-8")
    assert "Batch export to speech — log opened" in text
    assert "first document" in text


def test_conversion_log_close_is_idempotent(tmp_path: Path) -> None:
    log = open_conversion_log(tmp_path)
    log.close()
    log.close()  # second close must not raise
    log.log("after close")  # writing after close is a silent no-op


def test_null_conversion_log_swallows_everything() -> None:
    log = NullConversionLog()
    log.log("ignored")
    log.close()  # no file, no error


def test_count_words_and_document(tmp_path: Path) -> None:
    assert count_words("one two three") == 3
    assert count_words("   ") == 0
    doc = tmp_path / "doc.txt"
    doc.write_text("alpha beta gamma delta", encoding="utf-8")
    assert count_document_words(doc) == 4
    # An unreadable / missing file contributes 0 rather than raising.
    assert count_document_words(tmp_path / "missing.txt") == 0
