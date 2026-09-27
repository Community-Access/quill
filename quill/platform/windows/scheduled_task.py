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
from typing import Any

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
    """The command Task Scheduler runs: Quill Weather, one-shot check mode.

    Through its launcher (or ``-m quill.apps.weather`` on the runtime), never
    the bare runtime exe -- see :mod:`quill.core.app_command`."""
    from quill.core.app_command import app_command

    return app_command("quill.apps.weather", "QuillWeather.exe", args=("--check-once",))


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


def _interval_minutes(xml: str) -> int | None:
    """The repetition interval of a task definition (``PT15M``, ``PT1H``)."""
    import re

    from quill.platform.windows import launch_heal

    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", launch_heal.task_element(xml, "Interval"))
    if not match or not any(match.groups()):
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def heal_registered_task(
    fallback_interval_minutes: int = 15, *, frozen: bool | None = None, query: Any = None
) -> bool:
    """Re-register an existing, stale background-check task at its own cadence.

    Every shared-runtime build until 2026-09-27 registered it as the bare
    runtime exe plus ``--check-once``, which the runtime cannot read as an app
    -- so instead of a silent check, every run showed the runtime's "not an
    app" message. Only an existing, enabled task is touched (never created),
    never from a portable copy, never raising. True when it was re-registered.
    """
    from quill.platform.windows import launch_heal

    try:
        if not is_windows() or not launch_heal.heal_allowed(frozen=frozen):
            return False
        xml = query() if query else launch_heal.query_task_xml(_schtasks_path(), _TASK_NAME)
        if not launch_heal.task_needs_heal(xml, launch_command()):
            return False
        return register(_interval_minutes(xml) or fallback_interval_minutes)
    except Exception:  # noqa: BLE001 - a heal must never cost the launch
        return False
