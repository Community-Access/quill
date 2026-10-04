"""A read-only answer from QUILL Cast's AI, to read at your own pace (ear.md A3-A5).

What Is This Podcast About, Is This Episode for Me and Summarise This Episode
only *say* something, so their answer is spoken and shown here: a read-only
text field the arrow keys can review, Copy, and Close.
"""

from __future__ import annotations

from typing import Any

__all__ = ["show_answer"]


def show_answer(host: Any, title: str, text: str) -> None:
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(host.frame, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label="&Answer:"), 0, wx.LEFT | wx.TOP, 8)
    field = wx.TextCtrl(dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
    field.SetHelpText(
        "What the AI said. It is read only; arrow through it, or press Copy to "
        "take it to the clipboard. AI can be wrong, so check anything that matters."
    )
    root.Add(field, 1, wx.EXPAND | wx.ALL, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    copy = wx.Button(dialog, label="&Copy")
    copy.SetHelpText("Puts the whole answer on the clipboard.")
    close = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close.SetHelpText("Closes this window.")
    buttons.Add(copy, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer(1)
    buttons.Add(close, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((640, 420))
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)

    def _copy(_event: Any) -> None:
        if host._copy_to_clipboard(text):
            host._announce("Copied.")
        else:
            host._announce("The clipboard is busy; nothing was copied.")

    copy.Bind(wx.EVT_BUTTON, _copy)
    field.SetFocus()
    try:
        host._show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
