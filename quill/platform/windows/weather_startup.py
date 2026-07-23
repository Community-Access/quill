"""Launch the standalone Quill Weather app when Windows starts (per-user Run
key), so its alert watch is running from login even before anyone opens a window.

Mirrors ``startup.py`` exactly, but with its own Run-key value name (so it never
collides with QUILL's own autostart entry) and a launch command that appends
``--tray`` -- the app comes up hidden in the notification area and starts
monitoring, rather than popping a window at every login. Per-user
(``HKEY_CURRENT_USER``), no elevation, cleanly removable. Guards the ``winreg``
import so the module stays importable off Windows (and unit-testable there).
"""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "QuillWeather"


def launch_command() -> str:
    """The command written to the Run key: this app's own executable, quoted,
    with the start-in-tray flag."""
    return f'"{sys.executable}" --tray'


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """True if Quill Weather currently has its per-user Run-key entry."""
    if not is_windows():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def set_launch_at_startup(enabled: bool) -> None:
    """Add or remove Quill Weather's per-user Run-key autostart entry.

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
