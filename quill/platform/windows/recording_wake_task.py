"""Ask Windows to wake the computer for a scheduled recording.

The strongest of the three defences in :mod:`quill.core.radio.schedule_wake`,
and the only one that helps a machine that is *already* asleep when the moment
comes. Inhibiting standby (the other two) can keep a waking machine up; nothing
inside a sleeping process can rouse it. Only the OS can, and on Windows the way
to ask is a Task Scheduler task with ``WakeToRun``.

``schtasks /Create`` has no command-line switch for that flag, so the task is
registered from an XML definition (``/XML``) instead of the argument form the
weather check uses. The XML also carries the settings that decide whether a
wake is honoured at all: ``DisallowStartIfOnBatteries`` off, so a laptop
recording still fires, and ``StopIfGoingOnBatteries`` off, so unplugging
mid-show does not kill it.

Everything here is best effort and never raises. A locked-down machine where
policy blocks ``schtasks`` simply does not get the wake -- the app still runs,
the schedule still fires whenever the machine happens to be awake, and the
listener was told about the requirement in the schedule dialog. A crash here
would be a far worse trade than a missed wake.

The task is **one-shot**: it is re-registered for the next occurrence each time
the schedule changes or a recording finishes, rather than mirroring the whole
recurrence into Task Scheduler. Two schedules that disagree is a bug waiting to
happen, and the app's own scheduler remains the single source of truth about
what records when.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from quill.stability.safe_subprocess import run_subprocess_safely

logger = logging.getLogger(__name__)

#: One task, replaced in place. A per-occurrence task name would leave a litter
#: of dead entries in Task Scheduler that nobody would ever go and clean up.
TASK_NAME = "QuillRadioScheduledRecordingWake"

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Wakes this computer for a Quill Radio scheduled recording.</Description>
    <URI>\\{task_name}</URI>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <WakeToRun>true</WakeToRun>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
    </Exec>
  </Actions>
</Task>
"""


def is_windows() -> bool:
    return sys.platform == "win32"


def _schtasks_path() -> str:
    """Absolute path to ``schtasks.exe``, never a bare name.

    Same reasoning as the weather task: a ``schtasks.exe`` planted earlier on
    PATH would otherwise be launched instead of the real one.
    """
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return str(Path(system_root) / "System32" / "schtasks.exe")


def launch_command() -> str:
    """What the wake runs: Quill Radio itself.

    If the app is already running, its single-instance guard means this is
    little more than a knock at the door -- the wake was the point, and the
    scheduler already inside the running app does the recording. If it is
    *not* running, this starts it in time for the entry to fire, which is the
    case the wake exists for.
    """
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{executable}"'
    return f'"{executable}" -m quill.apps.radio'


def _run(args: list[str]) -> bool:
    """Run a schtasks verb. True on exit 0; never raises."""
    if not is_windows():
        return False
    try:
        result = run_subprocess_safely([_schtasks_path(), *args], timeout_seconds=20.0)
    except Exception:  # noqa: BLE001 - a wake we cannot register is not fatal
        logger.warning("schtasks could not be run for the recording wake task.", exc_info=True)
        return False
    return getattr(result, "returncode", 1) == 0


def is_registered() -> bool:
    """Whether a wake task currently exists."""
    return _run(["/Query", "/TN", TASK_NAME])


def register(when: datetime, *, command: str = "") -> bool:
    """Register (or replace) a one-shot wake for *when*. True when it took.

    *when* is interpreted in local time and written without a zone offset,
    which is what Task Scheduler expects for a plain ``TimeTrigger``.
    """
    if not is_windows():
        return False
    local = when.astimezone().replace(tzinfo=None) if when.tzinfo is not None else when
    xml = _TASK_XML.format(
        task_name=TASK_NAME,
        start=local.strftime("%Y-%m-%dT%H:%M:%S"),
        command=(command or launch_command()).strip('"'),
    )
    # UTF-16 with a BOM: Task Scheduler rejects the file otherwise, and the
    # declaration above says so, so the two must agree.
    handle = None
    try:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".xml", encoding="utf-16", delete=False, newline="\r\n"
        )
        handle.write(xml)
        handle.close()
        return _run(["/Create", "/TN", TASK_NAME, "/XML", handle.name, "/F"])
    except OSError:
        logger.warning("Could not write the recording wake task definition.", exc_info=True)
        return False
    finally:
        if handle is not None:
            try:
                Path(handle.name).unlink(missing_ok=True)
            except OSError:
                pass


def unregister() -> bool:
    """Remove the wake task. True once it is gone, including if it never was."""
    if not is_windows():
        return False
    if _run(["/Delete", "/TN", TASK_NAME, "/F"]):
        return True
    # Deleting a task that does not exist reports failure; "already absent" is
    # the outcome the caller wanted, so a toggle-off stays idempotent.
    return not is_registered()
