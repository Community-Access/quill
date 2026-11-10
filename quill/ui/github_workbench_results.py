"""A batch's results: one line per item, Copy Results, Retry Failed (GitHub PRD 16.4, C7).

Never a message box: a list a screen reader moves through line by line and a
braille display pans, each line "#42: Done, #42: added bug." or "#43: Failed,
..." with the totals last. Copy Results copies the lot; Retry Failed (F8)
runs the failed ones again when the caller can. Opening says nothing: the
caller has already said the totals (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = ["show_results"]


def show_results(
    parent: Any,
    title: str,
    text: str,
    *,
    copy_text: Callable[[str], None],
    retry: Callable[[], None] | None = None,
) -> None:
    import wx

    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(dip_size(dialog, 560, 420))
    root = wx.BoxSizer(wx.VERTICAL)
    lines = text.splitlines() or ["Nothing happened."]
    results = wx.ListBox(dialog, choices=lines)
    set_spoken_name(results, "Results")
    results.SetHelpText(
        "One line per item: Done, Skipped because it was already so, or Failed and why. "
        "The last line is the totals."
    )
    results.SetSelection(0)
    root.Add(results, 1, wx.EXPAND | wx.ALL, 8)
    row = wx.BoxSizer(wx.HORIZONTAL)
    copy = wx.Button(dialog, label="&Copy Results")
    copy.SetHelpText("Copy every line as text. Ctrl+C does the same.")
    copy.Bind(wx.EVT_BUTTON, lambda _e: copy_text(text))
    row.Add(copy, 0, wx.RIGHT, 6)
    if retry is not None and any(": Failed" in line for line in lines):
        again = wx.Button(dialog, label="&Retry Failed")
        again.SetHelpText("Run the failed items again. F8 does the same.")

        def on_retry(_event: Any) -> None:
            dialog.EndModal(wx.ID_RETRY)

        again.Bind(wx.EVT_BUTTON, on_retry)
        row.Add(again, 0, wx.RIGHT, 6)
    row.AddStretchSpacer()
    close = wx.Button(dialog, wx.ID_CANCEL, "Close")
    close.SetHelpText("Close the results.")
    bind_close_button(dialog, close, modeless=False)
    row.Add(close)
    root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    apply_modal_ids(dialog)
    dialog.SetEscapeId(wx.ID_CANCEL)

    def on_key(event: Any) -> None:
        code = event.GetKeyCode()
        if event.ControlDown() and code in (ord("C"), ord("c")):
            copy_text(text)
            return
        if code == wx.WXK_F8 and retry is not None:
            dialog.EndModal(wx.ID_RETRY)
            return
        event.Skip()

    dialog.Bind(wx.EVT_CHAR_HOOK, on_key)
    try:
        answer = show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
    if answer == wx.ID_RETRY and retry is not None:
        retry()
