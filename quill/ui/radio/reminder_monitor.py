"""The timer that makes a reminder go off (6.4, 7.5, 7.6).

One ``wx.Timer``, thirty seconds apart, reading a small local file. That is the
whole mechanism, and the cheapness is deliberate: a reminder that needs a
background service is a reminder that stops working the day the service does.

Four decisions live here rather than in the store, because each needs a UI:

* **Quiet hours can hold it.** Reminders go through as the ``reminder`` kind,
  which the listener can let through explicitly -- the switch quiet hours
  already carries. A *high priority* reminder needs both: the priority and the
  let-reminders-through switch. One switch is a preference; two agreeing is a
  decision, and nothing in this app should be able to wake somebody on the
  strength of a dropdown they set once.
* **Held back is not lost.** A reminder quiet hours withholds is *not* marked
  fired -- it stays due, and the Upcoming window shows it as waiting. Marking
  it done would be the app deciding that the quiet window ended the reminder.
* **It fires once**, because marking fired is what the store is for.
* **A missed one still speaks**, within the store's grace window -- an app
  closed at 6:55 says what it missed when it opens.

The check runs at launch too, deferred, for that last reason.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: How often to look. Thirty seconds: a reminder is not a stopwatch, and the
#: worst error this can produce -- half a minute late -- is one nobody notices.
TICK_MS = 30_000


class ReminderMonitor:
    """Fires reminders as they come due, and stops when the frame goes."""

    def __init__(self, parent: Any, *, announce: Any, wx: Any = None) -> None:
        if wx is None:
            import wx as wx_module

            wx = wx_module
        self._wx = wx
        self._announce = announce
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

    def start(self) -> None:
        self._timer.Start(TICK_MS)

    def stop(self) -> None:
        try:
            if self._timer.IsRunning():
                self._timer.Stop()
        except Exception:  # noqa: BLE001 - a dying timer must not crash shutdown
            return

    def _on_timer(self, event: Any) -> None:
        # One frame's EVT_TIMER is shared by every timer bound to it, so
        # identity has to be checked before acting on a tick.
        if event.GetId() != self._timer.GetId():
            event.Skip()
            return
        self.check_now()

    def check_now(self, *, now: datetime | None = None) -> int:
        """Announce everything due. Returns how many were announced.

        Reads the file on every tick rather than caching it: reminders are set
        from another window, and a monitor holding a stale list would miss the
        one just added.
        """
        moment = now or datetime.now(UTC)
        try:
            fired = self._fire(moment)
        except Exception:  # noqa: BLE001 - a reminder must never take the app down
            logger.exception("reminder check failed")
            return 0
        return fired

    def _fire(self, now: datetime) -> int:
        from quill.core.paths import app_data_dir
        from quill.core.radio import reminders

        data_dir = app_data_dir()
        due = reminders.due_now(reminders.load_reminders(data_dir), now)
        if not due:
            return 0
        spoken = 0
        for reminder in due:
            if self._held_back(reminder):
                # Held, not done: the quiet window did not end the reminder,
                # and the Upcoming window still shows it waiting.
                continue
            self._announce(reminders.announcement(reminder, now))
            reminders.mark_fired(data_dir, reminder.reminder_id, now=now)
            spoken += 1
        return spoken

    def _held_back(self, reminder: Any) -> bool:
        """Whether quiet hours should keep this one back for now."""
        from quill.core.quiet_hours import Kind
        from quill.ui.quiet_hours_ui import held_back

        try:
            return bool(held_back(Kind.REMINDER))
        except Exception:  # noqa: BLE001 - an unreadable quiet window speaks
            return False


def install(app: Any, wx: Any) -> ReminderMonitor:
    """Build the monitor, start it, and check once at launch.

    The launch check is why a reminder missed while the app was closed is not
    lost: it is deferred, like every other launch task, so it never delays the
    window appearing.
    """
    monitor = ReminderMonitor(app.frame, announce=app._announce, wx=wx)
    monitor.start()
    wx.CallAfter(monitor.check_now)
    return monitor


__all__ = ["TICK_MS", "ReminderMonitor", "install"]
