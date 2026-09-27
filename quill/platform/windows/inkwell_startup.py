"""Launch Quill Inkwell when Windows starts (per-user Run key).

Mirrors ``weather_startup.py`` exactly, with its own Run-key value name so it
never collides with QUILL's or a sibling app's autostart entry. The command
appends ``--tray``: an expander that only works once you remember to open it is
not much of an expander, so it comes up hidden and starts watching. Per-user
(``HKEY_CURRENT_USER``), no elevation, cleanly removable. The ``winreg`` import
is guarded so the module stays importable -- and unit-testable -- off Windows.
"""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "QuillInkwell"


#: The native launcher an installed copy starts from, and the app's module;
#: on the shared runtime ``sys.executable`` alone is not the app (2026-09-27).
LAUNCHER_NAME = "QuillInkwell.exe"
MODULE = "quill.apps.inkwell"


def launch_command() -> str:
    """The command written to the Run key: this app's own executable, quoted,
    with the start-in-tray flag."""
    from quill.core.app_command import app_command

    return app_command(MODULE, LAUNCHER_NAME, args=("--tray",))


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """True if Quill Inkwell currently has its per-user Run-key entry."""
    if not is_windows():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def heal_launch_at_startup(*, frozen: bool | None = None) -> bool:
    """Rewrite an existing, stale Run-key entry to :func:`launch_command`.

    Never creates one, never from a portable copy, never raises. See
    :mod:`quill.platform.windows.launch_heal`.
    """
    from quill.platform.windows import launch_heal

    if not is_windows() or not launch_heal.heal_allowed(frozen=frozen):
        return False
    return launch_heal.heal_run_value(winreg, _VALUE_NAME, launch_command())


def set_launch_at_startup(enabled: bool) -> None:
    """Add or remove Quill Inkwell's per-user Run-key autostart entry.

    A no-op off Windows; never raises -- a locked-down registry (corporate
    policy) must not crash the app or block saving other settings.
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
