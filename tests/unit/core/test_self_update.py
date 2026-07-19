from __future__ import annotations

import subprocess as _subprocess
import sys as _sys
import zipfile
from pathlib import Path

import pytest

import quill.core.self_update as su
from quill.core.self_update import (
    SelfUpdateError,
    build_apply_update_script,
    install_root_and_exe,
    stage_portable_update,
)

# --- build_apply_update_script (pure) ---------------------------------------


def _portable_script() -> str:
    return build_apply_update_script(
        pid=4242,
        mode="portable",
        install_dir=Path(r"C:\Apps\QuillRadio"),
        exe_path=Path(r"C:\Apps\QuillRadio\QuillRadio.exe"),
        log_path=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\apply-update.log"),
        source_dir=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\staging\app"),
    )


def test_portable_script_waits_for_pid_then_copies_excluding_data_then_relaunches() -> None:
    script = _portable_script()
    assert "4242" in script
    assert "pid eq 4242" in script.lower()
    assert "robocopy" in script.lower()
    assert r'"C:\Apps\QuillRadio\data"' in script  # excluded via /XD
    assert "/xd" in script.lower()
    assert r'"C:\Apps\QuillRadio\QuillRadio.exe"' in script
    assert "apply-update.log" in script


def test_installer_script_runs_setup_elevated_and_silent_then_relaunches() -> None:
    script = build_apply_update_script(
        pid=99,
        mode="installer",
        install_dir=Path(r"C:\Program Files\Quill Radio"),
        exe_path=Path(r"C:\Program Files\Quill Radio\QuillRadio.exe"),
        log_path=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\apply-update.log"),
        setup_exe=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\Setup-2.0.3.exe"),
    )
    assert "Start-Process" in script
    assert "RunAs" in script
    assert "/VERYSILENT" in script
    assert "Setup-2.0.3.exe" in script
    assert r'"C:\Program Files\Quill Radio\QuillRadio.exe"' in script


def test_portable_mode_requires_source_dir() -> None:
    with pytest.raises(SelfUpdateError):
        build_apply_update_script(
            pid=1,
            mode="portable",
            install_dir=Path(r"C:\a"),
            exe_path=Path(r"C:\a\x.exe"),
            log_path=Path(r"C:\a\l.log"),
            source_dir=None,
        )


def test_installer_mode_requires_setup_exe() -> None:
    with pytest.raises(SelfUpdateError):
        build_apply_update_script(
            pid=1,
            mode="installer",
            install_dir=Path(r"C:\a"),
            exe_path=Path(r"C:\a\x.exe"),
            log_path=Path(r"C:\a\l.log"),
            setup_exe=None,
        )


# --- staging + install detection --------------------------------------------


def _make_zip(path: Path, arcnames: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name in arcnames:
            zf.writestr(name, b"x")


def test_stage_flat_layout_returns_root_with_exe(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["QuillRadio.exe", "tools/ffmpeg/ffmpeg.exe"])
    root = stage_portable_update(zip_path, tmp_path / "staging", exe_name="QuillRadio.exe")
    assert (root / "QuillRadio.exe").is_file()


def test_stage_descends_single_wrapping_folder(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["QuillRadio-2.0.3/QuillRadio.exe", "QuillRadio-2.0.3/docs/readme.txt"])
    root = stage_portable_update(zip_path, tmp_path / "staging", exe_name="QuillRadio.exe")
    assert root.name == "QuillRadio-2.0.3"
    assert (root / "QuillRadio.exe").is_file()


def test_stage_rejects_zip_without_exe(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["readme.txt"])
    with pytest.raises(SelfUpdateError):
        stage_portable_update(zip_path, tmp_path / "staging", exe_name="QuillRadio.exe")


def test_install_root_and_exe_is_none_in_dev_run() -> None:
    assert install_root_and_exe() is None


# --- begin_self_update orchestration ----------------------------------------


def test_begin_self_update_portable_stages_and_launches(tmp_path, monkeypatch) -> None:
    install = tmp_path / "install"
    (install / "data").mkdir(parents=True)
    (install / "QuillRadio.exe").write_bytes(b"old")
    monkeypatch.setattr(su, "install_root_and_exe", lambda: (install, install / "QuillRadio.exe"))

    zip_path = tmp_path / "updates" / "QuillRadio-Portable-2.0.3.zip"
    zip_path.parent.mkdir(parents=True)
    _make_zip(zip_path, ["QuillRadio.exe"])

    launched: dict = {}

    def _fake_launch(script, helper_dir):
        launched["script"] = script
        return helper_dir / "apply-update.bat"

    monkeypatch.setattr(su, "write_and_launch_helper", _fake_launch)

    su.begin_self_update(
        download_path=zip_path, portable=True, app_data_dir=tmp_path / "appdata", pid=1234
    )
    assert "robocopy" in launched["script"].lower()
    assert "1234" in launched["script"]
    assert (tmp_path / "appdata" / "updates" / "staging" / "QuillRadio.exe").is_file()


def test_begin_self_update_installer_builds_installer_script(tmp_path, monkeypatch) -> None:
    install = tmp_path / "install"
    install.mkdir(parents=True)
    (install / "QuillRadio.exe").write_bytes(b"old")
    monkeypatch.setattr(su, "install_root_and_exe", lambda: (install, install / "QuillRadio.exe"))
    setup = tmp_path / "updates" / "Setup-2.0.3.exe"
    setup.parent.mkdir(parents=True)
    setup.write_bytes(b"setup")
    captured: dict = {}

    def _fake_launch(script, helper_dir):
        captured["script"] = script
        return helper_dir / "apply-update.bat"

    monkeypatch.setattr(su, "write_and_launch_helper", _fake_launch)

    su.begin_self_update(
        download_path=setup, portable=False, app_data_dir=tmp_path / "appdata", pid=7
    )
    assert "/VERYSILENT" in captured["script"]
    assert "Setup-2.0.3.exe" in captured["script"]


def test_begin_self_update_raises_in_dev_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(su, "install_root_and_exe", lambda: None)
    with pytest.raises(SelfUpdateError):
        su.begin_self_update(
            download_path=tmp_path / "x.zip", portable=True, app_data_dir=tmp_path, pid=1
        )


# --- end-to-end helper batch (Windows only) ---------------------------------


@pytest.mark.skipif(not _sys.platform.startswith("win"), reason="Windows helper batch")
def test_portable_helper_batch_copies_and_preserves_data(tmp_path: Path) -> None:
    install = tmp_path / "install"
    (install / "data").mkdir(parents=True)
    (install / "QuillRadio.exe").write_text("OLD", encoding="utf-8")
    (install / "data" / "favorites.json").write_text("keep me", encoding="utf-8")

    source = tmp_path / "staging" / "app"
    source.mkdir(parents=True)
    (source / "QuillRadio.exe").write_text("NEW", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "readme.txt").write_text("hello", encoding="utf-8")

    log = tmp_path / "apply.log"
    # Relaunch target: a .cmd that exits immediately, so running the real script
    # end-to-end never opens a lingering console or steals focus on this box.
    relaunch = tmp_path / "relaunch.cmd"
    relaunch.write_text("@exit /b 0\r\n", encoding="utf-8")
    script = build_apply_update_script(
        pid=999999,  # already-gone PID: the wait loop falls straight through
        mode="portable",
        install_dir=install,
        exe_path=relaunch,
        log_path=log,
        source_dir=source,
    )
    bat = tmp_path / "apply-update.bat"
    bat.write_text(script, encoding="utf-8")
    _subprocess.run(["cmd.exe", "/c", str(bat)], check=False, timeout=60)

    assert (install / "QuillRadio.exe").read_text(encoding="utf-8") == "NEW"
    assert (install / "docs" / "readme.txt").read_text(encoding="utf-8") == "hello"
    assert (install / "data" / "favorites.json").read_text(encoding="utf-8") == "keep me"
