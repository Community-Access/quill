"""The update helper's portable swap and health check, as batch lines (plan 6.6).

:func:`quill.core.self_update.build_apply_update_script` writes the helper; these
are the two pieces release channels added to it, kept here so the helper's own
module stays small and each piece is tested as text:

* :func:`swap_lines` -- a portable copy is updated by **swapping folders**, not
  by copying over itself: the new copy goes to ``<folder>.new``, the running
  copy is renamed ``<folder>.previous``, ``.new`` takes its place, and ``data``
  moves across. If the rename fails (a file still open), the old in-place copy
  (``robocopy /MIR``) runs instead, exactly as before.
* :func:`health_lines` -- after relaunching, wait up to two minutes for the new
  version to say it started (:func:`quill.core.updater.apply.started_marker`).
  If it never does, undo: swap the portable folders back, or run the kept
  installer of the previous version, write ``apply-result.json`` saying so, and
  start the previous version.

Pure and wx-free: nothing here runs anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

__all__ = ["health_lines", "swap_lines"]


def swap_lines(
    *, source_dir: Path, install_dir: Path, data_dirname: str, mir_fallback: str
) -> list[str]:
    """Replace *install_dir* with *source_dir*, keeping ``.previous`` for an undo."""
    new = f"{install_dir}.new"
    old = f"{install_dir}.previous"
    return [
        f'echo [apply] swapping "{install_dir}" for the new copy >>"%LOG%" 2>&1',
        f'if exist "{new}" rmdir /S /Q "{new}" >>"%LOG%" 2>&1',
        f'if exist "{old}" rmdir /S /Q "{old}" >>"%LOG%" 2>&1',
        f'move "{source_dir}" "{new}" >>"%LOG%" 2>&1',
        "if errorlevel 1 goto :swapfailed",
        f'move "{install_dir}" "{old}" >>"%LOG%" 2>&1',
        "if errorlevel 1 goto :swapundo",
        f'move "{new}" "{install_dir}" >>"%LOG%" 2>&1',
        f'move "{old}\\{data_dirname}" "{install_dir}\\{data_dirname}" >>"%LOG%" 2>&1',
        'echo [apply] swapped; the old copy is kept as .previous >>"%LOG%" 2>&1',
        "goto :swapped",
        ":swapundo",
        f'move "{new}" "{source_dir}" >>"%LOG%" 2>&1',
        ":swapfailed",
        'echo [apply] could not swap folders; copying in place instead >>"%LOG%" 2>&1',
        mir_fallback,
        ":swapped",
    ]


def health_lines(
    *,
    marker: Path,
    result_file: Path,
    from_version: str,
    to_version: str,
    relaunch: str,
    portable: bool,
    install_dir: Path,
    data_dirname: str = "data",
    rollback_setup: Path | None = None,
    setup_args: Sequence[str] = (),
    wait_seconds: int = 120,
) -> list[str]:
    """Wait for *marker*; undo the update when it never appears.

    *relaunch* is the helper's ``start`` line for the app. An installed copy
    with no kept installer cannot be undone: it records the failure and stops.
    """
    old = f"{install_dir}.previous"
    lines = [
        f'echo [apply] waiting up to {wait_seconds}s for {to_version} to start >>"%LOG%" 2>&1',
        "set /a HEALTH=0",
        ":healthloop",
        f'if exist "{marker}" goto :healthy',
        "ping -n 2 127.0.0.1 >NUL",
        "set /a HEALTH+=1",
        f"if %HEALTH% LSS {wait_seconds} goto :healthloop",
        f'echo [apply] {to_version} did not start in time >>"%LOG%" 2>&1',
    ]
    result = (
        f'echo {{"version": "{from_version}", "rolled_back": true, '
        f'"failed_version": "{to_version}"}}> "{result_file}"'
    )
    if portable:
        lines += [
            f'if not exist "{old}" goto :cannotundo',
            f'move "{install_dir}\\{data_dirname}" "{old}\\{data_dirname}" >>"%LOG%" 2>&1',
            f'move "{install_dir}" "{install_dir}.failed" >>"%LOG%" 2>&1',
            f'move "{old}" "{install_dir}" >>"%LOG%" 2>&1',
            f'echo [apply] went back to {from_version} >>"%LOG%" 2>&1',
            result,
            relaunch,
            "goto :healthdone",
        ]
    elif rollback_setup is not None:
        args = ",".join(["'/VERYSILENT'", "'/SUPPRESSMSGBOXES'", "'/NORESTART'", *setup_args])
        lines += [
            f'echo [apply] reinstalling {from_version} from "{rollback_setup}" >>"%LOG%" 2>&1',
            "powershell -NoProfile -Command "
            f"\"Start-Process -FilePath '{rollback_setup}' -ArgumentList {args} "
            f'-Verb RunAs -Wait" >>"%LOG%" 2>&1',
            result,
            relaunch,
            "goto :healthdone",
        ]
    lines += [
        ":cannotundo",
        'echo [apply] nothing to go back to; leaving it as it is >>"%LOG%" 2>&1',
        "goto :healthdone",
        ":healthy",
        f'echo [apply] {to_version} started >>"%LOG%" 2>&1',
        ":healthdone",
    ]
    return lines
