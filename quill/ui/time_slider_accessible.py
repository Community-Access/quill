"""A position slider a screen reader reads as a time, not a percentage.

A ``wx.Slider`` is a Windows trackbar, and a trackbar's value reaches MSAA and
UIA as a bare percentage of its range: Jeff, 2026-11-27, "Position reads as a
percentage". The slider's range is seconds, so the number is not even a
percentage of anything a listener thinks in.

:func:`speak_time_value` puts a ``wx.Accessible`` on the slider whose value is
the spoken time ("12 minutes 34 of 58 minutes") and whose name is the caption
beside it -- the trackbar is also the one control wxMSW does not name from the
label before it (see ``sound_enhance_dialog.py``). Every other property falls
through to the trackbar's own, so its role, state and keys are unchanged.

Where wx was built without accessibility support this does nothing, and the
slider keeps reading as it did.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

__all__ = ["speak_time_value"]


def speak_time_value(slider: Any, name: str, value: Callable[[], str]) -> bool:
    """Give *slider* the accessible *name* and a value read from *value*.

    *value* is called each time the reader asks, so it is always current.
    Returns whether the accessible object was installed.
    """
    base = getattr(wx, "Accessible", None)
    if base is None or not hasattr(slider, "SetAccessible"):
        return False

    class _TimeSliderAccessible(base):  # type: ignore[misc, valid-type]
        def GetName(self, child_id: int) -> tuple[int, str]:
            if child_id:
                return wx.ACC_NOT_IMPLEMENTED, ""
            return wx.ACC_OK, name

        def GetValue(self, child_id: int) -> tuple[int, str]:
            if child_id:
                return wx.ACC_NOT_IMPLEMENTED, ""
            try:
                return wx.ACC_OK, str(value())
            except Exception:  # noqa: BLE001 - a reader asking mid-teardown
                return wx.ACC_NOT_IMPLEMENTED, ""

    try:
        accessible = _TimeSliderAccessible(slider)
        slider.SetAccessible(accessible)
    except Exception:  # noqa: BLE001 - no accessibility in this wx build
        return False
    # Held on the slider: wx does not keep the Python wrapper alive.
    slider._quill_time_accessible = accessible
    return True
