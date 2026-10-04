"""Apply an already-downloaded Quill update and relaunch, on Windows.

A running .exe cannot overwrite itself, so applying a portable update means
handing the swap to a tiny external helper that runs after this process exits.
This module builds that helper (a pure, unit-tested batch script), stages the
downloaded zip, and launches the helper detached. Every Quill app's update flow
(``quill.ui.app_shell`` for Radio/Cast, ``quill.ui.main_frame_updates`` for
QUILL, and Quill Social's own frame) calls :func:`begin_self_update` from its
post-download dialog and then closes the window; the helper waits for this PID
to exit before touching a single file. wx-free, strict-typed, Windows-only in
effect (a dev run reports nothing to apply and callers fall back to revealing
the download).

**Where the app is** (3.0.3). Since the shared runtime, the running Python is
not the app: an installed QuillVille app runs ``QuillVilleRuntime.exe`` from
the runtime folder, and a portable one runs its bundle's ``pythonw.exe``, which
is not a frozen build at all -- so the portable updater refused with "not a
packaged build" and left the zip in ``updates`` for somebody to unpack by hand
(reported 2026-09-28). The app's own launcher (``QuillRadio.exe``,
``QuillLite.exe``) exports its folder as ``QUILL_LAUNCHER_DIR``; that folder and
that exe are what an update replaces and what it starts again.

**Update when I close.** ``when="on_close"`` stages the same helper but tells it
to wait for as long as the app stays open, then apply the update and *not*
restart: the next time the app is opened, it is the new version.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from quill.core.app_command import GENERIC_INTERPRETERS
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
    relaunch_args: Sequence[str] = (),
    also_wait_for: Sequence[int] = (),
    relaunch: bool = True,
    wait_limit_seconds: int | None = _PID_WAIT_SECONDS,
    channel: str = "",
    setup_log: Path | None = None,
    swap: bool = False,
    health_marker: Path | None = None,
    result_file: Path | None = None,
    from_version: str = "",
    to_version: str = "",
    rollback_setup: Path | None = None,
) -> str:
    """The Windows ``.bat`` that applies an update after this process exits (pure).

    ``mode="portable"``: robocopy ``source_dir`` over ``install_dir`` excluding
    the ``data_dirname`` folder (favorites/recordings/settings survive), then
    relaunch ``exe_path``. ``mode="installer"``: run ``setup_exe`` elevated and
    silent, then relaunch. Both wait for ``pid`` to exit first and tee every
    step to ``log_path``.

    ``relaunch_args`` are appended to the relaunch, and without them the restart
    half of "Install and restart now" silently stopped working the day the
    shared runtime landed (2026-08-17). ``exe_path`` is ``sys.executable``, which
    used to be the app's own frozen exe and is now a *generic interpreter*:
    ``QuillVilleRuntime.exe`` for an installed QuillVille app, ``pythonw.exe``
    inside a portable bundle. Started bare, the runtime prints a usage line and
    exits 2 -- invisibly, since it is a windowed build -- and bare ``pythonw.exe``
    opens an interpreter with no script. The update applied correctly and the
    app simply never came back. See :func:`relaunch_command`.

    ``also_wait_for`` are more processes that must be gone first -- the app's
    launcher, which holds ``QuillRadio.exe`` open until the app exits.
    ``relaunch=False`` with ``wait_limit_seconds=None`` is "update when I
    close": wait however long the app stays open, apply, and leave it closed.

    ``channel`` (release channels, plan 6.6) is passed to the installer as
    ``/CHANNEL=<channel>``, which puts a shared-runtime app's runtime in that
    channel's slot (``installer/shared-runtime.iss``); ``setup_log`` becomes
    ``/LOG="<path>"`` so a failed install leaves Inno's own account of it.

    Phase 4 of release channels: ``swap=True`` updates a portable copy by
    swapping folders (``.previous`` kept for an undo) instead of copying over
    itself; ``health_marker`` makes the helper wait for the relaunched app to
    say it started, and undo the update -- the ``.previous`` folder, or
    ``rollback_setup`` for an installed copy -- when it never does
    (:mod:`quill.core.updater.apply_script`).
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
        # Wait for the app (and its launcher) to exit -- up to the ceiling, or
        # for as long as it takes when the update is to happen on close.
        "set /a WAITED=0",
        ":waitloop",
    ]
    for waited_pid in (pid, *also_wait_for):
        lines += [
            f'tasklist /FI "PID eq {waited_pid}" 2>NUL | find " {waited_pid} " >NUL',
            "if not errorlevel 1 goto :stillrunning",
        ]
    lines += [
        "goto :exited",
        ":stillrunning",
        "ping -n 2 127.0.0.1 >NUL",
        "set /a WAITED+=1",
    ]
    if wait_limit_seconds is None:
        lines.append("goto :waitloop")
    else:
        lines.append(f"if %WAITED% LSS {wait_limit_seconds} goto :waitloop")
    lines += [
        ":exited",
        'echo [apply] app exited (waited %WAITED%s) >>"%LOG%" 2>&1',
    ]
    if mode == "portable":
        # /IS forces same-size/same-timestamp files to be overwritten too, so
        # the install becomes exactly the new version -- never skipping a
        # changed-but-same-size file (and making the swap deterministic).
        mirror = (
            f'robocopy "{source_dir}" "{install_dir}" /MIR /IS /XD "{data_dir}" '
            f'/R:2 /W:1 /NP >>"%LOG%" 2>&1'
        )
        if swap and source_dir is not None:
            from quill.core.updater.apply_script import swap_lines

            lines += swap_lines(
                source_dir=source_dir,
                install_dir=install_dir,
                data_dirname=data_dirname,
                mir_fallback=mirror,
            )
        else:
            lines += [
                f'echo [apply] robocopy "{source_dir}" -> "{install_dir}" (xd data) >>"%LOG%" 2>&1',
                mirror,
                'echo [apply] robocopy exit %ERRORLEVEL% >>"%LOG%" 2>&1',
            ]
    else:
        setup_args = ["'/VERYSILENT'", "'/SUPPRESSMSGBOXES'", "'/NORESTART'"]
        if channel:
            setup_args.append(f"'/CHANNEL={channel}'")
        if setup_log is not None:
            setup_args.append(f'\'/LOG=""{setup_log}""\'')
        lines += [
            f'echo [apply] running installer "{setup_exe}" >>"%LOG%" 2>&1',
            "powershell -NoProfile -Command "
            f"\"Start-Process -FilePath '{setup_exe}' "
            f"-ArgumentList {','.join(setup_args)} "
            f'-Verb RunAs -Wait" >>"%LOG%" 2>&1',
            'echo [apply] installer done %ERRORLEVEL% >>"%LOG%" 2>&1',
        ]
    # Quoted only when it needs to be: a module name never contains a space, and
    # an unquoted "-m quill.apps.lite" is what the Start Menu shortcut passes and
    # what the apply log should show.
    arguments = " ".join(f'"{arg}"' if (not arg or " " in arg) else arg for arg in relaunch_args)
    if relaunch:
        start = f'start "" "{exe_path}" {arguments}'.rstrip()
        lines += [
            f'echo [apply] relaunching "{exe_path}" {arguments} >>"%LOG%" 2>&1',
            start,
        ]
        if health_marker is not None and result_file is not None:
            from quill.core.updater.apply_script import health_lines

            lines += health_lines(
                marker=health_marker,
                result_file=result_file,
                from_version=from_version,
                to_version=to_version,
                relaunch=start,
                portable=mode == "portable",
                install_dir=install_dir,
                data_dirname=data_dirname,
                rollback_setup=rollback_setup,
                setup_args=[f"'/CHANNEL={channel}'"] if channel else [],
            )
    else:
        lines.append('echo [apply] not relaunching: updated on close >>"%LOG%" 2>&1')
    if mode == "portable" and source_dir is not None:
        # Delete the staging *parent* (…/staging) so a re-run starts clean.
        lines.append(f'rmdir /S /Q "{source_dir.parent}" >>"%LOG%" 2>&1')
    lines += [
        'echo [apply] done >>"%LOG%" 2>&1',
        # Delete the running batch on exit (self-cleanup).
        '(goto) 2>nul & del "%~f0"',
    ]
    return "\r\n".join(lines) + "\r\n"


def launcher_exe(env: dict[str, str] | None = None) -> Path | None:
    """The app's own launcher (``QuillRadio.exe``), when it started this app.

    The launcher exports its folder as ``QUILL_LAUNCHER_DIR``; its file name is
    the app's (``quill.core.runtime_apps``). ``None`` for a dev run, for an app
    started some other way, or when the file is not where it should be.
    """
    from quill.core.runtime_apps import app_for_module

    folder = ((os.environ if env is None else env).get("QUILL_LAUNCHER_DIR") or "").strip()
    app = app_for_module(main_module())
    if not folder or app is None:
        return None
    exe = Path(folder) / app.launcher_exe
    return exe if exe.is_file() else None


def install_root_and_exe() -> tuple[Path, Path] | None:
    """The app's program and the folder it lives in, or ``None`` in a dev run.

    The app's own launcher first (see the module docstring for why the running
    Python is no longer the answer); otherwise a frozen build's own exe
    (QUILL's ``quill.exe``). A dev run (``python -m quill``) returns ``None`` so
    callers fall back to revealing the download.
    """
    launcher = launcher_exe()
    if launcher is not None:
        return launcher.parent, launcher
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    return exe.parent, exe


#: Executables that are an *interpreter*, not an app: started with no arguments
#: they do nothing a user can see. The shared QuillVille runtime is one of these
#: by design -- it exists to be handed ``-m <module>`` (see
#: ``standalone/runtime/runtime_launcher.py``), and every installed QuillVille
#: shortcut passes it one.
#: One list, shared with :mod:`quill.core.app_command` (autostart, wake task).
_GENERIC_INTERPRETERS = GENERIC_INTERPRETERS


def main_module() -> str:
    """The module this process was started as (``quill.apps.lite``), or "".

    Read off ``__main__.__spec__``, which Python sets for ``-m`` and which
    ``runpy.run_module(..., alter_sys=True)`` sets too -- so it answers the same
    way whether the app was launched by the shared runtime or by a plain
    interpreter in a portable bundle. A package entry point reports
    ``<package>.__main__``; the suffix is trimmed so the answer is the module a
    shortcut would name.
    """
    spec = getattr(sys.modules.get("__main__"), "__spec__", None)
    name = str(getattr(spec, "name", "") or "")
    return name[: -len(".__main__")] if name.endswith(".__main__") else name


def relaunch_command(exe_path: Path) -> list[str]:
    """The arguments needed to bring *exe_path* back up as this app.

    Empty for an app whose own frozen exe is running (QUILL's ``quill.exe``):
    starting it bare is right, and appending ``-m`` to it would hand the app an
    argument it would read as a file to open. ``["-m", "<module>"]`` when the
    running executable is a generic interpreter -- the shared runtime, or a
    portable bundle's ``pythonw.exe`` -- because then the executable alone does
    not identify the app, and that is exactly the pair the Start Menu shortcut
    uses.
    """
    module = main_module()
    if not module:
        return []
    if exe_path.stem.lower() not in _GENERIC_INTERPRETERS:
        return []
    return ["-m", module]


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
    raise SelfUpdateError(f"The downloaded update does not contain {exe_name}; not applying it.")


def write_and_launch_helper(script_text: str, helper_dir: Path) -> Path:
    """Write ``apply-update.bat`` into ``helper_dir`` and launch it detached.

    ``helper_dir`` MUST be outside the install directory (the system temp dir),
    so overwriting the install never clobbers the running helper. Launched with
    a single hidden console (no visible window) so it outlives this process
    without popping a terminal.
    """
    helper_dir.mkdir(parents=True, exist_ok=True)
    helper = helper_dir / "apply-update.bat"
    helper.write_text(script_text, encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        # CREATE_NO_WINDOW alone: cmd.exe and the console children it spawns to
        # wait for us to exit (tasklist, find, robocopy) share ONE hidden
        # console, so nothing is ever shown. It must NOT be OR'd with
        # DETACHED_PROCESS: that gives cmd.exe no console at all, so each console
        # child allocates its own *visible* window and steals focus -- the "find"
        # terminal that left one-click updates hanging (#1191). The helper still
        # outlives us: it is an independent child, unaffected by our exit.
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    command = ["cmd.exe", "/c", str(helper)]
    if os.name != "nt":
        subprocess.Popen(command, close_fds=True, cwd=str(helper_dir))  # noqa: S603
        return helper
    # OUT OF THE LAUNCHER'S JOB (2026-09-30). Every QuillVille launcher runs the
    # app inside a Job Object with KILL_ON_JOB_CLOSE, and a child of the app is
    # in that job too -- so when the app exited and the launcher closed the job,
    # Windows killed this helper in its wait loop, before it had written a line
    # of its log or started setup. "Install and restart now" closed the app and
    # nothing else ever happened (reported for QUILL Lite 1.1.1). Breakaway is
    # the clean way out, and launchers built from now on allow it
    # (JOB_OBJECT_LIMIT_BREAKAWAY_OK); a launcher already installed does not, so
    # then the helper is started by the WMI service instead, which is outside
    # every job.
    try:
        subprocess.Popen(  # noqa: S603 - our own generated script at a fixed path
            command,
            creationflags=creationflags | _CREATE_BREAKAWAY_FROM_JOB,
            close_fds=True,
            cwd=str(helper_dir),
        )
        return helper
    except OSError:
        pass
    _launch_outside_job(command, helper_dir)
    return helper


#: CREATE_BREAKAWAY_FROM_JOB. Spelled out: ``subprocess`` does not export it.
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def _launch_outside_job(command: list[str], cwd: Path) -> None:
    """Start *command* through WMI (``Win32_Process.Create``), hidden.

    The process WMI creates is a child of the WMI provider host, not of this
    app, so no job this app is in can reach it. ``ShowWindow = 0`` keeps the
    helper's console hidden, and its console children share it (the #1191 rule
    above). Raises :class:`SelfUpdateError` if WMI will not start it, so the
    caller keeps the app open and the user can install by hand.
    """
    line = subprocess.list2cmdline(command).replace("'", "''")
    folder = str(cwd).replace("'", "''")
    script = (
        "$s = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly "
        "-Property @{ShowWindow=[uint16]0}; "
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        f"-Arguments @{{CommandLine='{line}'; CurrentDirectory='{folder}'; "
        "ProcessStartupInformation=$s}; exit [int]$r.ReturnValue"
    )
    result = subprocess.run(  # noqa: S603 - fixed PowerShell, our own argv
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode != 0:
        raise SelfUpdateError(
            "Windows would not start the update helper outside this app "
            f"(WMI returned {result.returncode})."
        )


def running_app_key() -> str:
    """The family key of the app this process is (``radio``), ``quill`` for QUILL."""
    from quill.core.runtime_apps import app_for_module

    app = app_for_module(main_module())
    return app.ref_id if app is not None else "quill"


def running_channel() -> str:
    """The release channel this app is on, for the installer's ``/CHANNEL=``."""
    try:
        from quill.core.updater.channels import state_for

        return state_for(running_app_key()).channel
    except Exception:  # noqa: BLE001 - unknown: the installer decides by version
        return ""


def begin_self_update(
    *,
    download_path: Path,
    portable: bool,
    app_data_dir: Path,
    pid: int | None = None,
    when: str = "now",
    channel: str | None = None,
    version: str = "",
) -> None:
    """Apply the already-downloaded update at ``download_path`` and relaunch.

    ``when="on_close"`` applies it after the app is closed, however long that
    takes, and does not relaunch.

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
    # The helper appends to a log here; cmd cannot create the folder, and a
    # missing folder meant a failed update left no trace at all (2026-09-30).
    updates_dir.mkdir(parents=True, exist_ok=True)
    log_path = updates_dir / "apply-update.log"
    resolved_pid = os.getpid() if pid is None else pid
    relaunch_args = relaunch_command(exe_path)
    on_close = when == "on_close"
    # The launcher that started us holds its own exe open until we exit, so
    # the helper waits for it too -- but only a launcher: any other parent
    # (Explorer, for a frozen quill.exe) is not ours to wait for.
    parent = os.getppid() if launcher_exe() is not None else 0
    timing = {
        "also_wait_for": (parent,) if parent and pid is None else (),
        "relaunch": not on_close,
        "wait_limit_seconds": None if on_close else _PID_WAIT_SECONDS,
    }

    # Release channels, Phase 4: the health check and the undo. The pending
    # note and the kept installer live in quill.core.updater.apply.
    from quill.core.updater import apply as kept
    from quill.core.updater.profiles import PROFILES

    previous = kept.installed_version(updates_dir)
    health: dict[str, object] = {}
    # Only apps that confirm their start (quill.ui.updates.started) can be
    # health-checked; any other app would be undone for staying silent.
    if version and not on_close and running_app_key() in PROFILES:
        health = {
            "health_marker": kept.started_marker(updates_dir, version),
            "result_file": kept.result_path(updates_dir),
            "from_version": previous,
            "to_version": version,
            "rollback_setup": None if portable else kept.rollback_setup_for(updates_dir, previous),
        }
    if version:
        kept.record_pending(
            updates_dir,
            app_key=running_app_key(),
            from_version=previous,
            to_version=version,
            setup=None if portable else download_path,
            portable_previous=Path(f"{install_dir}.previous") if portable else None,
        )

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
            relaunch_args=relaunch_args,
            swap=True,
            **health,  # type: ignore[arg-type]
            **timing,  # type: ignore[arg-type]
        )
    else:
        script = build_apply_update_script(
            pid=resolved_pid,
            mode="installer",
            install_dir=install_dir,
            exe_path=exe_path,
            log_path=log_path,
            setup_exe=download_path,
            relaunch_args=relaunch_args,
            channel=running_channel() if channel is None else channel,
            setup_log=updates_dir / f"setup-{download_path.stem}.log",
            **health,  # type: ignore[arg-type]
            **timing,  # type: ignore[arg-type]
        )
    helper_dir = Path(tempfile.gettempdir()) / "quill-apply-update"
    write_and_launch_helper(script, helper_dir)


__all__ = [
    "SelfUpdateError",
    "begin_self_update",
    "build_apply_update_script",
    "install_root_and_exe",
    "launcher_exe",
    "main_module",
    "relaunch_command",
    "running_app_key",
    "running_channel",
    "stage_portable_update",
    "write_and_launch_helper",
]
