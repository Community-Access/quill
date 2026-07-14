"""Report macOS accessibility preferences.

Counterpart to ``quill.platform.windows.high_contrast.is_high_contrast_enabled``.
Reads the Universal Access ``increaseContrast`` preference via the ``defaults``
CLI and returns False when the value can't be read.

Dark Mode is reported by wx's ``SystemSettings.GetAppearance().IsDark()``
(see ``MainFrame._system_appearance_is_dark``), so a separate ``defaults``-CLI
probe here would be redundant. There are no visual animations or transitions in
this wxPython app to gate on a Reduce Motion preference, so no motion probe is
exposed either. Both were prototyped under #6 and removed as dead code with no
consumer; the ``defaults``-CLI reads are trivial to reintroduce if a future
OS-sync feature needs them.
"""

from __future__ import annotations

import subprocess


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
