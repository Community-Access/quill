"""Ctrl+G: one window that goes to a line, a page, a bookmark or a heading.

Word's shape, and now the family's. QUILL had **Go To Line** on ``Ctrl+G`` and
**Go To Page** on ``Ctrl+Shift+G`` as two separate commands with two separate
prompts, and its bookmarks under a third surface entirely -- three places to
look and three things to learn for one verb (bad.md 5.4, P1.6). QuillLite moved
onto the shared :mod:`quill.ui.go_to_dialog` first; this is QUILL's half, and
QUILL brings the **Page** kind QuillLite has no model for.

Both old keys still work. ``Ctrl+Shift+G`` is now **Document Statistics**, which
is Word's key for it and QuillLite's, and Go To Page is the Page row of this
dialog -- one keystroke further and one surface fewer.

What this module does is answer "what places does this document have?". The
moving is ``_move_point`` and the location ring next door.
"""

from __future__ import annotations

from quill.core.navigation import (
    estimate_page_count,
    estimate_page_start_for_number,
    page_starts,
)
from quill.ui.go_to_dialog import GoToTarget, ask_go_to

__all__ = ["GoToMixin"]

#: Beyond this the list stops being a list and starts being a scroll. A
#: thousand-page PDF's Page rows are all identical but for the number, so the
#: number field is the faster route anyway and the list is there for browsing.
_MAX_LISTED_PAGES = 200


class GoToMixin:
    """The one Go To window, and the four kinds of place it offers."""

    def go_to(self) -> None:
        """Ctrl+G. Escape answers nothing and moves nothing."""
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        line = text.count("\n", 0, cursor) + 1
        last_line = text.count("\n") + 1
        answer = ask_go_to(
            self.frame,
            line=line,
            last_line=last_line,
            kinds={
                "Page": self._go_to_page_targets(text),
                "Bookmark": self._go_to_bookmark_targets(),
                "Heading": self._go_to_heading_targets(text),
            },
        )
        self.editor.SetFocus()
        if answer is None:
            return
        if answer.line is not None:
            self.go_to_line_number(answer.line)
            return
        if answer.position is not None:
            self._record_location_before_jump()
            target = min(answer.position, len(self.editor.GetValue()))
            self._move_point(target)
            self.editor.SetFocus()
            self._location_ring.record(target)

    # -- the three older doors, which still work ---------------------------- #

    def go_to_line(self) -> None:
        """The old Go To Line command, now the same window with Line chosen.

        Kept as a command id rather than deleted: somebody may have rebound it,
        and the palette should still answer the words they type (bad.md P1.6).
        """
        self.go_to()

    def go_to_line_number(self, lineno: int) -> None:
        """Navigate to *lineno* (1-based) without prompting.

        Used by GoToAnythingDialog (§8.1 NAV-4).
        """
        if self.editor is None:
            return
        text = self.editor.GetValue()
        line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                line_starts.append(index + 1)
        if lineno < 1 or lineno > len(line_starts):
            self._set_status(f"Line {lineno} out of range (document has {len(line_starts)} lines)")
            return
        insertion_point = line_starts[lineno - 1]
        self._record_location_before_jump()
        self._move_point(insertion_point)
        self.editor.SetFocus()
        self._location_ring.record(insertion_point)
        self._set_status(f"Moved to line {lineno}")

    def go_to_page(self) -> None:
        """The old Go To Page command, now the Page row of the same window."""
        self.go_to()

    # -- the four kinds ----------------------------------------------------- #

    def _go_to_page_targets(self, text: str) -> list[GoToTarget]:
        """Real pages where the file has them, estimates where it does not.

        The row says which: a PDF knows its page boundaries, and everything else
        is a guess from word count that depends on a font and a paper size QUILL
        does not have while you are writing. "~4 (estimated)" carries the tilde
        and the word together, the same promise the status bar's Page cell makes
        -- a page number without them is a real one.
        """
        starts = page_starts(text)
        if len(starts) > 1:
            return [
                GoToTarget(label=str(number), position=start)
                for number, start in enumerate(starts[:_MAX_LISTED_PAGES], start=1)
            ]
        words_per_page = int(getattr(self.settings, "page_estimate_words_per_page", 300) or 300)
        total = estimate_page_count(text, words_per_page)
        targets: list[GoToTarget] = []
        for number in range(1, min(total, _MAX_LISTED_PAGES) + 1):
            position = estimate_page_start_for_number(text, number, words_per_page)
            if position is None:
                break
            targets.append(GoToTarget(label=f"~{number} (estimated)", position=position))
        return targets

    def _go_to_bookmark_targets(self) -> list[GoToTarget]:
        """The numbered bookmarks, each row led by its digit (bad.md 5.2).

        Led by the digit so a listener can pick a row out by its first word, and
        so the same row reads the same way here as in QuillLite's list.
        """
        try:
            marks = self.numbered_bookmarks.all()
        except Exception:  # noqa: BLE001 - an untitled tab may have none yet
            return []
        return [
            GoToTarget(label=f"{mark.number}, {mark.label}", position=mark.position)
            for mark in marks
        ]

    def _go_to_heading_targets(self, text: str) -> list[GoToTarget]:
        """This document's headings, each row led by its level."""
        from quill.core.markdown_sections import parse_heading_blocks

        markup_kind = self._effective_markup_kind()
        if markup_kind not in {"markdown", "html"}:
            return []
        return [
            GoToTarget(label=f"Heading {block.level}, {block.title}", position=block.start)
            for block in parse_heading_blocks(text, markup_kind)
        ]
