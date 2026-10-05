"""QUILL Lite's rows for reviewing a document: notes, tasks and a shareable page.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced back
into ``COMMANDS`` where the table marks. The shape of every row is the
table's (``menu, label, key, handler, kind``); see that module.

All three came to the family together on 2026-10-04 from PlanCake (Andre of
Oire Software), and all three run QUILL's code, shared
(:mod:`quill.ui.inline_notes_commands`, :mod:`quill.ui.task_list_commands`,
:mod:`quill.ui.html_export_commands`), on QUILL's chords:

**Inline notes**, Tools > Inline Notes, on the four chords QUILL has had for
years plus the two new ones (rule 2: the command both products have keeps the
chord). Alt+Shift+I was Snippets here; Snippets moved to Ctrl+Alt+Shift+Home,
free in both editors, and QUILL aliased the same chord for its gallery (rule
5), so the divergence ``parity.py`` used to record is gone.

**Toggle Task Done**, Format, beside Lists, on Ctrl+Alt+Enter -- Word's style
separator, which neither editor has (rule 1 does not bite).

**Export as HTML**, File, on Ctrl+Alt+Shift+End: a once-in-a-while command
gets a key, not a short one (rule 9).
"""

from __future__ import annotations

__all__ = ["EXPORT_ROWS", "NOTE_ROWS", "NOTE_SUBMENU_ROWS", "TASK_ROWS"]

_NOTES = "&Tools|Inline &Notes"

NOTE_SUBMENU_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools", "Inline &Notes", "", "", "sub"),
)

NOTE_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    (_NOTES, "&Add Inline Note...", "Alt+Shift+I", "cmd_add_inline_note", ""),
    (_NOTES, "&Next Inline Note", "Alt+Shift+J", "cmd_next_inline_note", ""),
    (_NOTES, "&Previous Inline Note", "Alt+Shift+K", "cmd_previous_inline_note", ""),
    (_NOTES, "&Speak Inline Note (Twice to Edit)", "Alt+Shift+H", "cmd_speak_inline_note", ""),
    (_NOTES, "", "", "", "sep"),
    (_NOTES, "&Delete Inline Note...", "Alt+Shift+Delete", "cmd_delete_inline_note", ""),
    (_NOTES, "&List Inline Notes...", "Alt+Shift+Enter", "cmd_list_inline_notes", ""),
)

TASK_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("F&ormat", "Toggle T&ask Done", "Ctrl+Alt+Enter", "cmd_toggle_task_done", ""),
)

EXPORT_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&File", "Export as &HTML...", "Ctrl+Alt+Shift+End", "cmd_export_html", ""),
)
