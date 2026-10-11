"""The background podcast new-episode check, under the shared monitor policy.

Podcast feeds only ever refreshed when asked. That is a perfectly
defensible default -- and a poor one for somebody who subscribes to a dozen
shows and would like to be told, rather than to go and look. What was missing
was not the refresh (``refresh_podcast_feed`` already existed) but a *policy*:
a cadence you choose, a way to hear that the check is alive, and a say in
whether the answer interrupts you.

This is the podcast half of the ambient-monitor triple defined in
:mod:`quill.core.monitor_policy`. The tick and interrupt legs come from that
one shared resolver, so "tick audibly, don't interrupt" means exactly the same
thing here as it does for watched folders.

**The cadence leg answers to** :mod:`quill.core.podcasts.refresh_policy`
instead, because that is the question Quill Radio also asks. Before this the
two apps clamped the same setting to different ranges and offered different
lists, so "every 12 hours" was a choice in one app and not the other, and a
value one app accepted the other quietly rewrote. One list, one normalisation,
one meaning for zero -- which is *manually only*, an answer rather than the
absence of one.

**And each app skips a check the other has just run.** The cadence is per app
by design (a single shared switch would mean turning the check on in Cast
turned it on in Radio, with no way to say "let Radio do it"), so the cost of
that rightness is two timers over one set of feeds. The shared
``PodcastLibrary.last_auto_check`` stamp settles it: whoever checks says when,
and the other stays quiet inside the same interval. Nobody configures this.

Everything is off until asked for: with ``podcast_check_enabled`` false (the
default) the timer never starts and this class costs one object.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from typing import Any

import wx

from quill.core.monitor_policy import MONITOR_PODCASTS, MonitorPolicy, resolve_monitor_policy
from quill.core.podcasts import refresh_policy

logger = logging.getLogger(__name__)

MAX_REFRESHES_IN_FLIGHT = 2
REFRESH_START_CADENCE_MS = 250


class PodcastCheckMonitor:
    """Runs the new-episode check on the user's chosen cadence.

    The check itself is delegated: this owns *when*, not *how*. ``refresh_show``
    is the shell's existing per-show refresh, which already handles safe mode,
    paused shows, feed authentication and the announcement of what it found.
    """

    def __init__(
        self,
        parent: Any,
        *,
        settings_provider: Callable[[], Any],
        library_provider: Callable[[], Any],
        refresh_show: Callable[[str], None],
        safe_mode: bool = False,
        post_tick: Callable[[str], None] | None = None,
        feature_enabled: Callable[[], bool] | None = None,
        on_refresh_error: Callable[[str, BaseException], None] | None = None,
        library_changed: Callable[[], None] | None = None,
    ) -> None:
        self._settings_provider = settings_provider
        self._library_provider = library_provider
        self._refresh_show = refresh_show
        self._safe_mode = safe_mode
        #: Asked on every enablement check so a Podcasts feature that is off --
        #: including a build where it is not released yet -- never polls feeds
        #: in the background, whatever the saved setting says. Omitted means
        #: "no feature gate" (the standalone apps).
        self._feature_enabled = feature_enabled
        self._on_refresh_error = on_refresh_error
        self._library_changed = library_changed
        self._post_tick = post_tick
        self._policy = resolve_monitor_policy(self._settings(), MONITOR_PODCASTS)
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._refresh_queue: deque[str] = deque()
        self._refreshes_in_flight: set[str] = set()
        self._refresh_pump: Any = None
        self._refresh_pump_pending = False

    @property
    def is_checking(self) -> bool:
        """Whether a feed sweep still has queued or in-flight work."""
        return bool(self._refresh_queue or self._refreshes_in_flight)

    # -- policy ---------------------------------------------------------

    def _settings(self) -> Any:
        try:
            return self._settings_provider()
        except Exception:  # noqa: BLE001 - a missing settings object is not an error
            return None

    @property
    def policy(self) -> MonitorPolicy:
        """The live triple: cadence, audible tick, interrupt preference."""
        return self._policy

    @property
    def interrupt_speech(self) -> bool:
        """Whether a result should cut across whatever is being spoken.

        The shell passes this straight to ``_announce(..., force=)``, which the
        announcement policy reads as ``WARNING`` rather than ``ROUTINE``.
        """
        return self._policy.interrupt_speech

    def describe(self) -> str:
        """The whole policy as one spoken sentence, for status and Preferences."""
        if not self._enabled():
            return "Podcast feeds are only checked when you ask."
        return self._policy.describe()

    def _enabled(self) -> bool:
        if self._safe_mode:
            return False
        if self._feature_enabled is not None and not self._feature_enabled():
            return False
        return bool(getattr(self._settings(), "podcast_check_enabled", False))

    def _manually_allowed(self) -> bool:
        """Whether a check somebody asked for may run. Safe Mode still says no."""
        if self._safe_mode:
            return False
        return self._feature_enabled is None or bool(self._feature_enabled())

    # -- lifecycle ------------------------------------------------------

    def interval_minutes(self) -> int:
        """The chosen cadence in minutes; 0 is "manually only".

        Normalised through :mod:`quill.core.podcasts.refresh_policy`, the same
        function Quill Radio uses, so both apps accept the same values and mean
        the same thing by them.
        """
        return refresh_policy.normalize_interval(
            getattr(self._settings(), "podcast_check_interval_minutes", 0)
        )

    def apply(self) -> bool:
        """Re-read settings and start or stop the timer. Returns whether it runs.

        Called at startup and again whenever settings change, so turning the
        check on or retuning its cadence takes effect without a restart.
        """
        self._policy = resolve_monitor_policy(self._settings(), MONITOR_PODCASTS)
        self.stop()
        if not self._enabled():
            return False
        minutes = self.interval_minutes()
        if not minutes:
            return False  # manually only -- an answer, not the absence of one
        self._timer.Start(minutes * 60_000)
        return True

    def stop(self) -> None:
        if self._timer.IsRunning():
            self._timer.Stop()

    def shutdown(self) -> None:
        """Stop scheduling feeds before the app tears down its worker pool."""
        self.stop()
        self._refresh_queue.clear()
        self._refreshes_in_flight.clear()
        pump = self._refresh_pump
        self._refresh_pump = None
        self._refresh_pump_pending = False
        if pump is not None:
            pump.Stop()

    def refresh_completed(self, show_id: str) -> None:
        """Release one slot after the feed's UI-side merge has completed."""
        if show_id not in self._refreshes_in_flight:
            return
        self._refreshes_in_flight.remove(show_id)
        if self._refresh_queue:
            self._schedule_refresh_pump(REFRESH_START_CADENCE_MS)

    def cancel_queued(self) -> list[str]:
        """Drop feeds not yet started; in-flight requests are allowed to finish."""
        cancelled = list(self._refresh_queue)
        self._refresh_queue.clear()
        pump = self._refresh_pump
        self._refresh_pump = None
        self._refresh_pump_pending = False
        if pump is not None:
            pump.Stop()
        return cancelled

    def cancel_all(self) -> list[str]:
        """Release this sweep immediately; its host suppresses old worker delivery."""
        cancelled = self.cancel_queued()
        cancelled.extend(self._refreshes_in_flight)
        self._refreshes_in_flight.clear()
        return cancelled

    def _schedule_refresh_pump(self, delay_ms: int = 0) -> None:
        if self._refresh_pump_pending or not self._refresh_queue:
            return
        if len(self._refreshes_in_flight) >= MAX_REFRESHES_IN_FLIGHT:
            return
        self._refresh_pump_pending = True
        if delay_ms:
            self._refresh_pump = wx.CallLater(delay_ms, self._pump_refresh_queue)
        else:
            wx.CallAfter(self._pump_refresh_queue)

    def _pump_refresh_queue(self, *, schedule_next: bool = True) -> None:
        self._refresh_pump = None
        self._refresh_pump_pending = False
        if not self._refresh_queue or len(self._refreshes_in_flight) >= MAX_REFRESHES_IN_FLIGHT:
            return

        show_id = self._refresh_queue.popleft()
        self._refreshes_in_flight.add(show_id)
        try:
            self._refresh_show(show_id)
        except Exception as error:  # noqa: BLE001 - one failed submission cannot strand the sweep
            logger.exception("Podcast background check could not start for show %s", show_id)
            self._refreshes_in_flight.discard(show_id)
            if self._on_refresh_error is not None:
                self._on_refresh_error(show_id, error)
            if self._refresh_queue:
                self._schedule_refresh_pump(REFRESH_START_CADENCE_MS)
            return

        if (
            schedule_next
            and self._refresh_queue
            and len(self._refreshes_in_flight) < MAX_REFRESHES_IN_FLIGHT
        ):
            self._schedule_refresh_pump(REFRESH_START_CADENCE_MS)

    def _on_timer(self, event: Any) -> None:
        # One wx.Timer per frame shares EVT_TIMER with every other timer bound
        # to the same parent, so identity has to be checked before acting.
        if event.GetId() != self._timer.GetId():
            event.Skip()
            return
        if self.check_now(defer_start=True):
            wx.CallAfter(self.start_queued)

    # -- the check ------------------------------------------------------

    def check_now(
        self,
        *,
        force: bool = False,
        defer_start: bool = False,
        show_ids: set[str] | None = None,
    ) -> int:
        """Queue every eligible feed once. Returns how many will be checked.

        The tick fires first (when enabled and when the check is actually
        going to run): it announces that a *check happened*, which is exactly
        the information silence cannot carry. Whether that check found
        anything is a separate message, delivered by the refresh itself at the
        policy's severity.

        *force* is the manual verb, which never defers to the other app's
        stamp and never skips a paused show: somebody who pressed Refresh has
        said which shows they mean.
        """
        # *force* passes the switch, but never Safe Mode or a disabled
        # feature. "Check the feeds now" is a thing somebody asked for; the
        # automatic-check switch answers a different question -- whether to
        # check without being asked -- and leaving it off, which is the
        # default, must not disable the manual verb too.
        if not self._enabled() and not (force and self._manually_allowed()):
            return 0
        library = self._library_provider()
        if not force and not self._claim_this_round(library):
            return 0  # the other app checked inside this interval
        self._tick()
        #: The shows this round started, for a run a person asked for (check_run).
        self.last_started_ids: list[str] = []
        scheduled = set(self._refresh_queue) | self._refreshes_in_flight
        for show in list(getattr(library, "shows", []) or []):
            if str(show.id) in scheduled:
                continue
            if show_ids is not None and str(show.id) not in show_ids:
                continue
            if not refresh_policy.can_refresh(show):
                continue
            if not force and refresh_policy.is_paused(show):
                continue
            # Each podcast's own cadence (7.1). A shared interval over a
            # three-hundred-podcast library is either wasteful or late: this
            # timer is the *heartbeat*, and every show decides for itself
            # whether its own hour has elapsed. A show with no cadence of its
            # own inherits the shared one and behaves exactly as before.
            if not force and not self._show_is_due(library, show):
                continue
            self.last_started_ids.append(str(show.id))
            scheduled.add(str(show.id))
        self._refresh_queue.extend(self.last_started_ids)
        if not defer_start:
            self.start_queued()
        return len(self.last_started_ids)

    def start_queued(self) -> None:
        """Start only the first small batch; the remaining feeds are paced."""
        self._pump_refresh_queue()

    def _show_is_due(self, library: Any, show: Any) -> bool:
        """Whether this one podcast's own interval has elapsed.

        Guarded: a library shape this monitor cannot read must not stop the
        check, so anything unexpected answers "yes, check it" -- the same
        direction every other doubt in this feature resolves.
        """
        try:
            from quill.core.podcasts.check_state import is_due
            from quill.core.podcasts.show_policy import cadence_minutes

            if cadence_minutes(library, show) <= 0:
                # No cadence of its own and none shared: the timer only got
                # here because *something* is due, so this show rides along.
                return self.interval_minutes() > 0
            return is_due(library, show)
        except Exception:  # noqa: BLE001 - never let bookkeeping stop a check
            logger.exception(
                "could not read the check cadence for show %s", getattr(show, "id", "")
            )
            return True

    def _claim_this_round(self, library: Any) -> bool:
        """Whether this app should do this round of checking, and claim it.

        Reads the shared stamp, and writes it before doing any work rather
        than after: two apps whose timers fire in the same second must not
        both decide they are the one, and the fetch takes seconds during which
        the other would otherwise still see the old stamp.
        """
        import time

        now = time.time()
        if not refresh_policy.is_due(
            getattr(library, "last_auto_check", ""), self.interval_minutes(), now
        ):
            return False
        if self._library_changed is None:
            raise RuntimeError("The podcast monitor has no asynchronous persistence callback")
        previous = library.last_auto_check
        library.last_auto_check = refresh_policy.stamp_now(now)
        try:
            self._library_changed()
        except Exception:
            library.last_auto_check = previous
            raise
        return True

    def _tick(self) -> None:
        """Post the heartbeat earcon for one check, when the user asked for it."""
        event = self._policy.tick_sound_event
        if not event:
            return
        # Quiet hours (11.9): the check still runs -- feeds are still read and
        # downloads still start -- but the heartbeat that says so stays silent
        # between the listener's chosen hours.
        from quill.ui.quiet_hours_ui import should_tick

        if not should_tick():
            return
        poster = self._post_tick
        if poster is None:
            from quill.ui.sound_manager import post_sound

            poster = post_sound
        try:
            poster(event)
        except Exception:  # noqa: BLE001 - a silent earcon must never stop a check
            logger.exception("Podcast monitor tick failed")


__all__ = ["PodcastCheckMonitor"]
