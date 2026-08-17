"""The Book Library dialog: search LibriVox and pick an audiobook to play.

Self-contained so the player frame stays under budget. The actual search is an
injected callable (``search_fn``) returning
:class:`~quill.core.media.librivox.LibriVoxBook` records, so this dialog carries
no network code of its own and is easy to drive from either the standalone app or
the in-QUILL player. Shown through the host's ``_show_modal_dialog`` (GATE-16).
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.media.librivox import LibriVoxBook
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, set_accessible_name

SearchFn = Callable[[str], list[LibriVoxBook]]


class LibraryDialog(wx.Dialog):
    """Search the free LibriVox audiobook catalog and choose a book."""

    def __init__(self, parent: wx.Window, *, search_fn: SearchFn) -> None:
        super().__init__(parent, title="Book Library")
        self._search_fn = search_fn
        self._books: list[LibriVoxBook] = []

        outer = wx.BoxSizer(wx.VERTICAL)

        outer.Add(wx.StaticText(self, label="&Search LibriVox (free audiobooks):"), 0, wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._query = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._query, "Search LibriVox")
        self._query.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        from quill.ui.search_reset import bind_empty_query_reset

        bind_empty_query_reset(self._query, self._reset_results)
        search_btn = wx.Button(self, label="&Search")
        search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        row.Add(self._query, 1, wx.RIGHT, 6)
        row.Add(search_btn, 0)
        outer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        outer.Add(wx.StaticText(self, label="&Results:"), 0, wx.LEFT | wx.TOP, 8)
        self._results = wx.ListBox(self, name="Results")
        set_accessible_name(self._results, "Search results")
        apply_listbox_activation(self._results, lambda _c: self.EndModal(wx.ID_OK))
        outer.Add(self._results, 1, wx.EXPAND | wx.ALL, 8)

        self._status = wx.StaticText(self, label="Type a title and press Search.")
        outer.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(outer)
        apply_modal_ids(
            self, affirmative_id=wx.ID_OK, affirmative_label="&Play", cancel_id=wx.ID_CANCEL
        )

    def _reset_results(self) -> None:
        """Emptying the search field empties the results list (search_reset.py)."""
        if not self._books:
            return
        self._books = []
        self._results.Clear()
        self._status.SetLabel("Type a title and press Search.")

    def _on_search(self, _event: wx.CommandEvent) -> None:
        query = self._query.GetValue().strip()
        if not query:
            return
        self._status.SetLabel("Searching LibriVox...")
        wx.SafeYield()
        try:
            self._books = self._search_fn(query)
        except Exception as error:  # noqa: BLE001 - surfaced in the status line
            self._books = []
            self._status.SetLabel(f"Search failed: {error}")
            return
        self._results.Clear()
        for book in self._books:
            label = f"{book.title} - {book.authors}" if book.authors else book.title
            self._results.Append(label)
        if self._books:
            self._results.SetSelection(0)
            self._status.SetLabel(f"{len(self._books)} result(s). Choose one and press Play.")
            self._results.SetFocus()
        else:
            self._status.SetLabel("No results. Try a different title.")

    def selected_book(self) -> LibriVoxBook | None:
        """The chosen book, or None when nothing is selected."""
        index = self._results.GetSelection()
        if 0 <= index < len(self._books):
            return self._books[index]
        return None


__all__ = ["LibraryDialog"]
