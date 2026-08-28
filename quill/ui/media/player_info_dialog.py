"""Player Information -- what is playing, as reviewable text.

A read-only multi-line field rather than a row of labels, so the whole report
can be arrowed through by character, word, and line, and any part of it copied.
Speech says a status once; this lets someone check it as many times as they
like, at their own pace, without touching playback.

Hardened dialog (A11Y-4): exposes show() and close(); callers never touch the
inner wx.Dialog.
"""

from __future__ import annotations

import wx

from quill.core.media.player_info import PlayerInfo, player_info_text
from quill.ui.dialog_contract import apply_modal_ids


class PlayerInfoDialog:
    """Shows one :class:`PlayerInfo` report."""

    def __init__(
        self, parent: object, info: PlayerInfo, *, title: str = "Player Information"
    ) -> None:
        self._text = player_info_text(info) or "Nothing is playing."

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(460, 340))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="Player &information:"), 0, wx.LEFT | wx.TOP, 10)
        # Read-only but focusable and selectable: TE_READONLY alone still allows
        # caret review, which is the entire point of this dialog.
        self._field = wx.TextCtrl(
            self.dialog,
            value=self._text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        self._field.SetName("Player information; review it with the arrow keys")
        root.Add(self._field, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self.dialog, label="&Copy")
        copy_btn.SetHelpText(
            "Put the whole report on the clipboard as plain text, ready to "
            "paste into a document or a support message."
        )
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Close")
        close_btn.SetHelpText(
            "Close the report. It changes nothing; reopen it any time for the current state."
        )
        buttons.AddStretchSpacer(1)
        buttons.Add(copy_btn, 0, wx.RIGHT, 6)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self._field.SetFocus()
        self._field.SetInsertionPoint(0)

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._text))
            finally:
                wx.TheClipboard.Close()
