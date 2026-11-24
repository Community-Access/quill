"""Beacon's automatic sync keeps maintenance away from the moment that matters (FUX-15).

Auto-sync (off by default, PRD 45.10) backs up the store and syncs on a timer.
It used to say "Auto-synced. Pushed 0, pulled 0." at every interval, refresh
the list being read even when nothing had changed, and run under an open
dialog. Now:

* a tick is skipped while a modal dialog or a menu is open over the window
  (the next tick tries again);
* a sync that brought nothing here is written on the status bar when it sent
  something, and otherwise leaves the bar alone -- never spoken;
* a sync that brought something refreshes the list without announcing the
  count or moving the details pane, keeps the selected bookmark selected
  wherever it now is, and then says what arrived once;
* a failure and conflicts are said, as before.
"""

from __future__ import annotations

import sys
from typing import Any

import wx

from quill.core.sound_events import SoundEvent

__all__ = ["modal_open", "refresh_keeping_place", "tick"]


def modal_open(frame: Any) -> bool:
    """Whether a modal dialog or a menu is open over *frame*.

    Windows disables the owner of any modal dialog, including the system ones
    (a message box, a file picker) that ``wx.GetTopLevelWindows`` never lists,
    and a popup or menu-bar menu runs its own loop that a timer still fires in.
    """
    try:
        if any(
            isinstance(window, wx.Dialog) and window.IsModal() for window in wx.GetTopLevelWindows()
        ):
            return True
        if sys.platform != "win32":
            return False
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.IsWindowEnabled(frame.GetHandle()):
            return True
        info = (ctypes.c_uint32 * 18)()  # GUITHREADINFO: cbSize, flags, ...
        info[0] = ctypes.sizeof(info)
        thread = ctypes.windll.kernel32.GetCurrentThreadId()  # type: ignore[attr-defined]
        if user32.GetGUIThreadInfo(thread, info):
            return bool(info[1] & 0x14)  # GUI_INMENUMODE | GUI_POPUPMENUMODE
        return False
    except Exception:  # noqa: BLE001 - no answer: nothing in the way
        return False


def refresh_keeping_place(frame: Any) -> None:
    """Refresh the results without moving the reader: the bookmark that was
    selected stays selected, wherever it now is."""
    current = frame._selected_beacon()
    before = frame.results.GetFirstSelected()
    frame._refresh_results(quiet=True)
    keep = getattr(current, "beacon_id", None)
    if keep is None:
        return
    for index, beacon in enumerate(frame._results_cache):
        if getattr(beacon, "beacon_id", None) == keep:
            if index != before:
                if before >= 0:
                    frame.results.Select(before, on=False)
                frame.results.Select(index)
                frame.results.Focus(index)
            return


def tick(frame: Any) -> None:
    """One auto-sync timer tick on Beacon's main window."""
    if not frame.sync.config.is_configured() or not frame.sync.is_unlocked():
        return  # not ready; leave the timer running for when it is
    if modal_open(frame):
        return  # the backup and sync would change what the dialog shows
    res = frame.sync.sync_now()
    if "error" in res:
        frame.announcer.say(f"Auto-sync failed: {res['error']}", "minimal")
        return
    pushed, pulled = res.get("pushed", 0), res.get("pulled", 0)
    conflicts = res.get("conflicts") or []
    msg = f"Auto-synced. Pushed {pushed}, pulled {pulled}."
    if conflicts:
        msg += f" {len(conflicts)} conflict(s) need review."
    if not pulled and not conflicts:
        if pushed:
            frame.SetStatusText(msg)
        return
    refresh_keeping_place(frame)
    frame.announcer.say(msg, "minimal", sound=SoundEvent.BEACON_SYNC_COMPLETE)
