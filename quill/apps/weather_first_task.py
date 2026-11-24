"""Quill Weather, before the first place (FUX-09).

With no saved place, the window opened on Open Weather Center and spoke "Add a
weather location to begin monitoring." as it was being built, where the
screen reader's own reading of the window cut it, and it named no key and
did not say that finding a place uses the internet and covers US places only.
Now a line above the buttons, shown while there is no place, says so with the
live key and takes launch focus; the first place hides it, and focus goes to
Open Weather Center as before.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line
from quill.ui.empty_state_line import EmptyStateLine, key_for_host

__all__ = ["ADD_LOCATION", "build", "focus_initial", "line_text", "refresh", "say_if_hidden"]

ADD_LOCATION = NextAction(
    "Add Location",
    "weather.add_location",
    "finds a US place by ZIP code, city or address, over the internet",
    key="Alt+A",
)


def line_text(host: Any) -> str:
    return first_task_line("No weather location yet.", (ADD_LOCATION,), key_for_host(host))


def build(host: Any, parent: Any, sizer: Any) -> None:
    """The line, made before the buttons so it is first in the Tab order."""
    import wx

    line = EmptyStateLine(parent, name="Getting started")
    sizer.Add(line.ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    host._first_task_line = line
    # A place is added in Add Location or Weather Center, modal or not, or from
    # QUILL's hotkey: the window coming back to the front is when to look again.
    host.frame.Bind(wx.EVT_ACTIVATE, lambda event: _on_activate(host, event))


def _on_activate(host: Any, event: Any) -> None:
    event.Skip()
    if event.GetActive():
        import wx

        wx.CallAfter(refresh, host)


def say_if_hidden(host: Any) -> None:
    """Started in the tray with no place: the line is not on screen, so say it once."""
    frame = getattr(host, "frame", None)
    if frame is not None and not frame.IsShown():
        host._announce(line_text(host))


def _has_place(host: Any) -> bool:
    try:
        from quill.core.weather import locations as loc_store

        return loc_store.load_locations(host._weather_data_dir()).primary() is not None
    except Exception:  # noqa: BLE001 - an unreadable store has no place to offer
        return False


def refresh(host: Any) -> None:
    """Show the line while there is no saved place; hide it once there is one."""
    line = getattr(host, "_first_task_line", None)
    if line is None:
        return
    text = "" if _has_place(host) else line_text(host)
    line.update(text, then_focus=getattr(host, "_open_center_btn", None))


def focus_initial(host: Any) -> None:
    """The line while there is no place; Open Weather Center otherwise."""
    line = getattr(host, "_first_task_line", None)
    if line is not None and line.focus():
        return
    btn = getattr(host, "_open_center_btn", None)
    if btn is not None:
        try:
            btn.SetFocus()
        except Exception:  # noqa: BLE001 - initial focus is best-effort
            pass
