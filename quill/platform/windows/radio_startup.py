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

#: What the menu item says in a portable copy instead of changing the registry.
PORTABLE_REFUSAL = (
    "A portable copy does not add itself to this computer's startup. "
    "Install Quill Radio to start it with Windows."
)


def running_portable() -> bool:
    """True when this run keeps its data in a portable bundle.

    A portable copy writes nothing to the computer it visits, and a Run-key
    entry is exactly that: it would outlive the stick, and point at a drive
    letter that means something else tomorrow. The check state reads False
    too, so an installed Quill Radio's entry on the same computer neither
    shows as this copy's nor gets removed by toggling it.
    """
    from quill.core.paths import portable_bundle_root

    return portable_bundle_root() is not None


#: The native launcher an installed Quill Radio starts from.
LAUNCHER_NAME = "QuillRadio.exe"
MODULE = "quill.apps.radio"


def launch_command() -> str:
    """The command written to the Run key: the command that starts Quill Radio.

    Not ``sys.executable`` alone -- on the shared runtime that is
    ``QuillVilleRuntime.exe``, which run bare is not an app (2026-09-27). See
    :mod:`quill.core.app_command`.
    """
    from quill.core.app_command import app_command

    return app_command(MODULE, LAUNCHER_NAME)


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """True if Quill Radio currently has its per-user Run-key entry."""
    if not is_windows() or running_portable():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def heal_launch_at_startup(*, frozen: bool | None = None) -> bool:
    """Rewrite an existing, stale Run-key entry to :func:`launch_command`.

    Never creates one, never from a portable copy, never raises. True when
    the entry was rewritten. See :mod:`quill.platform.windows.launch_heal`.
    """
    from quill.platform.windows import launch_heal

    if not is_windows() or not launch_heal.heal_allowed(frozen=frozen):
        return False
    return launch_heal.heal_run_value(winreg, _VALUE_NAME, launch_command())


def set_launch_at_startup(enabled: bool) -> None:
    """Add or remove Quill Radio's per-user Run-key autostart entry.

    A no-op on non-Windows platforms; never raises -- a locked-down registry
    (corporate policy) must not crash the app or block saving other settings.
    Never writes anything from a portable copy.
    """
    if not is_windows() or running_portable():
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
