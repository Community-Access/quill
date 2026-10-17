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
    #: The owning process id. Read here because it is already in hand -- the
    #: process NAME is derived from it -- and because a name is not an identity:
    #: two windows can be "explorer.exe" and an elevation check has to know
    #: which process it is actually talking to.
    process_id: int = 0


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
            process_id=int(pid.value),
        )
    except Exception:  # noqa: BLE001
        return ForegroundWindow()


def window_process_name(hwnd: int) -> str:
    """The program file name that owns *hwnd* ("notepad.exe"), or "". Never raises.

    QUILL Transcribe's Dictation Status key names the program dictation is
    locked to with it (D-6); the window's title is not read.
    """
    try:
        if not hwnd:
            return ""
        pid = ctypes.wintypes.DWORD()
        _user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        return _process_name(int(pid.value))
    except Exception:  # noqa: BLE001
        return ""


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


_GW_HWNDNEXT = 2
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_DWMWA_CLOAKED = 14
#: Enough to pass every window on a busy desktop, few enough to bound the walk.
_MAX_WINDOWS = 4000


def _cloaked(hwnd: int) -> bool:
    """Whether *hwnd* is hidden by the window manager (a suspended Store app)."""
    try:
        value = ctypes.c_int(0)
        result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.wintypes.DWORD(_DWMWA_CLOAKED),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return result == 0 and bool(value.value)
    except Exception:  # noqa: BLE001 - no window manager answer: not cloaked
        return False


def program_behind(own_process_id: int) -> ForegroundWindow:
    """The program window that was in front before this program's own windows.

    Windows keeps top-level windows in z-order, most recently active first, so
    the first one down from the top that is visible, has a title, is not a tool
    window or a hidden Store app, belongs to another process and is not part
    of the Windows shell (``quill.core.transcribe.arming.SHELL_CLASSES``) is the
    program the person came here from. Used by the never-type list's "Add the
    Program in Front" (D-24), where the person's own program is behind the
    settings window. An empty answer when there is none. Never raises.
    """
    from quill.core.transcribe.arming import ready_to_start

    try:
        hwnd = int(_user32.GetTopWindow(None) or 0)
        for _ in range(_MAX_WINDOWS):
            if not hwnd:
                break
            if (
                _user32.IsWindowVisible(hwnd)
                and _user32.GetWindowTextLengthW(hwnd) > 0
                and not (_user32.GetWindowLongW(hwnd, _GWL_EXSTYLE) & _WS_EX_TOOLWINDOW)
            ):
                pid = ctypes.wintypes.DWORD()
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                class_buf = ctypes.create_unicode_buffer(256)
                _user32.GetClassNameW(hwnd, class_buf, 256)
                if ready_to_start(
                    hwnd=hwnd,
                    process_id=int(pid.value),
                    window_class=class_buf.value,
                    own_process=own_process_id,
                ) and not _cloaked(hwnd):
                    title_buf = ctypes.create_unicode_buffer(512)
                    _user32.GetWindowTextW(hwnd, title_buf, 512)
                    return ForegroundWindow(
                        hwnd=hwnd,
                        process_name=_process_name(int(pid.value)),
                        title=title_buf.value,
                        window_class=class_buf.value,
                        process_id=int(pid.value),
                    )
            hwnd = int(_user32.GetWindow(hwnd, _GW_HWNDNEXT) or 0)
    except Exception:  # noqa: BLE001
        pass
    return ForegroundWindow()
