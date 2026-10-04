"""Undo History: the last ten steps, each with its own Undo (qc.md 18.12).

Shared by Quill Radio and QUILL Cast, beside Ctrl+Z's Undo Last Action. Each
row is what its Undo would bring back, newest first; Undo This One takes back
that step alone and leaves the others where they are.
"""

from __future__ import annotations

from typing import Any

__all__ = ["TITLE", "show_undo_history"]

TITLE = "Undo History"


def show_undo_history(host: Any) -> None:
    import wx

    from quill.ui import undo_last_ui
    from quill.ui.dialog_contract import apply_modal_ids

    history = undo_last_ui.slot()
    entries = history.entries() if history is not None and hasattr(history, "entries") else []
    if not entries:
        host._announce("Nothing to undo.")
        return
    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label="&Steps you can undo, newest first:"), 0, wx.ALL, 8)
    listbox = wx.ListBox(dialog, choices=[action.offer() for action in entries])
    listbox.SetHelpText(
        "Each row says what undoing it brings back. Enter, or Undo This One, takes "
        "back that step alone; the others stay. Ctrl+Z always takes the newest."
    )
    listbox.SetSelection(0)
    root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    undo_btn = wx.Button(dialog, wx.ID_OK, label="Undo This One")
    undo_btn.SetHelpText("Takes back the highlighted step and closes this window.")
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close_btn.SetHelpText("Closes Undo History. Nothing changes.")
    buttons.AddStretchSpacer(1)
    buttons.Add(undo_btn, 0, wx.RIGHT, 6)
    buttons.Add(close_btn, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((640, 360))
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="Undo This One", cancel_id=wx.ID_CANCEL
    )
    from quill.ui.dialog_contract import apply_listbox_activation

    # Enter and Space undo the step as well as a double-click (GATE-13).
    apply_listbox_activation(listbox, lambda _e: dialog.EndModal(wx.ID_OK))
    try:
        answer = host._show_modal_dialog(dialog, TITLE)
        index = listbox.GetSelection()
    finally:
        dialog.Destroy()
    if answer != wx.ID_OK or history is None:
        return
    action = history.take_at(index)
    if action is None:
        return
    try:
        action.undo()
    except Exception as error:  # noqa: BLE001 - an undo that fails must say so
        host._announce(f"Could not undo {action.verb}: {error}.")
        return
    host._announce(action.done())
