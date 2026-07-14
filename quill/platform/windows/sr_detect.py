"""Detect a running screen reader from the live process list.

Process enumeration goes through the Windows Toolhelp API via ctypes, not a
``tasklist`` subprocess. ``quill.exe`` is a GUI process (pythonw); spawning the
console app ``tasklist`` flashed a visible terminal a screen reader announced on
every launch (e.g. JAWS reading ``C:\\WINDOWS\\SYSTEM32\\tasklist.exe``). The API
call creates no process and no window, and is faster than the old ~400-600 ms
shell-out.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenReaderDetection:
    detected: bool
    name: str
    source: str


_KNOWN_SCREEN_READERS = {
    "nvda.exe": "NVDA",
    "narrator.exe": "Narrator",
    "jfw.exe": "JAWS",
}


def detect_screen_reader(process_names: list[str] | None = None) -> ScreenReaderDetection:
    """Return which known screen reader (if any) is running.

    Pass *process_names* (a list of process image names) to test without touching
    the OS; when omitted, the live process list is read via the Windows API.
    """
    names = process_names if process_names is not None else _running_process_names()
    for image_name in names:
        lowered = image_name.strip().lower()
        if lowered in _KNOWN_SCREEN_READERS:
            return ScreenReaderDetection(
                detected=True,
                name=_KNOWN_SCREEN_READERS[lowered],
                source=image_name.strip(),
            )
    return ScreenReaderDetection(detected=False, name="none", source="")


_TH32CS_SNAPPROCESS = 0x00000002
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = (
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    )


def _running_process_names() -> list[str]:
    """Running process image names via the Windows Toolhelp API.

    Best-effort: returns an empty list on any failure or on a non-Windows
    platform, so detection degrades to "no screen reader" rather than raising.
    """
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (OSError, AttributeError):  # non-Windows: no WinDLL
        return []

    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W))
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == _INVALID_HANDLE_VALUE:
        return []

    names: list[str] = []
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            names.append(entry.szExeFile)
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return names
