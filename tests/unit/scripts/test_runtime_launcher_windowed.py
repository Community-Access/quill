"""The shared runtime's entry point survives a windowed (console-less) launch.

A listener's fresh Quill Radio install showed PyInstaller's "Unhandled
exception in script" box -- "'NoneType' object has no attribute 'write'" --
because a windowed process has sys.stdout/sys.stderr set to None (2026-09-27).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

_LAUNCHER = Path(__file__).resolve().parents[3] / "standalone" / "runtime" / "runtime_launcher.py"


def _load():
    spec = importlib.util.spec_from_file_location("quill_runtime_launcher_test", _LAUNCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def windowed(monkeypatch):
    launcher = _load()
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    told: list[str] = []
    monkeypatch.setattr(launcher, "_tell", lambda text, title="": told.append(text))
    return launcher, told


def test_no_module_is_explained_not_a_traceback(windowed, monkeypatch) -> None:
    launcher, told = windowed
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe"])

    assert launcher.main() == 2
    assert told and "not an app of its own" in told[0]
    assert sys.stderr is not None and sys.stdout is not None


def test_a_module_that_writes_to_stderr_runs(windowed, monkeypatch) -> None:
    launcher, told = windowed
    ran: list[str] = []

    def _run(module, **_kwargs):
        sys.stderr.write("noise a windowed app used to die on\n")
        sys.stdout.write("more noise\n")
        ran.append(module)

    monkeypatch.setattr(launcher.runpy, "run_module", _run)
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 0
    assert ran == ["quill.apps.radio"] and told == []


def test_a_relaunch_without_dash_m_still_starts_the_app(windowed, monkeypatch) -> None:
    launcher, _told = windowed
    ran: list[str] = []
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: ran.append(module))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "quill.apps.radio", "--safe-mode"])

    assert launcher.main() == 0
    assert ran == ["quill.apps.radio"]
    assert sys.argv == ["quill.apps.radio", "--safe-mode"]


def test_a_crash_is_saved_and_explained(windowed, monkeypatch, tmp_path) -> None:
    launcher, told = windowed
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    def _boom(module, **_kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(launcher.runpy, "run_module", _boom)
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 1
    reports = list((tmp_path / "QuillVille" / "Runtime" / "crash-reports").glob("crash-*.txt"))
    assert len(reports) == 1 and "kaboom" in reports[0].read_text(encoding="utf-8")
    assert told and "support@community-access.org" in told[0]
