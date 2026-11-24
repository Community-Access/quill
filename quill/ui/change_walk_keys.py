"""F8 and Shift+F8 in a read-only diff text: the next and previous change (FUX-12).

One helper for every read-only view of a difference written as text (a file
in a pull request, Compare Branches, Compare Configuration, WordPress's
Compare with Site), so they move the same way as the editor's Compare
dialog, where F8 and Shift+F8 already move between differences.

The caret moves to the first line of the change, and "Change 2 of 4. Lines 10
to 15:" is said, because a caret moved by the program is not something a
screen reader reliably reads, and the count is something only the app
knows. At the end "No more changes" is said, at the start "No earlier
changes", and in a text with no changes "No changes in this file"; the caret
stays.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.change_walk import change_starts, next_stop

__all__ = ["bind_change_walk", "walk"]


def _line_at(ctrl: Any) -> int:
    """The 0-based logical line the caret is on, whatever the control counts."""
    return str(ctrl.GetRange(0, ctrl.GetInsertionPoint())).count("\n")


def _units(text: str) -> int:
    """Windows counts text positions in UTF-16 units: an emoji is two."""
    return len(text.encode("utf-16-le")) // 2


def _position_of(ctrl: Any, text: str, line: int) -> int:
    """The control's position for the start of logical line *line* of *text*.

    Positions are UTF-16 units, and a rich edit counts a line break as one
    while a plain multi-line edit counts it as two.
    """
    import wx

    before = "".join(part + "\n" for part in text.split("\n")[:line])
    rich = bool(ctrl.GetWindowStyleFlag() & (wx.TE_RICH | wx.TE_RICH2))
    return _units(before) + (0 if rich else line)


def walk(ctrl: Any, announce: Callable[[str], None], *, forward: bool) -> bool:
    """Move *ctrl*'s caret to the next (or previous) change; True when it moved."""
    text = str(ctrl.GetValue())
    stop = next_stop(text, _line_at(ctrl), forward=forward)
    if stop is None:
        if not change_starts(text):
            announce("No changes in this file.")
        else:
            announce("No more changes." if forward else "No earlier changes.")
        return False
    position = _position_of(ctrl, text, stop.line)
    ctrl.SetInsertionPoint(position)
    ctrl.ShowPosition(position)
    announce(stop.spoken())
    return True


def bind_change_walk(ctrl: Any, announce: Callable[[str], None]) -> None:
    """Give *ctrl* F8 (next change) and Shift+F8 (previous change)."""
    import wx

    def on_key(event: Any) -> None:
        if (
            event.GetKeyCode() == wx.WXK_F8
            and not event.ControlDown()
            and not event.AltDown()
            and not event.MetaDown()
        ):
            walk(ctrl, announce, forward=not event.ShiftDown())
            return
        event.Skip()

    ctrl.Bind(wx.EVT_KEY_DOWN, on_key)
