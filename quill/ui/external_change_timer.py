"""The clock both editors watch an open file on (2026-10-04).

QUILL's watcher started a ``wx.Timer`` inside a closure and stopped it by hand
around its own question; QUILL Lite gained a watcher the same day and must not
have a second one. This is the shared half that touches wx: a repeating timer
that **does not tick while a modal window is up** -- the File Changed on Disk
question, Save's conflict question, Preferences, a message box -- and never
re-enters itself. A change found while a dialog is open is still there when it
closes, and is reported then, once.

The decisions are not here. They are wx-free, in
:mod:`quill.core.external_change`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

__all__ = ["ExternalChangeTimer", "modal_window_open"]


def modal_window_open(window: Any) -> bool:
    """Whether a modal dialog or message box is up over *window*'s application.

    ``ShowModal`` disables every other top-level window, and a native message
    box disables its owner, so a disabled window anywhere above *window* (an
    MDI document's shell included) is the one signal both kinds give.
    """
    try:
        for top in wx.GetTopLevelWindows():
            if isinstance(top, wx.Dialog) and top.IsModal():
                return True
        node = window
        while node is not None:
            if not node.IsEnabled():
                return True
            node = node.GetParent()
    except (RuntimeError, AttributeError):
        return False
    return False


class ExternalChangeTimer:
    """A repeating poll that pauses for modal windows and for *busy*.

    *interval* is read again after every tick, so a changed setting takes effect
    without anybody restarting the timer. :meth:`tick` is what the timer calls,
    and what a test calls instead of waiting.
    """

    def __init__(
        self,
        owner: Any,
        on_tick: Callable[[], None],
        *,
        interval: Callable[[], int],
        busy: Callable[[], bool] | None = None,
    ) -> None:
        self._owner = owner
        self._on_tick = on_tick
        self._interval = interval
        self._busy = busy
        self._running_ms = 0
        self._in_tick = False
        self._timer: Any = None

    @property
    def running(self) -> bool:
        return self._timer is not None

    def start(self) -> None:
        if self._timer is None:
            self._timer = wx.Timer(self._owner)
            self._owner.Bind(wx.EVT_TIMER, lambda _event: self.tick(), self._timer)
        self._running_ms = int(self._interval())
        self._timer.Start(self._running_ms)

    def stop(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            try:
                timer.Stop()
            except RuntimeError:
                pass  # the owner is already being destroyed

    def tick(self) -> None:
        """Poll once, unless already polling, busy, or under a modal window."""
        if self._in_tick:
            return
        if self._busy is not None and self._busy():
            return
        if modal_window_open(self._owner):
            return
        self._in_tick = True
        try:
            self._on_tick()
        finally:
            self._in_tick = False
        wanted = int(self._interval())
        if self._timer is not None and wanted != self._running_ms:
            self._running_ms = wanted
            self._timer.Start(wanted)
