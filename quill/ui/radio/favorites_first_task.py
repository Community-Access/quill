"""Quill Radio's Favorites, before the first favorite (FUX-09).

On a new installation the main window lands on an empty Favorites tree, and
the first-run welcome is answered once and gone. This puts a line before the
tree, shown only while it is empty, that names the two ways to a first
station by the menu's labels and their live keys. Browsing names its internet
dependency, because the directory is on the internet; a known address does not
need a directory.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine, key_for_host

__all__ = ["build", "focus", "line_text", "refresh"]

SITUATION = "No favorite stations yet."
ACTIONS = (
    NextAction("Browse Stations", "radio.browse", "finds one online"),
    NextAction("Add Custom Station", "radio.add_custom_station", "takes its address"),
)


def line_text(host: Any) -> str:
    return first_task_line(SITUATION, ACTIONS, key_for_host(host))


def build(host: Any, parent: Any) -> Any:
    """The Favorites page's sizer, holding the line (hidden).

    Made before the tree's label and the tree, so the line comes first in Tab
    order and the label's access key still lands on the tree.
    """
    import wx

    sizer = wx.BoxSizer(wx.VERTICAL)
    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    host._favorites_first_task = line
    return sizer


def refresh(host: Any) -> None:
    """Show the line while the tree has no folder or station; hide it otherwise."""
    line = getattr(host, "_favorites_first_task", None)
    tree = getattr(host, "_favorites_tree", None)
    if line is None or tree is None:
        return
    root = tree.GetRootItem()
    empty = not root.IsOk() or tree.GetChildrenCount(root, False) == 0
    line.update(line_text(host) if empty else "", then_focus=tree)


def focus(host: Any) -> bool:
    """Focus the line when the Favorites tree is empty. True when it took focus."""
    line = getattr(host, "_favorites_first_task", None)
    return bool(line is not None and line.focus())
