"""One list with its details and its buttons: GitHub Permissions, Change History, Access Review.

Account > GitHub Permissions (section 18.1), Account > Change History (18.5)
and the access tools of 18.3.2 and 22.10 are each a list a screen reader
reads row by row, a read-only details box for the selected row, and a row of
buttons that act on it. One window does all of them, so they share keys:
Enter runs the first button, Ctrl+C copies the selected row, and the details
follow the selection. Opening says nothing (GATE-13); results are said by
the caller through the announcement service.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = ["ListAction", "WorkbenchListDialog"]

#: (label with its letter, help, action given the selected index).
ListAction = tuple[str, str, Callable[[int], None]]


class WorkbenchListDialog:
    """A list, its details, and buttons that act on the selected row."""

    def __init__(
        self,
        parent: Any,
        title: str,
        rows: Sequence[str],
        *,
        list_name: str,
        list_help: str,
        detail: Callable[[int], str],
        actions: Sequence[ListAction],
        copy_text: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self.title = title
        self.rows = list(rows)
        self._detail = detail
        self._copy_text = copy_text
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 640, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(self.dialog, choices=self.rows or ["(Nothing here yet.)"])
        set_spoken_name(self.list, list_name)
        self.list.SetHelpText(list_help)
        root.Add(self.list, 2, wx.EXPAND | wx.ALL, 8)
        self.details = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_spoken_name(self.details, "Details")
        self.details.SetHelpText("The selected row in full.")
        root.Add(self.details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons: list[Any] = []
        for label, what, action in actions:
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(what)
            button.Bind(wx.EVT_BUTTON, lambda _e, a=action: a(self.selected()))
            buttons.Add(button, 0, wx.RIGHT, 6)
            self.buttons.append(button)
        buttons.AddStretchSpacer()
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._show_detail())
        if actions:
            first = actions[0][2]
            apply_listbox_activation(self.list, lambda _e: first(self.selected()))
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        if self.rows:
            self.list.SetSelection(0)
            self._show_detail()

    def selected(self) -> int:
        index = int(self.list.GetSelection())
        return index if 0 <= index < len(self.rows) else -1

    def _show_detail(self) -> None:
        index = self.selected()
        self.details.ChangeValue(self._detail(index) if index >= 0 else "")

    def set_rows(self, rows: Sequence[str]) -> None:
        """Replace the rows (after Check Again, an Undo, a Clear), keeping the place."""
        keep = self.selected()
        self.rows = list(rows)
        self.list.Set(self.rows or ["(Nothing here yet.)"])
        if self.rows:
            self.list.SetSelection(min(max(keep, 0), len(self.rows) - 1))
        self._show_detail()

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("c")):
            if wx.Window.FindFocus() is self.list and self.selected() >= 0:
                self._copy_text(self.rows[self.selected()])
                return
        event.Skip()

    def show(self) -> None:
        try:
            show_modal_dialog(self.dialog, self.title)
        finally:
            self.dialog.Destroy()
