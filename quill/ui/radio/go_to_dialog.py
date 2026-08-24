"""The Go To popup: a numbered list of places, and a visit rather than a move.

Ctrl+G opens it from anywhere in Quill Radio. Press the number, and you are
there. Escape puts you back exactly where you were -- the same contract
:mod:`quill.ui.radio.player_panel` keeps, and for the same reason: this is
somewhere you pass through, not somewhere you end up.

**Why a fixed list rather than a search box.** The command palette (Ctrl+Shift+P)
already answers "run a thing" by typing. This answers "take me to a place", and
for a screen-reader user a filtering search box is the most expensive way to
reach a destination whose name you already know: type, wait, read what survived,
choose. A list of ten in an order you set is two keystrokes and no reading.

**Why the rows show their own keys.** The popup teaches. Somebody who presses
Ctrl+G 2 for a month reads "Browse Stations, Ctrl+B" every time and eventually
stops needing the popup at all. A shortcut that trains you out of itself is
better than one that keeps you.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import go_to
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog

TITLE = "Go To"


def _row(index: int, destination: go_to.Destination) -> str:
    """``"1. Browse Stations  (Ctrl+B)"`` -- number first, because that is what
    the hand is about to press."""
    number = go_to.position_key(index)
    key = f"  ({destination.key})" if destination.key else ""
    return f"{number}. {destination.title}{key}"


def open_popup(host: Any, layout: go_to.GoToLayout) -> str | None:
    """Show the list. Returns the chosen destination id, or ``None``.

    Never raises: a navigation courtesy that can take the window down is worse
    than no courtesy.
    """
    wx = host._wx
    entries = layout.ordered()
    if not entries:
        return None

    dialog = wx.Dialog(host.frame, title=TITLE)
    root = wx.BoxSizer(wx.VERTICAL)

    label = wx.StaticText(dialog, label="&Go to:")
    root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

    listbox = wx.ListBox(dialog, choices=[_row(i, d) for i, d in enumerate(entries)])
    listbox.SetName("Places, numbered. Press a number to go straight there.")
    listbox.SetSelection(0)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    settings_btn = wx.Button(dialog, label="&Settings...")
    settings_btn.SetName("Choose which places are in this menu, and in what order")
    close_btn = wx.Button(dialog, wx.ID_CANCEL, "C&lose")
    close_btn.SetHelpText("Closes Go To and puts focus back exactly where it was.")
    bind_close_button(dialog, close_btn, modeless=False)
    buttons.Add(settings_btn, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer()
    buttons.Add(close_btn)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    chosen: dict[str, str | None] = {"id": None}

    def _choose(index: int) -> None:
        if 0 <= index < len(entries):
            chosen["id"] = entries[index].id
            dialog.EndModal(wx.ID_OK)

    def _on_key(event: Any) -> None:
        # The number row, including 0 for the tenth. Checked before the list box
        # sees the key, because a ListBox treats a digit as type-ahead.
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            _choose(listbox.GetSelection())
            return
        if not event.ControlDown() and not event.AltDown() and 0 <= code < 256:
            char = chr(code)
            if char.isdigit():
                index = go_to.MAX_ENTRIES - 1 if char == "0" else int(char) - 1
                if 0 <= index < len(entries):
                    _choose(index)
                    return
        event.Skip()

    dialog.Bind(wx.EVT_CHAR_HOOK, _on_key)
    listbox.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: _choose(listbox.GetSelection()))
    settings_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_APPLY))
    wx.CallAfter(listbox.SetFocus)

    answer = show_modal_dialog(dialog, TITLE, announce=getattr(host, "_announce", None))
    try:
        if answer == wx.ID_APPLY:
            return "__settings__"
        if answer == wx.ID_OK:
            return chosen["id"]
        return None
    finally:
        dialog.Destroy()
