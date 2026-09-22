r"""What each status-bar cell says when it is asked, which is not what it shows.

A cell's label is its value -- "Line 3, column 12" -- and its accessible name is
what it is: "Position". Neither says what pressing it *does*, and a cell that
does something when you press Enter has to be able to say so. This is that
sentence, per cell, which F1 reads and which the help-reference document is
generated from.

A table of prose rather than behaviour, so it lives beside the bar instead of
inside it (GATE-11): the sentences grow whenever a cell learns a new trick, and
the module that lays the row out should not grow with them.
"""

from __future__ import annotations

__all__ = ["STATUS_BAR_CELL_HELP"]


STATUS_BAR_CELL_HELP: dict[str, str] = {
    "message": "Open notifications",
    "line_column": "Go to line",
    "page": "Page position. Press Enter for Go To Page.",
    "word_count": "Show document statistics",
    "mode": "Toggle overwrite mode",
    "tab_mode": "Toggle Tab key mode (QUILL Key + U). Indent or insert a tab character.",
    "document_format": (
        "Current document format. Press Enter to switch between Plain "
        "text, Markdown, HTML, and Rich Text."
    ),
    "selection": "Show selection statistics",
    "encoding": "Choose document encoding",
    "line_endings": "Toggle line endings",
    "spell_check": "Open spell check dialog",
    "background_tasks": "Open notifications",
    "notifications": "Open notifications",
    "read_aloud": "Start or pause read aloud",
    "autosave": "Cycle autosave interval",
    "search_term": "Reopen Find",
    "file_path": "Open containing folder",
    "quill_key_mode": "QUILL key mode state",
    "extend_mode": "Extend selection mode active. Press F7 to toggle.",
    "abbreviations": "Abbreviation expansion. Press Enter to toggle on/off.",
    "copy_tray_slots": "Copy tray slots in use. Press Enter to open Copy Tray.",
    "language_profile": "Active language profile. Press Enter to change language.",
    "sr_name": "Detected screen reader. Press Enter to re-detect.",
    "suggestion": "Frequently used command. Press Enter to run it.",
    "braille": "Braille position. Press Enter for Read Braille Status.",
    "ai_engine": "Active AI engine. Press Enter to switch engines.",
    "radio_player": (
        "Internet Radio. Press Enter to play or pause; right-click for "
        "Stop, Mute, and Favorite Stations."
    ),
    "podcast_player": (
        "Podcasts. Press Enter to play or pause; right-click for Stop and download controls."
    ),
}
