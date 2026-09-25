"""Ctrl+G: one window that goes to a line, a bookmark or a heading.

Split out of :mod:`quill.apps.lite_window_commands` under GATE-11, and it earns
its own module for the same reason the dialog earns its own window: going
*somewhere* is one idea, and it had been three -- a line number here, a bookmark
list on Alt+Shift+G, a heading list on Ctrl+Alt+L. The dialog itself is shared
(:mod:`quill.ui.go_to_dialog`) so QUILL can open the same one; this is
QUILL Lite's half, which is answering "what places does this document have?".

``_go_to`` stays next door with the location ring it feeds. Everything here
*decides where*; that one does the moving.
"""

from __future__ import annotations

from quill.ui.go_to_dialog import GoToTarget, ask_go_to

__all__ = ["DocumentGoToMixin"]


class DocumentGoToMixin:
    """Ctrl+G, and the two lists it offers."""

    def cmd_goto_line(self) -> None:
        """Ctrl+G: go to a line, a bookmark or a heading -- one window.

        Word's shape, and now the family's. It asked for a line number and
        nothing else, so a bookmark meant Alt+Shift+G and a heading meant
        Ctrl+Alt+L: three surfaces for one verb, which is three places to look
        and three things to learn (bad.md 5.4, P1.6). Those two keys still work
        and go straight to their own list, which is the faster route when you
        know which kind you want; this is the one to press when you do not.

        No Page kind here. QUILL Lite has no pagination model, and a greyed row
        for a thing the product does not do is a row to walk past forever --
        the dialog shows the kinds it is given.
        """
        total = max(1, self.control.GetNumberOfLines())
        _ok, _column, line = self.control.PositionToXY(self.control.GetInsertionPoint())
        answer = ask_go_to(
            self,
            line=line + 1,
            last_line=total,
            kinds={
                "Bookmark": self._go_to_bookmark_targets(),
                "Heading": self._go_to_heading_targets(),
            },
        )
        self.control.SetFocus()
        if answer is None:
            return
        if answer.line is not None:
            self.go_to_line_number(answer.line)
            return
        if answer.position is not None:
            self._go_to(min(answer.position, self.control.GetLastPosition()))

    def _go_to_bookmark_targets(self) -> list[GoToTarget]:
        """This document's bookmarks, each row led by its digit.

        Led by the digit so "3, Enter" needs no extra chord and so a listener
        can pick a row out of the list by its first word (bad.md 5.2).
        """
        return [
            GoToTarget(label=f"{mark.number}, {mark.label}", position=mark.position)
            for mark in self.reanchored_bookmarks().all()
        ]

    def _go_to_heading_targets(self) -> list[GoToTarget]:
        """This document's headings, each row led by its level."""
        return [
            GoToTarget(label=f"Heading {level}, {title}", position=start)
            for start, level, title in self.all_document_headings()
        ]

    def go_to_line_number(self, line: int) -> None:
        """Put the caret at the start of *line* (1-based). Clamped, never refused.

        Public because it is the callback Go To Anything uses to land on a
        heading, and because "go to a line" is a reasonable thing for anything
        else to ask a document window for.
        """
        position = self.control.XYToPosition(0, max(0, int(line) - 1))
        self._go_to(position if position >= 0 else self.control.GetLastPosition())
