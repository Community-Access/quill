"""Per-user Windows startup presentation choices shared by Quill apps.

Whether an app starts at sign-in lives in that app's Run value. Whether its
window starts minimized is a separate preference, kept beside those values so
it remains local to this Windows account and survives turning autostart off.
Portable copies must not write here.
"""

from __future__ import annotations

import sys

try:  # pragma: no cover - Windows-only registry bridge
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]

_KEY_PATH = r"Software\Community Access\Quill\Startup"


def is_windows() -> bool:
    return winreg is not None and sys.platform.startswith("win")


def start_minimized(app_key: str, *, default: bool = False) -> bool:
    """Whether *app_key* should start minimized when its Windows Run entry fires."""
    if not is_windows() or not app_key.strip():
        return default
    from quill.core.paths import portable_bundle_root

    if portable_bundle_root() is not None:
        return default
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, app_key)
    except OSError:
        return default
    return bool(value)


def set_start_minimized(app_key: str, enabled: bool) -> bool:
    """Save the per-user choice; True means Windows reports the requested value."""
    if not is_windows() or not app_key.strip():
        return False
    from quill.core.paths import portable_bundle_root

    if portable_bundle_root() is not None:
        return False
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, app_key, 0, winreg.REG_DWORD, int(bool(enabled)))
    except OSError:
        return False
    return start_minimized(app_key, default=not enabled) == bool(enabled)


__all__ = ["is_windows", "set_start_minimized", "start_minimized"]
