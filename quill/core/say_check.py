"""testSay, from EdSharp: what QUILL meant to say, beside what was heard.

Every command whose whole job is to say something is run once, then twice in a
row, and what QUILL handed to speech is written down. The report is a document
with an empty column for the tester to fill in from JAWS or NVDA, because only
a person (or the reader's own speech viewer) can say what the reader actually
spoke. It catches the two failures a test suite cannot: over-announcing
(GATE-13: QUILL saying what the reader already said) and speech that never
arrived. complete.md Part 4, from EdSharp's history, 2026-11.

No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["SAY_CHECK_COMMANDS", "SayCheckRow", "say_check_report"]

#: The commands that only speak, in the order the report lists them.
SAY_CHECK_COMMANDS: tuple[str, ...] = (
    "verbosity.where_am_i",
    "verbosity.speak_status",
    "navigate.speak_window_title",
    "navigate.speak_full_path",
    "navigate.speak_status_summary",
    "navigate.say_time",
    "edit.say_selected",
    "edit.say_clipboard",
    "window.say_windows_open",
    "notes.speak_inline_note",
    "app.repeat_last_announcement",
)


@dataclass(frozen=True, slots=True)
class SayCheckRow:
    title: str
    key: str
    once: tuple[str, ...]
    twice: tuple[str, ...]


def _cell(said: Sequence[str]) -> str:
    text = " / ".join(said) if said else "(nothing)"
    return text.replace("|", "\\|").replace("\n", " ")


def say_check_report(rows: Sequence[SayCheckRow], *, reader: str = "") -> str:
    """The report as a Markdown document, one table row per press."""
    lines = [
        "# What QUILL says",
        "",
        "Each command was run once, then twice in a row. The third column is what "
        "QUILL handed to speech. Fill in the fourth from your screen reader "
        f"{'(' + reader + ') ' if reader else ''}"
        "and mark the last: **Same**, **Extra** (it said more than QUILL meant, or "
        "repeated what the reader had already said), or **Missing** (QUILL meant to "
        "say it and nothing was heard).",
        "",
        "| Command | Key | Press | QUILL meant to say | Your screen reader said "
        "| Same, Extra or Missing |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        key = row.key or "(no key)"
        lines.append(f"| {row.title} | {key} | Once | {_cell(row.once)} |  |  |")
        lines.append(f"| {row.title} | {key} | Twice | {_cell(row.twice)} |  |  |")
    return "\n".join(lines) + "\n"
