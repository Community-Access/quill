"""Force a window to the foreground on Windows, and describe the current one.

Windows focus-stealing prevention blocks simple Raise() calls when another
process (e.g. a launch terminal) owns the foreground.  The AttachThreadInput
technique temporarily merges the calling thread's input queue with the
foreground thread's, which grants SetForegroundWindow permission.

:func:`foreground_window_info` answers the opposite question -- *what* has focus
right now -- which system-wide abbreviation expansion needs before it types
anything (see :mod:`quill.core.expansion.targets`).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
from dataclasses import dataclass

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_MAX_PATH = 260


def force_foreground_window(hwnd: int) -> None:
    """Bring *hwnd* to the foreground, bypassing focus-stealing prevention."""
    fg_hwnd: int = _user32.GetForegroundWindow()
    fg_tid: int = _user32.GetWindowThreadProcessId(fg_hwnd, None)
    cur_tid: int = _kernel32.GetCurrentThreadId()
    if fg_tid and fg_tid != cur_tid:
        _user32.AttachThreadInput(fg_tid, cur_tid, True)
        try:
            _user32.BringWindowToTop(hwnd)
            _user32.SetForegroundWindow(hwnd)
        finally:
            _user32.AttachThreadInput(fg_tid, cur_tid, False)
    else:
        _user32.SetForegroundWindow(hwnd)


@dataclass(frozen=True, slots=True)
class ForegroundWindow:
    """What currently has keyboard focus, as far as the shell can tell."""

    hwnd: int = 0
    process_name: str = ""
    title: str = ""
    window_class: str = ""


def foreground_window_info() -> ForegroundWindow:
    """Describe the foreground window; empty fields when it cannot be read.

    Never raises -- every caller is on a hot path (a keyboard hook) where an
    exception would be worse than a missing answer, and an empty answer is
    treated as "unknown", which the deny-list handles conservatively.
    """
    try:
        hwnd = int(_user32.GetForegroundWindow())
        if not hwnd:
            return ForegroundWindow()
        title_buf = ctypes.create_unicode_buffer(512)
        _user32.GetWindowTextW(hwnd, title_buf, 512)
        class_buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, class_buf, 256)
        pid = ctypes.wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return ForegroundWindow(
            hwnd=hwnd,
            process_name=_process_name(int(pid.value)),
            title=title_buf.value,
            window_class=class_buf.value,
        )
    except Exception:  # noqa: BLE001
        return ForegroundWindow()


def _process_name(pid: int) -> str:
    if not pid:
        return ""
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(_MAX_PATH)
        size = ctypes.wintypes.DWORD(_MAX_PATH)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit("\\", 1)[-1]
    finally:
        _kernel32.CloseHandle(handle)
    return ""
