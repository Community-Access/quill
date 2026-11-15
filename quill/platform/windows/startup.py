"""Launch QUILL automatically when Windows starts (per-user Run key).

Uses the standard, no-elevation-required per-user autostart location
(``HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``) --
the same mechanism most consumer Windows apps use for "start with Windows,"
requiring no installer changes and cleanly removable by unchecking the
setting. Mirrors ``shell_integration.py``'s pattern of resolving the launch
command from ``sys.executable`` (already correct for a frozen/installed
build, matching that module's existing, working approach) and guarding the
``winreg`` import so this module stays importable on non-Windows platforms.
"""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Quill"


def launch_command(*, start_minimized: bool | None = None) -> str:
    """The command written to the Run key: QUILL's own executable, quoted.

    An installed ``quill.exe`` starts QUILL bare (its sitecustomize); a source
    run's ``python.exe`` needs ``-m quill`` (:mod:`quill.core.app_command`).
    QUILL has no native launcher, so none is looked for.
    """
    from quill.core.app_command import app_command

    if start_minimized is None:
        from quill.core.settings import load_settings
        from quill.platform.windows.startup_options import start_minimized as stored_choice

        start_minimized = stored_choice(
            "quill", default=load_settings().start_minimized_at_windows_startup
        )
    return app_command("quill", args=("--tray",) if start_minimized else ())


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """True if QUILL currently has a Run-key entry pointing at this executable."""
    from quill.core.paths import portable_bundle_root

    if not is_windows() or portable_bundle_root() is not None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def set_launch_at_startup(enabled: bool, *, start_minimized: bool | None = None) -> None:
    """Add or remove QUILL's per-user Run-key autostart entry.

    A no-op on non-Windows platforms. Never raises -- a failure to write the
    registry (e.g. a locked-down corporate policy) should not block saving
    the rest of the user's settings.
    """
    from quill.core.paths import portable_bundle_root

    if not is_windows() or portable_bundle_root() is not None:
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    _VALUE_NAME,
                    0,
                    winreg.REG_SZ,
                    launch_command(start_minimized=start_minimized),
                )
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        pass
