"""Browse mode by misspelling and by page, and the page said once on crossing.

Two browse-mode keys, added 2026-10-17, in a module of their own because
``main_frame_browse.py`` is near the line cap (GATE-11):

* **M / Shift+M** -- the next or previous misspelled word. The same spelling
  data the Quick Nav panel lists as Misspellings
  (:func:`quill.core.spellcheck.list_misspellings`, with the user's
  dictionaries), so the panel and the key never disagree about what is wrong.
  The word itself is said with its line, because a caret moved by a command is
  not something every screen reader reads out.
* **F / Shift+F** -- the next or previous page, over the form feeds that mark
  page breaks (how QUILL's PDF reader separates pages, and how a BRF or a
  plain-text file with page breaks arrives). F for form feed: P is already
  Paragraph. Says "Page 5 of 12".

And one thing that is not a key: when the caret crosses a page break by any
movement -- an arrow, Page Down, a search -- "Page 5 of 12" is said **once**,
and not again until the caret is on a different page. The latch
(:class:`quill.core.navigation.PageLatch`) is what stops it being re-spoken on
every arrow key; a document without form feeds never says anything. F and
Shift+F settle the latch, so their own announcement is not followed by a
second one.

QUILL Lite has no browse mode, so it has neither key; its status bar shows
the same page count (:func:`quill.core.navigation.page_position`).
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

from quill.core.marks import line_column_for_position
from quill.core.navigation import PageLatch, page_starts, page_target

__all__ = ["BrowsePagesMixin"]


class BrowsePagesMixin:
    """Misspelling and page navigation for browse mode, mixed into MainFrame."""

    # ------------------------------------------------------------------ #
    # M and Shift+M
    # ------------------------------------------------------------------ #

    def _browse_misspelling(self, *, reverse: bool) -> None:
        from quill.core.spellcheck import list_misspellings

        text = self._browse_text()  # type: ignore[attr-defined]
        try:
            found = list_misspellings(
                text,
                self._spell_dictionary(),  # type: ignore[attr-defined]
                filename=getattr(getattr(self, "document", None), "path", None),
            )
        except Exception:  # noqa: BLE001 - a spell-check hiccup never breaks browse mode
            found = []
        if not found:
            self._quill_feedback(  # type: ignore[attr-defined]
                "No misspelled words in this document.",
                status_message="No misspellings found",
                sound_kind="error",
            )
            return
        cursor = int(self.editor.GetInsertionPoint())  # type: ignore[attr-defined]
        wrap = bool(getattr(self.settings, "browse_mode_wrap", True))  # type: ignore[attr-defined]
        ordered = list(reversed(found)) if reverse else found
        target = next(
            (m for m in ordered if (m.start < cursor if reverse else m.start > cursor)), None
        )
        if target is None and wrap:
            target = ordered[0]
        if target is None:
            direction = "previous" if reverse else "next"
            self._quill_feedback(  # type: ignore[attr-defined]
                f"No {direction} misspelled word.",
                status_message=f"No {direction} misspelling",
                sound_kind="error",
            )
            return
        self._browse_land(target.start)
        self.editor.SetSelection(target.start, target.end)  # type: ignore[attr-defined]
        line, _column = line_column_for_position(text, target.start)
        message = f"Misspelled: {target.word}, line {line}"
        self._quill_feedback(message, status_message=message, sound_kind="move")  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # F and Shift+F
    # ------------------------------------------------------------------ #

    def _browse_page(self, *, reverse: bool) -> None:
        text = self._browse_text()  # type: ignore[attr-defined]
        starts = page_starts(text)
        if len(starts) < 2:
            self._quill_feedback(  # type: ignore[attr-defined]
                "This document has no page breaks.",
                status_message="No page breaks",
                sound_kind="error",
            )
            return
        cursor = int(self.editor.GetInsertionPoint())  # type: ignore[attr-defined]
        target = page_target(starts, cursor, forward=not reverse)
        if target is None and bool(getattr(self.settings, "browse_mode_wrap", True)):  # type: ignore[attr-defined]
            target = starts[-1] if reverse else starts[0]
        if target is None:
            direction = "previous" if reverse else "next"
            self._quill_feedback(  # type: ignore[attr-defined]
                f"No {direction} page.", status_message=f"No {direction} page", sound_kind="error"
            )
            return
        self._browse_land(target)
        page = bisect_right(starts, target)
        self._page_latch().settle(page, getattr(self, "document", None))
        message = f"Page {page} of {len(starts)}"
        self._quill_feedback(message, status_message=message, sound_kind="move")  # type: ignore[attr-defined]

    def _browse_land(self, target: int) -> None:
        """Move the caret the way every browse jump does: Back returns from it."""
        self._record_location_before_jump()  # type: ignore[attr-defined]
        self._move_point(target)  # type: ignore[attr-defined]
        self.editor.SetFocus()  # type: ignore[attr-defined]
        self._location_ring.record(target)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # The page said once, on crossing
    # ------------------------------------------------------------------ #

    def _page_latch(self) -> PageLatch:
        latch = getattr(self, "_browse_page_latch", None)
        if latch is None:
            latch = PageLatch()
            self._browse_page_latch = latch
        return latch

    def _cached_page_starts(self) -> list[int]:
        """The page starts, re-read only when the document or its length changed,
        so an arrow key in a long PDF is not a read of the whole text."""
        editor: Any = getattr(self, "editor", None)
        document = getattr(self, "document", None)
        key = (id(document), int(editor.GetLastPosition()))
        cached = getattr(self, "_browse_page_starts_cache", None)
        if cached is not None and cached[0] == key:
            return list(cached[1])
        starts = page_starts(self._browse_text())  # type: ignore[attr-defined]
        self._browse_page_starts_cache = (key, starts)
        return starts

    def _maybe_announce_page_crossing(self) -> None:
        """Say "Page N of M" when the caret has just crossed a page break."""
        try:
            starts = self._cached_page_starts()
            if len(starts) < 2:
                return
            page = bisect_right(starts, int(self.editor.GetInsertionPoint()))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a dead control mid-close; a cue never raises
            return
        if self._page_latch().crossed(page, getattr(self, "document", None)):
            self._announce(f"Page {page} of {len(starts)}")  # type: ignore[attr-defined]
