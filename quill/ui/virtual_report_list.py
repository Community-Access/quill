"""A report list whose rows are asked for, not inserted: for libraries of any size.

A ``wx.ListCtrl`` in report mode stores a copy of every cell, and filling one
costs about a third of a millisecond a row: the Abbreviations manager rebuilt
its ten-thousand-row list in 3.7 seconds, and did it again on every key typed
in its search box (measured 2026-10-16,
``docs/design/2026-10-16-editor-completion-measurements.md``). A *virtual*
list (``wx.LC_VIRTUAL``) holds only a row count and asks for the text of the
rows on screen, so a refill is a count and a repaint, whatever the size.

For a screen reader the two are the same control: Windows' list view answers
for an owner-data list exactly as for an ordinary one -- role, row text,
position "12 of 9,000" -- and its own type-ahead asks the control for row text
(``LVN_ODFINDITEM``), which wx answers from :meth:`OnGetItemText`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import wx

__all__ = ["VirtualReportList"]


class VirtualReportList(wx.ListCtrl):
    """A single-selection report list that reads its cells from *cell*."""

    def __init__(
        self,
        parent: wx.Window,
        columns: Sequence[tuple[str, int]],
        cell: Callable[[int, int], str],
        *,
        style: int = 0,
    ) -> None:
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL | style,
        )
        self._cell = cell
        for index, (title, width) in enumerate(columns):
            self.InsertColumn(index, title, width=width)

    def OnGetItemText(self, item: int, column: int) -> str:  # noqa: N802 - wx's name
        try:
            return self._cell(int(item), int(column))
        except (IndexError, KeyError):
            return ""

    def show_rows(self, count: int, *, select: int = -1) -> None:
        """Show *count* rows and select (and focus) row *select* when it exists."""
        # -1 is every row: a row selected before the refill must not stay
        # selected under whatever text that index shows now.
        self.SetItemState(-1, 0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.SetItemCount(count)
        self.Refresh()
        if 0 <= select < count:
            self.Select(select)
            self.Focus(select)
            self.EnsureVisible(select)
