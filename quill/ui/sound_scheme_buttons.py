"""The Sound Scheme window's row of scheme buttons.

Split out of :mod:`quill.ui.sound_scheme_dialog` under GATE-11 (extract, never
rebaseline) when App Sounds Play On... joined the row on 2026-10-14. One row,
one function: the buttons that act on the scheme as a whole, as opposed to the
ones above that act on the event selected in the list.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["build_scheme_buttons"]


def build_scheme_buttons(window: Any) -> Any:
    """Save As, Delete, Restore All Defaults and, when the app offers it, App
    Sounds Play On. Sets ``window.delete_button``, which the list enables."""
    row = wx.BoxSizer(wx.HORIZONTAL)
    save_as = wx.Button(window.dialog, label="Save &As Scheme...")
    save_as.SetHelpText(
        "Save every sound in the list as a scheme of your own, under a name you "
        "choose. Schemes are ordinary folders you can copy or send to somebody."
    )
    save_as.Bind(wx.EVT_BUTTON, lambda _e: window._save_as())
    row.Add(save_as, 0, wx.RIGHT, 6)

    window.delete_button = wx.Button(window.dialog, label="De&lete Scheme")
    window.delete_button.SetHelpText("Remove one of your own saved schemes. Never a shipped one.")
    window.delete_button.Bind(wx.EVT_BUTTON, lambda _e: window._delete_scheme())
    row.Add(window.delete_button, 0, wx.RIGHT, 6)

    restore = wx.Button(window.dialog, label="&Restore All Defaults")
    restore.SetHelpText(
        "Put every event back to the sound this scheme ships, and switch them "
        "all on. Nothing you have saved is deleted."
    )
    restore.Bind(wx.EVT_BUTTON, lambda _e: window._restore_all())
    row.Add(restore, 0)

    choose_device = getattr(window, "_choose_device", None)
    if choose_device is not None:
        # Where this app's own sounds play (ui/app_sounds), beside the window
        # that says which sounds they are.
        device = wx.Button(window.dialog, label="App Sounds Play &On...")
        device.SetHelpText(
            "Which sound card this app's own sounds play on, or None to turn "
            "them off. Alt+Shift+M turns them off and on from anywhere."
        )
        device.Bind(wx.EVT_BUTTON, lambda _e: choose_device())
        row.Add(device, 0, wx.LEFT, 6)
    return row
