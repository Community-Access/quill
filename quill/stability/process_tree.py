"""Start a command whose whole process tree can be stopped at once (code.md 4.6, 4.8).

Stop must kill what the agent ran *and everything it started*: ``pytest``
under ``cmd``, a test that spawned a server, an ``npm`` script's children.
Killing only the first process leaves the rest running with nobody to hear
them.

- **Windows:** the child is put in a Job Object with
  ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`` straight after it starts (the
  pattern :mod:`quill.core.python_sandbox` uses), so terminating the job ends
  the tree, and so does QUILL exiting. If the job cannot be made, ``taskkill
  /T /F`` is the fallback.
- **Elsewhere:** the child leads a new session and the whole process group is
  signalled.

Output goes to a file, never a pipe, so a chatty command can never fill a
buffer and hang, and so the output can be opened as a document afterwards.
Only the redacted argv is logged.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Any

from quill.stability.redaction import format_args_for_log

__all__ = ["TreeProcess", "start_tree_process"]

logger = logging.getLogger(__name__)

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


def _kernel32() -> Any:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    return kernel32


def _make_kill_on_close_job(process_handle: int) -> Any:
    """A job holding *process_handle* that dies with its handle; None on failure."""
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

    class _Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _Io(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class _Extended(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _Basic),
            ("IoInfo", _Io),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = _Extended()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    )
    if not ok or not kernel32.AssignProcessToJobObject(job, process_handle):
        kernel32.CloseHandle(job)
        return None
    return job


class TreeProcess:
    """A running command and the means to stop all of it."""

    def __init__(self, popen: subprocess.Popen[bytes], output: IO[bytes], job: Any) -> None:
        self._popen = popen
        self._output = output
        self._job = job

    @property
    def pid(self) -> int:
        return self._popen.pid

    def poll(self) -> int | None:
        return self._popen.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self._popen.wait(timeout)

    def kill_tree(self) -> None:
        """End the command and everything it started. Safe to call twice."""
        if os.name == "nt":
            if self._job is not None:
                _kernel32().TerminateJobObject(self._job, 1)
            elif self._popen.poll() is None:
                subprocess.run(  # noqa: S603 - fixed system tool, our own child's pid
                    ["taskkill", "/T", "/F", "/PID", str(self._popen.pid)],
                    capture_output=True,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
        else:
            try:
                os.killpg(self._popen.pid, signal.SIGKILL)  # type: ignore[attr-defined,unused-ignore]
            except OSError:
                pass
        try:
            self._popen.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._popen.kill()

    def close(self) -> None:
        """Release the output file and the job (which, on Windows, ends the tree)."""
        try:
            self._output.close()
        except OSError:
            pass
        if self._job is not None and os.name == "nt":
            _kernel32().CloseHandle(self._job)
            self._job = None


def start_tree_process(
    args: str | Sequence[str], *, cwd: str, env: dict[str, str], output_path: Path
) -> TreeProcess:
    """Start *args* in *cwd* with *env*, stdout and stderr together into *output_path*.

    *args* may be a ready Windows command line (a string), because ``cmd /s /c``
    must receive the person's command exactly as typed: passing it inside an
    argv list would have Python escape its quotes with backslashes, which cmd
    does not understand.
    """
    arg_list: str | list[str] = args if isinstance(args, str) else list(args)
    if not arg_list:
        raise ValueError("start_tree_process requires a non-empty command")
    if not os.path.isdir(cwd):
        raise ValueError(f"cwd must be an existing directory: {cwd!r}")
    shown = [arg_list] if isinstance(arg_list, str) else arg_list
    logger.info("Starting command %s cwd=%s", format_args_for_log(shown), cwd)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = output_path.open("wb")
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        popen = subprocess.Popen(  # noqa: S603 - a command the person approved, as argv
            arg_list,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
    except OSError as error:
        output.close()
        raise OSError(f"Could not start {shown[0]!r}: {error}") from error
    job = None
    if os.name == "nt":
        try:
            job = _make_kill_on_close_job(int(popen._handle))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - taskkill is the fallback
            job = None
    return TreeProcess(popen, output, job)
