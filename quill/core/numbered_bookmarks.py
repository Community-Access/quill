"""Numbered bookmarks for one document -- nine slots that move with the text.

Shared core, not QuillLite's own, and deliberately so. QUILL already has *named*
bookmarks (:class:`quill.core.bookmarks.BookmarkVault`) and a mark ring
(:class:`quill.core.marks.MarkRing`); what neither of them is, is nine
slots you address by digit. QuillLite needed that, and a feature QuillLite has
and QUILL cannot reach would be exactly backwards -- the small product is not
allowed to be ahead of the big one. So it lives here, where QUILL's editor can
adopt it, and QuillLite is simply its first caller.

A bookmark is a place you meant to come back to. In a long document that is the
difference between "I was somewhere in the middle" and "I was at bookmark 3",
and for a listener it matters more than it does for a reader: there is no
scrollbar thumb to remember the position of, and no glance that finds the place
again.

Nine slots, numbered, because a number is a name a person can hold. Not named
bookmarks: naming one is a dialog and a decision at exactly the moment somebody
is trying not to lose their place, and QUILL's own named marks
(:class:`quill.core.marks.NamedMarks`) are the writing environment's answer to
that, not a notepad's.

**Bookmarks persist, since 2026-09-09.** They did not at first, and the reason
given was that keeping them would mean either a sidecar file next to somebody's
document or a database keyed by path -- both decisions an editor should not make
on a user's behalf. The first half of that still holds and no sidecar is
written. The second half was wrong twice over: QUILL has kept exactly such a
database in its own data folder since #300
(:class:`~quill.core.bookmarks.DocumentMemory`), so the decision was already
made and merely not shared; and the argument for numbered bookmarks -- there is
no scrollbar to remember the position of -- does not stop when the document
closes. It is *strongest* then. Reopening a long file and finding the nine
places you marked gone is the same loss as never having marked them, deferred.

:meth:`BookmarkSet.to_records` and :meth:`BookmarkSet.from_records` are the
serialisation, here rather than in either host so both products keep the same
on-disk shape. A caller that wants the old behaviour simply never calls them.

**Positions move when the document does.** Text inserted before a bookmark
pushes it along; text deleted around it collapses it. Without that a bookmark is
a lie after the first edit, which is worse than not having one -- so
:meth:`BookmarkSet.shift` is called on every edit and is the reason this class
exists at all rather than being a bare dict.

wx-free and directly tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.bookmark_anchor import BookmarkAnchor, capture_anchor, resolve_anchor

__all__ = ["MAX_BOOKMARKS", "Bookmark", "BookmarkSet", "capture_anchor"]

#: Nine, so every one can have a digit.
MAX_BOOKMARKS = 9


@dataclass(frozen=True, slots=True)
class Bookmark:
    """One numbered place, and the line it was on when it was set."""

    number: int
    position: int
    #: A snippet of the line, so the list reads as places rather than as numbers.
    label: str
    #: The text around the position when it was set, so the bookmark can be
    #: *relocated* rather than merely moved along. ``None`` for a bookmark
    #: written by a build that did not capture one; those still shift, they
    #: just shift less well.
    anchor: BookmarkAnchor | None = None


@dataclass
class BookmarkSet:
    """The nine slots for one document, plus the one that has no number."""

    _slots: dict[int, Bookmark] = field(default_factory=dict)
    #: The unnamed, unnumbered, one-shot jump point -- the *temporary* bookmark.
    #:
    #: A different thing from the nine, and kept here rather than beside them so
    #: both editors reach it through one seam. A numbered bookmark is a place you
    #: mean to keep and therefore has a digit, a label and a row in a list; this
    #: is a pin you drop before going to look something up, overwritten silently
    #: every time it is set and forgotten when the document closes. It is
    #: deliberately absent from :meth:`to_records`: something you did not name is
    #: something you did not mean to keep.
    _temporary: int | None = None

    # -- setting and clearing ------------------------------------------------ #

    def set(
        self,
        number: int,
        position: int,
        label: str,
        anchor: BookmarkAnchor | None = None,
    ) -> Bookmark:
        """Put bookmark *number* at *position*, replacing whatever was there."""
        if not 1 <= number <= MAX_BOOKMARKS:
            raise ValueError(f"bookmark number out of range: {number}")
        mark = Bookmark(
            number=number,
            position=max(0, int(position)),
            label=label.strip(),
            anchor=anchor,
        )
        self._slots[mark.number] = mark
        return mark

    def next_free_number(self) -> int:
        """The lowest unused slot, or 1 once all nine are taken.

        Wrapping to 1 rather than refusing: somebody pressing Set Bookmark a
        tenth time wants a bookmark, and the alternative is an error message
        telling them to go and clear one first.
        """
        for number in range(1, MAX_BOOKMARKS + 1):
            if number not in self._slots:
                return number
        return 1

    def set_temporary(self, position: int) -> int:
        """Drop the temporary pin at *position*, replacing whatever was there.

        No dialog, no number, no announcement of what it replaced: a pin you
        overwrite is the whole point of this one, and asking about it would cost
        more than losing it.
        """
        self._temporary = max(0, int(position))
        return self._temporary

    @property
    def temporary(self) -> int | None:
        """Where the temporary pin is, or ``None`` when none has been dropped."""
        return self._temporary

    def clear_temporary(self) -> bool:
        """Forget the temporary pin. ``True`` when there was one."""
        had = self._temporary is not None
        self._temporary = None
        return had

    def clear(self, number: int) -> bool:
        """Remove one bookmark. ``True`` when there was one."""
        return self._slots.pop(number, None) is not None

    def clear_all(self) -> int:
        """Remove every bookmark; returns how many there were."""
        count = len(self._slots)
        self._slots.clear()
        return count

    # -- reading -------------------------------------------------------------- #

    def get(self, number: int) -> Bookmark | None:
        return self._slots.get(number)

    def all(self) -> list[Bookmark]:
        """Every bookmark, in document order rather than by number.

        Order of appearance is what somebody walking the document wants; the
        number is still on each row for the ones who think in numbers.
        """
        return sorted(self._slots.values(), key=lambda mark: (mark.position, mark.number))

    def __len__(self) -> int:
        return len(self._slots)

    # -- persistence ---------------------------------------------------------- #

    def to_records(self) -> list[dict[str, object]]:
        """The bookmarks as plain JSON-safe dicts, in slot order.

        Slot order rather than :meth:`all`'s document order, because this is the
        on-disk form and a file whose lines reorder themselves as the user edits
        makes for a diff nobody can read.
        """
        records: list[dict[str, object]] = []
        for mark in sorted(self._slots.values(), key=lambda mark: mark.number):
            record: dict[str, object] = {
                "number": mark.number,
                "position": mark.position,
                "label": mark.label,
            }
            if mark.anchor is not None:
                record["anchor"] = mark.anchor.to_dict()
            records.append(record)
        return records

    @classmethod
    def from_records(cls, records: object) -> BookmarkSet:
        """Rebuild from :meth:`to_records`, ignoring anything malformed.

        Forgiving on purpose, like every other store in this codebase: a
        bookmark file that has been hand-edited, truncated by a power cut or
        written by a newer version must cost the user the bookmarks it cannot
        read and nothing else. Refusing to open the document would be a far
        worse answer to "one of nine integers is a string".
        """
        marks = cls()
        if not isinstance(records, list):
            return marks
        for record in records:
            if not isinstance(record, dict):
                continue
            number = record.get("number")
            position = record.get("position")
            if not isinstance(number, int) or not isinstance(position, int):
                continue
            if not 1 <= number <= MAX_BOOKMARKS:
                continue
            label = record.get("label")
            marks.set(
                number,
                position,
                label if isinstance(label, str) else "",
                BookmarkAnchor.from_dict(record.get("anchor")),
            )
        return marks

    def clamped_to(self, length: int) -> None:
        """Pull every bookmark inside a document of *length* characters.

        The file on disk can have changed since the bookmarks were written --
        by another program, or by this one with the save cancelled -- and a
        bookmark past the end would send the caret nowhere.
        """
        limit = max(0, int(length))
        for number, mark in list(self._slots.items()):
            if mark.position > limit:
                self._slots[number] = Bookmark(number, limit, mark.label, mark.anchor)
        if self._temporary is not None and self._temporary > limit:
            self._temporary = limit

    def next_after(self, position: int) -> Bookmark | None:
        """The first bookmark after *position*, wrapping to the first."""
        marks = self.all()
        if not marks:
            return None
        return next((m for m in marks if m.position > position), marks[0])

    def previous_before(self, position: int) -> Bookmark | None:
        """The last bookmark before *position*, wrapping to the last."""
        marks = self.all()
        if not marks:
            return None
        earlier = [m for m in marks if m.position < position]
        return earlier[-1] if earlier else marks[-1]

    # -- keeping up with the document ---------------------------------------- #

    def reanchor(self, text: str) -> None:
        """Relocate every bookmark to where its text actually is in *text* now.

        The better of the two models both editors had, and the one QUILL has
        used for its *named* bookmarks since #300: each bookmark remembers a
        window of the text around it, and re-anchoring finds that text again,
        preferring the occurrence nearest the old offset.

        It replaces a length-delta guess -- "the document grew by nine
        characters and the caret is here, so everything after that moves nine".
        That is right for one insertion at the caret and wrong for every other
        edit there is: a Replace All, an undo, a paste over a selection, a
        reload. Being wrong is the expensive direction, because a bookmark that
        is wrong is still trusted (bad.md L9).

        Called when a bookmark is *read* rather than on every keystroke -- the
        search is over the document, and a hook that ran it per character typed
        would be the cost the document mirror exists to remove. A bookmark with
        no anchor (written by an older build) is clamped and left where it is.
        """
        for number, mark in list(self._slots.items()):
            if mark.anchor is None:
                continue
            position = resolve_anchor(text, mark.anchor)
            if position != mark.position:
                self._slots[number] = Bookmark(number, position, mark.label, mark.anchor)
        self.clamped_to(len(text))

    def shift(self, at: int, delta: int) -> None:
        """Move every bookmark after *at* by *delta* characters.

        The fallback for bookmarks with no anchor to re-find -- see
        :meth:`reanchor`, which is what a bookmark set by this version gets.

        A deletion that swallows a bookmark collapses it onto the deletion point
        rather than dropping it: the place is still roughly where the person
        meant, and silently losing a bookmark is the other way to be wrong.
        """
        if not delta:
            return
        for number, mark in list(self._slots.items()):
            if mark.position <= at:
                continue
            self._slots[number] = Bookmark(
                number=number,
                position=max(at, mark.position + delta),
                label=mark.label,
                anchor=mark.anchor,
            )


def label_for(text: str, position: int, *, width: int = 60) -> str:
    """The start of the line at *position*, for a bookmark's row in the list.

    A bookmark list of nine numbers and nothing else is a list nobody can choose
    from. The line's own first words are what makes a row recognisable, and an
    empty line says so rather than showing nothing.
    """
    if not text:
        return "(empty document)"
    position = max(0, min(position, len(text)))
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    line = text[start : end if end != -1 else len(text)].strip()
    if not line:
        return "(blank line)"
    return line if len(line) <= width else line[: width - 1] + "…"
