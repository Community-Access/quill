"""Small dialogs the WordPress Workbench needs beyond quill.ui.wordpress_dialogs.

- :func:`ask_checks`: a run of real check boxes ("Which columns?"), each
  saying its state as focus reaches it (A11Y-SR-1); Enter is OK.
- :func:`ask_preview`: a preview before a change that reaches the site, one
  line per thing it will do, read only, with the button naming the change.
  A destructive or irreversible change starts on Cancel, as the family's
  message boxes do (``wx.NO_DEFAULT``), so Enter never deletes: the running
  command's tier decides (:func:`set_running_tier`), or the caller says so.
- :func:`choose_spreadsheet`: the standard Open dialog for a CSV file
  (Invite from a Spreadsheet).

Both go through the caller's ``show_modal`` (the dialog contract), carry
their help inline, and leave OK and Cancel without access keys (GATE-14).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import wx

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, labelled_row
from quill.ui.wordpress_item_dialogs import _check_group

__all__ = [
    "ChecksDialog",
    "PreviewDialog",
    "ask_checks",
    "ask_preview",
    "choose_spreadsheet",
    "set_running_tier",
]

#: Buttons that name a change nothing can take back, whatever the command's tier.
IRREVERSIBLE = frozenset({
    "Delete Permanently",
    "Delete All",
    "Merge",
    "Revoke",
    "Promote",
    "Cancel Membership",
    "Resend",
})

_RUNNING: list[int | None] = [None]


def set_running_tier(tier: int | None) -> None:
    """The tier of the Workbench command now running (``None`` when none is)."""
    _RUNNING[0] = None if tier is None else int(tier)


def _destructive_now() -> bool:
    tier = _RUNNING[0]
    return tier is not None and tier >= 3  # Tier.DESTRUCTIVE


class ChecksDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        prompt: str,
        rows: Sequence[str],
        checked: Sequence[int],
        help_text: str,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(help_text)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.rows = _check_group(
            sizer,
            self,
            prompt.replace("&", ""),
            list(rows),
            f"{help_text} Space checks or unchecks.",
        )
        for index in checked:
            if 0 <= index < len(rows):
                self.rows.Check(index, True)
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)


def ask_checks(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    prompt: str,
    rows: Sequence[str],
    checked: Sequence[int] = (),
    help_text: str,
) -> list[int] | None:
    """The indices checked when OK is pressed; None on Cancel."""
    dialog = ChecksDialog(
        parent, title=title, prompt=prompt, rows=rows, checked=checked, help_text=help_text
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.rows.GetCheckedItems()
    finally:
        dialog.Destroy()


class PreviewDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        summary: str,
        lines: Sequence[str],
        yes: str,
        destructive: bool = False,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.destructive = destructive
        self.SetHelpText(
            "What the change will do, before anything is sent. The button names the change; "
            "Cancel sends nothing."
            + (
                " This cannot be undone, so Enter is Cancel: press the button itself."
                if destructive
                else ""
            )
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.summary = wx.TextCtrl(self, value=summary, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.summary.SetHelpText("The change in one or two sentences.")
        self.summary.SetMinSize(dip_size(self, 460, 60))
        labelled_row(sizer, self, "&Summary:", self.summary)
        self.lines = wx.ListBox(self, choices=list(lines) or ["Nothing to change."])
        self.lines.SetHelpText("One line for each thing the change creates, replaces or skips.")
        self.lines.SetMinSize(dip_size(self, 460, 220))
        self.lines.SetSelection(0)
        labelled_row(sizer, self, "&Each change:", self.lines)
        sizer.Add(_buttons(self, yes), 0, wx.EXPAND | wx.ALL, 8)
        if destructive:  # Enter cancels; the change needs its own button
            cancel = self.FindWindow(wx.ID_CANCEL)
            if isinstance(cancel, wx.Button):
                cancel.SetDefault()
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)


def ask_preview(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    summary: str,
    lines: Sequence[str],
    yes: str,
    destructive: bool | None = None,
) -> bool:
    """True when the person presses the button that names the change.

    *destructive* (a change nothing takes back) starts the dialog on Cancel;
    left as ``None``, the running command's tier and the button's words decide.
    """
    if destructive is None:
        destructive = _destructive_now() or yes in IRREVERSIBLE
    dialog = PreviewDialog(
        parent, title=title, summary=summary, lines=lines, yes=yes, destructive=destructive
    )
    try:
        return bool(show_modal(dialog, title) == wx.ID_OK)
    finally:
        dialog.Destroy()


def choose_spreadsheet(parent: wx.Window, show_modal: ShowModal, *, title: str) -> Path | None:
    """A standard Open dialog for one CSV file; None when cancelled."""
    with wx.FileDialog(
        parent,
        title,
        wildcard="Spreadsheets saved as CSV|*.csv|All files|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())
