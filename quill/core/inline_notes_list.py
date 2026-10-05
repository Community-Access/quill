"""Every inline note in a document, as one list (wx-free).

Two kinds of note exist side by side: the private sidecar notes
(:mod:`quill.core.inline_notes`) and notes written into the file as
``quill-note`` comments (:mod:`quill.core.inline_notes_file`). Next, Previous,
Speak, Delete and the List Inline Notes window treat them the same, so they all
read this one list, built by :func:`collect_rows`.

The list window's idea is PlanCake's (Andre of Oire Software): a note you can
only meet one at a time is a note you cannot review, and one place that shows
them all -- what each says, the line it is on and the text it is about --
turns notes into something you can work through, clear when done and hand on.
An orphaned sidecar note, whose text was deleted, finally has a place to be
seen and removed: it sorts last and says so.

Also here, so both editors word them identically: the plain-text Copy All, and
the Markdown and JSON exports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from quill.core.inline_notes import InlineNote, resolve_inline_note
from quill.core.inline_notes_file import IN_FILE_KINDS, FileNote, parse_file_notes

__all__ = [
    "ORPHANED",
    "NoteRow",
    "collect_rows",
    "first_sentence",
    "row_at",
    "rows_as_json",
    "rows_as_markdown",
    "rows_as_text",
]

#: The On column, and the spoken label, for a note whose text is gone.
ORPHANED = "the text it was on is gone"

SIDECAR = "sidecar"
IN_FILE = "file"


@dataclass(frozen=True, slots=True)
class NoteRow:
    """One note, whichever kind, located in the current text.

    ``position`` is where Go To lands (the start of the text the note is
    about) and is ``None`` for an orphan. ``line`` is 1-based. ``sidecar`` or
    ``file_note`` holds the underlying record, whichever this row came from.
    """

    kind: str
    note_id: str
    text: str
    position: int | None
    end: int | None
    line: int | None
    anchor: str
    sidecar: InlineNote | None = None
    file_note: FileNote | None = None

    @property
    def orphaned(self) -> bool:
        return self.position is None

    def summary(self, limit: int = 60) -> str:
        first = self.text.strip().splitlines()[0] if self.text.strip() else "(empty note)"
        return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"

    def on_label(self) -> str:
        return ORPHANED if self.orphaned else (first_sentence(self.anchor) or "a blank line")

    def kind_label(self) -> str:
        return "In the file" if self.kind == IN_FILE else "Private"


def first_sentence(text: str, limit: int = 80) -> str:
    """The first sentence (or line) of *text*, short enough to read aloud."""
    flat = " ".join(text.split())
    match = re.match(r"(.+?[.!?])(\s|$)", flat)
    sentence = match.group(1) if match else flat
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def _line_of(text: str, position: int) -> int:
    return text.count("\n", 0, max(0, min(position, len(text)))) + 1


def collect_rows(
    doc_text: str, sidecar: list[InlineNote], kind: str | None = None
) -> list[NoteRow]:
    """Every note, located, in document order; orphans last.

    In-file notes are read only when *kind* is Markdown or HTML: a ``.txt``
    that happens to quote the form is not a document with notes in it.
    """
    rows: list[NoteRow] = []
    for note in sidecar:
        located = resolve_inline_note(doc_text, note)
        if located is None:
            rows.append(
                NoteRow(SIDECAR, note.note_id, note.text, None, None, None, note.quote, note)
            )
            continue
        start, end = located
        rows.append(
            NoteRow(
                SIDECAR,
                note.note_id,
                note.text,
                start,
                end,
                _line_of(doc_text, start),
                doc_text[start:end],
                note,
            )
        )
    if kind in IN_FILE_KINDS:
        for file_note in parse_file_notes(doc_text, kind or "markdown"):
            orphan = not file_note.anchor.strip()
            rows.append(
                NoteRow(
                    IN_FILE,
                    file_note.note_id,
                    file_note.text,
                    None if orphan else file_note.anchor_start,
                    None if orphan else file_note.anchor_end,
                    None if orphan else _line_of(doc_text, file_note.anchor_start),
                    file_note.anchor,
                    file_note=file_note,
                )
            )
    rows.sort(key=lambda r: (r.position is None, r.position or 0, r.end or 0))
    return rows


def row_at(rows: list[NoteRow], position: int) -> NoteRow | None:
    """The note whose text contains *position*, else the nearest located one.

    An in-file note's own comment counts as part of it, so the caret on the
    ``<!-- quill-note -->`` line finds that note.
    """
    located = [r for r in rows if r.position is not None]
    if not located:
        return None
    for row in located:
        assert row.position is not None and row.end is not None
        if row.position <= position <= row.end:
            return row
        if row.file_note is not None and row.file_note.start <= position < row.file_note.end:
            return row
    return min(located, key=lambda r: abs((r.position or 0) - position))


def _where(row: NoteRow) -> str:
    return "line unknown" if row.line is None else f"line {row.line}"


def rows_as_text(rows: list[NoteRow]) -> str:
    """Copy All: one note per paragraph, with its line and what it is on."""
    parts = []
    for number, row in enumerate(rows, start=1):
        parts.append(f'Note {number}, {_where(row)}, on "{row.on_label()}":\n{row.text.strip()}')
    return "\n\n".join(parts) + ("\n" if parts else "")


def rows_as_markdown(rows: list[NoteRow], title: str) -> str:
    """Export as Markdown: a heading per note, the anchor quoted beneath it."""
    out = [f"# Inline notes: {title}", ""]
    for number, row in enumerate(rows, start=1):
        out.append(f"## Note {number} ({_where(row)})")
        out.append("")
        out.append(f"> {row.on_label()}")
        out.append("")
        out.append(row.text.strip())
        out.append("")
    return "\n".join(out)


def rows_as_json(rows: list[NoteRow], document: str) -> str:
    """Export as JSON, for other tools: stable keys, one object per note."""
    payload = {
        "document": document,
        "notes": [
            {
                "note": row.text.strip(),
                "line": row.line,
                "on": "" if row.orphaned else first_sentence(row.anchor, 200),
                "orphaned": row.orphaned,
                "in_file": row.kind == IN_FILE,
            }
            for row in rows
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
