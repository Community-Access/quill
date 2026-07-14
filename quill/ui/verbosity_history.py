"""Announcement history viewer (verbosity §24, §25).

Review recent announcements, replay or copy the selected one, and read its full
"Why did QUILL say that?" explanation trace. Backed by the pure
:class:`quill.core.verbosity.history.AnnouncementHistory`. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.history import AnnouncementHistory
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityHistoryDialog"]


class VerbosityHistoryDialog:
    """Browse, replay, copy, and explain recent announcements."""

    def __init__(
        self,
        parent: object,
        history: AnnouncementHistory,
        *,
        announce_cb: Callable[[str], None] | None = None,
        copy_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._history = history
        self._announce = announce_cb or (lambda _m: None)
        self._copy = copy_cb or (lambda _t: None)
        self._entries = list(history.all())

        self.dialog = wx.Dialog(
            parent, title="Announcement history", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(600, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(
            wx.StaticText(self.dialog, label="&Filter:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._filter = wx.SearchCtrl(self.dialog)
        self._filter.SetName("Filter announcements")
        self._filter.SetHint("Filter by verb or text")
        filter_row.Add(self._filter, 1)
        root.Add(filter_row, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Announcements:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetName("Recent announcements")
        self._list.SetMinSize(wx.Size(-1, 170))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(wx.StaticText(self.dialog, label="&Explanation:"), 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._detail.SetName("Why did QUILL say that")
        self._detail.SetMinSize(wx.Size(-1, 110))
        root.Add(self._detail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._replay_btn = wx.Button(self.dialog, label="&Replay")
        self._copy_btn = wx.Button(self.dialog, label="&Copy")
        self._explain_btn = wx.Button(self.dialog, label="&Explain")
        self._clear_btn = wx.Button(self.dialog, label="Clear &History")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        for b in (self._replay_btn, self._copy_btn, self._explain_btn, self._clear_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._filter.Bind(wx.EVT_TEXT, lambda _e: self._repopulate())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select())
        self._replay_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_replay())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_copy())
        self._explain_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_explain())
        self._clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_clear())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self._repopulate()

    def _filtered(self) -> list:
        needle = self._filter.GetValue().strip().lower()
        if not needle:
            return list(self._entries)
        return [
            e for e in self._entries if needle in e.verb_id.lower() or needle in e.visual.lower()
        ]

    def _repopulate(self) -> None:
        self._list.Clear()
        self._visible = self._filtered()
        for entry in self._visible:
            stamp = entry.timestamp.strftime("%H:%M:%S")
            self._list.Append(f"{stamp}  {entry.verb_id}  —  {entry.visual}")
        if self._visible:
            self._list.SetSelection(0)
            self._on_select()
        else:
            self._detail.SetValue("")

    def _selected_entry(self):
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._visible):
            return None
        return self._visible[index]

    def _on_select(self) -> None:
        entry = self._selected_entry()
        if entry is not None:
            self._detail.SetValue(entry.trace.to_text())

    def _on_replay(self) -> None:
        entry = self._selected_entry()
        if entry is not None:
            self._announce(entry.visual)

    def _on_copy(self) -> None:
        entry = self._selected_entry()
        if entry is not None:
            self._copy(entry.trace.to_text())
            self._announce("Copied explanation to clipboard.")

    def _on_explain(self) -> None:
        entry = self._selected_entry()
        if entry is not None:
            self._announce(entry.trace.to_text())

    def _on_clear(self) -> None:
        self._history.clear()
        self._entries = []
        self._repopulate()
        self._announce("History cleared.")

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)
