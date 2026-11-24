"""Keep every Workbench pane inside the window, and the window on the screen.

The Details pane sits at the right of the Workbench, so it is the first thing
lost when the layout does not fit. Two ways it could be lost, both closed here
for every Workbench (WordPress and GitHub share the frame):

- **A window narrower than its two panes' minimums.** ``wx.SplitterWindow``
  then puts the sash past its own right edge, and the right pane -- filter,
  list and Details -- is laid out where nothing can see it. A minimum client
  size of both panes plus the sash means that state cannot be reached.
- **A window bigger than the screen.** The default 980 by 680 DIPs is 1960
  pixels wide at 200 percent, and a remembered size can come from a bigger
  display. :func:`quill.ui.dpi.fit_to_work_area` pulls it back when the window
  opens and again when it moves to a display with another scale.

Text in Details wraps at the control's own width (a multi-line ``wx.TextCtrl``
without ``wx.HSCROLL``), so once the control is inside the visible window every
line ends inside it too.
"""

from __future__ import annotations

from typing import Any

from quill.ui import dpi

__all__ = ["PANE_MINIMUM_DIP", "hold_panes"]

#: The narrowest either pane may become, in DIPs.
PANE_MINIMUM_DIP = 120
#: The shortest the window's client area may become, in DIPs.
CLIENT_MINIMUM_HEIGHT_DIP = 240


def _apply_minimums(frame: Any, splitter: Any) -> None:
    """Wide enough for both panes, tall enough for every row of the tallest pane.

    Never more than the work area holds, or the minimum would push the window
    back off the screen it was just fitted to.
    """
    import wx

    pane = frame.FromDIP(PANE_MINIMUM_DIP)
    splitter.SetMinimumPaneSize(pane)
    width = 2 * pane + splitter.GetSashSize() + frame.FromDIP(8)
    sizers = [w.GetSizer() for w in (splitter.GetWindow1(), splitter.GetWindow2()) if w]
    tallest = max((sizer.CalcMin().height for sizer in sizers if sizer), default=0)
    status_row = wx.Button.GetDefaultSize(frame).height + frame.FromDIP(8)
    height = max(frame.FromDIP(CLIENT_MINIMUM_HEIGHT_DIP), tallest + status_row)
    _x, _y, area_width, area_height = dpi.work_area(frame)
    outer, client = frame.GetSize(), frame.GetClientSize()
    width = min(width, area_width - (outer.width - client.width))
    height = min(height, area_height - (outer.height - client.height))
    frame.SetMinClientSize(wx.Size(width, height))


def hold_panes(frame: Any, splitter: Any) -> None:
    """Give *frame* minimums that keep both panes visible, and refit on a DPI change."""
    import wx

    _apply_minimums(frame, splitter)

    def dpi_changed(event: Any) -> None:
        event.Skip()  # wx rescales the window first; the minimums and fit follow it

        def refit() -> None:
            if not (frame and splitter):
                return  # the window closed
            if wx.GetMouseState().LeftIsDown():
                # Mid-drag onto the other display: moving it now would fight the
                # mouse, and throw a magnifier's view off the window. After the drop.
                wx.CallLater(250, refit)
                return
            _apply_minimums(frame, splitter)
            dpi.fit_to_work_area(frame)

        wx.CallAfter(refit)

    frame.Bind(wx.EVT_DPI_CHANGED, dpi_changed)
