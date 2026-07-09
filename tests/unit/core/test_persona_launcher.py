"""Tests for Work Persona launch commands and shortcuts (#896)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quill.core.persona_launcher import build_launch_argv, write_launch_shortcut


def test_build_launch_argv_from_source_uses_module_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    argv = build_launch_argv("School")
    assert argv == [sys.executable, "-m", "quill", "--persona", "School"]


def test_build_launch_argv_frozen_runs_executable_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    argv = build_launch_argv("Work")
    assert argv == [sys.executable, "--persona", "Work"]


def test_write_launch_shortcut_creates_some_launchable_file(tmp_path: Path) -> None:
    path = write_launch_shortcut("Novel Writing", tmp_path)
    assert path.exists()
    assert path.suffix in (".lnk", ".bat")
    assert "Novel Writing" in path.stem


def test_write_launch_shortcut_falls_back_to_bat_without_pywin32(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "win32com.client":
            raise ImportError("simulated: pywin32 not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    path = write_launch_shortcut("Hobby", tmp_path)
    assert path.suffix == ".bat"
    content = path.read_text(encoding="utf-8")
    assert "--persona" in content
    assert "Hobby" in content


def test_shortcut_filename_strips_unsafe_characters(tmp_path: Path) -> None:
    path = write_launch_shortcut("Sci/Fi: Draft?", tmp_path)
    assert "/" not in path.name
    assert ":" not in path.name.replace(".lnk", "").replace(".bat", "")
    assert "?" not in path.name
