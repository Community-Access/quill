"""Quill Converter, before anything is queued (FUX-09).

The window opens on the "Files to convert" list, and on a new installation
that list is empty: a screen reader said "Files to convert, list, empty" and
nothing else, no status text, nothing to do. A line before the list, shown
while the queue is empty, names the two File menu commands that fill it, by
their live keys, and takes launch focus; the moment anything is queued it
goes, and focus is on the queue as before.

Also here, extracted from ``converter.py`` (GATE-11): redrawing the queue,
which is where the line learns that the queue changed.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine

__all__ = ["build", "focus_initial", "line_text", "refresh", "reload"]

SITUATION = "Nothing to convert yet."
ACTIONS = (
    # The File menu's own fixed keys (converter_menu.py).
    NextAction("Add Files", does="chooses audio or video files", key="Ctrl+O"),
    NextAction("Add Folder", does="brings a whole folder", key="Ctrl+Shift+O"),
)


def line_text(host: Any) -> str:
    del host  # fixed keys: the menu bakes them into its labels
    return first_task_line(SITUATION, ACTIONS)


def build(host: Any, parent: Any) -> Any:
    """The main panel's sizer, holding the line, made before the queue's label."""
    import wx

    sizer = wx.BoxSizer(wx.VERTICAL)
    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    host._first_task_line = line
    line.update(line_text(host))  # the queue starts empty
    return sizer


def refresh(host: Any) -> None:
    line = getattr(host, "_first_task_line", None)
    if line is not None:
        empty = not getattr(host, "_entries", None)
        line.update(line_text(host) if empty else "", then_focus=getattr(host, "_list", None))


def focus_initial(host: Any) -> None:
    """The line while the queue is empty; the queue once it is not."""
    line = getattr(host, "_first_task_line", None)
    if line is not None and line.focus():
        return
    host._list.SetFocus()


def reload(host: Any, *, select: int | None = None) -> None:
    """Redraw the queue from ``host._entries``, keep a row selected, say the count."""
    queue = host._list
    queue.Clear()
    for entry, _root in host._entries:
        queue.Append(entry.name if not entry.is_dir() else f"{entry.name} (folder)")
    if host._entries:
        index = select if select is not None else len(host._entries) - 1
        queue.SetSelection(max(0, min(index, len(host._entries) - 1)))
    host._set_status(f"{len(host._entries)} item(s) queued.")
    refresh(host)
