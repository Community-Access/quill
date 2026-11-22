"""File > Scribe for Documents, QUILL Lite's rows (PRD 8.2).

Spliced into :data:`quill.core.lite.commands.COMMANDS` after Import /
Convert Document, and one row in Window. The handlers are
:mod:`quill.apps.lite_window_scribe`'s, each a door to the shared
:class:`quill.ui.scribe_entry.ScribeEntryPoints`, so QUILL has every one of
these commands under the id in :data:`SCRIBE_EQUIVALENTS` (rule 10: QUILL Lite
may never be ahead of QUILL).

**In File, as a submenu.** QUILL keeps these in Tools > Scribe for Documents
with My Scribe Documents and Convert with Scribe also in File; QUILL Lite's
File menu has three letters left, so the whole family sits in one File
submenu, where a person converting a document looks. The submenu takes B
(Scri&be), which Open from Clipboard gave up: it keeps Ctrl+Alt+Shift+Enter
as its route. Lite has no braille view, so there is no Translate with Scribe
row; a BRF is still one of the formats, saved and opened as text.

**No chords**, as in QUILL, where none of these has a default key either:
every row is a once-in-a-while command reached from this menu and the Command
Palette (rule 9). The reasons are in ``test_lite_commands.py``.

The whole submenu is the ``scribe`` feature area (command_areas.py), off
until it is turned on in Tools > Customize Features or on first need.
"""

from __future__ import annotations

_S = "&File|Scri&be for Documents"
_SEP = (_S, "", "", "", "sep")

#: The rows, spliced into ``COMMANDS``.
SCRIBE_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&File", "Scri&be for Documents", "", "", "sub"),
    (_S, "Convert a &File...", "", "cmd_scribe_convert_file", ""),
    (_S, "Convert &This Document...", "", "cmd_scribe_convert_this", ""),
    (_S, "&Export with Scribe for Documents...", "", "cmd_scribe_export", ""),
    (_S, "Convert from a &Link...", "", "cmd_scribe_convert_link", ""),
    _SEP,
    (_S, "&My Scribe Documents", "", "cmd_scribe_my_documents", ""),
    (_S, "&Conversions", "", "cmd_scribe_conversions", ""),
    (_S, "Scribe &Status", "", "cmd_scribe_status", ""),
    (_S, "&Repeat Last Scribe Message", "", "cmd_scribe_repeat", ""),
    _SEP,
    (_S, "Sign &In...", "", "cmd_scribe_sign_in", ""),
    (_S, "Sign &Out", "", "cmd_scribe_sign_out", ""),
    (_S, "Open My Scribe &Account in Browser", "", "cmd_scribe_account", ""),
    (_S, "O&ptions...", "", "cmd_scribe_options", ""),
    (_S, "A&bout Scribe for Documents", "", "cmd_scribe_about", ""),
)

#: Window > Scribe Conversions, as in QUILL (PRD 7.4: reachable from every app).
SCRIBE_WINDOW_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Window", "Scribe Con&versions", "", "cmd_scribe_window", ""),
)

#: QUILL Lite handler -> QUILL command id, for parity.py's COMMAND_EQUIVALENTS.
SCRIBE_EQUIVALENTS: dict[str, str] = {
    "cmd_scribe_convert_file": "scribe.convert_file",
    "cmd_scribe_convert_this": "scribe.convert_this",
    "cmd_scribe_export": "scribe.export",
    "cmd_scribe_convert_link": "scribe.convert_link",
    "cmd_scribe_my_documents": "scribe.my_documents",
    "cmd_scribe_conversions": "scribe.conversions",
    "cmd_scribe_status": "scribe.status",
    "cmd_scribe_repeat": "scribe.repeat",
    "cmd_scribe_sign_in": "scribe.sign_in",
    "cmd_scribe_sign_out": "scribe.sign_out",
    "cmd_scribe_account": "scribe.account",
    "cmd_scribe_options": "scribe.options",
    "cmd_scribe_about": "scribe.about",
    "cmd_scribe_window": "scribe.window",
}

__all__ = ["SCRIBE_EQUIVALENTS", "SCRIBE_ROWS", "SCRIBE_WINDOW_ROWS"]
