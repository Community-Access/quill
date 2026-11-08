"""QUILL's NEVER rows: named so the palette and the refusals can find them.

A sentence never reaches these. They have rows only because the palette searches
their aliases ("quit", "settings", "theme") and a refusal can say where each one
is ("It's in File, Exit").
"""

from __future__ import annotations

from quill.core.command_catalogue.spec import CommandSpec, Risk

__all__ = ["NEVER_ROWS"]

_N = Risk.NEVER

NEVER_ROWS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "app.command_key",
        "Say or Type a Command",
        risk=_N,
        group="Tools",
        where="F11",
    ),
    CommandSpec(
        "app.exit",
        "Exit",
        aliases=("quit", "leave", "shut down"),
        risk=_N,
        group="File",
        where="File, Exit",
    ),
    CommandSpec(
        "file.restore_backup",
        "Restore a Backup",
        aliases=("recover", "previous version", "undelete"),
        risk=_N,
        group="File",
        where="File, Restore a Backup",
    ),
    CommandSpec(
        "file.open_url",
        "Open a Web Address",
        aliases=("web address", "link", "internet"),
        risk=_N,
        group="File",
        where="File, Open a Web Address",
    ),
    CommandSpec(
        "app.preferences",
        "Settings",
        aliases=("settings", "options", "configure"),
        risk=_N,
        group="Tools",
        where="Tools, Settings",
    ),
    CommandSpec(
        "app.preferences_hub",
        "Preferences Hub",
        aliases=("preferences hub", "recipes", "working modes", "quillin", "glow", "pages"),
        risk=_N,
        group="Tools",
        where="Tools, Preferences Hub",
    ),
    CommandSpec(
        "app.announcement_self_test",
        "Speech and Braille Self-Test",
        aliases=("speech test", "braille test", "output check"),
        risk=_N,
        group="Help",
        where="Help, Troubleshooting",
    ),
    CommandSpec(
        "app.report_editor_surface",
        "Report the Editor Surface",
        aliases=("braille diagnostic", "surface class", "emulation"),
        risk=_N,
        group="Help",
        where="Help, Troubleshooting",
    ),
    CommandSpec(
        "app.braille_ab",
        "Compare Braille Surfaces",
        aliases=("braille compare", "test display", "cell dots", "emulate system edit"),
        risk=_N,
        group="Help",
        where="Help, Troubleshooting",
    ),
    CommandSpec(
        "edit.replace_all",
        "Replace All",
        aliases=("substitute", "swap"),
        risk=_N,
        group="Edit",
        where="Edit, Replace",
    ),
    CommandSpec(
        "edit.copy_to_next_slot",
        "Copy to the Next Tray Slot",
        aliases=("clipboard tray", "multi copy"),
        risk=_N,
        group="Edit",
        where="Edit, Copy Tray",
    ),
    CommandSpec(
        "view.toggle_dark_mode",
        "Dark Mode",
        aliases=("theme", "light", "night", "appearance"),
        risk=_N,
        group="View",
        where="View, Dark Mode",
    ),
    CommandSpec(
        "view.send_to_tray",
        "Send to Tray",
        aliases=("minimize", "background", "hide"),
        risk=_N,
        group="View",
        where="View, Send to Tray",
    ),
    CommandSpec(
        "verbosity.where_am_i",
        "Where Am I, in Detail",
        aliases=("position", "location", "context", "orient"),
        risk=_N,
        group="Navigate",
        where="Navigate, Where Am I",
    ),
    CommandSpec(
        "tools.copy_diagnostic_summary",
        "Copy a Diagnostic Summary",
        aliases=("debug info", "support report"),
        risk=_N,
        group="Help",
        where="Help, Troubleshooting",
    ),
    CommandSpec(
        "tools.check_updates",
        "Check for Updates",
        aliases=("updates", "new version"),
        risk=_N,
        group="Help",
        where="Help, Check for Updates",
    ),
    CommandSpec(
        "file.save_to_remote",
        "Save to Remote",
        risk=_N,
        group="File",
        where="File, Save to Remote",
    ),
    CommandSpec(
        "file.github_save_back",
        "Save to GitHub",
        risk=_N,
        group="File",
        where="the GitHub menu",
    ),
)
