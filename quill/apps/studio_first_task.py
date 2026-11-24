"""QUILL Studio, before the first book (FUX-09).

The home window put focus on a static text, "Ready - use the menu bar to
begin", which cannot take focus, so on a new installation focus fell to the
status bar's cells and nothing said what Studio could do first. While there is
no book yet, a line at the top of the home window names the two commands that
make one from what you already have, with their keys, and takes launch focus.
Both run on this computer with the voices Windows already has. Once a book
exists the line goes, and focus goes where it always went.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine

__all__ = ["NO_BOOKS", "build", "focus", "focus_home", "has_books", "refresh"]

# The Studio menu's own fixed keys (studio.py's menu bar).
NO_BOOKS = first_task_line(
    "No books yet.",
    (
        NextAction("Narrate Documents", key="Ctrl+Shift+N", does="reads documents into a book"),
        NextAction(
            "Build From Recordings", key="Ctrl+Shift+B", does="makes one from your recordings"
        ),
    ),
)


def build(host: Any, parent: Any, sizer: Any) -> None:
    """The line, made first on the home panel so it is first in the Tab order."""
    import wx

    from quill.ui.accessible_names import set_accessible_name
    from quill.ui.spoken_name import set_spoken_name

    # The panel is where focus can fall when the line goes: give it a name.
    set_accessible_name(parent, "QUILL Studio")
    set_spoken_name(parent, "QUILL Studio")
    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    host._first_task_line = line
    refresh(host)


def has_books(host: Any) -> bool:
    """A book filed in the library, or one opened recently."""
    if host._recent_books():
        return True
    try:
        from quill.core.audio_studio.library import load_library
        from quill.core.paths import app_data_dir

        return bool(load_library(app_data_dir()).books)
    except Exception:  # noqa: BLE001 - an unreadable library is an empty one
        return False


class _AfterTheLine:
    """Where focus goes when the line hides under it: the status bar's cell
    when the bar is shown, else the (named) home panel."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def SetFocus(self) -> None:  # noqa: N802 - the wx name EmptyStateLine calls
        bar = getattr(self._host, "_status_bar", None)
        if bar is not None and bar.is_shown():
            bar.focus_bar()
            return
        panel = getattr(self._host, "_main_panel", None)
        if panel is not None:
            panel.SetFocus()


def refresh(host: Any) -> None:
    """Show the line while there is no book; hide it once there is one."""
    line = getattr(host, "_first_task_line", None)
    if line is None:
        return
    line.update("" if has_books(host) else NO_BOOKS, then_focus=_AfterTheLine(host))


def focus_home(host: Any) -> None:
    """Where the home window puts focus: the line while there is no book, else
    the activity text (moved here from ``studio.py``, GATE-11)."""
    if focus(host):
        return
    control = getattr(host, "_activity_text", None)
    if control is None:
        control = getattr(host, "_main_panel", None)
    if control is not None:
        try:
            control.SetFocus()
        except Exception:  # noqa: BLE001 - focus is best-effort
            pass


def focus(host: Any) -> bool:
    """Focus the line while there is no book. True when it took focus."""
    line = getattr(host, "_first_task_line", None)
    return bool(line is not None and line.focus())
