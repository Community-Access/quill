"""Highlighted Passages: every highlighted passage in the document, in one list.

Shared by QUILL and QUILL Lite (Ctrl+F2 in both). One row per passage, in
document order, written words first so typing a letter finds a row: the
passage's words, its colour, and the paragraph around it --
``"budget is final, yellow highlight, in: The budget is final unless ..."``.
The colour alone would make every row in a one-colour document sound the same.

**Keys.** Enter, or the Go To button, closes the list and puts the caret on
the first character of the passage. Escape, or Close, leaves the caret where
it was. The list opens on the passage the caret is in, or the next one after
it, so a listener who opens it mid-document is not sent back to the top.

The window does no work of its own and says nothing: the rows read themselves
and the caller moves the caret (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.highlights import HighlightPassage, list_label

__all__ = ["TITLE", "show_highlight_list"]

TITLE = "Highlighted Passages"


def show_highlight_list(
    wx: Any,
    parent: Any,
    show_modal_dialog: Callable[[Any, str], int],
    passages: Sequence[HighlightPassage],
    start: int = 0,
) -> int | None:
    """Show the list. Returns the chosen passage's index, or ``None`` when closed."""
    from quill.ui.dialog_contract import (
        apply_listbox_activation,
        apply_modal_ids,
        bind_close_button,
    )

    chosen: dict[str, int | None] = {"index": None}
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize((720, 420))
    sizer = wx.BoxSizer(wx.VERTICAL)
    label = wx.StaticText(dialog, label="&Passages:")
    sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
    listing = wx.ListBox(dialog, choices=[list_label(p) for p in passages], style=wx.LB_SINGLE)
    listing.SetName("Highlighted passages")
    listing.SetHelpText(
        "Every highlighted passage in this document, in order: its words, its "
        "highlight colour, and the paragraph it is in. Enter goes to the passage "
        "and closes the list; Escape closes it and leaves the cursor where it was."
    )
    sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    go_btn = wx.Button(dialog, wx.ID_OK, label="&Go To")
    go_btn.SetHelpText("Move the cursor to the selected passage and close this list.")
    buttons.Add(go_btn, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer()
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close_btn.SetHelpText("Close the list. The cursor stays where it was.")
    buttons.Add(close_btn, 0)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    def _go(_event: Any = None) -> None:
        index = listing.GetSelection()
        if 0 <= index < len(passages):
            chosen["index"] = int(index)
            if dialog.IsModal():
                dialog.EndModal(wx.ID_OK)

    go_btn.Bind(wx.EVT_BUTTON, _go)
    apply_listbox_activation(listing, _go)  # Enter, Space and double-click
    bind_close_button(dialog, close_btn, modeless=False)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    go_btn.SetDefault()
    if passages:
        listing.SetSelection(max(0, min(start, len(passages) - 1)))
    wx.CallAfter(listing.SetFocus)
    try:
        result = show_modal_dialog(dialog, TITLE)
        # Enter on the default button can end the dialog through the modal
        # contract's own OK handling rather than _go; the selection is the answer.
        if result == wx.ID_OK and chosen["index"] is None:
            index = listing.GetSelection()
            if 0 <= index < len(passages):
                chosen["index"] = int(index)
    finally:
        dialog.Destroy()
    return chosen["index"]
