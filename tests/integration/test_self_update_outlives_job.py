"""The update helper survives the launcher's kill-on-close job (the real OS, no fakes).

Reproduces 2026-09-30: every launcher puts the app in a Job Object with
KILL_ON_JOB_CLOSE, the helper the app starts was in that job, and closing the
job killed it before setup ran. Both job shapes are exercised: one that allows
breakaway (launchers from now on) and one that does not (launchers already
installed), where the WMI route has to carry it.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows job objects")

_CHILD = r"""
import sys
from pathlib import Path
from quill.core import self_update
marker = Path(sys.argv[1])
script = "@echo off\r\nping -n 3 127.0.0.1 >NUL\r\necho survived> \"%s\"\r\n" % marker
self_update.write_and_launch_helper(script, marker.parent / "helper")
"""


def _run_in_job(tmp_path: Path, *, breakaway_ok: bool) -> Path:
    win32job = pytest.importorskip("win32job")
    win32api = pytest.importorskip("win32api")
    win32con = pytest.importorskip("win32con")
    import win32process

    marker = tmp_path / "survived.txt"
    job = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    flags = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if breakaway_ok:
        flags |= win32job.JOB_OBJECT_LIMIT_BREAKAWAY_OK
    info["BasicLimitInformation"]["LimitFlags"] = flags
    win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD, str(marker)],
        creationflags=win32process.CREATE_SUSPENDED | win32process.CREATE_BREAKAWAY_FROM_JOB,
    )
    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, child.pid)
    win32job.AssignProcessToJobObject(job, handle)
    import ctypes

    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtResumeProcess(int(handle))
    child.wait(timeout=60)
    # The app has exited; now the launcher closes its job, as it does for real.
    win32api.CloseHandle(job)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not marker.exists():
        time.sleep(0.5)
    return marker


def test_the_helper_breaks_away_from_a_job_that_allows_it(tmp_path: Path) -> None:
    assert _run_in_job(tmp_path, breakaway_ok=True).exists()


def test_the_helper_escapes_a_job_that_forbids_breakaway(tmp_path: Path) -> None:
    assert _run_in_job(tmp_path, breakaway_ok=False).exists()
