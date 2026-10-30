"""Removed Items and Recently Left: nothing leaves a Lineup without trace.

**Removed Items** is what the listener deleted; no rule brings these back.
**Recently Left** is what the rules let go -- finished, its days ran out, it no
longer matched -- each row saying why and when. Either list brings items back
as Kept rows, and either can be cleared.
"""

from __future__ import annotations

import time
from typing import Any

from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import KIND_LABELS, ItemRef
from quill.ui.dpi import dip_size

TITLES = {"removed": "Removed Items", "left": "Recently Left"}


def _ago(when: float, now: float) -> str:
    seconds = max(0.0, now - when)
    if seconds < 3600:
        minutes = max(1, int(seconds // 60))
        return "1 minute ago" if minutes == 1 else f"{minutes} minutes ago"
    if seconds < 86_400:
        hours = int(seconds // 3600)
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    days = int(seconds // 86_400)
    return "yesterday" if days == 1 else f"{days} days ago"


def _kind(ref: ItemRef) -> str:
    return KIND_LABELS.get(ref.kind, ref.kind)


def rows_of(lineup: Lineup, which: str, *, now: float) -> list[tuple[ItemRef, str]]:
    """``(ref, sentence)`` per entry, newest first: name, kind, why, when."""
    if which == "removed":
        return [
            (
                entry.ref,
                f"{entry.name or 'Unnamed item'}, {_kind(entry.ref)}, "
                f"removed {_ago(entry.when, now)}",
            )
            for entry in lineup.removed
        ]
    return [
        (
            entry.ref,
            f"{entry.name or 'Unnamed item'}, {_kind(entry.ref)}: "
            f"{entry.reason}, {_ago(entry.when, now)}",
        )
        for entry in lineup.recently_left
    ]


def choose_entries(window: Any, lineup: Lineup, which: str) -> tuple[list[ItemRef], bool] | None:
    """The entries to bring back (and whether to clear instead), or ``None``."""
    import wx

    host = window._lineups_host
    title = TITLES[which]
    rows = rows_of(lineup, which, now=time.time())
    if not rows:
        host.announce(
            "Nothing has been removed from this lineup."
            if which == "removed"
            else "Nothing has left this lineup recently."
        )
        return None
    style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    if which == "removed":
        dialog = wx.Dialog(window._win, title="Removed Items", style=style)
    else:
        dialog = wx.Dialog(window._win, title="Recently Left", style=style)
    sizer = wx.BoxSizer(wx.VERTICAL)
    label = "&Items you removed:" if which == "removed" else "&Items the rules let go:"
    sizer.Add(wx.StaticText(dialog, label=label), 0, wx.LEFT | wx.TOP, 10)
    listing = wx.ListBox(
        dialog,
        choices=[text for _ref, text in rows],
        style=wx.LB_EXTENDED,
        size=dip_size(dialog, 560, 220),
    )
    listing.SetName(title)
    listing.SetHelpText(
        "Newest first. Select one or more and press Bring Back; they return as kept "
        "items, which stay whatever the rules say."
    )
    listing.SetSelection(0)
    sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 10)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    back = wx.Button(dialog, wx.ID_OK, "&Bring Back")
    back.SetHelpText("Return the selected items to the lineup, kept.")
    clear = wx.Button(dialog, wx.ID_CLEAR, "C&lear the List")
    clear.SetHelpText("Forget every entry here. Removed items could then come back through a rule.")
    close = wx.Button(dialog, wx.ID_CANCEL, "Close")
    close.SetHelpText("Close without changing anything.")
    for button in (back, clear):
        buttons.Add(button, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer()
    buttons.Add(close)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizerAndFit(sizer)
    clear.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLEAR))
    listing.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: dialog.EndModal(wx.ID_OK))
    listing.SetFocus()
    try:
        from quill.ui import dialog_contract

        dialog_contract.apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        answer = host.show_modal_dialog(dialog, title)
        if answer == wx.ID_CLEAR:
            return [], True
        if answer != wx.ID_OK:
            return None
        return [rows[index][0] for index in listing.GetSelections()], False
    finally:
        dialog.Destroy()


__all__ = ["TITLES", "choose_entries", "rows_of"]
