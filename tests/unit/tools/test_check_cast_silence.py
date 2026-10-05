"""GATE-CAST-SILENT: a Cast status line or failure that says nothing fails the build."""

from __future__ import annotations

from pathlib import Path

from quill.tools import check_cast_silence


def test_the_tree_is_clean() -> None:
    assert check_cast_silence.scan() == []


def _scan(tmp_path: Path, monkeypatch, source: str) -> list[str]:
    monkeypatch.setattr(check_cast_silence, "_REPO_ROOT", tmp_path)
    target = tmp_path / "quill" / "ui" / "podcasts" / "x.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return [v.reason for v in check_cast_silence.scan_file(target)]


def test_a_direct_status_write_is_caught(tmp_path: Path, monkeypatch) -> None:
    assert _scan(tmp_path, monkeypatch, "self._status.SetLabel('Done')\n")
    assert not _scan(tmp_path, monkeypatch, "self._title.SetLabel('Done')\n")


def test_a_silent_failure_handler_is_caught(tmp_path: Path, monkeypatch) -> None:
    silent = "tasks.submit('x', work, on_failure=lambda *_a: None)\n"
    logs_only = (
        "def _failed(_op, error):\n    _log.warning('x %s', error)\n\n"
        "tasks.submit('x', work, on_failure=_failed)\n"
    )
    speaks = "tasks.submit('x', work, on_failure=lambda _o, e: report_failure(host, str(e)))\n"
    assert _scan(tmp_path, monkeypatch, silent)
    assert _scan(tmp_path, monkeypatch, logs_only)
    assert not _scan(tmp_path, monkeypatch, speaks)
