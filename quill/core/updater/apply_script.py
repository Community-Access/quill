"""The update helper's portable swap and health check, as batch lines (plan 6.6).

:func:`quill.core.self_update.build_apply_update_script` writes the helper; these
are the pieces release channels added to it, kept here so the helper's own
module stays small and each piece is tested -- as text, and by running the
batch for real against temp folders and stand-in processes
(``tests/unit/core/test_update_helper_runs.py``):

* :func:`swap_lines` -- a portable copy is updated by **swapping folders**, not
  by copying over itself: the new copy goes to ``<folder>.new``, the running
  copy is renamed ``<folder>.previous``, ``.new`` takes its place, and ``data``
  moves across. If any rename fails (a file still open), every step already
  taken is undone and the old in-place copy (``robocopy /MIR``) runs instead,
  exactly as before.
* :func:`health_lines` -- after relaunching, wait up to two minutes for the new
  version to say it started (:func:`quill.core.updater.apply.started_marker`).
  If it never does, stop whatever is still running from the app's folder and
  undo: swap the portable folders back, or run the kept installer of the
  previous version, write ``apply-result.json`` saying so, and start the
  previous version. An undo that cannot be completed puts everything back as
  it was and says so in the log; it never claims to have gone back.
* :func:`installer_lines` -- run an installer quietly and keep its exit code,
  so a failed install is reported as one instead of being "health-checked".

**Found by running it (2026-10-15).** Every portable zip ships a ``data``
folder (it is what marks the copy as portable), so moving the user's ``data``
"into" the new copy put it at ``data\\data``, where the app never looks: the
first portable update would have looked like it lost everything. The new
copy's own, empty ``data`` folder is now removed first, and the move is
checked. The installer was also started elevated (``-Verb RunAs``); every
QuillVille installer is per-user (``PrivilegesRequired=lowest``), so that
asked for an administrator for nothing, and for a standard user it installed
into the administrator's profile instead. Inno Setup elevates by itself when
the copy being updated was installed for all users.

Pure and wx-free: nothing here runs anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

__all__ = [
    "health_lines",
    "install_failed_lines",
    "installer_lines",
    "ps_single_quoted",
    "result_json",
    "stop_lines",
    "swap_lines",
]

#: The batch variable :func:`installer_lines` leaves the installer's exit code in.
INSTALL_RC = "INSTALLRC"


def ps_single_quoted(value: object) -> str:
    """*value* as a PowerShell single-quoted string literal.

    Inside single quotes PowerShell treats every character literally except
    the single quote itself, which is written twice. Without that, an installer
    kept under a profile folder named ``O'Brien`` ended the string early and
    the undo never ran.
    """
    return "'" + str(value).replace("'", "''") + "'"


def installer_lines(setup: Path, args: Sequence[str], *, label: str) -> list[str]:
    """Run *setup* with *args* (PowerShell literals), wait, keep its exit code.

    Not elevated: every QuillVille installer is per-user, and Inno Setup asks
    for elevation itself when the copy it updates was installed for all users.
    The exit code lands in ``%INSTALLRC%`` (0 means installed).
    """
    return [
        f'echo [apply] running {label} "{setup}" >>"%LOG%" 2>&1',
        f"set {INSTALL_RC}=1",
        # Reading .Handle before the wait is what makes Windows PowerShell keep
        # the exit code; without it ExitCode can come back empty.
        "powershell -NoProfile -NonInteractive -Command "
        f'"$p = Start-Process -FilePath {ps_single_quoted(setup)} '
        f"-ArgumentList {','.join(args)} -PassThru; $null = $p.Handle; "
        f'$p.WaitForExit(); exit $p.ExitCode" >>"%LOG%" 2>&1',
        f"set {INSTALL_RC}=%ERRORLEVEL%",
        f'echo [apply] {label} exit code %{INSTALL_RC}% >>"%LOG%" 2>&1',
    ]


def stop_lines(install_dir: Path) -> list[str]:
    """Stop every process still running from *install_dir* (the update that hung).

    Only programs whose own file is inside the app's folder: the app's
    launcher (whose job takes the shared runtime's process with it) or a
    portable copy's own interpreter. Nothing else on the computer is touched.
    """
    prefix = ps_single_quoted(f"{install_dir}\\")
    return [
        f'echo [apply] stopping anything still running from "{install_dir}" >>"%LOG%" 2>&1',
        "powershell -NoProfile -NonInteractive -Command "
        f'"Get-Process | Where-Object {{ $_.Path -and '
        f"$_.Path.StartsWith({prefix}, [System.StringComparison]::OrdinalIgnoreCase) }} "
        f'| Stop-Process -Force -ErrorAction SilentlyContinue" >>"%LOG%" 2>&1',
        # Give Windows a moment to let go of the files.
        "ping -n 3 127.0.0.1 >NUL",
    ]


def result_json(path: Path, *, version: str, failed_version: str, kind: str) -> str:
    """The ``echo`` that writes ``apply-result.json`` (*kind*: ``rolled_back``
    or ``install_failed``), read by :func:`quill.core.updater.apply.confirm_started`."""
    return (
        f'echo {{"version": "{version}", "{kind}": true, '
        f'"failed_version": "{failed_version}"}}> "{path}"'
    )


def install_failed_lines(
    *, result_file: Path | None, from_version: str, to_version: str, relaunch: str
) -> list[str]:
    """The ``:installfailed`` branch: the installer did not finish, so the old
    version is still installed. Say so in the log and to the app, start it again
    (when *relaunch* is a ``start`` line), and skip the health check."""
    lines = [
        "goto :installdone",
        ":installfailed",
        f"echo [apply] the update to {to_version or 'the new version'} was not installed; "
        'the version you had is unchanged >>"%LOG%" 2>&1',
    ]
    if result_file is not None:
        lines.append(
            result_json(
                result_file, version=from_version, failed_version=to_version, kind="install_failed"
            )
        )
    if relaunch:
        lines.append(relaunch)
    return [*lines, ":installdone"]


def swap_lines(
    *, source_dir: Path, install_dir: Path, data_dirname: str, mir_fallback: str
) -> list[str]:
    """Replace *install_dir* with *source_dir*, keeping ``.previous`` for an undo.

    The labels chain downwards, so a failure at any step falls through every
    undo below it: ``:swapdataback`` puts the new copy back in ``.new``,
    ``:swapback`` puts the old copy back, ``:swapundo`` puts the new copy back
    in staging, and ``:swapfailed`` copies in place instead.
    """
    new = f"{install_dir}.new"
    old = f"{install_dir}.previous"
    data_old = f"{old}\\{data_dirname}"
    data_new = f"{install_dir}\\{data_dirname}"
    return [
        f'echo [apply] swapping "{install_dir}" for the new copy >>"%LOG%" 2>&1',
        f'if exist "{new}" rmdir /S /Q "{new}" >>"%LOG%" 2>&1',
        f'if exist "{old}" rmdir /S /Q "{old}" >>"%LOG%" 2>&1',
        f'move "{source_dir}" "{new}" >>"%LOG%" 2>&1',
        "if errorlevel 1 goto :swapfailed",
        f'move "{install_dir}" "{old}" >>"%LOG%" 2>&1',
        "if errorlevel 1 goto :swapundo",
        f'move "{new}" "{install_dir}" >>"%LOG%" 2>&1',
        "if errorlevel 1 goto :swapback",
        # The user's data: replace the new copy's own (empty) data folder with
        # it. A copy with no data folder keeps the new one's, which is what
        # marks it portable.
        f'if not exist "{data_old}\\" goto :swapdone',
        f'if exist "{data_new}\\" rmdir /S /Q "{data_new}" >>"%LOG%" 2>&1',
        f'move "{data_old}" "{data_new}" >>"%LOG%" 2>&1',
        f'if exist "{data_old}\\" goto :swapdataback',
        ":swapdone",
        'echo [apply] swapped; the old copy is kept as .previous >>"%LOG%" 2>&1',
        "goto :swapped",
        ":swapdataback",
        'echo [apply] could not move your data across; putting the old copy back >>"%LOG%" 2>&1',
        f'move "{install_dir}" "{new}" >>"%LOG%" 2>&1',
        ":swapback",
        f'move "{old}" "{install_dir}" >>"%LOG%" 2>&1',
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
    failed = f"{install_dir}.failed"
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
    result = result_json(
        result_file, version=from_version, failed_version=to_version, kind="rolled_back"
    )
    if portable:
        data_failed = f"{failed}\\{data_dirname}"
        data_back = f"{install_dir}\\{data_dirname}"
        lines += [
            f'if not exist "{old}\\" goto :cannotundo',
            *stop_lines(install_dir),
            f'if exist "{failed}" rmdir /S /Q "{failed}" >>"%LOG%" 2>&1',
            f'move "{install_dir}" "{failed}" >>"%LOG%" 2>&1',
            "if errorlevel 1 goto :cannotundo",
            f'move "{old}" "{install_dir}" >>"%LOG%" 2>&1',
            "if errorlevel 1 goto :undoback",
            f'if not exist "{data_failed}\\" goto :undodone',
            f'if exist "{data_back}\\" rmdir /S /Q "{data_back}" >>"%LOG%" 2>&1',
            f'move "{data_failed}" "{data_back}" >>"%LOG%" 2>&1',
            f'if exist "{data_failed}\\" goto :undodataback',
            ":undodone",
            f'rmdir /S /Q "{failed}" >>"%LOG%" 2>&1',
            f'echo [apply] went back to {from_version} >>"%LOG%" 2>&1',
            result,
            relaunch,
            "goto :healthdone",
            ":undodataback",
            "echo [apply] could not move your data back; leaving the update in place "
            '>>"%LOG%" 2>&1',
            f'move "{install_dir}" "{old}" >>"%LOG%" 2>&1',
            ":undoback",
            f'move "{failed}" "{install_dir}" >>"%LOG%" 2>&1',
            "goto :cannotundo",
        ]
    elif rollback_setup is not None:
        args = ["'/VERYSILENT'", "'/SUPPRESSMSGBOXES'", "'/NORESTART'", *setup_args]
        lines += [
            f'if not exist "{rollback_setup}" goto :cannotundo',
            *stop_lines(install_dir),
            *installer_lines(rollback_setup, args, label=f"the installer of {from_version}"),
            f'if not "%{INSTALL_RC}%"=="0" goto :cannotundo',
            f'echo [apply] reinstalled {from_version} >>"%LOG%" 2>&1',
            result,
            relaunch,
            "goto :healthdone",
        ]
    lines += [
        ":cannotundo",
        'echo [apply] could not go back; leaving it as it is >>"%LOG%" 2>&1',
        "goto :healthdone",
        ":healthy",
        f'echo [apply] {to_version} started >>"%LOG%" 2>&1',
        ":healthdone",
    ]
    return lines
