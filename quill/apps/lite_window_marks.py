"""Selection, bookmarks, and "what character am I on?".

Three editor features that a text box does not give you, all of them worth more
to a listener than to a reader, and all three built on wx-free QUILL cores that
already existed and are already tested:

* **Structural selection** -- :mod:`quill.core.selection`. Select the word, the
  line, the paragraph; or press Expand Selection repeatedly and walk outwards
  word to line to sentence to paragraph to block to document. Shift+arrow
  selects by *character*, which is the right tool for two letters and the wrong
  one for a paragraph; this is how you take hold of a structure without knowing
  where it starts.
* **Numbered bookmarks** -- :mod:`quill.core.numbered_bookmarks`, which lives in
  QUILL's own core rather than QuillLite's so the editor can adopt it too. A
  place you meant
  to come back to, with a number you can hold. There is no scrollbar thumb to
  remember the position of and no glance that finds the place again, so a
  bookmark is not a convenience here.

  **They survive closing the document, since 2026-09-09**, along with where
  the cursor was. That was the missing half of the same argument: "no
  scrollbar to remember the position of" does not stop being true when the
  window closes, and reopening a long file to find the nine places you marked
  gone is the same loss, merely deferred. The store is QUILL's own
  :class:`~quill.core.bookmarks.DocumentMemory`, keyed by file path and kept in
  QuillLite's data folder -- no sidecar file is written next to anybody's
  document.
* **Describe Character** -- :func:`quill.core.char_describe.describe_character`.
  What is actually under the cursor: its Unicode name, its code point, and a
  plain-language note for the invisibles that bite writers -- a non-breaking
  space, a smart quote, a zero-width joiner. A screen reader says "space" for
  four different characters, and this is the only way to tell which one broke
  the search.

Every one of them announces its outcome, because none of them moves focus and
therefore none of them produces anything the screen reader would say on its own.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.apps.lite_dialogs import choose_bookmark, show_text_window
from quill.core.char_describe import describe_character
from quill.core.numbered_bookmarks import MAX_BOOKMARKS, BookmarkSet, label_for
from quill.core.selection import expand_selection, line_span, paragraph_span, word_span

__all__ = ["DocumentMarksMixin"]

#: The structural spans Select Word / Line / Paragraph take, and what to call
#: each when announcing how much was taken.
_SPANS: dict[str, Any] = {
    "word": word_span,
    "line": line_span,
    "paragraph": paragraph_span,
}


class DocumentMarksMixin:
    """Selection, bookmarks and character inspection for a document window."""

    # ------------------------------------------------------------------ #
    # Selection
    # ------------------------------------------------------------------ #

    def _select_span(self, kind: str) -> None:
        """Select the *kind* the caret is in, and say how much that was."""
        text = self.control.GetValue()
        start, end = _SPANS[kind](text, self.control.GetInsertionPoint())
        if end <= start:
            self._announce(f"No {kind} at the cursor")
            return
        self.control.SetSelection(start, end)
        self.control.ShowPosition(start)
        self._announce(f"Selected {kind}, {len(text[start:end])} characters")
        self._touch_status()

    def cmd_select_word(self) -> None:
        self._select_span("word")

    def cmd_select_line(self) -> None:
        self._select_span("line")

    def cmd_select_paragraph(self) -> None:
        self._select_span("paragraph")

    def cmd_expand_selection(self) -> None:
        """Take the next structure outwards. Press it again to keep going.

        Word, then line, then sentence, then paragraph, then block, then the
        whole document. The scope is announced each time, so the sequence is
        something a listener can follow rather than guess at.
        """
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        if end <= start:
            start = end = self.control.GetInsertionPoint()
        grown = expand_selection(text, start, end)
        if grown is None:
            self._announce("The whole document is selected")
            return
        new_start, new_end, scope = grown
        self.control.SetSelection(new_start, new_end)
        self.control.ShowPosition(new_start)
        self._announce(f"Selected {scope}, {new_end - new_start} characters")
        self._touch_status()

    # ------------------------------------------------------------------ #
    # Describe Character
    # ------------------------------------------------------------------ #

    def cmd_describe_character(self) -> None:
        """Say exactly which character is under the cursor.

        The summary is spoken, because that is the answer nine times in ten. The
        detail -- category, code point in decimal, the note about what this
        character does to a search -- goes to the status bar's message cell, so
        it can be read again without opening anything.
        """
        description = describe_character(self.control.GetValue(), self.control.GetInsertionPoint())
        self._announce(description.summary)

    def cmd_describe_character_detail(self) -> None:
        """The full character description, in a window that can be read line by line."""
        description = describe_character(self.control.GetValue(), self.control.GetInsertionPoint())
        show_text_window(self, "Character at the cursor", description.detail)
        self.control.SetFocus()

    # ------------------------------------------------------------------ #
    # Bookmarks
    # ------------------------------------------------------------------ #

    def _set_bookmark(self, number: int) -> None:
        position = self.control.GetInsertionPoint()
        mark = self.bookmarks.set(number, position, label_for(self.control.GetValue(), position))
        self._announce(f"Bookmark {mark.number} set: {mark.label}")

    def cmd_set_bookmark(self) -> None:
        """Drop a bookmark in the next free slot, or reuse slot 1 when full."""
        self._set_bookmark(self.bookmarks.next_free_number())

    def cmd_set_bookmark_1(self) -> None:
        self._set_bookmark(1)

    def cmd_set_bookmark_2(self) -> None:
        self._set_bookmark(2)

    def cmd_set_bookmark_3(self) -> None:
        self._set_bookmark(3)

    def cmd_set_bookmark_4(self) -> None:
        self._set_bookmark(4)

    def cmd_set_bookmark_5(self) -> None:
        self._set_bookmark(5)

    def cmd_set_bookmark_6(self) -> None:
        self._set_bookmark(6)

    def cmd_set_bookmark_7(self) -> None:
        self._set_bookmark(7)

    def cmd_set_bookmark_8(self) -> None:
        self._set_bookmark(8)

    def cmd_set_bookmark_9(self) -> None:
        self._set_bookmark(9)

    def _go_to_bookmark(self, mark: Any) -> None:
        self._go_to(min(mark.position, self.control.GetLastPosition()))
        self._announce(f"Bookmark {mark.number}: {mark.label}")

    def cmd_next_bookmark(self) -> None:
        mark = self.bookmarks.next_after(self.control.GetInsertionPoint())
        if mark is None:
            self._announce("No bookmarks in this document")
            return
        self._go_to_bookmark(mark)

    def cmd_previous_bookmark(self) -> None:
        mark = self.bookmarks.previous_before(self.control.GetInsertionPoint())
        if mark is None:
            self._announce("No bookmarks in this document")
            return
        self._go_to_bookmark(mark)

    def cmd_list_bookmarks(self) -> None:
        """The bookmark list: choose one to go there, or remove one from it."""
        marks = self.bookmarks.all()
        if not marks:
            self._announce(
                f"No bookmarks in this document. Control Shift B sets one, or "
                f"Control Shift 1 to {MAX_BOOKMARKS} sets a numbered one."
            )
            return
        chosen = choose_bookmark(self, marks)
        if chosen is None:
            self.control.SetFocus()
            return
        action, number = chosen
        mark = self.bookmarks.get(number)
        if mark is None:
            self.control.SetFocus()
            return
        if action == "remove":
            self.bookmarks.clear(number)
            self._announce(f"Bookmark {number} removed")
            self.control.SetFocus()
            return
        self._go_to_bookmark(mark)

    def cmd_clear_bookmarks(self) -> None:
        count = self.bookmarks.clear_all()
        self._announce(
            f"Cleared {count} bookmark{'s' if count != 1 else ''}"
            if count
            else "No bookmarks to clear"
        )

    # ------------------------------------------------------------------ #
    # What this document remembers between sessions
    # ------------------------------------------------------------------ #

    def _memory_key(self) -> str | None:
        """This document's key in the store, or ``None`` when it has no file.

        An unsaved document is deliberately never persisted: there is nothing
        stable to key it by, and a scratch buffer that grew a row in a database
        would be a promise the next session cannot keep.
        """
        store = getattr(self.app, "document_memory", None)
        if store is None:
            return None
        return store.key_for(self.path)

    def restore_document_memory(self) -> None:
        """Put back this document's bookmarks and last cursor position.

        Called after a load, when ``self.path`` is finally known. Nothing is
        announced: the cursor moving is not an outcome the user asked for, and
        the screen reader reads the line it lands on by itself. What *would* be
        wrong is landing silently in the middle of a file with no explanation --
        so the status bar's Position cell is refreshed, which is where somebody
        checks.

        Positions are clamped to the document's length, because the file can
        have been changed by another program since the bookmarks were written
        and a bookmark past the end would send the caret nowhere.
        """
        key = self._memory_key()
        if key is None:
            return
        store = self.app.document_memory
        length = self.control.GetLastPosition()
        try:
            self.bookmarks = BookmarkSet.from_records(store.numbered_for(key))
            self.bookmarks.clamped_to(length)
            last = store.last_position(key)
        except Exception:  # noqa: BLE001 - a bad row costs the memory, not the file
            return
        if isinstance(last, int) and 0 < last <= length:
            self.control.SetInsertionPoint(last)
            self.control.ShowPosition(last)
        self._tracked_length = length
        self._touch_status()

    def remember_document_memory(self) -> None:
        """Write this document's bookmarks and cursor position back to the store.

        Called when the window closes and after each save, not on every edit:
        the caret moves on every keystroke and this writes a file. A crash
        therefore costs the current cursor position and no bookmarks that were
        set before the last save, which is the right side of that trade -- the
        alternative is a JSON write per arrow key.
        """
        key = self._memory_key()
        if key is None:
            return
        store = self.app.document_memory
        try:
            store.set_numbered(key, self.bookmarks.to_records())
            store.set_last_position(key, self.control.GetInsertionPoint())
        except Exception:  # noqa: BLE001 - never let the store fail a close
            pass

    # ------------------------------------------------------------------ #
    # Keeping bookmarks honest
    # ------------------------------------------------------------------ #

    def _track_bookmarks(self, event: wx.CommandEvent) -> None:
        """Move the bookmarks with the text on every edit.

        The control does not say *where* it changed, only that it did, so the
        shift is inferred from the length change and the caret: a bookmark that
        stayed at a fixed offset while a paragraph was inserted above it would
        point somewhere arbitrary, and a bookmark that is wrong is worse than
        one that does not exist, because it is trusted.
        """
        length = self.control.GetLastPosition()
        delta = length - self._tracked_length
        self._tracked_length = length
        if delta and len(self.bookmarks):
            caret = self.control.GetInsertionPoint()
            self.bookmarks.shift(max(0, caret - max(0, delta)), delta)
        event.Skip()
