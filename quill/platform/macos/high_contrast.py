"""Report macOS appearance / accessibility preferences.

Counterpart to ``quill.platform.windows.high_contrast.is_high_contrast_enabled``.
Reads Universal Access and appearance preferences via the ``defaults`` CLI;
returns False when a value can't be read. Extended (#6) to also report Dark
Mode (``AppleInterfaceStyle``) and Reduce Motion (``reduceMotion``) so QUILL can
offer to sync its theme to the OS instead of being manual-only on macOS.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


def _read_defaults(domain: str, key: str) -> str | None:
    """Return the stripped ``defaults`` value, or None on any failure."""
    try:
        completed = subprocess.run(
            ["defaults", "read", domain, key],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _affirmative(value: str | None) -> bool:
    return value is not None and value in {"1", "true", "YES"}


def is_high_contrast_enabled() -> bool:
    return _affirmative(_read_defaults("com.apple.universalaccess", "increaseContrast"))


def is_reduce_motion_enabled() -> bool:
    """Report the macOS Reduce Motion accessibility preference (#6).

    ``com.apple.universalaccess reduceMotion`` is ``1`` when enabled. Absent
    (the default) reads as disabled, not an error.
    """
    return _affirmative(_read_defaults("com.apple.universalaccess", "reduceMotion"))


def is_dark_mode_enabled() -> bool:
    """Report the macOS Dark Mode appearance preference (#6).

    ``-g AppleInterfaceStyle`` returns ``Dark`` only while Dark Mode is active;
    the key is absent (nonzero exit) under Light Mode, which reads as disabled.
    """
    value = _read_defaults("-g", "AppleInterfaceStyle")
    return value is not None and value.lower() == "dark"


@dataclass(frozen=True, slots=True)
class MacOSAppearance:
    """Snapshot of the macOS appearance / motion preferences QUILL can sync to."""

    high_contrast: bool
    dark_mode: bool
    reduce_motion: bool


def macos_appearance() -> MacOSAppearance:
    """Read all three appearance/motion preferences in one call (#6)."""
    return MacOSAppearance(
        high_contrast=is_high_contrast_enabled(),
        dark_mode=is_dark_mode_enabled(),
        reduce_motion=is_reduce_motion_enabled(),
    )
