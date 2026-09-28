"""The radio volume slider that Browse Stations and Search Stations share.

Both surfaces put the same control on their volume row: a labelled 0 to 100
slider that follows the player's volume and, since 2026-09-28, answers Up
with louder (:func:`quill.ui.slider_keys.bind_up_means_more`). Extracted here
when that binding took the two dialogs over their GATE-11 ceilings; one
slider built in one place is also one fewer way for the pair to drift.

The Mute button beside it stays in each dialog, because its F1 help must be
written at the construction site for the help audit to see it.
"""

from __future__ import annotations

import wx

from quill.ui.slider_keys import bind_up_means_more


def add_volume_slider(surface: wx.Window, row: wx.BoxSizer, *, label: str, name: str) -> wx.Slider:
    """Append "<label> [slider]" to ``row`` and return the slider.

    ``label`` may carry an ``&`` access key; ``name`` is what a screen reader
    calls the slider. The caller binds ``EVT_SLIDER`` and syncs the value.
    """
    row.Add(wx.StaticText(surface, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    slider = wx.Slider(surface, value=100, minValue=0, maxValue=100)
    slider.SetName(name)
    slider.SetHelpText(
        "Internet Radio's own volume, 0 to 100 percent, separate from the system "
        "volume and your screen reader. Up and Right make it louder, Down and Left "
        "quieter; Page Up and Page Down move it in bigger steps. It follows Ctrl+Up "
        "and Ctrl+Down and the main window's Volume slider."
    )
    bind_up_means_more(slider)  # Up is louder, as in the main window
    row.Add(slider, 1, wx.EXPAND | wx.RIGHT, 6)
    return slider
