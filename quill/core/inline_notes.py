"""Inline notes — sticky, content-anchored annotations (wx-free domain logic).

An inline note is a private comment a writer attaches to a line or a selection.
Unlike a standalone sticky note, it is **anchored to the content**: it remembers the
text it was placed on (a quote plus a little surrounding context), so it follows that
text as the document is edited and is **relocated when the document is reopened**.

Anchoring uses the well-understood "text quote + position" model:

* ``quote`` — the exact text the note is about (the selection, or the whole line).
* ``prefix`` / ``suffix`` — a little context on each side, used to disambiguate when
  the quote appears more than once.
* ``start`` / ``end`` — the last-known offsets, used only as a proximity hint.

:func:`resolve_inline_note` re-locates a note against the *current* text by searching
for its quote (preferring the occurrence whose context and position best match), so
notes stay attached through edits and across reloads. A quote that no longer exists
returns ``None`` (the note is "orphaned" — kept, never silently lost).

Persistence is per-document via :class:`InlineNoteVault` (``inline_notes.json``),
keyed by the document's normalized path. wx-free so it is fully unit-testable.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.bookmarks import DocumentMemory
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

INLINE_NOTES_FILENAME = "inline_notes.json"
_CONTEXT = 40  # characters of surrounding context captured for relocation


@dataclass(frozen=True, slots=True)
class InlineNote:
    """One content-anchored note."""

    note_id: str
    text: str
    quote: str
    prefix: str
    suffix: str
    start: int
    end: int

    def summary(self, limit: int = 60) -> str:
        """A short, single-line label for announcements and lists."""
        first = self.text.strip().splitlines()[0] if self.text.strip() else "(empty note)"
        return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def new_note_id() -> str:
    return uuid.uuid4().hex


def line_bounds(text: str, position: int) -> tuple[int, int]:
    """The [start, end) offsets of the line containing ``position`` (newline excluded)."""
    position = min(max(position, 0), len(text))
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return (start, len(text) if end == -1 else end)


def make_inline_note(
    body: str,
    doc_text: str,
    start: int,
    end: int,
    *,
    note_id: str | None = None,
) -> InlineNote:
    """Build a note anchored to a selection, or to the caret's line when there is
    no selection (start == end)."""
    if start > end:
        start, end = end, start
    if start == end:
        start, end = line_bounds(doc_text, start)
    start = min(max(start, 0), len(doc_text))
    end = min(max(end, start), len(doc_text))
    return InlineNote(
        note_id=note_id or new_note_id(),
        text=body,
        quote=doc_text[start:end],
        prefix=doc_text[max(0, start - _CONTEXT) : start],
        suffix=doc_text[end : end + _CONTEXT],
        start=start,
        end=end,
    )


def resolve_inline_note(doc_text: str, note: InlineNote) -> tuple[int, int] | None:
    """Return the note's current ``(start, end)`` in ``doc_text``, or ``None`` if its
    anchor text no longer exists (orphaned)."""
    quote = note.quote
    if not quote:
        # Empty/blank-line anchor: keep it at the remembered position, clamped.
        pos = min(max(note.start, 0), len(doc_text))
        return (pos, pos)
    occurrences: list[int] = []
    index = doc_text.find(quote)
    while index != -1:
        occurrences.append(index)
        index = doc_text.find(quote, index + 1)
    if not occurrences:
        return None
    if len(occurrences) == 1:
        pos = occurrences[0]
        return (pos, pos + len(quote))

    def score(pos: int) -> tuple[int, int]:
        pre = doc_text[max(0, pos - len(note.prefix)) : pos]
        suf = doc_text[pos + len(quote) : pos + len(quote) + len(note.suffix)]
        match = 0
        if note.prefix and (pre.endswith(note.prefix) or note.prefix.endswith(pre)):
            match += 2
        if note.suffix and (suf.startswith(note.suffix) or note.suffix.startswith(suf)):
            match += 2
        # Higher context match wins; ties break toward the remembered position.
        return (match, -abs(pos - note.start))

    best = max(occurrences, key=score)
    return (best, best + len(quote))


def resolved_notes(doc_text: str, notes: list[InlineNote]) -> list[tuple[InlineNote, int, int]]:
    """All notes that still resolve, as ``(note, start, end)`` sorted by start."""
    out: list[tuple[InlineNote, int, int]] = []
    for note in notes:
        located = resolve_inline_note(doc_text, note)
        if located is not None:
            out.append((note, located[0], located[1]))
    out.sort(key=lambda item: (item[1], item[2]))
    return out


def note_at(doc_text: str, notes: list[InlineNote], position: int) -> InlineNote | None:
    """The note whose resolved range contains ``position``, else the nearest one."""
    located = resolved_notes(doc_text, notes)
    if not located:
        return None
    for note, start, end in located:
        if start <= position <= end:
            return note
    return min(located, key=lambda item: abs(item[1] - position))[0]


@dataclass(slots=True)
class InlineNoteVault:
    """Per-document inline-note store, persisted to ``inline_notes.json``.

    Keyed by the document's normalized absolute path (shared with
    :class:`quill.core.bookmarks.DocumentMemory`). Untitled documents key to
    ``None`` and are never persisted. Forgiving load, atomic save.
    """

    path: Path = field(default_factory=lambda: app_data_dir() / INLINE_NOTES_FILENAME)
    documents: dict[str, list[InlineNote]] = field(default_factory=dict)

    @staticmethod
    def key_for(doc_path: object) -> str | None:
        return DocumentMemory.key_for(doc_path)

    @classmethod
    def load(cls, path: Path | None = None) -> InlineNoteVault:
        target = path if path is not None else app_data_dir() / INLINE_NOTES_FILENAME
        try:
            raw = read_json(target, default={})
        except (OSError, ValueError):
            raw = {}
        documents: dict[str, list[InlineNote]] = {}
        if isinstance(raw, dict):
            for key, items in raw.items():
                if not isinstance(key, str) or not isinstance(items, list):
                    continue
                notes: list[InlineNote] = []
                for item in items:
                    note = _note_from_dict(item)
                    if note is not None:
                        notes.append(note)
                if notes:
                    documents[key] = notes
        return cls(path=target, documents=documents)

    def save(self) -> None:
        payload = {
            key: [asdict(note) for note in self.documents[key]] for key in sorted(self.documents)
        }
        write_json_atomic(self.path, payload)

    def notes_for(self, key: str | None) -> list[InlineNote]:
        if not key:
            return []
        return list(self.documents.get(key, []))

    def set_notes(self, key: str | None, notes: list[InlineNote]) -> None:
        if not key:
            return
        if notes:
            self.documents[key] = list(notes)
        else:
            self.documents.pop(key, None)
        self.save()


def _note_from_dict(item: object) -> InlineNote | None:
    if not isinstance(item, dict):
        return None
    try:
        return InlineNote(
            note_id=str(item.get("note_id") or new_note_id()),
            text=str(item.get("text", "")),
            quote=str(item.get("quote", "")),
            prefix=str(item.get("prefix", "")),
            suffix=str(item.get("suffix", "")),
            start=max(0, int(item.get("start", 0))),
            end=max(0, int(item.get("end", 0))),
        )
    except (TypeError, ValueError):
        return None
