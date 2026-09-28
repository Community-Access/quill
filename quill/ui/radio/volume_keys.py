"""Ctrl+Up and Ctrl+Down as Volume Up and Volume Down, whatever has focus.

The Playback menu carries the accelerator, and on Win32 it never fires
while a TreeCtrl has focus: the tree gets first claim on WM_KEYDOWN for
Up/Down and moves its own cursor instead. A focused button can swallow the
chord too. So the favorites tree's key handler and the frame's char hook
both answer the chord themselves, through this one function (extracted
from ``quill/apps/radio.py`` on 2026-09-28 under GATE-11; both call sites
had the same eleven lines).

Inside a text field the chord is left alone: Ctrl+arrow is editing there.
"""

from __future__ import annotations

from typing import Any

import wx


def volume_chord_handled(
    app: Any, event: Any, code: int, *, skip_text_fields: bool = False
) -> bool:
    """Run Volume Up/Down for a bare Ctrl+Up / Ctrl+Down and say so.

    Returns False, and touches nothing, for any other key or modifier, or
    when ``skip_text_fields`` is set and focus is in a text control.
    """
    if not event.ControlDown() or event.ShiftDown() or event.AltDown():
        return False
    if code not in (wx.WXK_UP, wx.WXK_DOWN):
        return False
    if skip_text_fields and isinstance(wx.Window.FindFocus(), (wx.TextCtrl, wx.ComboBox)):
        return False
    if code == wx.WXK_UP:
        app.radio_volume_up()
    else:
        app.radio_volume_down()
    return True
