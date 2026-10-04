"""The review window every QUILL Cast AI proposal goes through (ear.md A2-A9).

The model proposes; the listener disposes. Each row starts accepted and says
so in words -- "Accept:" or "Skip:" at the front, because a check box in a list
is a state screen readers do not reliably speak -- and Space turns one row
between the two. Apply Selected does the accepted rows and nothing else;
Cancel and Escape change nothing at all.
"""

from __future__ import annotations

from typing import Any

__all__ = ["review"]


def _row(accepted: bool, text: str) -> str:
    return f"{'Accept' if accepted else 'Skip'}: {text}"


def review(host: Any, title: str, intro: str, rows: list[str]) -> list[int] | None:
    """Show *rows* for review; the accepted indices, or None when cancelled."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    accepted = [True] * len(rows)
    dialog = wx.Dialog(host.frame, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label=intro), 0, wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&Suggestions:"), 0, wx.LEFT | wx.RIGHT, 8)
    listbox = wx.ListBox(dialog, choices=[_row(True, text) for text in rows])
    listbox.SetHelpText(
        "Each suggestion starts accepted. Space switches the highlighted one between "
        "Accept and Skip. Nothing changes until you press Apply Selected."
    )
    if rows:
        listbox.SetSelection(0)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    accept_all = wx.Button(dialog, label="&Accept All")
    accept_all.SetHelpText("Marks every suggestion Accept.")
    skip_all = wx.Button(dialog, label="S&kip All")
    skip_all.SetHelpText("Marks every suggestion Skip, so you can accept just a few.")
    apply_btn = wx.Button(dialog, wx.ID_OK, label="Apply Selected")
    apply_btn.SetHelpText("Does every suggestion marked Accept, and nothing else.")
    cancel = wx.Button(dialog, wx.ID_CANCEL, label="Cancel")
    cancel.SetHelpText("Closes this window. Nothing changes.")
    for button in (accept_all, skip_all):
        buttons.Add(button, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer(1)
    buttons.Add(apply_btn, 0, wx.RIGHT, 6)
    buttons.Add(cancel, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((700, 460))
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="Apply Selected", cancel_id=wx.ID_CANCEL
    )

    def _set(index: int, value: bool) -> None:
        accepted[index] = value
        listbox.SetString(index, _row(value, rows[index]))

    def _toggle() -> None:
        index = listbox.GetSelection()
        if 0 <= index < len(rows):
            _set(index, not accepted[index])
            listbox.SetSelection(index)
            host._announce("Accept" if accepted[index] else "Skip")

    def _all(value: bool) -> None:
        for index in range(len(rows)):
            _set(index, value)
        host._announce(f"All {len(rows)} marked {'Accept' if value else 'Skip'}.")

    def _on_key(event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_SPACE:
            _toggle()
            return
        event.Skip()

    listbox.Bind(wx.EVT_KEY_DOWN, _on_key)
    accept_all.Bind(wx.EVT_BUTTON, lambda _e: _all(True))
    skip_all.Bind(wx.EVT_BUTTON, lambda _e: _all(False))
    try:
        answer = host._show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
    if answer != wx.ID_OK:
        host._announce("Nothing was changed.")
        return None
    return [index for index, keep in enumerate(accepted) if keep]
