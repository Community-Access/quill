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


def test_frozen_sibling_not_installed_returns_none(monkeypatch, tmp_path) -> None:
    # A frozen build whose sibling .exe is NOT next to it (the app was installed
    # on its own -- e.g. Quill Radio present but Quill Weather never installed,
    # and the reverse) must report "cannot launch" rather than guess a path.
    # The running exe is a neutral name so it is not itself a Radio/Weather
    # candidate; no sibling exes exist beside it.
    running = tmp_path / "Launcher.exe"
    running.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(running), raising=False)
    assert app_launcher.build_launch_argv("weather") is None
    assert app_launcher.build_launch_argv("radio") is None
    assert app_launcher.launch_app("weather") is False
    assert app_launcher.launch_app("radio") is False


def test_frozen_sibling_installed_alongside_launches(monkeypatch, tmp_path) -> None:
    # When the sibling .exe IS present next to the running app, launch it by path.
    (tmp_path / "QuillRadio.exe").write_bytes(b"MZ")
    (tmp_path / "QuillWeather.exe").write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "QuillRadio.exe"), raising=False)
    assert app_launcher.build_launch_argv("weather") == [str(tmp_path / "QuillWeather.exe")]
    assert app_launcher.build_launch_argv("radio") == [str(tmp_path / "QuillRadio.exe")]


def test_frozen_portable_sibling_in_adjacent_folder_launches(monkeypatch, tmp_path) -> None:
    # Portable layout: each app in its own folder under a shared parent, e.g.
    #   USB\QuillRadio\QuillRadio.exe   and   USB\QuillWeather\QuillWeather.exe
    # Radio must find Weather one level over (its own folder is not enough).
    (tmp_path / "QuillRadio").mkdir()
    (tmp_path / "QuillRadio" / "QuillRadio.exe").write_bytes(b"MZ")
    (tmp_path / "QuillWeather").mkdir()
    (tmp_path / "QuillWeather" / "QuillWeather.exe").write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "QuillRadio" / "QuillRadio.exe"), raising=False
    )
    assert app_launcher.build_launch_argv("weather") == [
        str(tmp_path / "QuillWeather" / "QuillWeather.exe")
    ]
    # And the reverse direction (Weather finding Radio) from Weather's folder.
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "QuillWeather" / "QuillWeather.exe"), raising=False
    )
    assert app_launcher.build_launch_argv("radio") == [
        str(tmp_path / "QuillRadio" / "QuillRadio.exe")
    ]


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
