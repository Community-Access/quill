"""Apply an already-downloaded Quill update and relaunch, on Windows.

A running .exe cannot overwrite itself, so applying a portable update means
handing the swap to a tiny external helper that runs after this process exits.
This module builds that helper (a pure, unit-tested batch script), stages the
downloaded zip, and launches the helper detached. Every Quill app's update flow
(``quill.ui.app_shell`` for Radio/Cast, ``quill.ui.main_frame_updates`` for
QUILL, and Quill Social's own frame) calls :func:`begin_self_update` from its
post-download dialog and then closes the window; the helper waits for this PID
to exit before touching a single file. wx-free, strict-typed, Windows-only in
effect (a dev or non-frozen run reports nothing to apply and callers fall back
to revealing the download).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from quill.core.error_codes import CodedError

#: How many ~1s poll iterations the helper waits for the app to exit before
#: proceeding anyway. The app is expected to exit within a second or two of
#: launching the helper; the ceiling only prevents a wedged process from
#: stranding the helper forever (robocopy then just retries any locked file).
_PID_WAIT_SECONDS = 60


class SelfUpdateError(CodedError):
    """A downloaded update could not be staged or applied."""

    code = "QUILL-UPDATE-SELF-APPLY"


def build_apply_update_script(
    *,
    pid: int,
    mode: str,
    install_dir: Path,
    exe_path: Path,
    log_path: Path,
    source_dir: Path | None = None,
    setup_exe: Path | None = None,
    data_dirname: str = "data",
) -> str:
    """The Windows ``.bat`` that applies an update after this process exits (pure).

    ``mode="portable"``: robocopy ``source_dir`` over ``install_dir`` excluding
    the ``data_dirname`` folder (favorites/recordings/settings survive), then
    relaunch ``exe_path``. ``mode="installer"``: run ``setup_exe`` elevated and
    silent, then relaunch. Both wait for ``pid`` to exit first and tee every
    step to ``log_path``.
    """
    if mode == "portable" and source_dir is None:
        raise SelfUpdateError("Portable apply needs a staged source directory.")
    if mode == "installer" and setup_exe is None:
        raise SelfUpdateError("Installer apply needs the setup executable.")

    data_dir = install_dir / data_dirname
    lines = [
        "@echo off",
        "setlocal",
        # Put the real Windows tools first so tasklist/find/robocopy/ping/
        # powershell always resolve to System32, never a shadowing copy earlier
        # on PATH (a polluted PATH or a hijack).
        'set "PATH=%SystemRoot%\\System32;%SystemRoot%\\System32\\WindowsPowerShell\\v1.0;%PATH%"',
        f'set "LOG={log_path}"',
        f'echo [apply] start pid={pid} mode={mode} >>"%LOG%" 2>&1',
        # Wait for the app process to exit (up to the ceiling), then proceed.
        "set /a WAITED=0",
        ":waitloop",
        f'tasklist /FI "PID eq {pid}" 2>NUL | find " {pid} " >NUL',
        "if errorlevel 1 goto :exited",
        "ping -n 2 127.0.0.1 >NUL",
        "set /a WAITED+=1",
        f"if %WAITED% LSS {_PID_WAIT_SECONDS} goto :waitloop",
        ":exited",
        'echo [apply] app exited (waited %WAITED%s) >>"%LOG%" 2>&1',
    ]
    if mode == "portable":
        lines += [
            f'echo [apply] robocopy "{source_dir}" -> "{install_dir}" (xd data) >>"%LOG%" 2>&1',
            # /IS forces same-size/same-timestamp files to be overwritten too, so
            # the install becomes exactly the new version -- never skipping a
            # changed-but-same-size file (and making the swap deterministic).
            f'robocopy "{source_dir}" "{install_dir}" /MIR /IS /XD "{data_dir}" '
            f'/R:2 /W:1 /NP >>"%LOG%" 2>&1',
            'echo [apply] robocopy exit %ERRORLEVEL% >>"%LOG%" 2>&1',
        ]
    else:
        lines += [
            f'echo [apply] running installer "{setup_exe}" >>"%LOG%" 2>&1',
            "powershell -NoProfile -Command "
            f"\"Start-Process -FilePath '{setup_exe}' "
            "-ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' "
            f'-Verb RunAs -Wait" >>"%LOG%" 2>&1',
            'echo [apply] installer done %ERRORLEVEL% >>"%LOG%" 2>&1',
        ]
    lines += [
        f'echo [apply] relaunching "{exe_path}" >>"%LOG%" 2>&1',
        f'start "" "{exe_path}"',
    ]
    if mode == "portable" and source_dir is not None:
        # Delete the staging *parent* (…/staging) so a re-run starts clean.
        lines.append(f'rmdir /S /Q "{source_dir.parent}" >>"%LOG%" 2>&1')
    lines += [
        'echo [apply] done >>"%LOG%" 2>&1',
        # Delete the running batch on exit (self-cleanup).
        '(goto) 2>nul & del "%~f0"',
    ]
    return "\r\n".join(lines) + "\r\n"


def install_root_and_exe() -> tuple[Path, Path] | None:
    """The frozen exe and its install directory, or ``None`` in a dev run.

    ``sys.frozen`` is set only in a PyInstaller build; ``sys.executable`` is
    then the app exe (QuillRadio.exe / QUILLCast.exe / quill.exe / ...). A dev
    run (``python -m quill``) returns ``None`` so callers fall back to reveal.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    return exe.parent, exe


def stage_portable_update(zip_path: Path, staging_root: Path, *, exe_name: str) -> Path:
    """Extract a portable update zip and return the dir that holds ``exe_name``.

    Extracts into ``staging_root`` (cleared first) using the zip-slip- and
    bomb-guarded :func:`quill.core.updates.extract_portable_update`. If the zip
    wraps everything in a single top-level folder, descends into it. Raises
    :class:`SelfUpdateError` if no ``exe_name`` is found -- so a wrong/corrupt
    asset never drives a swap that would break the install.
    """
    import shutil

    from quill.core.updates import extract_portable_update

    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    try:
        extract_portable_update(zip_path, staging_root)
    except Exception as exc:  # noqa: BLE001 - surface as a coded error
        raise SelfUpdateError(f"Could not extract the update: {exc}") from exc
    if (staging_root / exe_name).is_file():
        return staging_root
    entries = list(staging_root.iterdir())
    if len(entries) == 1 and entries[0].is_dir() and (entries[0] / exe_name).is_file():
        return entries[0]
    raise SelfUpdateError(
        f"The downloaded update does not contain {exe_name}; not applying it."
    )


def write_and_launch_helper(script_text: str, helper_dir: Path) -> Path:
    """Write ``apply-update.bat`` into ``helper_dir`` and launch it detached.

    ``helper_dir`` MUST be outside the install directory (the system temp dir),
    so overwriting the install never clobbers the running helper. Launched with
    no console window and fully detached so it outlives this process.
    """
    helper_dir.mkdir(parents=True, exist_ok=True)
    helper = helper_dir / "apply-update.bat"
    helper.write_text(script_text, encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
        )
    subprocess.Popen(  # noqa: S603 - our own generated script at a fixed path
        ["cmd.exe", "/c", str(helper)],
        creationflags=creationflags,
        close_fds=True,
        cwd=str(helper_dir),
    )
    return helper


def begin_self_update(
    *,
    download_path: Path,
    portable: bool,
    app_data_dir: Path,
    pid: int | None = None,
) -> None:
    """Apply the already-downloaded update at ``download_path`` and relaunch.

    Stages a portable zip (or targets the setup exe), builds the helper script,
    and launches it detached. Raises :class:`SelfUpdateError` if this is not a
    packaged build or the asset can't be staged -- the caller then leaves the
    app running. On success the caller closes the window; the helper waits for
    this process to exit before applying anything.
    """
    import tempfile

    target = install_root_and_exe()
    if target is None:
        raise SelfUpdateError("This is not a packaged build; nothing to update in place.")
    install_dir, exe_path = target
    updates_dir = app_data_dir / "updates"
    log_path = updates_dir / "apply-update.log"
    resolved_pid = os.getpid() if pid is None else pid

    if portable:
        staging = updates_dir / "staging"
        source = stage_portable_update(download_path, staging, exe_name=exe_path.name)
        script = build_apply_update_script(
            pid=resolved_pid,
            mode="portable",
            install_dir=install_dir,
            exe_path=exe_path,
            log_path=log_path,
            source_dir=source,
        )
    else:
        script = build_apply_update_script(
            pid=resolved_pid,
            mode="installer",
            install_dir=install_dir,
            exe_path=exe_path,
            log_path=log_path,
            setup_exe=download_path,
        )
    helper_dir = Path(tempfile.gettempdir()) / "quill-apply-update"
    write_and_launch_helper(script, helper_dir)


__all__ = [
    "SelfUpdateError",
    "begin_self_update",
    "build_apply_update_script",
    "install_root_and_exe",
    "stage_portable_update",
    "write_and_launch_helper",
]
