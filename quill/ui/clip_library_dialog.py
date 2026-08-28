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
        left.Add(wx.StaticText(self.dialog, label="C&lips"), 0, wx.BOTTOM, 2)
        # Extended selection, not single: marking several clips and joining
        # them is the one assembly job this dialog does. Ordinary arrow-key use
        # is unchanged -- a plain move still selects exactly one.
        self._listbox = wx.ListBox(self.dialog, style=wx.LB_EXTENDED)
        self._listbox.SetName(
            "Clip Library entries; mark several with Ctrl or Shift to combine them"
        )
        left.Add(self._listbox, 1, wx.EXPAND)
        body.Add(left, 1, wx.EXPAND | wx.RIGHT, 8)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.dialog, label="C&ontent:"), 0, wx.BOTTOM, 2)
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
        self._btn_rename = wx.Button(self.dialog, label="Re&name...")
        self._btn_combine = wx.Button(self.dialog, label="Com&bine Marked...")
        self._btn_abbreviation = wx.Button(self.dialog, label="Save as &Abbreviation...")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Close")
        for btn in (
            self._btn_copy,
            self._btn_favorite,
            self._btn_promote,
            self._btn_rename,
            self._btn_combine,
            self._btn_abbreviation,
            self._btn_remove,
        ):
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
        self._btn_rename.Bind(wx.EVT_BUTTON, self._on_rename)
        self._btn_combine.Bind(wx.EVT_BUTTON, self._on_combine)
        self._btn_abbreviation.Bind(wx.EVT_BUTTON, self._on_save_as_abbreviation)

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
        marked = self._marked_indexes()
        return marked[0] if marked else None

    def _marked_indexes(self) -> list[int]:
        """Library indexes for every marked row, in the order they appear."""
        return [
            self._indices[row]
            for row in self._listbox.GetSelections()
            if 0 <= row < len(self._indices)
        ]

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
        self._btn_rename.Enable(has_selection)
        self._btn_abbreviation.Enable(has_selection)
        # Combining one clip with itself is not a thing; require two.
        self._btn_combine.Enable(len(self._marked_indexes()) > 1)
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

    def _on_rename(self, _event: object) -> None:
        """Give a clip a short name -- easier to find later than its contents."""
        index = self._selected_index()
        if index is None:
            return
        entry = self._library.entry(index)
        dialog = wx.TextEntryDialog(
            self.dialog,
            "A short name for this clip (leave it empty to go back to a preview of the text):",
            "Rename Clip",
            entry.fragment.title,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        if show_modal_dialog(dialog, "Rename Clip") == wx.ID_OK:
            self._library.rename(index, dialog.GetValue())
            self._rebuild_list(query=self._search.GetValue())
            self._set_status("Renamed.")
        dialog.Destroy()

    def _on_combine(self, _event: object) -> None:
        """Join the marked clips, in the order they appear, onto the clipboard."""
        from quill.core.clip_library import COMBINE_SEPARATORS
        from quill.ui.dialog_contract import show_modal_dialog

        indexes = self._marked_indexes()
        if len(indexes) < 2:
            return
        labels = list(COMBINE_SEPARATORS)
        dialog = wx.SingleChoiceDialog(
            self.dialog,
            f"Join the {len(indexes)} marked clips with:",
            "Combine Clips",
            labels,
        )
        if show_modal_dialog(dialog, "Combine Clips") == wx.ID_OK:
            separator = COMBINE_SEPARATORS[labels[dialog.GetSelection()]]
            text = self._library.combine(indexes, separator)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
            self._set_status(f"Combined {len(indexes)} clips onto the clipboard.")
        dialog.Destroy()

    def _on_save_as_abbreviation(self, _event: object) -> None:
        """Turn a clip into an abbreviation -- which then works everywhere,
        here and in Quill Inkwell, because both read the same library."""
        import uuid

        from quill.core.abbreviations import (
            Abbreviation,
            load_abbreviation_library,
            save_abbreviation_library,
        )
        from quill.ui.abbreviation_manager_dialog import _AbbreviationEditDialog
        from quill.ui.dialog_contract import show_modal_dialog

        index = self._selected_index()
        if index is None:
            return
        text = render_fragment(self._library.entry(index).fragment, FragmentFormat.TEXT)
        library = load_abbreviation_library()
        entry = Abbreviation(id=str(uuid.uuid4()), abbreviation="", expansion=text)
        dialog = _AbbreviationEditDialog(
            self.dialog,
            entry,
            categories=sorted({a.category for a in library.abbreviations if a.category}),
        )
        if show_modal_dialog(dialog.dialog, "New Abbreviation") == wx.ID_OK and dialog.trigger_text:
            dialog.apply_to(entry)
            library.abbreviations.append(entry)
            library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(library)
            self._set_status(f"Saved as the abbreviation {entry.abbreviation}.")
        dialog.close()

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
