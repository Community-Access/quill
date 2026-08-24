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

from collections.abc import Callable
from typing import Any


def show_toast(
    title: str,
    body: str,
    *,
    parent: Any = None,
    icon: Any = None,
    action_label: str = "",
    on_action: Callable[[], None] | None = None,
    keep: bool = False,
) -> Any:
    """Show an OS notification. Returns the message, or ``None`` if not shown.

    Best-effort by contract: every failure path answers ``None`` rather than
    raising, so a caller can report the outcome without wrapping the call. The
    return value is truthy on success, so an existing ``if show_toast(...)``
    reads the same as it did when this returned a bool.

    **An action turns news into a way back** (list.md 7.6). ``action_label``
    and ``on_action`` add a button to the toast -- "Go There" on a reminder --
    so somebody hearing it can act on it without hunting for the window that
    owns it. Not every platform draws one; where it is not drawn the toast is
    still shown and still says what happened, which is why the action is an
    addition to the words rather than a replacement for them.

    ``keep`` is the caller promising to hold a reference. A toast with an
    action must outlive this call or its handler is collected before anybody
    can press the button -- and a toast *without* one need not, so the default
    stays cheap.
    """
    if not str(title).strip() and not str(body).strip():
        return None
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
        if action_label and on_action is not None:
            _add_action(note, wx, action_label, on_action)
        note.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    except Exception:  # noqa: BLE001 - news that cannot be shown is not a crash
        return None
    if keep:
        _LIVE.append(note)
        del _LIVE[:-_KEEP_AT_MOST]
    return note


#: Toasts with an action, held so their handlers outlive the call that made
#: them. Bounded, because a list that only grows is a leak with a good excuse:
#: a handful is more than anybody has on screen, and the oldest is the one
#: least likely to still be waiting for a press.
_LIVE: list[Any] = []
_KEEP_AT_MOST = 8


def _add_action(note: Any, wx: Any, label: str, handler: Callable[[], None]) -> None:
    """Attach one button, where the platform draws one.

    Silent when it cannot: ``AddAction`` is not implemented everywhere, and a
    notification that failed to grow a button is still a notification. The
    handler is wrapped so a failing action reports nothing rather than raising
    inside a wx event -- there is no caller left to tell.
    """
    try:
        if not note.AddAction(wx.ID_ANY, label):
            return
    except Exception:  # noqa: BLE001 - unimplemented on this platform
        return

    def _fire(_event: Any) -> None:
        try:
            handler()
        except Exception:  # noqa: BLE001 - nothing left to report it to
            return

    try:
        note.Bind(wx.adv.EVT_NOTIFICATION_MESSAGE_ACTION, _fire)
    except Exception:  # noqa: BLE001 - a button nobody can bind is no button
        return


__all__ = ["show_toast"]
