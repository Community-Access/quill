"""Launch QUILL Cast automatically when Windows starts (per-user Run key)."""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "QuillCast"
LAUNCHER_NAME = "QuillCast.exe"
MODULE = "quill.apps.podcasts"

PORTABLE_REFUSAL = (
    "A portable copy does not add itself to this computer's startup. "
    "Install QUILL Cast to start it with Windows."
)


def running_portable() -> bool:
    """A portable copy must not leave a startup entry on the computer it visits."""
    from quill.core.paths import portable_bundle_root

    return portable_bundle_root() is not None


def launch_command() -> str:
    """Return the command that starts Cast through its app launcher."""
    from quill.core.app_command import app_command

    return app_command(MODULE, LAUNCHER_NAME)


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def is_launch_at_startup_enabled() -> bool:
    """Whether this installed copy has its per-user Run-key entry."""
    if not is_windows() or running_portable():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def heal_launch_at_startup(*, frozen: bool | None = None) -> bool:
    """Repair an existing stale entry without creating one."""
    from quill.platform.windows import launch_heal

    if not is_windows() or not launch_heal.heal_allowed(frozen=frozen):
        return False
    return launch_heal.heal_run_value(winreg, _VALUE_NAME, launch_command())


def set_launch_at_startup(enabled: bool) -> None:
    """Add or remove Cast's per-user entry; portable copies never write."""
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
