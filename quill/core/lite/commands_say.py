"""The Say rows of QUILL Lite's menu bar: the clipboard, the time, the open documents.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced back into
``COMMANDS`` at the positions the table marks. The shape of every row is the
table's (``menu, label, key, handler, kind``). The handlers are QUILL's
(``quill/ui/say_commands.py``, shared), on the same keys in both editors.

**The keys.** Measured on 2026-11-06, almost nothing plain was free in both
editors; what was left after the system-wide show/hide keys, the picker's
suggestions (Alt+Shift+PageUp/PageDown), the screen-reader profile's table moves
(Ctrl+Alt+Shift+arrows), Word's Redo (Alt+Shift+Backspace) and the bare Ctrl+Alt
AltGr range were taken out was a handful (and two that looked free, Ctrl+Alt+Shift+Comma
and Ctrl+Alt+Shift+Backspace, are Previous Difference and Delete Paragraph). The four
that get pressed went to those:

* **Say Clipboard, Alt+Shift+Home**: the one people press to check before they
  paste. One press says it, a quick second spells it, a third shows it.
* **Append Selection to Clipboard, Alt+Shift+End**: added at the end, so End.
* **Say Time and Date, Alt+Shift+Space**: one press the time, a quick second
  press the date.
* **Say Windows Open, Ctrl+Shift+Space**: one press the count, a quick
  second press the names.

Save Clipboard to File and Clear Clipboard are once-in-a-while commands (rule
9) with no chord left free in both editors, so they are reached from this
submenu -- Alt+E, B, then F or B -- the same as in QUILL. Copy Log is Help's
(:mod:`quill.core.lite.commands_help`).
"""

from __future__ import annotations

_CLIPBOARD = "&Edit|Clip&board"

CLIPBOARD_SAY_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    (_CLIPBOARD, "Sa&y Clipboard", "Alt+Shift+Home", "cmd_say_clipboard", ""),
    (_CLIPBOARD, "&Append Selection to Clipboard", "Alt+Shift+End", "cmd_append_to_clipboard", ""),
    (_CLIPBOARD, "Save Clipboard to &File...", "", "cmd_save_clipboard", ""),
    (_CLIPBOARD, "Clear Clip&board", "", "cmd_clear_clipboard", ""),
    (_CLIPBOARD, "", "", "", "sep"),
)

TIME_SAY_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    # No access letter: Tools has spent all but Q, V, X and Z, and none is in
    # the name. Silence beats a duplicate (GATE-14); the key is the route.
    ("&Tools", "Say Time and Date", "Alt+Shift+Space", "cmd_say_time", ""),
)

WINDOW_SAY_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Window", "&Say Windows Open", "Ctrl+Shift+Space", "cmd_say_windows_open", ""),
)

__all__ = ["CLIPBOARD_SAY_ROWS", "TIME_SAY_ROWS", "WINDOW_SAY_ROWS"]
