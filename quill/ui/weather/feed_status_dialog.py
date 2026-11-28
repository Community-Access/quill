"""Alert Feed Status: a read-only text window with Copy.

The text itself is built by ``quill.core.weather.feed_health`` (so every
sentence is testable without a window); this is only the frame around it. The
text box is multi-line and read-only so a screen reader's review cursor works,
and the same text is what Copy puts on the clipboard.
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
from quill.ui.dpi import dip_size


class FeedStatusDialog:
    def __init__(
        self,
        parent: object,
        *,
        text: str,
        announce_cb: Callable[[str], None] | None = None,
        title: str = "Alert Feed Status",
    ) -> None:
        import wx

        self._wx = wx
        self._text = text
        self._title = title
        self._announce = announce_cb or (lambda _m: None)
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self.dialog,
            label="Whether Quill Weather can reach the National Weather Service, "
            "and the last alerts it provided.",
        )
        root.Add(intro, 0, wx.ALL, 12)
        self._box = wx.TextCtrl(
            self.dialog,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=dip_size(self.dialog, 560, 320),
        )
        set_accessible_name(self._box, "Alert feed status report")
        self._box.SetHelpText(
            "A read-only report. For each watched place it gives the state of the "
            "alert feed, the last successful check, the last attempt, what went "
            "wrong in plain words, and the last alerts the service provided, "
            "marked last known when they are old. Use the arrow keys to read it."
        )
        root.Add(self._box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        copy_btn = wx.Button(self.dialog, wx.ID_ANY, "&Copy")
        copy_btn.SetHelpText("Copy the whole report to the clipboard.")
        row.Add(copy_btn, 0, wx.RIGHT, 6)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. Escape does the same.")
        row.Add(close_btn)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 12)
        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy())
        bind_close_button(self.dialog, close_btn, modeless=False)

    def _copy(self) -> None:
        wx = self._wx
        clipboard: Any = wx.TheClipboard
        if clipboard.Open():
            try:
                clipboard.SetData(wx.TextDataObject(self._text))
            finally:
                clipboard.Close()
            self._announce("Alert feed status copied.")
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
        try:
            show_modal_dialog(self.dialog, self._title, announce=self._announce)
        finally:
            self.dialog.Destroy()
