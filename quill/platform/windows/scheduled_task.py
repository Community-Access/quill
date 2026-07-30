"""Register an OS-scheduled background weather check (Windows Task Scheduler).

This is the "alerts with no Quill Weather process running" mechanism: a per-user
Scheduled Task wakes a short-lived ``quill-weather --check-once`` on a cadence,
which polls the NWS and toasts any newly-issued alert, then exits. No persistent
process, no elevation (a per-user task, created with ``schtasks``), and the task
runs in the interactive session so its toast is shown and screen-read.

Every call is a safe no-op off Windows and never raises -- a locked-down machine
(corporate policy blocking ``schtasks``) must not crash the app. All subprocess
launches go through ``stability.safe_subprocess`` (timeout + logged, redacted
args), never a raw ``subprocess`` or a shell.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from quill.stability.safe_subprocess import run_subprocess_safely

_TASK_NAME = "QuillWeatherAlertCheck"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def _schtasks_path() -> str:
    """Absolute path to ``schtasks.exe`` under the Windows System32 directory.

    Launching a bare ``schtasks`` would let a ``schtasks.exe`` planted on the
    PATH (or in the current directory) run instead. Resolving against
    ``%SystemRoot%`` (falling back to the conventional ``C:\\Windows`` when the
    env var is unset) pins the launch to the real system binary. If the file is
    somehow absent, the absolute path simply fails to start and ``_schtasks``
    reports False -- never a hijack.
    """
    system_root = os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows"
    return str(Path(system_root) / "System32" / "schtasks.exe")


def launch_command() -> str:
    """The command Task Scheduler runs: this executable, one-shot check mode."""
    return f'"{sys.executable}" --check-once'


def _schtasks(args: list[str]) -> bool:
    """Run a schtasks verb; True on success (exit 0), False on any failure.
    Never raises -- callers reflect the returned state in the UI."""
    if not is_windows():
        return False
    try:
        result = run_subprocess_safely([_schtasks_path(), *args], timeout_seconds=20.0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def is_registered() -> bool:
    """Whether the background-check task currently exists."""
    return _schtasks(["/Query", "/TN", _TASK_NAME])


def register(interval_minutes: int) -> bool:
    """Create (or replace) the per-user task to run every ``interval_minutes``
    (minimum 1). ``/F`` overwrites an existing one so changing the cadence is a
    plain re-register."""
    minutes = max(1, int(interval_minutes))
    return _schtasks([
        "/Create",
        "/TN",
        _TASK_NAME,
        "/TR",
        launch_command(),
        "/SC",
        "MINUTE",
        "/MO",
        str(minutes),
        "/F",
    ])


def unregister() -> bool:
    """Remove the background-check task (True if it is gone afterwards)."""
    if not is_windows():
        return False
    if _schtasks(["/Delete", "/TN", _TASK_NAME, "/F"]):
        return True
    # Deleting a task that was never there reports failure; treat "already
    # absent" as success so a toggle-off is idempotent.
    return not is_registered()
