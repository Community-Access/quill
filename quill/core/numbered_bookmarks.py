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

__all__ = ["MAX_BOOKMARKS", "Bookmark", "BookmarkSet"]

#: Nine, so every one can have a digit.
MAX_BOOKMARKS = 9


@dataclass(frozen=True, slots=True)
class Bookmark:
    """One numbered place, and the line it was on when it was set."""

    number: int
    position: int
    #: A snippet of the line, so the list reads as places rather than as numbers.
    label: str


@dataclass
class BookmarkSet:
    """The nine slots for one document."""

    _slots: dict[int, Bookmark] = field(default_factory=dict)

    # -- setting and clearing ------------------------------------------------ #

    def set(self, number: int, position: int, label: str) -> Bookmark:
        """Put bookmark *number* at *position*, replacing whatever was there."""
        if not 1 <= number <= MAX_BOOKMARKS:
            raise ValueError(f"bookmark number out of range: {number}")
        mark = Bookmark(number=number, position=max(0, int(position)), label=label.strip())
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
        return [
            {"number": mark.number, "position": mark.position, "label": mark.label}
            for mark in sorted(self._slots.values(), key=lambda mark: mark.number)
        ]

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
            marks.set(number, position, label if isinstance(label, str) else "")
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
                self._slots[number] = Bookmark(number, limit, mark.label)

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

    def shift(self, at: int, delta: int) -> None:
        """Move every bookmark after *at* by *delta* characters.

        Called on every edit. A bookmark that stayed at a fixed offset while the
        text moved under it would point somewhere arbitrary after the first
        paragraph is inserted above it -- and a bookmark that is wrong is worse
        than one that does not exist, because it is trusted.

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
