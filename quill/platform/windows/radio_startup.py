"""Launch Quill Radio automatically when Windows starts (per-user Run key).

The same per-user autostart mechanism QUILL itself uses (``startup.py``) and the
Quill Weather app uses (``weather_startup.py``): a value under
``HKEY_CURRENT_USER\\...\\CurrentVersion\\Run``. No elevation, no installer
changes, cleanly removable, and -- unlike a Startup-folder ``.lnk`` -- it needs
no pywin32/COM (which QUILL does not bundle), so it works in the frozen build.
Its own value name keeps it independent of QUILL's and Quill Weather's entries.
Guards the ``winreg`` import so the module stays importable (and testable) off
Windows.
"""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "QuillRadio"


def launch_command() -> str:
    """The command written to the Run key: Quill Radio's own executable, quoted."""
    return f'"{sys.executable}"'


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """True if Quill Radio currently has its per-user Run-key entry."""
    if not is_windows():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def set_launch_at_startup(enabled: bool) -> None:
    """Add or remove Quill Radio's per-user Run-key autostart entry.

    A no-op on non-Windows platforms; never raises -- a locked-down registry
    (corporate policy) must not crash the app or block saving other settings.
    """
    if not is_windows():
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        pass
