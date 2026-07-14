"""Unit tests for git/gh executable resolution and the subprocess allowlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import git_binaries
from quill.core.git_binaries import GitBinaryError, resolve_gh, resolve_git, validate_executable


def test_validate_executable_accepts_known_basenames() -> None:
    for name in ("git", "git.exe", "gh", "gh.exe"):
        validate_executable(Path(f"/usr/bin/{name}"))  # must not raise


def test_validate_executable_rejects_unknown_basename() -> None:
    with pytest.raises(GitBinaryError, match="not a recognized"):
        validate_executable(Path("/usr/bin/rm"))


def test_resolve_git_prefers_system_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: f"/usr/bin/{name}")
    result = resolve_git()
    assert result == Path("/usr/bin/git")


def test_resolve_gh_prefers_system_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: f"/usr/bin/{name}")
    result = resolve_gh()
    assert result == Path("/usr/bin/gh")


def test_resolve_git_falls_back_to_vendor_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # MinGit's git.exe lives nested under cmd/, alongside sibling etc/,
    # mingw64/, usr/ folders it needs at runtime -- see the "git-windows"
    # ASSETS entry in quill.core.release_assets.
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: None)
    vendor = tmp_path / "vendor" / "git"
    (vendor / "cmd").mkdir(parents=True)
    exe_name = "git.exe" if git_binaries.sys.platform == "win32" else "git"
    (vendor / "cmd" / exe_name).write_text("", encoding="utf-8")
    monkeypatch.setattr(git_binaries, "_vendor_dir", lambda: vendor)
    result = resolve_git()
    assert result == vendor / "cmd" / exe_name


def test_resolve_gh_falls_back_to_flat_vendor_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: None)
    vendor = tmp_path / "vendor" / "git"
    vendor.mkdir(parents=True)
    exe_name = "gh.exe" if git_binaries.sys.platform == "win32" else "gh"
    (vendor / exe_name).write_text("", encoding="utf-8")
    monkeypatch.setattr(git_binaries, "_vendor_dir", lambda: vendor)
    result = resolve_gh()
    assert result == vendor / exe_name


def test_resolve_git_returns_none_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: None)
    monkeypatch.setattr(git_binaries, "_vendor_dir", lambda: tmp_path / "nope")
    assert resolve_git() is None
    assert resolve_gh() is None


def test_git_available_and_gh_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert git_binaries.git_available() is True
    assert git_binaries.gh_available() is True
    monkeypatch.setattr(git_binaries.shutil, "which", lambda name: None)
    monkeypatch.setattr(git_binaries, "_vendor_dir", lambda: Path("/nonexistent"))
    assert git_binaries.git_available() is False
    assert git_binaries.gh_available() is False
