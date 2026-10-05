"""What Was Left Out: the list behind "N files were left out".

A backup, a restore, or Export / Import My Setup that leaves something out
says how many in its spoken result -- and then, because a count with no names
is the sentence that made a listener about to reset their computer ask whether
their favorites were gone (2026-10-04), offers this window: one row per item,
each with its reason, and what to do about it underneath.

Shared by Quill Radio's Back Up / Restore and by Export / Import My Setup in
both Radio and QUILL Cast. The pure half is :mod:`quill.core.skipped_files`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from quill.core.skipped_files import SkippedFile, report_lines, what_to_do
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)

TITLE = "What Was Left Out"


def report_text(summary: str, items: Iterable[SkippedFile]) -> str:
    """The plain-text form: the summary, every row, then what to do."""
    rows = list(items)
    lines = [summary, ""]
    lines.extend(report_lines(rows))
    advice = what_to_do(rows)
    if advice:
        lines.append("")
        lines.append("What to do:")
        lines.extend(advice)
    return "\n".join(lines).rstrip() + "\n"


def offer_skipped_list(
    parent: Any,
    outcome: str,
    items: Iterable[SkippedFile],
    *,
    caption: str,
    announce: Callable[[str], None] | None = None,
) -> None:
    """Say *outcome* in a message box that offers the list, and show it on Yes.

    The outcome is the message box's own text, so the screen reader reads it
    when the box opens; nothing is announced on top of it (GATE-13).
    """
    import wx

    from quill.ui.dialog_contract import show_message_box

    rows = list(items)
    if not rows:
        return
    answer = show_message_box(
        f"{outcome}\n\nShow what was left out, and why?",
        caption,
        wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION,
        parent,
        announce=announce,
    )
    if answer == wx.YES:
        show_skipped_items(parent, outcome, rows, announce=announce)


def show_skipped_items(
    parent: Any,
    summary: str,
    items: Iterable[SkippedFile],
    *,
    announce: Callable[[str], None] | None = None,
) -> None:
    """Show every item left out, with its reason, and what to do. Modal."""
    import wx

    rows = list(items)
    say = announce or (lambda _text: None)
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetMinSize(wx.Size(560, 400))
    root = wx.BoxSizer(wx.VERTICAL)

    heading = wx.StaticText(dialog, label=summary)
    heading.Wrap(520)
    root.Add(heading, 0, wx.ALL, 8)

    root.Add(wx.StaticText(dialog, label="&Left out, with the reason:"), 0, wx.LEFT | wx.RIGHT, 8)
    listbox = wx.ListBox(dialog, choices=report_lines(rows), style=wx.LB_SINGLE)
    set_accessible_name(listbox, "Left out, with the reason")
    listbox.SetHelpText(
        "Every file or item that was left out, one per row, with why. Nothing "
        "here was deleted; each row is something the backup, restore or setup "
        "file does not hold."
    )
    if listbox.GetCount():
        listbox.SetSelection(0)
    root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    advice = what_to_do(rows)
    if advice:
        tip = wx.StaticText(dialog, label="What to do: " + " ".join(advice))
        tip.Wrap(520)
        root.Add(tip, 0, wx.ALL, 8)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    copy_btn = wx.Button(dialog, label="&Copy List")
    copy_btn.SetHelpText(
        "Copies the whole list, with the reasons and what to do, so you can "
        "paste it into an email or a note."
    )
    close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
    close_btn.SetHelpText("Closes this list. Nothing changes when you close it.")
    buttons.Add(copy_btn, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer()
    buttons.Add(close_btn)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)

    def _copy(_event: object) -> None:
        text = report_text(summary, rows)
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            say("List copied.")
        else:
            say("The clipboard is busy; the list was not copied.")

    copy_btn.Bind(wx.EVT_BUTTON, _copy)
    bind_close_button(dialog, close_btn, modeless=False)
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
    dialog.Fit()
    dialog.CentreOnParent()
    try:
        show_modal_dialog(dialog, TITLE, announce=announce)
    finally:
        dialog.Destroy()
