"""Small modal questions the Lineups window asks, every one through the dialog contract.

Each goes through :meth:`LineupsHost.show_modal` (the app's ``_show_modal_dialog``),
never ``ShowModal()`` directly, so the enter and exit cues and the keyboard
contract are the same as every other dialog in the app.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.ui.lineups.host import LineupsHost


def ask_text(
    host: LineupsHost, parent: Any, prompt: str, title: str, value: str = ""
) -> str | None:
    """One line of text, or ``None`` when cancelled."""
    import wx

    with wx.TextEntryDialog(parent, prompt, title, value=value) as entry:
        if host.show_modal_dialog(entry, title) != wx.ID_OK:
            return None
        return str(entry.GetValue()).strip()


def ask_number(
    host: LineupsHost, parent: Any, prompt: str, title: str, *, value: int, low: int, high: int
) -> int | None:
    """A whole number between *low* and *high*, or ``None``."""
    import wx

    # The third argument is the label right before the spin control: what the
    # reader names it by. Empty, it was announced as just "spin button" (S3).
    with wx.NumberEntryDialog(parent, prompt, "Position:", title, value, low, high) as entry:
        if host.show_modal_dialog(entry, title) != wx.ID_OK:
            return None
        return int(entry.GetValue())


def confirm(host: LineupsHost, parent: Any, question: str, title: str) -> bool:
    """Yes or No, with **No** already chosen: these questions remove things."""
    import wx

    with wx.MessageDialog(
        parent, question, title, style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
    ) as box:
        return host.show_modal_dialog(box, title) == wx.ID_YES


def ask_keep_or_let_go(host: LineupsHost, parent: Any, question: str, title: str) -> bool | None:
    """``True`` keep, ``False`` let go, ``None`` cancel (nothing changes)."""
    import wx

    with wx.MessageDialog(
        parent, question, title, style=wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION
    ) as box:
        box.SetYesNoCancelLabels("Keep Them", "Let Them Go", "Cancel")
        answer = host.show_modal_dialog(box, title)
    if answer == wx.ID_YES:
        return True
    if answer == wx.ID_NO:
        return False
    return None


def choose(
    host: LineupsHost,
    parent: Any,
    prompt: str,
    title: str,
    choices: Sequence[str],
    *,
    selection: int = 0,
) -> int | None:
    """The index of one of *choices*, or ``None``."""
    import wx

    with wx.SingleChoiceDialog(parent, prompt, title, list(choices)) as chooser:
        if choices:
            chooser.SetSelection(max(0, min(selection, len(choices) - 1)))
        if host.show_modal_dialog(chooser, title) != wx.ID_OK:
            return None
        return int(chooser.GetSelection())


WHY_TITLE = "Why Is This Here"


def show_why(host: LineupsHost, parent: Any, text: str) -> None:
    """Why Is This Here: a read-only sentence to arrow through, closed with Escape or OK."""
    import wx

    title = WHY_TITLE
    dialog = wx.Dialog(
        parent, title="Why Is This Here", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label="&Reason:"), 0, wx.LEFT | wx.TOP, 10)
    box = wx.TextCtrl(
        dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(520, 160)
    )
    box.SetName(title)
    box.SetHelpText("Read with the arrow keys. OK or Escape closes.")
    sizer.Add(box, 1, wx.EXPAND | wx.ALL, 10)
    buttons = wx.StdDialogButtonSizer()
    ok = wx.Button(dialog, wx.ID_OK, "OK")
    ok.SetHelpText("Close.")
    buttons.AddButton(ok)
    buttons.Realize()
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizerAndFit(sizer)
    from quill.ui import dialog_contract

    dialog_contract.apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    box.SetFocus()
    try:
        host.show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()


def ask_path(host: LineupsHost, parent: Any, title: str, *, save: bool, name: str = "") -> str:
    """A rules file to open or save, or ``""``."""
    import wx

    style = (wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if save else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    with wx.FileDialog(
        parent, title, defaultFile=name, wildcard="Lineup rules (*.json)|*.json", style=style
    ) as chooser:
        if host.show_modal_dialog(chooser, title) != wx.ID_OK:
            return ""
        return str(chooser.GetPath())


__all__ = [
    "ask_keep_or_let_go",
    "ask_number",
    "ask_path",
    "ask_text",
    "choose",
    "confirm",
    "WHY_TITLE",
    "show_why",
]
