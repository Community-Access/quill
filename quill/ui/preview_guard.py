"""Escape and closing stop a setting's preview (FUX-08, family M8).

The one rule every preview button in the family follows for stopping: while a
preview plays, Escape stops it and does nothing else, so the window stays open
and the person can try another choice; with nothing playing, Escape is the
window's own again (Cancel or Close). Closing the window, by any route, stops
the preview, so a sound never outlives the window that started it. So does
the window losing the foreground -- a child dialog opening over it, or
another program coming to the front -- so a late step never speaks over the
screen reader reading what has just appeared. Scribe's
Play Sample worked this way first (``scribe_convert_dialog._on_key``).

Bound after the window's own handlers, so it runs first.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["STOPPED", "guard_preview"]


#: Said when Escape stops a preview: focus does not move, so the screen reader
#: says nothing, and without it Escape would seem to have done nothing at all.
STOPPED = "Preview stopped."


def guard_preview(
    window: Any, stop: Callable[[], bool], announce: Callable[[str], None] | None = None
) -> None:
    """Escape stops a playing preview without closing *window*; closing or
    leaving it stops it.

    *stop* stops the preview and answers True when something was playing.
    *announce* (the app's announcement service, so it is brailled too) says
    :data:`STOPPED` when Escape stopped one.
    """
    import wx

    def on_key(event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE and not event.HasAnyModifiers() and stop():
            if announce is not None:
                announce(STOPPED)
            return
        event.Skip()

    def on_activate(event: Any) -> None:
        if not event.GetActive():
            stop()
        event.Skip()

    def on_destroy(event: Any) -> None:
        if event.GetEventObject() is window:
            stop()
        event.Skip()

    window.Bind(wx.EVT_CHAR_HOOK, on_key)
    window.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    if isinstance(window, wx.TopLevelWindow):
        window.Bind(wx.EVT_ACTIVATE, on_activate)
