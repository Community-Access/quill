"""Tests for the Crash Recovery dialog's Clear Logs helper."""

from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame


def _frame() -> MainFrame:
    return MainFrame.__new__(MainFrame)


def test_clear_recovery_logs_removes_files_and_counts(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "quill.log").write_text("a", encoding="utf-8")
    (logs / "startup-errors.log").write_text("b", encoding="utf-8")
    (logs / "old.log").write_text("c", encoding="utf-8")

    removed = _frame()._clear_recovery_logs(logs)

    assert removed == 3
    assert list(logs.iterdir()) == []


def test_clear_recovery_logs_empty_folder_returns_zero(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    assert _frame()._clear_recovery_logs(logs) == 0


def test_clear_recovery_logs_missing_folder_returns_zero(tmp_path: Path) -> None:
    assert _frame()._clear_recovery_logs(tmp_path / "nope") == 0


def test_clear_recovery_logs_ignores_subdirectories(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "a.log").write_text("x", encoding="utf-8")
    (logs / "archive").mkdir()

    removed = _frame()._clear_recovery_logs(logs)

    assert removed == 1
    assert (logs / "archive").is_dir()
