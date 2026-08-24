"""One desktop notification, built one way.

``wx.adv.NotificationMessage`` had grown two hand-written copies before this
(the weather alert toast in the editor and the one in the standalone Quill
Weather), differing only in whether they passed a parent -- which is the same
shape ``core/file_manager.py`` exists to prevent, and for the same reason: two
copies is where the third one goes wrong, and QUILL Cast's finished-download
notice was going to be the third.

The standalone Quill Weather call site keeps its own throwaway ``wx.App`` and
pump around this, deliberately: a headless check has no window and no loop, and
that is a fact about *that* caller rather than about notifications.

What has to be right every time, and is easy to get wrong once:

* **A toast failure is never the caller's problem.** Notifications can be off
  at the OS level, missing on a platform, or refused by a policy. A download
  that finished must not fail because the news about it could not be shown.
* **The parent matters when there is one.** wxMSW associates the toast with
  the window, which is what lets a screen reader place it and what stops it
  outliving the app; a parentless toast is the fallback, not the default.
* **Flags are cosmetic.** An icon a platform will not render is not a reason
  to skip the notification.

This is the transport only -- *whether* to show anything is the caller's, and
for anything ambient that means going through quiet hours first
(:mod:`quill.ui.quiet_hours_ui`). A toast is not exempt from being unwanted at
three in the morning; it is the most literal form of it.
"""

from __future__ import annotations

from typing import Any


def show_toast(title: str, body: str, *, parent: Any = None, icon: Any = None) -> bool:
    """Show an OS notification. Returns whether it was actually shown.

    Best-effort by contract: every failure path answers ``False`` rather than
    raising, so a caller can report the outcome without wrapping the call.
    """
    if not str(title).strip() and not str(body).strip():
        return False
    try:
        import wx
        import wx.adv

        note = (
            wx.adv.NotificationMessage(title, body, parent)
            if parent is not None
            else wx.adv.NotificationMessage(title, body)
        )
        if icon is not None:
            try:
                note.SetFlags(icon)
            except Exception:  # noqa: BLE001 - an icon is not the message
                pass
        note.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    except Exception:  # noqa: BLE001 - news that cannot be shown is not a crash
        return False
    return True


__all__ = ["show_toast"]
