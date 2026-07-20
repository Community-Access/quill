"""Large-file open guard (#1150)."""

from __future__ import annotations

from pathlib import Path

from quill.ui.large_file_guard import (
    LARGE_FILE_WARN_BYTES,
    human_size,
    is_large_file,
    large_file_warning,
)


def test_is_large_file_threshold() -> None:
    assert not is_large_file(0)
    assert not is_large_file(LARGE_FILE_WARN_BYTES - 1)
    assert is_large_file(LARGE_FILE_WARN_BYTES)
    assert is_large_file(32 * 1024 * 1024)  # the 32 MB report in #1150


def test_human_size() -> None:
    assert human_size(500) == "500 bytes"
    assert human_size(32 * 1024 * 1024) == "32.0 MB"
    assert human_size(1536 * 1024 * 1024).endswith("GB")


def test_large_file_warning_mentions_size_and_screen_reader() -> None:
    msg = large_file_warning("outbox.json", 32 * 1024 * 1024)
    assert "outbox.json" in msg and "32.0 MB" in msg
    assert "screen reader" in msg and "anyway" in msg.lower()


def _open_file_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )


def test_open_file_warns_and_reads_large_files_off_thread() -> None:
    """Regression #1150: open_file must warn before a large file and read it on
    a worker thread (not synchronously on the UI thread)."""
    src = _open_file_source()
    assert "large_file_guard" in src
    assert "Open large file?" in src
    # The large-file branch routes through the background task, like office/PDF.
    assert "#1150 Tier 2" in src and "_run_background_task" in src
