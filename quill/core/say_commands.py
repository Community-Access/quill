"""What the Say commands say: the clipboard, the time, the open documents, the log.

Both editors have these commands and both read their words from here, so the
two cannot drift on a sentence (family rule 10). Nothing here touches wx or the
system clipboard; the shared handlers in :mod:`quill.ui.say_commands` read the
clipboard and hand this module plain values.

Every one of these is a spoken *result* -- the screen reader cannot know what is
on the clipboard, what time it is, or how many documents sit behind the one in
front -- so speaking them is exactly what GATE-13 allows.

The repeated-press shape is shared too: one press says the short answer, a quick
second press says more (spells the clipboard, gives the date, names the
documents), and for the clipboard a third shows it in a window to read through.
:data:`PRESS_WINDOW_SECONDS` is the family's half second, the same window as the
double-press echo and Choose Your AI.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from quill.core.spelling.voicing import spell_out
from quill.core.storage import write_text_atomic

__all__ = [
    "LOG_FILE_NAME",
    "PRESS_WINDOW_SECONDS",
    "SPELL_LIMIT",
    "SPEAK_LIMIT",
    "ClipboardContents",
    "append_selection",
    "describe_append",
    "describe_clear",
    "describe_clipboard",
    "describe_copied_log",
    "describe_saved_clipboard",
    "review_text",
    "save_clipboard_text",
    "say_date",
    "say_time",
    "session_log_file",
    "spell_clipboard",
    "suggested_clipboard_file_name",
    "windows_open_count",
    "windows_open_names",
]

#: A quick second press: the family's half second.
PRESS_WINDOW_SECONDS = 0.5

#: How much clipboard text one press speaks before saying how much is left.
#: Enough for a paragraph or an address; a whole copied chapter is what the
#: third press, the review window, is for.
SPEAK_LIMIT = 2000

#: How many characters a spelling covers. Spelling is for a code, a name, a
#: password reset link -- past this it stops being something anybody can hold.
SPELL_LIMIT = 200

#: How many file names one press reads before it says how many more there are.
_NAME_LIMIT = 10

#: The rotating log both editors write (``quill.stability.logging_config``).
LOG_FILE_NAME = "quill.log"


@dataclass(frozen=True, slots=True)
class ClipboardContents:
    """What the clipboard holds, as plain values.

    *files* wins over *text* when both are present, because a file copied in
    Explorer also carries its path as text, and "three files" is the answer a
    person who copied three files expects. *other* is True when the clipboard
    holds something that is neither, such as a picture.
    """

    text: str = ""
    files: tuple[str, ...] = field(default_factory=tuple)
    other: bool = False

    @property
    def empty(self) -> bool:
        return not self.files and not self.text and not self.other


def _count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def _file_names(files: Sequence[str], limit: int = _NAME_LIMIT) -> str:
    names = [Path(item).name or str(item) for item in files]
    shown = ", ".join(names[:limit])
    rest = len(names) - limit
    return f"{shown}, and {_count(rest, 'more', 'more')}" if rest > 0 else shown


def _nothing_to_say(contents: ClipboardContents) -> str:
    if contents.other:
        return "The clipboard holds something that is not text, such as a picture"
    return "The clipboard is empty"


def describe_clipboard(contents: ClipboardContents) -> str:
    """The first press: the text itself, or how many files and their names."""
    if contents.files:
        count = _count(len(contents.files), "file", "files")
        return f"{count} on the clipboard: {_file_names(contents.files)}"
    text = contents.text
    if not text:
        return _nothing_to_say(contents)
    if not text.strip():
        return (
            f"The clipboard holds only blank space, {_count(len(text), 'character', 'characters')}"
        )
    if len(text) <= SPEAK_LIMIT:
        return text
    rest = len(text) - SPEAK_LIMIT
    return (
        f"{text[:SPEAK_LIMIT]} ... and {_count(rest, 'more character', 'more characters')}. "
        "Press three times quickly to read it all"
    )


def spell_clipboard(contents: ClipboardContents) -> str:
    """The second press: the text spelled, or each file's full path."""
    if contents.files:
        return "; ".join(str(item) for item in contents.files)
    text = contents.text
    if not text:
        return _nothing_to_say(contents)
    spelled = spell_out(text[:SPELL_LIMIT])
    if len(text) <= SPELL_LIMIT:
        return spelled
    return f"The first {SPELL_LIMIT} of {len(text):,} characters: {spelled}"


def review_text(contents: ClipboardContents) -> str:
    """The third press: everything, for the read-only window. One path a line."""
    if contents.files:
        return "\n".join(str(item) for item in contents.files)
    return contents.text


def append_selection(existing: str, selection: str) -> str:
    """The clipboard text with *selection* added on its own line.

    No blank line is invented: text that already ends with a line break gets
    the selection straight after it. An empty clipboard simply becomes the
    selection, with nothing in front of it.
    """
    if not existing:
        return selection
    if existing.endswith(("\n", "\r")):
        return existing + selection
    return f"{existing}\n{selection}"


def describe_append(selection: str, combined: str) -> str:
    added = _count(len(selection), "character", "characters")
    total = _count(len(combined), "character", "characters")
    return f"Appended {added} to the clipboard, which now holds {total}"


def describe_clear(had_anything: bool) -> str:
    return "Cleared the clipboard" if had_anything else "The clipboard was already empty"


def suggested_clipboard_file_name(now: datetime) -> str:
    """A name the Save dialog can offer: ``clipboard 2026-11-06 1405.txt``."""
    return f"clipboard {now:%Y-%m-%d %H%M}.txt"


def save_clipboard_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically, UTF-8, with this system's line breaks.

    The clipboard's own line breaks are normalised first, so a copy from a web
    page with bare ``\\n`` and one from Word with ``\\r\\n`` save the same way.
    """
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    write_text_atomic(path, normalised.replace("\n", os.linesep), encoding="utf-8")


def describe_saved_clipboard(path: Path, text: str) -> str:
    return f"Saved {_count(len(text), 'character', 'characters')} to {path.name}"


def say_time(now: datetime) -> str:
    """The first press: the time, as a clock reads it -- "2:05 PM"."""
    hour = now.hour % 12 or 12
    return f"{hour}:{now.minute:02d} {'AM' if now.hour < 12 else 'PM'}"


def say_date(now: datetime) -> str:
    """The quick second press: the date in full -- "Friday, November 6, 2026"."""
    return f"{now:%A}, {now:%B} {now.day}, {now.year}"


def windows_open_count(names: Sequence[str]) -> str:
    """The first press: how many documents are open."""
    return f"{_count(len(names), 'document', 'documents')} open"


def windows_open_names(names: Sequence[str], current: int = -1) -> str:
    """The quick second press: their names, in order, the one in front marked."""
    if not names:
        return "No documents open"
    said = [f"{name} (current)" if index == current else name for index, name in enumerate(names)]
    return f"{_count(len(names), 'document', 'documents')}: " + ", ".join(said)


def session_log_file(log_dir: Path) -> Path | None:
    """This session's log in *log_dir*, or None when there is none yet.

    ``quill.log`` is the file the running app writes to; the numbered ones
    beside it are earlier sessions rotated out.
    """
    path = Path(log_dir) / LOG_FILE_NAME
    return path if path.is_file() else None


def describe_copied_log(path: Path) -> str:
    return (
        f"Copied the log, {path.name}, to the clipboard. Paste it into an email to "
        "attach the file, or into a document for its location"
    )
