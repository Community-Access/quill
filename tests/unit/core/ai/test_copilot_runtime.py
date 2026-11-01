"""Finding the bundled Copilot CLI, and the environment its child gets."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

from quill.core.ai import copilot_runtime as rt


def _plant(root: Path) -> Path:
    exe = root / "tools" / "copilot" / rt.COPILOT_EXE
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    return exe


@pytest.fixture
def no_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, absent_env) -> Path:
    absent_env("QUILL_APP_ROOT", "COPILOT_CLI_PATH")
    fake_python = tmp_path / "runtime" / "python.exe"
    fake_python.parent.mkdir()
    monkeypatch.setattr(sys, "executable", str(fake_python))
    return fake_python.parent


def test_none_when_the_build_carries_no_cli(no_overrides: Path) -> None:
    assert rt.find_copilot_cli() is None
    assert rt.resolve_cli_path() is None


def test_found_beside_the_interpreter(no_overrides: Path) -> None:
    exe = _plant(no_overrides)
    assert rt.find_copilot_cli() == exe


def test_app_root_is_tried_first(no_overrides: Path, monkeypatch, tmp_path: Path) -> None:
    _plant(no_overrides)
    app_root = tmp_path / "app"
    preferred = _plant(app_root)
    monkeypatch.setenv("QUILL_APP_ROOT", str(app_root))
    assert rt.copilot_search_dirs()[0] == app_root / "tools" / "copilot"
    assert rt.find_copilot_cli() == preferred


def test_never_searches_path(no_overrides: Path, monkeypatch, tmp_path: Path) -> None:
    on_path = tmp_path / "bin"
    on_path.mkdir()
    (on_path / rt.COPILOT_EXE).write_bytes(b"")
    monkeypatch.setenv("PATH", str(on_path))
    assert rt.find_copilot_cli() is None


def test_cli_path_override_wins_only_when_it_exists(
    no_overrides: Path, monkeypatch, tmp_path: Path
) -> None:
    bundled = _plant(no_overrides)
    monkeypatch.setenv("COPILOT_CLI_PATH", str(tmp_path / "missing.exe"))
    assert rt.resolve_cli_path() == bundled
    dev = tmp_path / "dev-copilot.exe"
    dev.write_bytes(b"")
    monkeypatch.setenv("COPILOT_CLI_PATH", str(dev))
    assert rt.resolve_cli_path() == dev


def test_child_env_carries_no_token_and_pins_the_binary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "gho_leak")
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "gho_leak")
    exe = tmp_path / "copilot.exe"
    env = rt.copilot_child_env(exe)
    assert "GITHUB_TOKEN" not in env
    assert "COPILOT_GITHUB_TOKEN" not in env
    assert env["COPILOT_SKIP_CLI_DOWNLOAD"] == "1"
    assert env["COPILOT_CLI_PATH"] == str(exe)


def test_child_env_without_a_binary_adds_nothing(monkeypatch, absent_env) -> None:
    absent_env("COPILOT_SKIP_CLI_DOWNLOAD")
    env = rt.copilot_child_env(None)
    assert "COPILOT_SKIP_CLI_DOWNLOAD" not in env


def test_pin_matches_only_the_pinned_bytes(monkeypatch, tmp_path: Path) -> None:
    good = tmp_path / "good.exe"
    good.write_bytes(b"MZ pinned")
    bad = tmp_path / "bad.exe"
    bad.write_bytes(b"MZ other")
    monkeypatch.setattr(rt, "COPILOT_EXE_SHA256", hashlib.sha256(b"MZ pinned").hexdigest())
    assert rt.copilot_cli_matches_pin(good) is True
    assert rt.copilot_cli_matches_pin(bad) is False
    assert rt.copilot_cli_matches_pin(tmp_path / "missing.exe") is False


def test_launch_path_refuses_an_unpinned_bundle(no_overrides: Path) -> None:
    _plant(no_overrides)  # empty file: never the pinned exe
    with pytest.raises(rt.CopilotCliUnverified):
        rt.cli_path_for_launch()


def test_launch_path_is_none_without_a_bundle(no_overrides: Path) -> None:
    assert rt.cli_path_for_launch() is None


def test_pin_is_the_one_the_build_stages() -> None:
    assert rt.COPILOT_CLI_VERSION == "1.0.105"
    assert len(rt.COPILOT_EXE_SHA256) == 64
