"""The Help rows of QUILL Lite's menu bar.

Split out of :mod:`quill.core.lite.commands` under GATE-11 when What's New
arrived, and spliced back into ``COMMANDS`` at the end, where Help sits on the
bar. The shape of every row is the table's (``menu, label, key, handler,
kind``); see that module.

Most of these rows also work with no document open: the empty window's bar
(:mod:`quill.apps.lite_shell_menu`) borrows them, so a listener who closed the
last document still reaches Help.
"""

from __future__ import annotations

HELP_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    # F1 belongs to the family's context help (quill.ui.app_context_help): it
    # answers with what *this* window is for and then what the focused control
    # does. The static key list moved to Ctrl+F1 rather than taking F1 from the
    # engine every other QuillVille app answers with.
    ("&Help", "&Help for This Window", "F1", "cmd_context_help", ""),
    # The family key for lessons, and the family window. Ctrl+Alt+F1 is what
    # Radio, Cast, Weather and QUILL answer with (bad.md P3.2).
    ("&Help", "&Tutorials...", "Ctrl+Alt+F1", "cmd_tutorials", ""),
    ("&Help", "&Keyboard Shortcuts", "Ctrl+F1", "cmd_shortcuts", ""),
    ("&Help", "Activit&y...", "Shift+F9", "cmd_activity", ""),
    ("&Help", "&Repeat Last Result", "F9", "cmd_repeat_last_result", ""),
    # The family item and key: Lite's users least know where else to write.
    ("&Help", "&Get Help from Support...", "Ctrl+Alt+F2", "cmd_get_help_from_support", ""),
    ("&Help", "Check for &Updates...", "Ctrl+Alt+U", "cmd_check_updates", ""),
    # No key (rules 4 and 9; keymap.py): Alt+H, C. See KEYLESS_WITH_REASON.
    ("&Help", "Release &Channel...", "", "cmd_release_channel", ""),
    # The changelog, as HTML in the browser -- every QuillVille app has this row
    # (quill.ui.whats_new). No key, as in QUILL: no chord is free in both
    # editors (Ctrl+Shift+F1 is QUILL's User Guide), and rule 9 asks only for a
    # way in. Alt+H, W. See KEYLESS_WITH_REASON.
    ("&Help", "&What's New", "", "cmd_whats_new", ""),
    ("&Help", "&About QUILL Lite", "Shift+F1", "cmd_about", ""),
)

__all__ = ["HELP_ROWS"]
