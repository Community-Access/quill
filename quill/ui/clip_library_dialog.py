"""Clip Library dialog (#895) — browse, search, favorite, promote to Copy
Tray, or copy any remembered Fragment straight to the clipboard.

Modeled on ``copy_tray_dialog.py``'s list + preview + action-buttons shape,
adapted for a much larger, favorite-protected rolling history instead of 12
fixed slots.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.clip_library import ClipLibrary
from quill.core.fragment import FragmentFormat, render_fragment


class ClipLibraryDialog:
    """Browse, search, favorite, remove, or promote a remembered Fragment."""

    def __init__(
        self,
        parent: object,
        library: ClipLibrary,
        announce_cb: Callable[[str], None] | None = None,
        promote_cb: Callable[[int], None] | None = None,
        content_format: FragmentFormat = FragmentFormat.TEXT,
    ) -> None:
        self._library = library
        self._announce = announce_cb or (lambda _msg: None)
        self._promote_cb = promote_cb
        self._content_format = content_format
        self._indices: list[int] = []

        self.dialog = wx.Dialog(
            parent, title="Clip Library", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(640, 440))
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(self.dialog, label="&Search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self._search = wx.TextCtrl(self.dialog)
        self._search.SetName("Search the clip library")
        search_row.Add(self._search, 1, wx.EXPAND)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 8)

        body = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.dialog, label="&Clips"), 0, wx.BOTTOM, 2)
        self._listbox = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._listbox.SetName("Clip Library entries")
        left.Add(self._listbox, 1, wx.EXPAND)
        body.Add(left, 1, wx.EXPAND | wx.RIGHT, 8)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.dialog, label="&Content:"), 0, wx.BOTTOM, 2)
        self._content = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self._content.SetName("Clip content")
        right.Add(self._content, 1, wx.EXPAND)
        body.Add(right, 2, wx.EXPAND)
        root.Add(body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_copy = wx.Button(self.dialog, label="&Copy to Clipboard")
        self._btn_favorite = wx.Button(self.dialog, label="&Favorite")
        self._btn_promote = wx.Button(self.dialog, label="&Promote to Copy Tray...")
        self._btn_remove = wx.Button(self.dialog, label="&Remove")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Close")
        for btn in (self._btn_copy, self._btn_favorite, self._btn_promote, self._btn_remove):
            btn_row.Add(btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        self._search.Bind(wx.EVT_TEXT, self._on_search)
        self._listbox.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        apply_listbox_activation(self._listbox, lambda _e: self._on_copy(_e))
        self._btn_copy.Bind(wx.EVT_BUTTON, self._on_copy)
        self._btn_favorite.Bind(wx.EVT_BUTTON, self._on_favorite)
        self._btn_promote.Bind(wx.EVT_BUTTON, self._on_promote)
        self._btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)

        self._rebuild_list()
        self._listbox.SetFocus()

    # -- public API --

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Clip Library")

    def close(self) -> None:
        self.dialog.Destroy()

    # -- internal helpers --

    def _selected_index(self) -> int | None:
        sel = self._listbox.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._indices):
            return None
        return self._indices[sel]

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _rebuild_list(self, *, query: str = "") -> None:
        pairs = self._library.search(query) if query else self._library.all_entries()
        self._indices = [index for index, _entry in pairs]
        self._listbox.Clear()
        for _index, entry in pairs:
            tag = "[favorite] " if entry.favorite else ""
            self._listbox.Append(f"{tag}{entry.display_label()}")
        if self._indices:
            self._listbox.SetSelection(0)
        self._refresh_preview()
        self._update_buttons()

    def _refresh_preview(self) -> None:
        index = self._selected_index()
        if index is None:
            self._content.SetValue("")
            return
        entry = self._library.entry(index)
        self._content.SetValue(render_fragment(entry.fragment, FragmentFormat.TEXT))

    def _update_buttons(self) -> None:
        index = self._selected_index()
        has_selection = index is not None
        self._btn_copy.Enable(has_selection)
        self._btn_promote.Enable(has_selection)
        self._btn_remove.Enable(has_selection)
        self._btn_favorite.Enable(has_selection)
        if has_selection:
            entry = self._library.entry(index)  # type: ignore[arg-type]
            self._btn_favorite.SetLabel("Un&favorite" if entry.favorite else "&Favorite")

    # -- event handlers --

    def _on_search(self, _event: object) -> None:
        self._rebuild_list(query=self._search.GetValue())

    def _on_selection_changed(self, _event: object) -> None:
        self._refresh_preview()
        self._update_buttons()

    def _on_copy(self, _event: object) -> None:
        index = self._selected_index()
        if index is None:
            return
        text = render_fragment(self._library.entry(index).fragment, self._content_format)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        self._set_status("Copied to the system clipboard.")

    def _on_favorite(self, _event: object) -> None:
        index = self._selected_index()
        if index is None:
            return
        entry = self._library.entry(index)
        now_favorite = not entry.favorite
        self._library.set_favorite(index, now_favorite)
        self._rebuild_list(query=self._search.GetValue())
        message = "Marked as a favorite." if now_favorite else "Removed from favorites."
        self._set_status(message)

    def _on_promote(self, _event: object) -> None:
        index = self._selected_index()
        if index is None or self._promote_cb is None:
            return
        self._promote_cb(index)

    def _on_remove(self, _event: object) -> None:
        index = self._selected_index()
        if index is None:
            return
        self._library.remove(index)
        self._rebuild_list(query=self._search.GetValue())
        self._set_status("Clip removed.")
