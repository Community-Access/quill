"""Quill Media Player, before anything is open (FUX-09).

With nothing open, every transport button is greyed, so focus that "opens on
the transport" fell to whatever was left -- the Volume slider -- and the Now
Playing line said only "Open a file or a folder to begin." Now a line before
Now Playing names the two File menu commands that begin, with their keys, and
it is where focus lands while nothing is open. It is a single-line read-only
field (:class:`~quill.ui.empty_state_line.EmptyStateLine`), so a screen reader
reads the whole sentence on focus, and the app never speaks it. It goes away
the moment something opens, and Now Playing says what is playing as before.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine

__all__ = ["NOTHING_OPEN", "NOW_PLAYING_EMPTY", "attach", "build", "focus_initial"]

#: Now Playing's own value while nothing is open.
NOW_PLAYING_EMPTY = "Nothing open."
NOTHING_OPEN = first_task_line(
    "Nothing is open yet.",
    (
        NextAction("Open File", key="Ctrl+O", does="plays a file"),
        NextAction("Open Folder as Book", key="Ctrl+Shift+O", does="plays a folder in order"),
    ),
)


def build(host: Any, parent: Any, sizer: Any) -> None:
    """The line, made before Now Playing so it is first in the Tab order."""
    import wx

    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    host._first_task_line = line


def _sync(host: Any) -> None:
    line = getattr(host, "_first_task_line", None)
    now_playing = getattr(host, "_now_playing", None)
    if line is None or now_playing is None:
        return
    empty = now_playing.GetValue() == NOW_PLAYING_EMPTY
    line.update(NOTHING_OPEN if empty else "", then_focus=getattr(host, "_player", None))


def attach(host: Any) -> None:
    """Now Playing starts empty, and the line follows it: shown until something opens."""
    import wx

    host._now_playing.SetValue(NOW_PLAYING_EMPTY)
    host._now_playing.Bind(wx.EVT_TEXT, lambda event: (_sync(host), event.Skip()))
    _sync(host)


def focus_initial(host: Any) -> None:
    """The line while nothing is open; the transport once something is."""
    line = getattr(host, "_first_task_line", None)
    if line is not None and line.focus():
        return
    host._player.SetFocus()
