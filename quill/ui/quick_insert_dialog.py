"""Quick Insert -- pick an abbreviation and insert its expansion.

The way to use an abbreviation without remembering it, and the only way to
reach an entry whose trigger mode is "manual". Type to filter, arrow to choose,
Enter to insert; the list starts in most-used order so the everyday entries are
one keystroke away.

Hardened dialog (A11Y-4): exposes show() and close(); callers never touch the
inner wx.Dialog.
"""

from __future__ import annotations

import wx

from quill.core.abbreviations import (
    Abbreviation,
    AbbreviationLibrary,
    quick_insert_order,
)
from quill.ui.dialog_contract import apply_modal_ids


class QuickInsertDialog:
    """A type-to-filter picker over the abbreviation library."""

    def __init__(self, parent: object, library: AbbreviationLibrary) -> None:
        self._entries = quick_insert_order(library)
        self._visible: list[Abbreviation] = list(self._entries)
        self._chosen: Abbreviation | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Quick Insert",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(520, 380))

        root = wx.BoxSizer(wx.VERTICAL)

        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(
            wx.StaticText(self.dialog, label="&Find:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self._filter_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._filter_ctrl.SetName("Filter abbreviations by name or text")
        filter_row.Add(self._filter_ctrl, 1, wx.EXPAND)
        root.Add(filter_row, 0, wx.EXPAND | wx.ALL, 8)

        self._list = wx.ListCtrl(
            self.dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self._list.SetName("Abbreviations")
        self._list.InsertColumn(0, "Abbreviation", width=130)
        self._list.InsertColumn(1, "Expands to", width=290)
        self._list.InsertColumn(2, "Category", width=90)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._preview = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 70)
        )
        self._preview.SetName("Full expansion of the selected abbreviation")
        root.Add(self._preview, 0, wx.EXPAND | wx.ALL, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_btn = self.dialog.FindWindowById(wx.ID_OK)
            if ok_btn is not None:
                ok_btn.SetLabel("&Insert")
                ok_btn.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
        )

        self._filter_ctrl.Bind(wx.EVT_TEXT, self._on_filter)
        # Down from the filter field moves into the list, so the whole dialog is
        # usable without leaving the keyboard's home position.
        self._filter_ctrl.Bind(wx.EVT_KEY_DOWN, self._on_filter_key)
        self._filter_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_accept)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selected)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_accept)

        self._rebuild()
        self._filter_ctrl.SetFocus()

    # -- public API --------------------------------------------------------------

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    @property
    def chosen(self) -> Abbreviation | None:
        """The entry the user picked, or None when they cancelled."""
        return self._chosen

    # -- internals ---------------------------------------------------------------

    def _rebuild(self) -> None:
        query = self._filter_ctrl.GetValue().strip().lower()
        if query:
            self._visible = [
                a
                for a in self._entries
                if query in a.abbreviation.lower()
                or query in a.expansion.lower()
                or query in a.description.lower()
            ]
        else:
            self._visible = list(self._entries)
        self._list.DeleteAllItems()
        for i, entry in enumerate(self._visible):
            self._list.InsertItem(i, entry.abbreviation)
            self._list.SetItem(i, 1, entry.expansion.replace("\n", " ")[:60])
            self._list.SetItem(i, 2, entry.category)
        if self._visible:
            self._list.Select(0)
            self._list.EnsureVisible(0)
            self._update_preview(0)
        else:
            self._preview.SetValue("")

    def _update_preview(self, index: int) -> None:
        if 0 <= index < len(self._visible):
            self._preview.SetValue(self._visible[index].expansion)

    def _on_filter(self, _event: object) -> None:
        self._rebuild()

    def _on_filter_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_DOWN and self._visible:
            self._list.SetFocus()
            return
        event.Skip()

    def _on_selected(self, event: wx.ListEvent) -> None:
        self._update_preview(event.GetIndex())
        event.Skip()

    def _on_accept(self, _event: object) -> None:
        index = self._list.GetFirstSelected()
        if index < 0 and self._visible:
            index = 0
        if 0 <= index < len(self._visible):
            self._chosen = self._visible[index]
            self.dialog.EndModal(wx.ID_OK)
