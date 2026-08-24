"""The timer that makes a reminder go off (6.4, 7.5, 7.6).

One ``wx.Timer``, thirty seconds apart, reading a small local file. That is the
whole mechanism, and the cheapness is deliberate: a reminder that needs a
background service is a reminder that stops working the day the service does.

Four decisions live here rather than in the store, because each needs a UI:

* **Quiet hours can hold it**, and a reminder has two ways through. The
  standing one is quiet hours' own "let reminders through" switch, set once for
  all of them. The per-reminder one is the priority chosen when it was made.
  Either is enough: requiring both would make the per-reminder choice do
  nothing for anybody who had not already turned the standing switch on, which
  is precisely the case it exists for.
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

    def __init__(self, parent: Any, *, announce: Any, wx: Any = None, host: Any = None) -> None:
        if wx is None:
            import wx as wx_module

            wx = wx_module
        self._wx = wx
        self._announce = announce
        #: The app, for the toast's Go There. Optional: a monitor built with
        #: no host still speaks, which is what the tests and any headless
        #: caller need.
        self._host = host
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
            # The earcon first, then the words (7.4). A reminder is the one
            # thing here that arrives because somebody asked to be interrupted
            # at a moment they chose, so it announces itself as a reminder
            # before it says which -- and a listener who recognises the sound
            # has already turned their attention by the time the sentence
            # starts.
            self._cue()
            said = reminders.announcement(reminder, now)
            self._announce(said)
            self._toast(reminder, said)
            reminders.mark_fired(data_dir, reminder.reminder_id, now=now)
            spoken += 1
        return spoken

    def _cue(self) -> None:
        """The reminder earcon, when this app has a sound stack and it is on.

        Two switches, and both are honoured: ``post_cue`` already goes through
        the global per-event disable list, and ``reminder_sound`` is the app's
        own (7.8). Separate on purpose -- somebody who has turned most earcons
        off has probably not meant to turn off the one sound they asked to be
        interrupted by, so the reminder gets its own answer rather than
        inheriting the general one.
        """
        history = getattr(self._host, "_radio_history", None)
        if history is not None and not getattr(history, "reminder_sound", True):
            return
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.RADIO_REMINDER)

    def _toast(self, reminder: Any, said: str) -> None:
        """A desktop notice with a way back to the thing (list.md 7.6).

        Spoken *and* shown: the speech is the reminder, and the toast is what
        is still there thirty seconds later for somebody who was mid-sentence
        with a screen reader when it arrived. Its button opens whatever the
        reminder is about, so acting on it costs nothing but the press --
        where before, the only route was to open Upcoming and find the row.

        Best-effort throughout. A platform that draws no toast, or no button
        on one, has still had the reminder spoken.
        """
        host = self._host
        if host is None:
            return
        from quill.ui.toast import show_toast

        show_toast(
            "Quill Radio",
            said,
            parent=getattr(host, "frame", None),
            action_label="Go There",
            on_action=lambda: self._go_there(reminder),
            keep=True,
        )

    def _go_there(self, reminder: Any) -> None:
        """Open what the reminder was about, and say what happened either way.

        Routed through the Upcoming window's opener rather than a second copy
        of it: "where does this kind of reminder lead?" is one question, and
        two answers would drift the first time a kind was added.
        """
        from quill.ui.radio.upcoming_dialog import open_target

        try:
            self._announce(open_target(self._host, reminder))
        except Exception:  # noqa: BLE001 - a press must never crash the app
            self._announce("That could not be opened.")

    def _held_back(self, reminder: Any) -> bool:
        """Whether quiet hours should keep this one back for now.

        The reminder's own priority is part of the question (7.3): a
        high-priority one gets through on its own, without the standing
        let-reminders-through switch having been set.
        """
        from quill.core.quiet_hours import Kind
        from quill.core.radio.reminders import PRIORITY_HIGH
        from quill.ui.quiet_hours_ui import held_back

        try:
            urgent = getattr(reminder, "priority", "") == PRIORITY_HIGH
            return bool(held_back(Kind.REMINDER, high_priority=urgent))
        except Exception:  # noqa: BLE001 - an unreadable quiet window speaks
            return False


def install(app: Any, wx: Any) -> ReminderMonitor:
    """Build the monitor, start it, and check once at launch.

    The launch check is why a reminder missed while the app was closed is not
    lost: it is deferred, like every other launch task, so it never delays the
    window appearing.
    """
    monitor = ReminderMonitor(app.frame, announce=app._announce, wx=wx, host=app)
    monitor.start()
    wx.CallAfter(monitor.check_now)
    return monitor


__all__ = ["TICK_MS", "ReminderMonitor", "install"]
