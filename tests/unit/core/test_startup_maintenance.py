from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.startup_maintenance import (
    MAINTENANCE_EPOCH,
    run_pending_startup_maintenance,
)


def _seed(data_dir: Path) -> None:
    for name in ("logs", "crash-reports", "diagnostics"):
        sub = data_dir / name
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "old.txt").write_text("stale", encoding="utf-8")
    (data_dir / "logs" / "nested").mkdir()
    (data_dir / "logs" / "nested" / "more.log").write_text("x", encoding="utf-8")


def test_clears_diagnostic_clutter_but_keeps_user_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _seed(tmp_path)
    # User data that must survive.
    (tmp_path / "autosave").mkdir()
    (tmp_path / "autosave" / "draft.quill").write_text("my work", encoding="utf-8")
    (tmp_path / "settings.json").write_text("{}", encoding="utf-8")

    run_pending_startup_maintenance()

    # Diagnostic dirs are emptied (the dirs themselves remain).
    for name in ("logs", "crash-reports", "diagnostics"):
        assert (tmp_path / name).is_dir()
        assert list((tmp_path / name).rglob("*")) == []
    # User data untouched.
    assert (tmp_path / "autosave" / "draft.quill").read_text(encoding="utf-8") == "my work"
    assert (tmp_path / "settings.json").exists()
    # Marker records the completed epoch.
    marker = json.loads((tmp_path / "startup-maintenance.json").read_text(encoding="utf-8"))
    assert marker["epoch"] == MAINTENANCE_EPOCH


def test_runs_at_most_once_per_epoch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    # Marker already at the current epoch: a freshly written log must survive.
    (tmp_path / "startup-maintenance.json").write_text(
        json.dumps({"epoch": MAINTENANCE_EPOCH}), encoding="utf-8"
    )
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "today.log").write_text("keep me", encoding="utf-8")

    run_pending_startup_maintenance()

    assert (tmp_path / "logs" / "today.log").read_text(encoding="utf-8") == "keep me"


def test_safe_on_fresh_install_with_no_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    run_pending_startup_maintenance()  # must not raise
    marker = json.loads((tmp_path / "startup-maintenance.json").read_text(encoding="utf-8"))
    assert marker["epoch"] == MAINTENANCE_EPOCH
