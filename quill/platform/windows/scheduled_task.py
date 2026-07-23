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

import subprocess
import sys

from quill.stability.safe_subprocess import run_subprocess_safely

_TASK_NAME = "QuillWeatherAlertCheck"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def launch_command() -> str:
    """The command Task Scheduler runs: this executable, one-shot check mode."""
    return f'"{sys.executable}" --check-once'


def _schtasks(args: list[str]) -> bool:
    """Run a schtasks verb; True on success (exit 0), False on any failure.
    Never raises -- callers reflect the returned state in the UI."""
    if not is_windows():
        return False
    try:
        result = run_subprocess_safely(["schtasks", *args], timeout_seconds=20.0)
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
