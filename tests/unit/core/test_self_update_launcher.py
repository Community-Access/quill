"""Updating a QuillVille app where the app really is, now or when it closes.

Reported 2026-09-28: a portable Quill Radio 3.x refused to install its own
update ("not a packaged build") and left the zip in ``updates``, because the
running Python is the bundle's ``pythonw.exe`` rather than a frozen app. The
app's launcher names its folder in ``QUILL_LAUNCHER_DIR``; that folder and that
launcher are what an update replaces and restarts. And "Install when I close"
waits for as long as the app stays open, applies, and does not restart.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import self_update
from quill.core.app_folders import app_folders
from quill.core.runtime_apps import app_for_module


def _launcher_env(tmp_path: Path, monkeypatch, name: str = "QuillRadio.exe") -> Path:
    exe = tmp_path / name
    exe.write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(tmp_path))
    monkeypatch.setattr(self_update, "main_module", lambda: "quill.apps.radio")
    return exe


def test_the_launcher_is_the_program_an_update_replaces(tmp_path, monkeypatch) -> None:
    exe = _launcher_env(tmp_path, monkeypatch)
    assert self_update.launcher_exe() == exe
    assert self_update.install_root_and_exe() == (tmp_path, exe)
    # Started bare: the launcher is the app, so no "-m" is appended.
    assert self_update.relaunch_command(exe) == []


def test_no_launcher_file_means_no_launcher(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(tmp_path))
    monkeypatch.setattr(self_update, "main_module", lambda: "quill.apps.radio")
    assert self_update.launcher_exe() is None


def test_every_runtime_app_knows_its_launcher_name() -> None:
    assert app_for_module("quill.apps.radio").launcher_exe == "QuillRadio.exe"
    assert app_for_module("quill.apps.lite").launcher_exe == "QuillLite.exe"


def _script(**kwargs) -> str:
    base = {
        "pid": 111,
        "mode": "portable",
        "install_dir": Path("C:/Apps/QuillRadio"),
        "exe_path": Path("C:/Apps/QuillRadio/QuillRadio.exe"),
        "log_path": Path("C:/Apps/QuillRadio/data/updates/apply-update.log"),
        "source_dir": Path("C:/Apps/QuillRadio/data/updates/staging/QuillRadio"),
    }
    base.update(kwargs)
    return self_update.build_apply_update_script(**base)


def test_install_now_waits_for_the_app_and_its_launcher_then_restarts() -> None:
    script = _script(also_wait_for=(222,))
    assert 'find " 111 "' in script and 'find " 222 "' in script
    assert "if %WAITED% LSS 60 goto :waitloop" in script
    assert 'start "" "C:\\Apps\\QuillRadio\\QuillRadio.exe"' in script.replace("/", "\\")
    assert '/XD "C:' in script  # the data folder is never touched


def test_install_when_i_close_waits_as_long_as_it_takes_and_does_not_restart() -> None:
    script = _script(relaunch=False, wait_limit_seconds=None)
    assert "LSS" not in script
    assert "goto :waitloop" in script
    assert 'start ""' not in script
    assert "updated on close" in script
    assert "robocopy" in script


def test_the_apps_folder_is_the_launchers_first(tmp_path) -> None:
    folders = app_folders(
        env={"QUILL_LAUNCHER_DIR": str(tmp_path)},
        executable=str(Path("C:/Runtime/3.13/QuillVilleRuntime.exe")),
    )
    assert folders[0] == tmp_path
    assert folders[1].name == "3.13"


def test_without_a_launcher_the_programs_own_folder_is_used(tmp_path) -> None:
    exe = tmp_path / "pythonw.exe"
    assert app_folders(env={}, executable=str(exe)) == [tmp_path]
