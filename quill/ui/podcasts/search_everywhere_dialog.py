"""Podcasts > Search Everywhere... -- search every subscription, episode,
and note at once, grouped by type."""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.filtering import SearchResult
from quill.ui.dialog_contract import apply_modal_ids


class SearchEverywhereDialog:
    """Returns the selected :class:`SearchResult`, or ``None`` if closed
    without picking one."""

    def __init__(
        self,
        parent: object,
        *,
        on_search: Callable[[str], list[SearchResult]],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_search = on_search
        self._announce = announce_cb or (lambda _m: None)
        self._results: list[SearchResult] = []
        self._result: SearchResult | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Search Everywhere",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((520, 440))
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        self._query_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._query_ctrl.SetName("Search every subscription, episode, and note at once")
        search_row.Add(self._query_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        search_btn = wx.Button(self.dialog, label="&Search")
        search_row.Add(search_btn, 0)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Results, grouped by shows, then episodes, then notes")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._status = wx.StaticText(self.dialog, label="")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        go_btn = wx.Button(self.dialog, wx.ID_OK, "&Go To")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.AddStretchSpacer()
        btn_row.Add(go_btn, 0, wx.RIGHT, 6)
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._query_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search_click)
        search_btn.Bind(wx.EVT_BUTTON, self._on_search_click)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_go)
        go_btn.Bind(wx.EVT_BUTTON, self._on_go)

    def show(self) -> SearchResult | None:
        self.dialog.CentreOnParent()
        self._query_ctrl.SetFocus()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Go To",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Search Everywhere", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_search_click(self, _event: object) -> None:
        query = self._query_ctrl.GetValue().strip()
        self._list.Clear()
        self._results = self._on_search(query) if query else []
        for result in self._results:
            self._list.Append(result.label)
        if self._results:
            self._list.SetSelection(0)
        count = len(self._results)
        self._status.SetLabel(f'{count} result(s) for "{query}".' if query else "")
        self._announce(self._status.GetLabel() or "Type something to search.")

    def _on_go(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._results):
            self._result = self._results[index]
            self.dialog.EndModal(self._wx.ID_OK)
