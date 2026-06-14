"""Force a window to the foreground on Windows.

Windows focus-stealing prevention blocks simple Raise() calls when another
process (e.g. a launch terminal) owns the foreground.  The AttachThreadInput
technique temporarily merges the calling thread's input queue with the
foreground thread's, which grants SetForegroundWindow permission.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


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
