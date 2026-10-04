"""Update History: what the updater did for this app (plan 6.8, read-only).

A report list -- Date, What happened, From, To, Channel -- newest first, with
the selected row's full details in a read-only box below. Focus starts on the
list. Phase 1 has no actions here; restoring a saved copy arrives with safe
downgrades (Phase 4).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import wx

from quill.core.updater.channels import channel_label
from quill.core.updater.history import UpdateEvent
from quill.core.updater.wording import history_title
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["UpdateHistoryDialog", "details_text"]

_COLUMNS = ("Date", "What happened", "From", "To", "Channel")


def details_text(event: UpdateEvent) -> str:
    """The details box for one row: every field, in words."""
    lines = [f"{event.what}, {event.when()}."]
    if event.from_version:
        lines.append(f"From version: {event.from_version}")
    if event.to_version:
        lines.append(f"To version: {event.to_version}")
    if event.channel:
        lines.append(f"Channel: {channel_label(event.channel)}")
    if event.detail:
        lines.append(event.detail)
    return "\n".join(lines)


class UpdateHistoryDialog(wx.Dialog):  # type: ignore[misc]
    def __init__(self, parent: Any, *, app_name: str, events: Sequence[UpdateEvent]) -> None:
        super().__init__(
            parent,
            title=history_title(app_name),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._events = list(events)
        sizer = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(self, label="&Events, newest first:")
        sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 220))
        self._list.SetName("Events, newest first")
        self._list.SetHelpText(
            "Everything the updater did for this app, newest first. The box below "
            "shows the whole of the selected row."
        )
        for index, title in enumerate(_COLUMNS):
            self._list.InsertColumn(index, title)
        for row, event in enumerate(self._events):
            self._list.InsertItem(row, event.when())
            self._list.SetItem(row, 1, event.what)
            self._list.SetItem(row, 2, event.from_version)
            self._list.SetItem(row, 3, event.to_version)
            self._list.SetItem(row, 4, channel_label(event.channel) if event.channel else "")
        if not self._events:
            self._list.InsertItem(0, "Nothing yet")
            self._list.SetItem(0, 1, "The updater has not done anything for this app yet.")
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 12)
        details_label = wx.StaticText(self, label="&Details:")
        sizer.Add(details_label, 0, wx.LEFT | wx.RIGHT, 12)
        self._details = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 90)
        )
        self._details.SetName("Details")
        self._details.SetHelpText("Every detail of the row selected above. Read-only.")
        sizer.Add(self._details, 0, wx.EXPAND | wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close Update History.")
        bind_close_button(self, close, modeless=False)
        close.SetDefault()
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizerAndFit(sizer)
        self.SetSize((640, 480))
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        if self._list.GetItemCount():
            self._list.Select(0)
            self._list.Focus(0)
        self._list.SetFocus()

    def _on_select(self, event: Any) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self._events):
            self._details.SetValue(details_text(self._events[index]))
        else:
            self._details.SetValue("")
