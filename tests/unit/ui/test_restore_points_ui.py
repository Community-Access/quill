"""Restore Previous Version: labels, the save hook, and wiring contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.restore_points import RestorePoint
from quill.ui.main_frame import MainFrame
from quill.ui.main_frame_restore_points import (
    RestorePointsMixin,
    restore_point_label,
)

_ROOT = Path(__file__).resolve().parents[3]
_SOURCE = (_ROOT / "quill" / "ui" / "main_frame.py").read_text(encoding="utf-8")
_MENU_SOURCE = (_ROOT / "quill" / "ui" / "main_frame_menu.py").read_text(encoding="utf-8")


def _point(saved_at: datetime, words: int = 2341, source: str = "save") -> RestorePoint:
    return RestorePoint(
        content_hash="abc123",
        saved_at=saved_at.isoformat(),
        word_count=words,
        size_bytes=10,
        source=source,
    )


def test_labels_are_speakable() -> None:
    now = datetime.now(UTC)
    assert restore_point_label(_point(now)).startswith("Today at ")
    assert restore_point_label(_point(now - timedelta(days=1))).startswith("Yesterday at ")
    old = restore_point_label(_point(now - timedelta(days=30)))
    assert "at" in old and "2,341 words" in old
    assert restore_point_label(_point(now, words=1)).endswith("1 word")
    assert restore_point_label(_point(now, source="restore")).endswith("(before a restore)")


def _frame(tmp_path: Path, enabled: bool = True) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(restore_points_enabled=enabled, restore_points_max_mb=200)
    return frame


def test_save_hook_records_and_prunes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.record_restore_point",
        lambda path, text, *, source: calls.append(f"record:{source}") or object(),
    )
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.prune_restore_points",
        lambda path, *, max_total_mb: calls.append(f"prune:{max_total_mb}"),
    )
    frame = _frame(tmp_path)
    document = SimpleNamespace(path=tmp_path / "a.md", text="hello")
    frame._record_save_restore_point(document)
    assert calls == ["record:save", "prune:200"]


def test_save_hook_respects_disabled_setting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.record_restore_point",
        lambda *a, **k: pytest.fail("must not record when disabled"),
    )
    frame = _frame(tmp_path, enabled=False)
    frame._record_save_restore_point(SimpleNamespace(path=tmp_path / "a.md", text="x"))


def test_save_hook_never_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A restore-point failure must never be the reason a save fails.
    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("quill.ui.main_frame_restore_points.record_restore_point", _boom)
    frame = _frame(tmp_path)
    frame._record_save_restore_point(SimpleNamespace(path=tmp_path / "a.md", text="x"))


def test_save_hook_skips_unsaved_documents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.record_restore_point",
        lambda *a, **k: pytest.fail("must not record without a path"),
    )
    _frame(tmp_path)._record_save_restore_point(SimpleNamespace(path=None, text="x"))


def test_main_frame_mixes_in_restore_points() -> None:
    assert issubclass(MainFrame, RestorePointsMixin)
    assert "self.register_restore_point_commands()" in _SOURCE


def test_every_save_records_a_restore_point() -> None:
    start = _SOURCE.index("def _write_document_to_disk(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "self._record_save_restore_point(document)" in body


def test_file_menu_offers_restore_previous_version() -> None:
    assert "Restore Previous &Version..." in _MENU_SOURCE
    assert "self.restore_previous_version()" in _MENU_SOURCE
