"""Starting minimized when Windows starts: the pieces every family app shares.

A Run-key launch carries ``--tray`` (come up in the tray) or ``--window`` (come
up as usual), chosen by the per-user "Start minimized when Windows starts"
preference (``quill.platform.windows.startup_options``). ``--window`` always
wins, so a login launch never hides a window the user asked to see, whatever
an app's own "start in the tray" option says.

Kept out of the app modules on purpose (GATE-11): the same menu row, the same
launch decision and the same hidden first show repeat in QUILL, Radio, Cast,
Weather and Inkwell, and one copy is one place to get them right.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import Any

__all__ = [
    "START_MINIMIZED_LABEL",
    "append_windows_startup_items",
    "apply_editor_startup",
    "editor_starts_hidden",
    "present_at_launch",
    "starts_in_tray",
]

#: The Options-menu row. Ctrl+Alt+L ("login") is free in every app that shows
#: it (Inkwell, Weather, Transcribe); S&tart because S is App Sounds and M is
#: the neighbouring "Start minimized to the tray".
START_MINIMIZED_LABEL = "S&tart minimized when Windows starts\tCtrl+Alt+L"


def starts_in_tray(saved_preference: bool = False, argv: Sequence[str] | None = None) -> bool:
    """Whether this launch comes up in the tray: ``--window`` beats everything."""
    args = sys.argv[1:] if argv is None else list(argv)
    if "--window" in args:
        return False
    return "--tray" in args or bool(saved_preference)


def present_at_launch(
    host: Any,
    app_name: str,
    *,
    in_tray: bool | None = None,
    to_tray: Callable[[], None] | None = None,
    say: Callable[[str], None] | None = None,
    focus: Callable[[], None] | None = None,
    raise_window: bool = True,
) -> bool:
    """Show *host*'s window, or keep it in the tray; True when it was shown.

    *to_tray* is the app's own send-to-tray for a window already showing; a
    window not yet shown is simply left hidden and *say* (default: the status
    bar) reports where it went.
    """
    import wx

    if starts_in_tray() if in_tray is None else in_tray:
        if to_tray is not None and host.frame.IsShown():
            to_tray()
        else:
            host.frame.Hide()
            (say or host._set_status)(f"{app_name} started minimized to the system tray.")
        return False
    host.frame.Show()
    if raise_window:
        host.frame.Raise()
    if focus is not None:
        wx.CallAfter(focus)
    return True


def append_windows_startup_items(
    host: Any,
    menu: Any,
    startup: Any,
    *,
    start_label: str,
    start_checked: bool,
    on_start: Callable[[bool], None],
) -> None:
    """Append "Start <app> with Windows" and "Start minimized when Windows starts".

    *startup* is the app's ``quill.platform.windows.<app>_startup`` module. The
    second row is disabled off Windows and in a portable copy, which must not
    leave anything behind on the computer it visits; its handler is the host's
    ``_set_start_minimized_at_windows_startup``.
    """
    import wx

    host._startup_item_id = wx.NewIdRef()
    menu.AppendCheckItem(host._startup_item_id, start_label)
    menu.Check(host._startup_item_id, start_checked)
    host.frame.Bind(wx.EVT_MENU, lambda e: on_start(e.IsChecked()), id=host._startup_item_id)
    host._startup_minimized_item_id = wx.NewIdRef()
    menu.AppendCheckItem(host._startup_minimized_item_id, START_MINIMIZED_LABEL)
    menu.Check(host._startup_minimized_item_id, startup.start_minimized_at_startup())
    menu.Enable(
        host._startup_minimized_item_id,
        startup.is_windows() and not startup.running_portable(),
    )
    host.frame.Bind(
        wx.EVT_MENU,
        lambda e: host._set_start_minimized_at_windows_startup(e.IsChecked()),
        id=host._startup_minimized_item_id,
    )


def editor_starts_hidden(frame: Any, start_minimized: bool) -> bool:
    """QUILL's first show from a ``--tray`` login launch: hidden, with a tray icon.

    Only when the tray is on and its icon really exists -- a hidden window with
    no icon would leave no way back. Runs what a visible first show runs
    (startup is over; the deferred startup tasks are queued) and returns True;
    otherwise does nothing and returns False, and the caller shows the window.
    """
    if not (start_minimized and frame.settings.tray_enabled and sys.platform == "win32"):
        return False
    frame._ensure_tray_icon()
    if frame._tray_icon is None:
        return False
    frame.frame.Hide()
    frame._set_status("QUILL started minimized to the system tray")
    frame.starting_up = False
    if not frame._startup_deferred_ran:
        frame._startup_deferred_ran = True
        frame._wx.CallAfter(frame._run_deferred_startup_tasks)
    return True


def apply_editor_startup(settings: Any) -> None:
    """Write QUILL's Run-key entry and its start-minimized choice from *settings*."""
    from quill.platform.windows.startup import set_launch_at_startup
    from quill.platform.windows.startup_options import set_start_minimized

    minimized = bool(settings.start_minimized_at_windows_startup)
    set_start_minimized("quill", minimized)
    set_launch_at_startup(settings.launch_at_windows_startup, start_minimized=minimized)
