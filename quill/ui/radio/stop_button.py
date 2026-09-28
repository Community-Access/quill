"""The main window's Stop button, back beside Mute (Quill Radio 3.0.3).

Play/Stop left the main window's button row on 2026-08-21 with the rest of the
player furniture, keeping its menu item (Station > Stop) and its key
(Ctrl+Period). A listener who updated from 2.x found the button gone and a
Pause button still in other windows, and asked where Stop went (2026-09-28).
Stopping is the one action every listener needs at once without knowing a key,
so it is a button again -- first in the row, before Mute and Volume.

Built here rather than in ``quill/apps/radio.py`` (at its GATE-11 budget), with
its F1 sentence inline at the construction site, where the help audit reads it.
"""

from __future__ import annotations

from typing import Any

from quill.ui.accessible_names import set_accessible_name

__all__ = ["add_stop_button"]


def add_stop_button(host: Any, panel: Any, row: Any, wx: Any) -> Any:
    """Add Stop to *row* and return it. Pressing it runs the app's own Stop."""
    button = wx.Button(panel, label="S&top")
    set_accessible_name(button, "Stop (Ctrl+Period)")
    button.SetHelpText(
        "Stops the radio, podcast or recording you are listening to. The same as "
        "Ctrl+Period and Station, Stop."
    )
    button.Bind(wx.EVT_BUTTON, lambda _e: host.radio_stop())
    row.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    host._stop_btn = button
    return button
