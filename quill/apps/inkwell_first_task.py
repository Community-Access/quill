"""Inkwell's abbreviation list, when it is empty (FUX-09).

A new library is never empty -- Inkwell starts with its built-in shorthand --
but once every entry is deleted the list said only "Abbreviations, list,
empty". While it is empty, a line before it names the two commands that make
a first entry, with their keys, and takes launch focus; the first entry hides
it and focus goes to the list.

``refresh`` runs each time the list is drawn, which is where the line learns
that the library changed.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine

__all__ = ["NO_ABBREVIATIONS", "build", "focus_initial", "refresh", "reload"]

# The Abbreviations menu's own fixed keys (inkwell.py's menu bar).
NO_ABBREVIATIONS = first_task_line(
    "No abbreviations yet.",
    (
        NextAction("Manage Abbreviations", key="Ctrl+M", does="makes one"),
        NextAction("New from Clipboard", key="Ctrl+Shift+N", does="saves the copied text as one"),
    ),
)


def build(host: Any, parent: Any, sizer: Any) -> None:
    """The line, made before the list so it comes first in the Tab order."""
    import wx

    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
    host._first_task_line = line


def refresh(host: Any) -> None:
    """Show the line only while the library is empty."""
    line = getattr(host, "_first_task_line", None)
    if line is not None:
        empty = not host._library.abbreviations
        line.update(NO_ABBREVIATIONS if empty else "", then_focus=host._list)


def reload(host: Any) -> None:
    """Draw the list (``inkwell_row_help``), then show the line if it is empty."""
    from quill.apps import inkwell_row_help

    inkwell_row_help.fill_list(host)
    refresh(host)


def focus_initial(host: Any) -> None:
    """The line while the library is empty; the list otherwise."""
    line = getattr(host, "_first_task_line", None)
    if line is not None and line.focus():
        return
    host._list.SetFocus()
