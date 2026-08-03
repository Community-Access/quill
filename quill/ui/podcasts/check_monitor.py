"""The background podcast new-episode check, under the shared monitor policy.

Podcast feeds only ever refreshed when asked. That is a perfectly
defensible default -- and a poor one for somebody who subscribes to a dozen
shows and would like to be told, rather than to go and look. What was missing
was not the refresh (``refresh_podcast_feed`` already existed) but a *policy*:
a cadence you choose, a way to hear that the check is alive, and a say in
whether the answer interrupts you.

This is the podcast half of the ambient-monitor triple defined in
:mod:`quill.core.monitor_policy`. All three controls come from that one shared
resolver, so "check every 30 minutes, tick audibly, don't interrupt" means
exactly the same thing here as it does for watched folders.

Everything is off until asked for: with ``podcast_check_enabled`` false (the
default) the timer never starts and this class costs one object.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import wx

from quill.core.monitor_policy import MONITOR_PODCASTS, MonitorPolicy, resolve_monitor_policy

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._settings_provider = settings_provider
        self._library_provider = library_provider
        self._refresh_show = refresh_show
        self._safe_mode = safe_mode
        self._post_tick = post_tick
        self._policy = resolve_monitor_policy(self._settings(), MONITOR_PODCASTS)
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

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
        return bool(getattr(self._settings(), "podcast_check_enabled", False))

    # -- lifecycle ------------------------------------------------------

    def apply(self) -> bool:
        """Re-read settings and start or stop the timer. Returns whether it runs.

        Called at startup and again whenever settings change, so turning the
        check on or retuning its cadence takes effect without a restart.
        """
        self._policy = resolve_monitor_policy(self._settings(), MONITOR_PODCASTS)
        self.stop()
        if not self._enabled():
            return False
        self._timer.Start(self._policy.poll_interval_ms)
        return True

    def stop(self) -> None:
        if self._timer.IsRunning():
            self._timer.Stop()

    def _on_timer(self, event: Any) -> None:
        # One wx.Timer per frame shares EVT_TIMER with every other timer bound
        # to the same parent, so identity has to be checked before acting.
        if event.GetId() != self._timer.GetId():
            event.Skip()
            return
        self.check_now()

    # -- the check ------------------------------------------------------

    def check_now(self) -> int:
        """Refresh every eligible subscribed feed once. Returns how many ran.

        The tick fires first and unconditionally (when enabled): it announces
        that a *check happened*, which is exactly the information silence
        cannot carry. Whether that check found anything is a separate message,
        delivered by the refresh itself at the policy's severity.
        """
        if not self._enabled():
            return 0
        self._tick()
        library = self._library_provider()
        started = 0
        for show in list(getattr(library, "shows", []) or []):
            if getattr(show, "paused", False) or not getattr(show, "feed_url", ""):
                continue
            try:
                self._refresh_show(str(show.id))
            except Exception:  # noqa: BLE001 - one bad feed never stops the rest
                logger.exception("Podcast background check failed for show %s", show.id)
                continue
            started += 1
        return started

    def _tick(self) -> None:
        """Post the heartbeat earcon for one check, when the user asked for it."""
        event = self._policy.tick_sound_event
        if not event:
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
