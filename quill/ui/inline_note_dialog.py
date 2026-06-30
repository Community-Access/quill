"""Accessible add/edit dialog for inline notes.

A single labeled multi-line field (not a bare TextEntryDialog, so the control
announces its name on macOS too — same lesson as #212). Returns an ``(action,
text)`` pair: ``action`` is ``"save"``, ``"delete"`` (edit mode only), or
``"cancel"``. Routed through the host's ``_show_modal_dialog`` with the standard
affirmative/escape ids so it is reliably keyboard-dismissable.
"""

from __future__ import annotations

from typing import Any


def show_inline_note_dialog(
    wx: Any,
    parent: Any,
    show_modal_dialog: Any,
    *,
    title: str,
    initial: str = "",
    allow_delete: bool = False,
) -> tuple[str, str]:
    """Prompt for an inline note's text. Returns ``(action, text)``."""
    from quill.ui.dialog_contract import apply_modal_ids

    result = {"action": "cancel", "text": initial}
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize((520, 360))
    sizer = wx.BoxSizer(wx.VERTICAL)

    label = wx.StaticText(dialog, label="Note (about the line or selection):")
    sizer.Add(label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
    field = wx.TextCtrl(dialog, value=initial, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
    field.SetName("Inline note text")
    sizer.Add(field, 1, wx.EXPAND | wx.ALL, 10)

    btns = wx.BoxSizer(wx.HORIZONTAL)
    save_btn = wx.Button(dialog, wx.ID_OK, label="&Save", name="inline_note_save")
    save_btn.SetDefault()
    btns.AddStretchSpacer()
    delete_btn = None
    if allow_delete:
        delete_btn = wx.Button(dialog, label="&Delete", name="inline_note_delete")
        btns.Add(delete_btn, 0, wx.RIGHT, 8)
    cancel_btn = wx.Button(dialog, wx.ID_CANCEL, label="&Cancel")
    btns.Add(save_btn, 0, wx.RIGHT, 8)
    btns.Add(cancel_btn, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

    def _on_save(_e: Any) -> None:
        result["action"] = "save"
        result["text"] = field.GetValue()
        dialog.EndModal(wx.ID_OK)

    def _on_delete(_e: Any) -> None:
        result["action"] = "delete"
        dialog.EndModal(wx.ID_OK)

    save_btn.Bind(wx.EVT_BUTTON, _on_save)
    if delete_btn is not None:
        delete_btn.Bind(wx.EVT_BUTTON, _on_delete)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    wx.CallAfter(field.SetFocus)
    try:
        show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
    return (result["action"], result["text"])
