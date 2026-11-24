"""Finding and verifying the native Copilot SDK runtime shipped with QUILL."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from quill.core.ai import copilot_runtime as rt


def _plant(root: Path, *, runtime: bytes = b"pinned runtime") -> Path:
    directory = root / "tools" / "copilot"
    directory.mkdir(parents=True)
    path = directory / rt.COPILOT_RUNTIME_NODE
    path.write_bytes(runtime)
    return path


@pytest.fixture
def pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    digest = hashlib.sha256(b"pinned runtime").hexdigest()
    monkeypatch.setattr(rt, "COPILOT_RUNTIME_NODE_SHA256", digest)


@pytest.fixture
def no_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, absent_env) -> Path:
    absent_env("QUILL_APP_ROOT", rt.SDK_RUNTIME_PATH_ENV)
    fake_python = tmp_path / "runtime" / "python.exe"
    fake_python.parent.mkdir()
    monkeypatch.setattr(sys, "executable", str(fake_python))
    return fake_python.parent


def test_none_when_the_build_carries_no_runtime(no_overrides: Path) -> None:
    assert rt.find_copilot_runtime() is None
    with pytest.raises(rt.CopilotRuntimeUnavailable, match="missing from this copy of the app"):
        rt.runtime_path_for_launch()


def test_found_beside_the_interpreter(no_overrides: Path) -> None:
    runtime = _plant(no_overrides)
    assert rt.find_copilot_runtime() == runtime


def test_app_root_is_tried_first(no_overrides: Path, monkeypatch, tmp_path: Path) -> None:
    _plant(no_overrides)
    app_root = tmp_path / "app"
    preferred = _plant(app_root)
    monkeypatch.setenv("QUILL_APP_ROOT", str(app_root))
    assert rt.copilot_runtime_search_dirs()[0] == app_root / "tools" / "copilot"
    assert rt.find_copilot_runtime() == preferred


def test_never_searches_path(no_overrides: Path, monkeypatch, tmp_path: Path) -> None:
    on_path = tmp_path / "bin"
    on_path.mkdir()
    (on_path / rt.COPILOT_RUNTIME_NODE).write_bytes(b"pinned runtime")
    monkeypatch.setenv("PATH", str(on_path))
    assert rt.find_copilot_runtime() is None


def test_empty_runtime_is_unavailable(no_overrides: Path) -> None:
    runtime = _plant(no_overrides, runtime=b"")
    assert rt.find_copilot_runtime() is None
    assert rt.copilot_runtime_matches_pin(runtime) is False


def test_runtime_pin_accepts_only_the_pinned_library(pinned: None, tmp_path: Path) -> None:
    good = _plant(tmp_path / "good")
    other = _plant(tmp_path / "other", runtime=b"another runtime")
    assert rt.copilot_runtime_matches_pin(good) is True
    assert rt.copilot_runtime_matches_pin(other) is False
    assert rt.copilot_runtime_matches_pin(tmp_path / "missing" / rt.COPILOT_RUNTIME_NODE) is False


def test_explicit_runtime_path_is_verified(pinned: None, monkeypatch, tmp_path: Path) -> None:
    runtime = _plant(tmp_path)
    monkeypatch.setenv(rt.SDK_RUNTIME_PATH_ENV, str(runtime))
    assert rt.runtime_path_for_launch() == runtime


def test_invalid_explicit_runtime_fails_instead_of_downloading(
    pinned: None, monkeypatch, tmp_path: Path
) -> None:
    runtime = _plant(tmp_path, runtime=b"untrusted")
    monkeypatch.setenv(rt.SDK_RUNTIME_PATH_ENV, str(runtime))
    with pytest.raises(rt.CopilotRuntimeUnverified, match=rt.COPILOT_RUNTIME_VERSION):
        rt.runtime_path_for_launch()


def test_stale_explicit_path_falls_back_to_bundled_runtime(
    no_overrides: Path, pinned: None, monkeypatch, tmp_path: Path
) -> None:
    runtime = _plant(no_overrides)
    monkeypatch.setenv(rt.SDK_RUNTIME_PATH_ENV, str(tmp_path / "missing" / "runtime.node"))
    assert rt.runtime_path_for_launch() == runtime


def test_prepare_directs_sdk_to_verified_library(
    pinned: None, no_overrides: Path, monkeypatch
) -> None:
    runtime = _plant(no_overrides)
    assert rt.prepare_inprocess_runtime() == runtime
    assert rt.SDK_RUNTIME_PATH_ENV in os.environ
    assert os.environ[rt.SDK_RUNTIME_PATH_ENV] == str(runtime)


def test_release_runtime_pin_is_explicit() -> None:
    assert rt.COPILOT_RUNTIME_VERSION == "1.0.114"
    assert rt.COPILOT_RUNTIME_PLATFORM == "win32-x64"
    assert len(rt.COPILOT_RUNTIME_NODE_SHA256) == 64
    assert rt.COPILOT_RUNTIME_NODE_SHA256 == rt.COPILOT_RUNTIME_NODE_SHA256.lower()
