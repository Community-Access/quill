"""The Windows half of the text-editor registration: registry, prompt, Settings.

Shared by QUILL and QUILL Lite. Everything that decides *what* to write is in
:mod:`quill.core.windows_editor`. This module only touches the system, in four small ways:

* :class:`CurrentUserWriter` writes HKEY_CURRENT_USER values (the per-user
  registration needs no elevation);
* :class:`MachineReader` reads HKEY_LOCAL_MACHINE, which any user may do, so the
  Notepad switch can show the truth without asking for anything;
* :func:`run_elevated` starts one program through ``ShellExecuteEx`` with the
  ``runas`` verb -- the administrator prompt -- and waits for it;
* :func:`open_settings` opens an ``ms-settings:`` page.

Each is a seam the tests replace, so no test writes a real registry value or
raises a real prompt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:  # pragma: no cover - Windows-only
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

__all__ = [
    "DECLINED",
    "DONE",
    "FAILED",
    "CurrentUserWriter",
    "MachineReader",
    "notify_association_change",
    "open_settings",
    "run_elevated",
    "system32",
    "windows_build",
]

#: What :func:`run_elevated` reports.
DONE = "done"
DECLINED = "declined"
FAILED = "failed"

_ERROR_CANCELLED = 1223  # the user said No to the administrator prompt


class CurrentUserWriter:
    """Sets values under HKEY_CURRENT_USER, creating keys as it goes."""

    def set_value(self, path: str, name: str, data: str, kind: str) -> None:
        if winreg is None:  # pragma: no cover - non-Windows fallback
            raise OSError("The Windows registry is not available here")
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
            if kind == "none":
                winreg.SetValueEx(key, name, 0, winreg.REG_NONE, b"")
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, data)


class MachineReader:
    """Reads HKEY_LOCAL_MACHINE in the 64-bit view. Never raises."""

    def _open(self, path: str):  # type: ignore[no-untyped-def]
        assert winreg is not None
        access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        return winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, access)

    def value(self, path: str, name: str) -> object | None:
        if winreg is None:  # pragma: no cover - non-Windows fallback
            return None
        try:
            with self._open(path) as key:
                return winreg.QueryValueEx(key, name)[0]
        except OSError:
            return None

    def subkeys(self, path: str) -> list[str]:
        if winreg is None:  # pragma: no cover - non-Windows fallback
            return []
        names: list[str] = []
        try:
            with self._open(path) as key:
                index = 0
                while True:
                    try:
                        names.append(winreg.EnumKey(key, index))
                    except OSError:
                        break
                    index += 1
        except OSError:
            return []
        return names


def notify_association_change() -> None:
    """Tell Explorer the file associations changed, so Open With refreshes now."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        shcne_assocchanged = 0x08000000
        ctypes.windll.shell32.SHChangeNotify(shcne_assocchanged, 0, None, None)
    except Exception:  # noqa: BLE001 - a refresh courtesy must never fail the command
        pass


def system32() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"


def windows_build() -> int:
    try:
        return int(sys.getwindowsversion().build)  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        return 0


def open_settings(uri: str) -> bool:
    """Open a Settings page. ``False`` when Windows would not."""
    try:
        os.startfile(uri)  # type: ignore[attr-defined]  # noqa: S606
    except Exception:  # noqa: BLE001 - an OS that will not open it is not an error
        return False
    return True


def run_elevated(executable: str, parameters: str, *, timeout_ms: int = 120_000) -> str:
    """Run *executable* as administrator and wait for it; DONE, DECLINED or FAILED.

    ``ShellExecuteEx`` with ``runas`` is the documented way to ask: Windows shows
    its own prompt, and the program runs only if the user approves it.
    """
    if sys.platform != "win32":
        return FAILED
    import ctypes
    from ctypes import wintypes

    class _ShellExecuteInfo(ctypes.Structure):
        _fields_ = [  # noqa: RUF012 - ctypes layout
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    see_mask_nocloseprocess = 0x00000040
    sw_hide = 0
    info = _ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = see_mask_nocloseprocess
    info.lpVerb = "runas"
    info.lpFile = executable
    info.lpParameters = parameters
    info.lpDirectory = str(system32())
    info.nShow = sw_hide
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.windll.kernel32
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_ShellExecuteInfo)]
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        return DECLINED if ctypes.get_last_error() == _ERROR_CANCELLED else FAILED
    if not info.hProcess:
        return FAILED
    try:
        kernel32.WaitForSingleObject(info.hProcess, timeout_ms)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    finally:
        kernel32.CloseHandle(info.hProcess)
    return DONE if code.value == 0 else FAILED
