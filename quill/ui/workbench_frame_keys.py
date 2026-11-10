"""Keys a Workbench provider wants only in the list: Delete, Shift+Delete, Ctrl+Z.

Split from :mod:`quill.ui.workbench_frame` (GATE-11). A provider whose menu
puts Move to Trash on Delete (WordPress PRD Part C) names those chords in its
``list_keys``. The window's key hook runs before the menu's accelerators, so
outside the list such a key never reaches the menu and never acts on the
selected rows: in the filter box it edits the text, as the box itself would,
and anywhere else it does nothing.
"""

from __future__ import annotations

from typing import Any

__all__ = ["keep_list_key"]


def keep_list_key(frame: Any, event: Any, focused: Any) -> bool:
    """Handle a list-only key pressed outside the list; True when it was kept."""
    wx = frame._wx
    keys = getattr(frame.provider, "list_keys", frozenset())
    name = {wx.WXK_DELETE: "Delete", ord("Z"): "Z"}.get(event.GetKeyCode(), "")
    if not name:
        return False
    mods = ("Ctrl+" if event.ControlDown() else "") + ("Shift+" if event.ShiftDown() else "")
    if f"{mods}{name}" not in keys:
        return False
    box = frame.filter
    if focused is box:
        if name == "Z":
            box.Undo()
        elif event.ShiftDown():
            box.Cut()
        else:
            start, end = box.GetSelection()
            box.Remove(start, end if end != start else start + 1)
    return True
