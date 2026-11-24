"""Cast's first useful task, at launch (FUX-09).

An empty Podcasts place says what fills it ("No podcasts yet. Add Podcast
(Ctrl+N) finds one..."), once, on arrival. At launch that arrival happened
while the window was still being built, before it was on screen and before
the welcome opened over it, so a new listener never heard it, and after the
welcome closed they were left on a silent, empty tree.

Now the launch is quiet while the window is built, and the arrival is made
after the welcome is answered (or at once, for somebody who has had it): focus
on the landing place's content, and its empty sentence said once. Choosing
Add Your First Podcast in the welcome opens that window instead, so nothing is
said over it.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["SAY_AFTER_MS", "launch_first_task", "say_landing_place"]

logger = logging.getLogger(__name__)

#: The sentence waits this long after focus lands: closing the welcome gives
#: the window back to the screen reader, whose own focus speech would cut a
#: sentence said at once.
SAY_AFTER_MS = 300


def say_landing_place(host: Any) -> None:
    """Focus the place Cast landed on, and say what fills it if it is empty."""
    frame = getattr(host, "frame", None)
    if frame is None or not frame.IsShown():
        return  # in the tray: nobody is looking, and the arrival comes with the window
    if getattr(host, "_cast_adding_first_podcast", False):
        return  # Add Podcast is opening; it is the next thing to read
    place = getattr(host, "_current_place", "")
    content = getattr(host, "_content", None)
    if not place or content is None:
        return
    try:
        content.focus()
    except Exception:  # noqa: BLE001 - a window mid-teardown is not a crash
        return
    _later(SAY_AFTER_MS, _say_if_still_here, host, place)


def _later(ms: int, fn: Any, *args: Any) -> None:
    import wx

    wx.CallLater(ms, fn, *args)


def _say_if_still_here(host: Any, place: str) -> None:
    """Said only if Cast is still in front, on that place, with nothing over it."""
    try:
        frame = host.frame
        if not frame.IsActive() or getattr(host, "_current_place", "") != place:
            return
        if getattr(host, "_cast_adding_first_podcast", False):
            return
    except Exception:  # noqa: BLE001 - a window mid-teardown is not a crash
        return
    host._place_announced_empty = ""
    host._say_empty_place_once(place)


def launch_first_task(host: Any) -> None:
    """The welcome when it is due, then the landing place's first task."""
    from quill.ui.podcasts.first_run_dialog import maybe_run_first_run

    try:
        maybe_run_first_run(host)
        say_landing_place(host)
    except Exception:  # noqa: BLE001 - nothing here is worth failing a launch over
        logger.exception("Cast's launch first task failed")
