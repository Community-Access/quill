"""Select All and Invert Selection in an episode list (earshot.md E5).

The episode list has always taken a multiple selection, and the bulk actions
(Add to Queue, Download, Mark as Played, Mark as Unplayed...) read all of it --
but there was no way to select *everything* from the keyboard, so clearing a
400-episode backlog meant Shift+End from the top and hoping. Earshot's recipe
(1.2.5) is the one people reach for: select all, deselect the few to keep,
invert, and act on what is left.

**Keys that belong to the list.** Ctrl+A and Ctrl+Shift+I are answered only
while the episode list has focus. As menu accelerators they would fire from
Cast's search box too, where Ctrl+A has to mean "select this text". The
context menu shows them, so they are discoverable where the selection is.

The count is spoken because a screen reader announces only the focused row's
state; "All 412 episodes selected" is the one fact it cannot know (GATE-13).
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["invert_selection", "select_all", "selection_key"]


def _list(host: Any) -> Any:
    return getattr(host, "_episodes", None)


def _count(episodes: Any) -> int:
    return int(episodes.GetItemCount()) if episodes is not None else 0


def _say(count: int, total: int) -> str:
    if count == total:
        return f"All {total} episode{'' if total == 1 else 's'} selected."
    if count == 0:
        return "No episodes selected."
    return f"{count} of {total} episodes selected."


def select_all(host: Any) -> None:
    """Select every row in the episode list."""
    episodes = _list(host)
    total = _count(episodes)
    if not total:
        host._announce("There are no episodes here to select.")
        return
    for index in range(total):
        episodes.Select(index, True)
    host._announce(_say(total, total))


def invert_selection(host: Any) -> None:
    """Select what was not selected, and deselect what was."""
    episodes = _list(host)
    total = _count(episodes)
    if not total:
        host._announce("There are no episodes here to select.")
        return
    selected = set()
    index = episodes.GetFirstSelected()
    while index != -1:
        selected.add(index)
        index = episodes.GetNextSelected(index)
    for row in range(total):
        episodes.Select(row, row not in selected)
    host._announce(_say(total - len(selected), total))


def selection_key(host: Any, event: Any) -> bool:
    """Ctrl+A and Ctrl+Shift+I on the focused episode list. True when handled."""
    episodes = _list(host)
    if episodes is None or wx.Window.FindFocus() is not episodes:
        return False
    if not event.ControlDown() or event.AltDown():
        return False
    code = event.GetKeyCode()
    if code == ord("A") and not event.ShiftDown():
        select_all(host)
        return True
    if code == ord("I") and event.ShiftDown():
        invert_selection(host)
        return True
    return False
