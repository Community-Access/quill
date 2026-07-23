"""Sibling-app launcher: the pure argv builder (from source it runs
``python -m quill.apps.<app>``), the unknown-key guard, and that launch_app is
best-effort (never raises, reports success/failure)."""

from __future__ import annotations

import sys

from quill.core import app_launcher


def test_build_argv_from_source_uses_dash_m(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert app_launcher.build_launch_argv("weather") == [sys.executable, "-m", "quill.apps.weather"]
    assert app_launcher.build_launch_argv("radio") == [sys.executable, "-m", "quill.apps.radio"]
    assert app_launcher.build_launch_argv("quill") == [sys.executable, "-m", "quill"]


def test_unknown_key_returns_none() -> None:
    assert app_launcher.build_launch_argv("nope") is None


def test_app_names() -> None:
    assert app_launcher.app_name("weather") == "Quill Weather"
    assert app_launcher.app_name("radio") == "Quill Radio"


def test_launch_app_unknown_key_is_false() -> None:
    assert app_launcher.launch_app("nope") is False


def test_launch_app_spawns_and_never_raises(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    spawned: dict = {}

    class _FakePopen:
        def __init__(self, argv, **kwargs):
            spawned["argv"] = argv

    monkeypatch.setattr("subprocess.Popen", _FakePopen)
    assert app_launcher.launch_app("weather") is True
    assert spawned["argv"][:2] == [sys.executable, "-m"]
    assert spawned["argv"][2] == "quill.apps.weather"


def test_launch_app_swallows_spawn_errors(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    def _boom(*_a, **_k):
        raise OSError("no exec")

    monkeypatch.setattr("subprocess.Popen", _boom)
    assert app_launcher.launch_app("weather") is False  # error -> False, not a crash
