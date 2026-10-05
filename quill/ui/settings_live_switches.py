"""Settings that have to *do* something the moment they change.

Most settings are read at the point their feature decides, so changing one
needs nothing more. A few drive something outside that flow -- a microphone
that is listening, keys written to the Windows registry -- and those need an
explicit start/stop when the app starts and when Settings is closed with OK.
This module is that one place, so ``main_frame.py`` and the Settings dialog
each carry a single call instead of one per switch.

* "Listen for 'Hey QUILL'" and "Keep listening across restarts":
  :mod:`quill.ui.wakeword_switch`.
* The right-click menu ("Show QUILL in the file-manager right-click menu",
  each "Offer ..." verb, and "File types offered to QUILL"): re-registered
  when any of them changed since the last time QUILL applied them. Comparing
  against what was last applied, rather than re-writing on every OK, means
  pressing OK on an unrelated page never touches the registry.

Nothing here may raise; both callers are paths that must always complete.
"""

from __future__ import annotations

from typing import Any

from quill.ui import wakeword_switch

_SHELL_KEYS_EXTRA: tuple[str, ...] = (
    "shell_integration_enabled",
    "shell_file_types",
    "assistant_enabled",
)


def _shell_snapshot(settings: Any) -> tuple[object, ...]:
    from quill.core.shell_verbs import default_shell_verbs

    keys = _SHELL_KEYS_EXTRA + tuple(verb.settings_key for verb in default_shell_verbs())
    return tuple(getattr(settings, key, None) for key in keys)


def _apply_shell_verbs(settings: Any) -> None:
    """Re-register the right-click verbs (Windows, current user only)."""
    from quill.platform.windows.shell_integration import apply_shell_verb_settings

    apply_shell_verb_settings(settings)


def remember_shell_verbs(host: Any) -> None:
    """Record the right-click settings as applied (startup, or after Install)."""
    try:
        host._shell_verbs_applied = _shell_snapshot(getattr(host, "settings", None))
    except Exception:  # noqa: BLE001 - must never raise
        pass


def apply_shell_verbs_if_changed(host: Any) -> bool:
    """Re-register the verbs when a right-click setting changed. True if it did."""
    try:
        before = getattr(host, "_shell_verbs_applied", None)
        settings = getattr(host, "settings", None)
        now = _shell_snapshot(settings)
        if before is None or before == now:
            return False
        host._shell_verbs_applied = now
        _apply_shell_verbs(settings)
        return True
    except Exception:  # noqa: BLE001 - no registry (macOS) or a locked key
        return False


def at_startup(host: Any) -> None:
    """Startup task: resume listening if asked, note the applied verb state."""
    remember_shell_verbs(host)
    wakeword_switch.start_wakeword_if_enabled(host)


def after_settings_applied(host: Any) -> None:
    """Settings OK / Import / Reset: make the live switches match."""
    wakeword_switch.apply_wakeword_setting(host)
    apply_shell_verbs_if_changed(host)
