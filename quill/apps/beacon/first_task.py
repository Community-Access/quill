"""QuillBeacon, before the first bookmark (FUX-09).

A new library opened on the search box over an empty results list, and said
only "0 results". While the library holds no bookmark at all (not merely no
match for a search), a line above the search box names the two File menu
commands that fill it, with their keys, and takes launch focus. Both work on
this computer. The first bookmark hides it.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine

__all__ = ["NO_BOOKMARKS", "build", "focus_initial", "refresh"]

# The File menu's own fixed keys (app.py's menu bar).
NO_BOOKMARKS = first_task_line(
    "No bookmarks yet.",
    (
        NextAction("New Bookmark", key="Ctrl+N", does="saves one"),
        NextAction("Import", key="Ctrl+I", does="brings bookmarks or subscriptions in"),
    ),
)


def build(host: Any, parent: Any, sizer: Any) -> None:
    """The line, made before the search box so it is first in the right pane."""
    import wx

    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
    host._first_task_line = line


def refresh(host: Any) -> None:
    """Show the line while the library is empty; hide it at the first bookmark."""
    line = getattr(host, "_first_task_line", None)
    store = getattr(host, "store", None)
    if line is None or store is None:
        return
    try:
        empty = store.count(include_trashed=True) == 0  # Trash is not empty
    except Exception:  # noqa: BLE001 - a store mid-close is not news
        return
    line.update(NO_BOOKMARKS if empty else "", then_focus=getattr(host, "results", None))


def focus_initial(host: Any) -> None:
    """The line while the library is empty; the search box otherwise."""
    line = getattr(host, "_first_task_line", None)
    if line is not None and line.focus():
        return
    host.search_box.SetFocus()
