"""The three sentences an editor should be able to say about itself.

A screen reader tells you what is under the cursor. It cannot tell you what the
application just did on its own behalf, and it cannot tell you what kind of
document you have arrived in -- both of those are the application's own
knowledge, and if it does not say them nobody does.

Three questions, approved 2026-09-16 as the magical tier (bad.md P3.7), each of
which a sighted user answers with a glance and a listener could not answer at
all:

* **"What is this?"** on arriving in a document. Not the file name, which the
  title bar has: the *shape* -- how long it is, whether it has headings, whether
  it is a list of things or a wall of prose. It is the glance at a page before
  you start reading, and the thing a listener pays twenty seconds to reconstruct.
* **"What just changed?"** after a command rewrote the text. Sort Lines, Remove
  Duplicates, Change Case and thirty others rewrite the buffer and the reader
  says nothing, so the only way to find out was to read the document again.
* **"What did that undo take back?"** Ctrl+Z is the most-pressed command in any
  editor and the most silent: it is not even clear whether it did anything.

The fourth of the four -- repeat the last announcement -- already shipped as
#1304, which is why it is not here.

Sentences rather than numbers, because these are read aloud: "Sorted lines
ascending: 40 lines, unchanged length" is something you can act on, and
"lines=40 delta=0" is something you have to translate first.

wx-free, and the phrasing lives here so the two editors cannot describe the same
change two different ways.
"""

from __future__ import annotations

from quill.core.document_text import EditRecord
from quill.core.metrics import DocumentStats

__all__ = [
    "NOTHING_CHANGED",
    "NOTHING_TO_REPORT",
    "arrival_summary",
    "describe_change",
    "describe_undo",
]

#: Said when the journal has nothing in it. Not silence: silence is the symptom
#: the command exists to cure, and answering "nothing yet" is an answer.
NOTHING_TO_REPORT = "Nothing has changed this document yet."

#: Said when an edit made no difference to the text at all.
NOTHING_CHANGED = "That changed nothing."


def _plural(count: int, noun: str) -> str:
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def _size_phrase(record: EditRecord) -> str:
    """How the size moved, in the terms somebody would check it in."""
    characters = record.characters_delta
    lines = record.lines_delta
    if characters == 0 and lines == 0:
        return "same length"
    parts: list[str] = []
    if lines:
        parts.append(f"{'+' if lines > 0 else ''}{lines:,} lines")
    if characters:
        parts.append(f"{'+' if characters > 0 else ''}{characters:,} characters")
    return ", ".join(parts)


def describe_change(record: EditRecord | None) -> str:
    """What the last edit did, in one sentence.

    Reads the action's own status sentence rather than a command id, because
    this is spoken: the words the command chose for itself are better English
    than any identifier, and they are the words the person just heard.
    """
    if record is None:
        return NOTHING_TO_REPORT
    where = "over the whole document" if record.position < 0 else f"at position {record.position:,}"
    return f"{record.action} {where}: {_size_phrase(record)}."


def describe_undo(record: EditRecord | None, *, worked: bool) -> str:
    """What an undo just took back, or that there was nothing to take back.

    ``worked`` is what the control reported. The distinction matters more than
    it looks: an undo at the bottom of the stack and an undo that reversed a
    forty-line sort are both silent, and telling them apart by listening is
    impossible.
    """
    if not worked:
        return "Nothing left to undo."
    if record is None:
        return "Undone."
    # Reversed on purpose: undoing an edit that ADDED ten lines removes ten.
    reversed_lines = -record.lines_delta
    reversed_characters = -record.characters_delta
    if reversed_lines == 0 and reversed_characters == 0:
        return f"Undone: {record.action}, same length."
    parts: list[str] = []
    if reversed_lines:
        parts.append(f"{'+' if reversed_lines > 0 else ''}{reversed_lines:,} lines")
    if reversed_characters:
        parts.append(f"{'+' if reversed_characters > 0 else ''}{reversed_characters:,} characters")
    return f"Undone: {record.action}, {', '.join(parts)}."


def arrival_summary(
    stats: DocumentStats,
    *,
    kind: str = "",
    headings: int = 0,
    list_items: int = 0,
    read_only: bool = False,
) -> str:
    """One sentence about the document you have just arrived in.

    The order is the order somebody would want it: **how big**, then **what
    shape**, then **anything that will stop you** -- because the last of those
    changes what you do next and the rest only changes how you feel about it.

    Empty is worth saying out loud. An empty document and a document that failed
    to load sound identical, and the difference is whether to start typing.
    """
    if stats.characters == 0:
        opening = "Empty document"
    else:
        opening = f"{_plural(stats.words, 'word')}, {_plural(max(1, stats.lines), 'line')}"
    parts = [f"{kind}: {opening}" if kind else opening]

    shape: list[str] = []
    if headings:
        shape.append(_plural(headings, "heading"))
    if list_items:
        shape.append(_plural(list_items, "list item"))
    if shape:
        parts.append(" and ".join(shape))
    elif stats.characters:
        # Worth saying: "no headings" is why Alt+Down will not move, and a
        # listener who does not hear it spends the next few presses finding out.
        parts.append("No headings")

    if read_only:
        # Last, because it is the one that changes what you do next.
        parts.append("Read-only")
    return ". ".join(parts) + "."
