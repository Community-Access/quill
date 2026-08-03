"""Tying an ffmpeg recording child to QUILL's own lifetime on Windows.

Extracted from :mod:`quill.core.radio.recording` (GATE-11: extract instead of
grow) so the recorder module keeps room for the recording-integrity work
without losing this hardening. Behaviour is unchanged -- these are the same
two helpers the recorder has always called, verbatim.

Without a job object, a crashed or killed QUILL leaves a bare ffmpeg process
still writing to the temp folder: the user sees a file growing forever with no
app to stop it. ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`` makes the OS take the
child down when the host's handle closes, which happens on any host exit,
clean or not.

Everything here is best-effort by design: a failure degrades to the pre-job
behaviour (the recording still works, it is simply not tied to the host's
lifetime) and never breaks a recording.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import cast

logger = logging.getLogger(__name__)

__all__ = ["assign_kill_on_close_job", "close_job_handle"]


def assign_kill_on_close_job(process: subprocess.Popen[bytes]) -> object | None:
    """Put *process* in a Windows job object that kills it when the host dies,
    so a crashed/killed QUILL can no longer strand a bare ffmpeg writing to the
    temp dir.

    Best-effort: returns the job handle (an int) on success, or ``None``
    off-Windows or if anything goes wrong (job creation, assignment, or the
    kill-on-close flag). A ``None`` return degrades to the pre-job behavior --
    the recording still works, it just is not tied to the host's lifetime."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        class _IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _BASIC_LIMITS(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _EXTENDED_LIMITS(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC_LIMITS),
                ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JobObjectExtendedLimitInformation = 9
        job: object = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXTENDED_LIMITS()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return None
        # subprocess.Popen keeps the process handle on Windows as _handle (int).
        # AssignProcessToJobObject needs that handle; the child must inherit it
        # (CREATE_NO_WINDOW does not block inheritance of the handle Popen keeps).
        proc_handle = getattr(process, "_handle", None)
        if not proc_handle or not kernel32.AssignProcessToJobObject(job, proc_handle):
            kernel32.CloseHandle(job)
            return None
        return job
    except Exception:  # noqa: BLE001 - best-effort; never break a recording
        logger.debug("Could not bind radio recording to a kill-on-close job.", exc_info=True)
        return None


def close_job_handle(job: object) -> None:
    """Close a job handle returned by :func:`assign_kill_on_close_job`.

    Safe to call only after the child has exited (the recorder does so from
    its monitor thread once ``process.wait()`` returns), so closing the handle
    cannot kill a still-running recording."""
    if not job:
        return
    try:
        import ctypes

        ctypes.windll.kernel32.CloseHandle(cast("int", job))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass
