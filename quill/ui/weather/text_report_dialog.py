"""A read-only weather report in a window, with Copy (Weather Around Me).

The text is built in ``quill.core.weather`` (testable without a window); this is
only the frame around it. The box is multi-line and read-only so the screen
reader's review cursor works, it takes focus when the window opens with the
caret on the first line, and Copy puts exactly that text on the clipboard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.dpi import dip, dip_size


class TextReportDialog:
    def __init__(
        self,
        parent: object,
        *,
        intro: str,
        text: str,
        box_name: str,
        box_help: str,
        credits: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._title = "Weather Around Me"
        self._text = f"{text}\n\nSources: {credits}" if credits else text
        self._announce = announce_cb or (lambda _m: None)
        self.dialog = wx.Dialog(
            parent, title="Weather Around Me", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dlg = self.dialog
        gap = dip(dlg, 12)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(dlg, label=intro), 0, wx.ALL, gap)
        self._box = wx.TextCtrl(
            dlg,
            value=self._text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=dip_size(dlg, 560, 260),
        )
        set_accessible_name(self._box, box_name)
        self._box.SetHelpText(box_help)
        root.Add(self._box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        copy_btn = wx.Button(dlg, wx.ID_ANY, "&Copy")
        copy_btn.SetHelpText("Copy the whole report to the clipboard.")
        row.Add(copy_btn, 0, wx.RIGHT, dip(dlg, 6))
        close_btn = wx.Button(dlg, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. Escape does the same.")
        row.Add(close_btn)
        root.Add(row, 0, wx.EXPAND | wx.ALL, gap)
        dlg.SetSizer(root)
        root.Fit(dlg)
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy())
        bind_close_button(dlg, close_btn, modeless=False)
        self._box.SetInsertionPoint(0)

    @property
    def text(self) -> str:
        return self._text

    def copy(self) -> None:
        wx = self._wx
        clipboard: Any = wx.TheClipboard
        if clipboard.Open():
            try:
                clipboard.SetData(wx.TextDataObject(self._text))
            finally:
                clipboard.Close()
            self._announce(f"{self._title} copied.")
        else:
            self._announce("Could not open the clipboard.")

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Close",
        )
        # Focus the report once the window is up: a SetFocus before ShowModal
        # holds only while the box happens to be the first focusable control.
        self._wx.CallAfter(self._box.SetFocus)
        try:
            show_modal_dialog(self.dialog, self._title, announce=self._announce)
        finally:
            self.dialog.Destroy()
