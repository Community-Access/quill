"""Where a reopened document puts the cursor back, and when to say so (FUX-01).

Both editors remember where the cursor was in each saved document
(:class:`~quill.core.bookmarks.DocumentMemory`). A bare offset is right only
while the file is unchanged: edit it in another program and the same number
lands in a different sentence, and nothing tells the listener -- who cannot
glance at the page to notice -- that this is not where they stopped.

So the place is remembered with the text around it (a
:class:`~quill.core.bookmark_anchor.BookmarkAnchor`, the model the bookmarks
already use) and found again on reopen:

* **Found** -- still there, or moved because text above it changed: the cursor
  goes to it and nothing is said. The screen reader reads the line it lands on.
* **Gone** -- the text was rewritten or deleted: the cursor goes to the start of
  the line it was on, and :func:`lost_place_sentence` says so once, with the
  line, so the listener knows to look rather than trust it. An emptied file
  is left at its start, which the reader already says is blank.
* **No anchor** -- remembered by an older build: the offset, as before, since
  there is nothing to check it by.

A place is remembered only while the text is what the file holds: the anchor
is checked against the file on the next open, and text that was never saved is
not in it.

wx-free and shared, so QUILL and QUILL Lite cannot disagree about it.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.bookmark_anchor import BookmarkAnchor, capture_anchor, locate_anchor

__all__ = [
    "PLACE_NOTE_DELAY_MS",
    "ResumedPlace",
    "anchor_if_saved",
    "lost_place_sentence",
    "resume_place",
]

#: How long after arriving in the document the lost-place sentence waits, so the
#: screen reader has said the window and the line first and does not cut it off.
PLACE_NOTE_DELAY_MS = 400


@dataclass(frozen=True, slots=True)
class ResumedPlace:
    """Where to put the cursor, and whether the remembered text was gone."""

    position: int
    lost: bool = False


def anchor_if_saved(text: str, saved_text: str | None, position: int) -> BookmarkAnchor | None:
    """The anchor to remember with *position*, or ``None`` when it would mislead.

    Only when *text* is what the file holds: the anchor is checked against the
    file on the next open, and text that was never saved is not in it, so an
    anchor taken from it would report a change that never happened.
    """
    if saved_text is None or text != saved_text:
        return None
    return capture_anchor(text, position)


def resume_place(text: str, last: int | None, anchor: BookmarkAnchor | None) -> ResumedPlace | None:
    """Where to put the cursor in *text*, or ``None`` to leave it at the start."""
    if last is None:
        return None
    length = len(text)
    if anchor is None:
        return ResumedPlace(last) if 0 < last <= length else None
    position, found = locate_anchor(text, anchor)
    if found:
        return ResumedPlace(position) if position > 0 else None
    if not text:
        return None  # an emptied file: the reader says it is blank
    return ResumedPlace(_line_start(text, anchor.line), lost=True)


def lost_place_sentence(text: str, position: int) -> str:
    """What to say when the remembered text is gone. One sentence, with the line."""
    line = text.count("\n", 0, max(0, min(position, len(text)))) + 1
    return f"The text where you left off has changed. The cursor is at the start of line {line}."


def _line_start(text: str, line: int) -> int:
    """The offset of 0-based *line*, or of the last line when the text is shorter."""
    start = 0
    for _ in range(max(0, line)):
        found = text.find("\n", start)
        if found == -1:
            break
        start = found + 1
    return start
