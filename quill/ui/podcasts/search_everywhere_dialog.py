"""Podcasts > Search Everywhere... -- search every subscription, episode,
and note at once, grouped by type.

The box is a **combo**, not a plain text field, because the searches somebody
runs here are worth keeping (list.md 5.5). A podcast search is not usually a
one-off: "the episode about the harbour" is a thing somebody looks for several
times across a week, from a different place in the library each time, and the
query is the part they have to reconstruct from memory every attempt. Quill
Radio has remembered its searches for a while; this is the same idea over one
field instead of three, and the pure half is
:mod:`quill.core.podcasts.search_history`.

Two details that are easy to get wrong and cost the whole feature:

* **Only a committed search is remembered.** Typing is not searching, and a
  history full of the half-words somebody passed through on the way to what
  they meant is a history nobody can find anything in.
* **Re-filling the dropdown clears the text on wxMSW**, so what was typed is
  put back afterwards. A search box that empties itself the moment you press
  Search is indistinguishable from one that lost the query.
"""

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
        recent_searches: tuple[str, ...] = (),
        on_recent_searches_changed: Callable[[tuple[str, ...]], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_search = on_search
        self._announce = announce_cb or (lambda _m: None)
        self._results: list[SearchResult] = []
        self._result: SearchResult | None = None
        self._recent = tuple(recent_searches)
        self._on_recent_changed = on_recent_searches_changed

        self.dialog = wx.Dialog(
            parent,
            title="Search Everywhere",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((520, 440))
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        # A combo rather than a text field: the same box, plus everything
        # searched before it on the down arrow. An editable combo keeps
        # typing exactly as it was -- nothing is selected until somebody
        # arrows to it deliberately.
        self._query_ctrl = wx.ComboBox(
            self.dialog,
            value="",
            choices=list(self._recent),
            style=wx.TE_PROCESS_ENTER,
        )
        self._query_ctrl.SetName(
            "Search every subscription, episode, and note at once; "
            "down arrow for searches you have run before"
        )
        self._query_ctrl.SetHelpText(
            "Searches show titles, episode titles, show notes, your own notes "
            "and any transcripts already downloaded. The last "
            f"{len(self._recent) or 'few'} searches are on the down arrow."
        )
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
        # Picking a remembered search runs it: choosing a row from a list of
        # searches is a commit, not a way of filling in a text box.
        self._query_ctrl.Bind(wx.EVT_COMBOBOX, self._on_recent_picked)
        search_btn.Bind(wx.EVT_BUTTON, self._on_search_click)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_go)
        go_btn.Bind(wx.EVT_BUTTON, self._on_go)
        from quill.ui.search_reset import bind_empty_query_reset

        bind_empty_query_reset(self._query_ctrl, self._reset_results)

    def _reset_results(self) -> None:
        """Emptying the field empties the list -- results for text that is no
        longer there must not linger looking current."""
        if not self._results:
            return
        self._results = []
        self._list.Clear()
        self._status.SetLabel("")
        self._announce("Search cleared.")

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
        if query:
            self._remember(query)
        self._status.SetLabel(f'{count} result(s) for "{query}".' if query else "")
        self._announce(self._status.GetLabel() or "Type something to search.")

    def _on_recent_picked(self, event: object) -> None:
        """Run a search the listener has run before."""
        index = int(getattr(event, "GetSelection", lambda: -1)() or -1)
        if not (0 <= index < len(self._recent)):
            return
        query = self._recent[index]
        self._query_ctrl.SetValue(query)
        self._announce(f"Searching again for {query}.")
        self._on_search_click(None)

    def _remember(self, query: str) -> None:
        """Record a search that was actually committed."""
        from quill.core.podcasts import search_history

        updated = search_history.remember(self._recent, query)
        if updated == self._recent:
            return
        self._recent = updated
        try:
            self._query_ctrl.Set(list(self._recent))
        except RuntimeError:  # the dialog is being torn down
            return
        # Re-filling the dropdown clears the text on wxMSW; put back what was
        # typed, or the box appears to have swallowed the query.
        if self._query_ctrl.GetValue() != query:
            self._query_ctrl.SetValue(query)
        if self._on_recent_changed is not None:
            self._on_recent_changed(updated)

    def _on_go(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._results):
            self._result = self._results[index]
            self.dialog.EndModal(self._wx.ID_OK)
