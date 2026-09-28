"""Up means more on a horizontal slider.

A Windows trackbar answers Up and Page Up with *less* and Down and Page Down
with *more*: to the control, Up is "towards the start", and on a horizontal
bar the start is the left end. On a volume slider that is backwards to every
listener -- a user of Quill Radio wrote (2026-09-28) "when you turn it up it's
down arrow, when you turn it down it's up arrow" -- and it contradicts the
Windows volume mixer, which a screen-reader user hears as Up-is-louder every
day. Left and Right are already right and are left alone.

:func:`bind_up_means_more` takes the four vertical keys away from the
trackbar, moves the value the way a person expects, and fires the slider's
own ``EVT_SLIDER`` so whatever the slider is wired to hears the change exactly
as it does for Left, Right, the mouse or Home and End. Shift, Ctrl and Alt
chords are left to the frame, so Ctrl+Up and Ctrl+Down still reach the app's
Volume Up and Volume Down commands from the slider as from anywhere else.
"""

from __future__ import annotations

from typing import Any

import wx

#: Up/Down move by the slider's line size, Page Up/Page Down by its page size,
#: exactly as the trackbar does -- only the direction changes.
_KEY_STEPS: dict[int, tuple[str, int]] = {
    wx.WXK_UP: ("line", +1),
    wx.WXK_NUMPAD_UP: ("line", +1),
    wx.WXK_DOWN: ("line", -1),
    wx.WXK_NUMPAD_DOWN: ("line", -1),
    wx.WXK_PAGEUP: ("page", +1),
    wx.WXK_NUMPAD_PAGEUP: ("page", +1),
    wx.WXK_PAGEDOWN: ("page", -1),
    wx.WXK_NUMPAD_PAGEDOWN: ("page", -1),
}


def step_for_key(key_code: int, line_size: int, page_size: int) -> int | None:
    """The signed change a vertical key makes, or None for any other key.

    Pure, so the direction rule is testable without a window: Up and Page Up
    are positive, Down and Page Down negative.
    """
    entry = _KEY_STEPS.get(key_code)
    if entry is None:
        return None
    kind, sign = entry
    size = max(1, line_size if kind == "line" else page_size)
    return sign * size


def bind_up_means_more(slider: Any) -> None:
    """Make Up and Page Up raise ``slider`` and Down and Page Down lower it."""

    def on_key(event: Any) -> None:
        if event.ControlDown() or event.ShiftDown() or event.AltDown():
            event.Skip()
            return
        delta = step_for_key(event.GetKeyCode(), slider.GetLineSize(), slider.GetPageSize())
        if delta is None:
            event.Skip()
            return
        before = slider.GetValue()
        after = max(slider.GetMin(), min(slider.GetMax(), before + delta))
        if after == before:
            return  # at an end already; nothing to say and nothing to fire
        slider.SetValue(after)
        changed = wx.CommandEvent(wx.wxEVT_SLIDER, slider.GetId())
        changed.SetInt(after)
        changed.SetEventObject(slider)
        slider.GetEventHandler().ProcessEvent(changed)

    slider.Bind(wx.EVT_KEY_DOWN, on_key)
    # Reachable for tests, which drive it with a stand-in event: a real
    # keystroke needs focus, and focus needs a screen.
    slider._quill_up_means_more = on_key
