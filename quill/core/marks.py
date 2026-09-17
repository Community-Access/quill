"""Marks: where you were standing a moment ago, in both editors.

A mark is not a bookmark, and the difference is the whole design. A bookmark is
a place you *mean to keep* -- it has a number, a label and a row in a list, and
it is still there tomorrow. A mark is where you were before you went to look
something up: you drop it without thinking, you use it up getting back, and you
never name it.

One ring, shared. QuillLite had its own -- a plain list, capped at ten, with no
de-duplication -- beside this one, which is capped at twenty and de-dupes
(bad.md L6). Two implementations of a thing that simple is not a bug on its own;
it is the mechanism by which the two editors drift, because there is no place
where the behaviour is decided once (bad.md 7.7).

**Marks survive edits**, through the same anchor QUILL's named bookmarks have
used since #300 and the numbered ones took in 2026-09-16: each mark remembers a
window of the text around it, and is relocated by finding that text again rather
than by guessing a length delta. A mark that silently drifted into the middle of
a word after a Replace All is a mark that takes you to the wrong place while
still looking like it worked.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.bookmark_anchor import BookmarkAnchor, capture_anchor, resolve_anchor

__all__ = ["MarkRing", "NamedMarks", "line_column_for_position"]


class NamedMarks:
    """Persistent name-to-position mapping for SEL-4 named marks."""

    def __init__(self) -> None:
        self._marks: dict[str, int] = {}

    def set(self, name: str, position: int) -> None:
        self._marks[name] = max(0, position)

    def get(self, name: str) -> int | None:
        return self._marks.get(name)

    def remove(self, name: str) -> bool:
        if name in self._marks:
            del self._marks[name]
            return True
        return False

    def names(self) -> list[str]:
        return sorted(self._marks)

    def items(self) -> list[tuple[str, int]]:
        return sorted(self._marks.items())


@dataclass(frozen=True, slots=True)
class _Mark:
    """One position, and the text around it when it was dropped."""

    position: int
    #: ``None`` for a mark set through the bare :meth:`MarkRing.set_mark` --
    #: those still clamp, they just cannot relocate.
    anchor: BookmarkAnchor | None = None


class MarkRing:
    """The last *max_size* places you were, most recent last."""

    def __init__(self, max_size: int = 20) -> None:
        self._max_size = max_size
        self._marks: list[_Mark] = []

    def set_mark(self, position: int, text: str | None = None) -> None:
        """Remember *position*. Pass *text* and the mark can survive an edit.

        *text* is optional so the signature stays the one every existing caller
        already uses; a caller that has the document to hand should pass it,
        because a mark that cannot be relocated is a mark that quietly points at
        the wrong word after the next Replace All.
        """
        normalized = max(0, position)
        existing = [m for m in self._marks if m.position == normalized]
        if self._marks and self._marks[-1].position == normalized:
            return
        for one in existing:
            self._marks.remove(one)
        anchor = capture_anchor(text, normalized) if text is not None else None
        self._marks.append(_Mark(normalized, anchor))
        if len(self._marks) > self._max_size:
            self._marks = self._marks[-self._max_size :]

    def pop_mark(self) -> int | None:
        if not self._marks:
            return None
        return self._marks.pop().position

    def exchange_point_and_mark(self, position: int, text: str | None = None) -> int | None:
        """Swap the newest mark with *position*, returning where the mark was."""
        if not self._marks:
            return None
        current = max(0, position)
        mark = self._marks[-1].position
        anchor = capture_anchor(text, current) if text is not None else None
        self._marks[-1] = _Mark(current, anchor)
        return mark

    def list_marks(self) -> tuple[int, ...]:
        return tuple(mark.position for mark in self._marks)

    def reanchor(self, text: str) -> None:
        """Relocate every mark to where its text actually is in *text* now.

        Called when the marks are *read* rather than on every keystroke: the
        search is over the document, and a hook that ran it per character typed
        would cost exactly what the document mirror exists to save.
        """
        relocated: list[_Mark] = []
        for mark in self._marks:
            if mark.anchor is None:
                relocated.append(_Mark(min(mark.position, len(text)), None))
                continue
            relocated.append(_Mark(resolve_anchor(text, mark.anchor), mark.anchor))
        self._marks = relocated

    def clamped_to(self, limit: int) -> None:
        """Pull every mark back inside a document that has got shorter.

        QuillLite clamped on pop and QUILL did not, so the same shrunken
        document gave two answers (bad.md L6). It is done here now, once.
        """
        ceiling = max(0, limit)
        self._marks = [_Mark(min(mark.position, ceiling), mark.anchor) for mark in self._marks]

    def __len__(self) -> int:
        return len(self._marks)


def line_column_for_position(text: str, position: int) -> tuple[int, int]:
    capped = max(0, min(position, len(text)))
    line = text.count("\n", 0, capped) + 1
    line_start = text.rfind("\n", 0, capped) + 1
    column = capped - line_start + 1
    return line, column
