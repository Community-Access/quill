"""Convert a size written in device-independent pixels to real pixels (#1702).

Every QuillVille app declares itself per-monitor DPI aware
(:mod:`quill.platform.windows.dpi_awareness`), so Windows no longer stretches
it -- and a size written as plain pixels would then be too small at 150 or
200 percent. Every fixed size in ``quill/ui`` and ``quill/apps`` goes through
one of the two functions here instead, and ``tests/unit/ui/test_dpi_awareness_gate.py``
fails on a new one that does not.

Both work before the window they size exists, which is the common case: a
dialog passes ``size=`` to its own ``__init__``, so it converts against its
*parent*. With no usable window they use the primary display's scale factor,
and with no ``wx.App`` yet (a module-level constant) they return the value
unchanged. ``wx`` is imported only when a function runs, so any module can
import this one at top level. At 100 percent the result is always identical to the input, and
``-1`` (``wx.DefaultCoord``, "let the sizer decide") is always preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import wx


def scale_factor(window: Any = None) -> float:
    """The DPI scale factor for ``window``, or for the primary display."""
    if window is not None:
        getter = getattr(window, "GetDPIScaleFactor", None)
        if getter is not None:
            try:
                factor = float(getter())
                if factor > 0:
                    return factor
            except Exception:  # noqa: BLE001 - not created yet, or already destroyed
                pass
    try:
        import wx

        if wx.GetApp() is None:
            return 1.0
        factor = float(wx.Display(0).GetScaleFactor())
    except Exception:  # noqa: BLE001 - sizing must never stop a window opening
        return 1.0
    return factor if factor > 0 else 1.0


def _scale(value: int, factor: float) -> int:
    if value == -1 or factor == 1.0:
        return int(value)
    return int(round(value * factor))


def dip(window: Any, value: int) -> int:
    """One length in device-independent pixels, converted for ``window``."""
    return _scale(value, scale_factor(window))


def dip_size(window: Any, width: int, height: int) -> wx.Size:
    """A ``wx.Size`` from device-independent pixels, converted for ``window``."""
    import wx

    factor = scale_factor(window)
    return wx.Size(_scale(width, factor), _scale(height, factor))
