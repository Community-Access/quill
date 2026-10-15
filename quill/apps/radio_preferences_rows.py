"""Quill Radio Preferences rows that need more than a label and a value.

Split from ``radio_preferences.py`` under GATE-11 when the "App sounds play on"
work arrived and that module was one line under its ceiling. Each function here
builds one row, or turns one row's answer back into a setting; the dialog's
assembly and its apply step stay in ``radio_preferences``, where the order of
the rows and the order they are unpacked in sit side by side.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import reminders

__all__ = [
    "PORTABLE_WAKE_HELP",
    "RESUME_CHOICES",
    "lead_index",
    "resume_index",
    "startup_checkbox",
    "wake_checkbox",
]

#: What the wake checkbox says in a portable copy, where it is greyed out.
PORTABLE_WAKE_HELP = (
    "A portable copy does not change this computer's Task Scheduler, so it "
    "cannot wake the computer for a scheduled recording. Keeping the computer "
    "awake before a recording still works."
)


def startup_checkbox() -> Any:
    from quill.platform.windows import radio_startup
    from quill.ui.app_preferences_dialog import PreferenceCheckbox

    enabled = radio_startup.is_windows() and not radio_startup.running_portable()
    if radio_startup.running_portable():
        help_text = radio_startup.PORTABLE_REFUSAL
    elif enabled:
        help_text = (
            "Starts Quill Radio when you sign in to this Windows account. "
            "This uses your per-user startup settings and needs no administrator rights."
        )
    else:
        help_text = "Starting with Windows is only available on Windows."
    return PreferenceCheckbox(
        "Start Quill Radio with &Windows",
        help_text,
        radio_startup.is_launch_at_startup_enabled(),
        enabled=enabled,
    )


def wake_checkbox(value: bool) -> Any:
    """The one preference that changes the machine, so the one a portable copy
    cannot offer: registering a wake task on a friend's computer would outlive
    the stick. The value is kept, so an installed copy sharing the data folder
    is not quietly switched off."""
    from quill.core.paths import portable_bundle_root
    from quill.ui.app_preferences_dialog import PreferenceCheckbox

    label = "Wa&ke the computer for a scheduled recording"
    if portable_bundle_root() is not None:
        return PreferenceCheckbox(label, PORTABLE_WAKE_HELP, value, enabled=False)
    return PreferenceCheckbox(
        label,
        "If the computer is already asleep when a recording is due, "
        "ask Windows to wake it a couple of minutes beforehand. This "
        "adds a task to Windows Task Scheduler. On by default; turn "
        "it off to leave your machine's sleep entirely alone.",
        value,
    )


#: Until 2026-09-25 "Don't ask me again" on the Resume Recording dialog wrote
#: this with no way back; this row is the way back.
RESUME_CHOICES: tuple[tuple[str, str], ...] = (
    ("ask", "Ask each time (default)"),
    ("always", "Always resume them"),
    ("never", "Never resume them"),
)


def resume_index(value: object) -> int:
    """Which row a stored resume choice is, or Ask when unknown."""
    values = [stored for stored, _label in RESUME_CHOICES]
    return values.index(value) if value in values else 0


def lead_index(seconds: object) -> int:
    """Which lead-time row a stored default is, or the first when unknown."""
    for index, (offered, _label) in enumerate(reminders.LEAD_CHOICES):
        if offered == seconds:
            return index
    return 1
