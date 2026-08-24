"""Quill Radio checking its subscribed feeds on its own.

Radio has carried the Subscriptions branch, the unheard badges and the shared
library for a while, and it refreshed a feed only when you opened that show.
Which meant the badge on a show you had not opened was as old as the last time
you opened it, and "what is new?" could only be answered by walking the tree
and opening everything.

So Radio gets the check QUILL and Quill Cast already had -- the same shape, the
same shared library, the same per-show pause -- rather than a second, subtly
different idea of what refreshing means:

* **The cadence is the listener's**, from Preferences, and *Manually only* is
  one of its answers rather than the absence of one
  (:mod:`quill.core.podcasts.refresh_policy`).
* **A paused show is skipped**, and Refresh on its own row checks it anyway.
* **It reads the episode list and nothing else.** No download is started, no
  episode is routed, nothing is queued: those are Quill Cast's jobs, and a
  background check in Radio that quietly did them would be Radio making
  decisions in Cast's library.
* **It says what it found, once, at the end** -- counted and named, not one
  announcement per feed. A check that talks nine times has stopped being
  information.
* **Never on the UI thread**, and never at launch unless asked: a launch that
  spends four seconds on feeds is a launch a screen-reader user spends waiting.

Off by default. An app that starts reaching the network on a schedule nobody
chose is an app spending somebody else's data allowance.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.core.podcasts import refresh_policy

logger = logging.getLogger(__name__)

#: The timer never fires faster than this, whatever the interval says. A
#: guard against a stored value that survived a units change.
_MIN_TICK_MS = 60_000


class PodcastRefreshMonitor:
    """Runs the subscribed-feed check on Radio's own cadence."""

    def __init__(
        self,
        parent: Any,
        *,
        history_provider: Any,
        announce: Any,
        task_manager: Any,
        safe_mode: bool = False,
        wx: Any = None,
    ) -> None:
        if wx is None:
            import wx as wx_module

            wx = wx_module
        self._wx = wx
        self._history_provider = history_provider
        self._announce = announce
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._running = False
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

    # -- policy ---------------------------------------------------------------

    def _settings(self) -> Any:
        """The shared podcast settings, or ``None`` when there is no library yet.

        Read fresh every time rather than cached at construction: Preferences
        writes the library, and a monitor holding a stale copy would keep the
        old cadence until the next restart.
        """
        try:
            return self._history_provider()
        except Exception:  # noqa: BLE001 - a missing library is not an error
            return None

    def _interval_minutes(self) -> int:
        return refresh_policy.normalize_interval(getattr(self._settings(), "refresh_minutes", 0))

    def _on_launch(self) -> bool:
        return bool(getattr(self._settings(), "refresh_on_launch", False))

    def describe(self) -> str:
        """The policy as one sentence, for Preferences and the status readout."""
        if self._safe_mode:
            return "Subscribed feeds are not checked in Safe Mode."
        return refresh_policy.describe_schedule(
            self._interval_minutes(), on_launch=self._on_launch()
        )

    # -- lifecycle ------------------------------------------------------------

    def apply(self) -> bool:
        """Re-read the settings and start or stop the timer. Returns whether it runs.

        Called at startup and again whenever Preferences is saved, so changing
        the cadence takes effect without a restart.
        """
        self.stop()
        if self._safe_mode:
            return False
        minutes = self._interval_minutes()
        if not minutes:
            return False
        self._timer.Start(max(_MIN_TICK_MS, minutes * 60_000))
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False
        try:
            if self._timer.IsRunning():
                self._timer.Stop()
        except Exception:  # noqa: BLE001 - a dying timer must not crash shutdown
            return

    def start_if_asked_at_launch(self) -> bool:
        """Run one check now, if the listener asked for one at launch.

        Deferred by the caller (``wx.CallAfter``), and quiet when it finds
        nothing: a launch is not the moment to be told that nothing happened.
        """
        if self._safe_mode or not self._on_launch():
            return False
        self.check_now(announce_when_empty=False)
        return True

    def _on_timer(self, event: Any) -> None:
        # One wx.Timer per frame shares EVT_TIMER with every other timer bound
        # to the same parent, so identity has to be checked before acting.
        if event.GetId() != self._timer.GetId():
            event.Skip()
            return
        self.check_now(announce_when_empty=False)

    # -- the check ------------------------------------------------------------

    def check_now(self, *, announce_when_empty: bool = True, force: bool = False) -> bool:
        """Check every eligible feed once, off-thread. True when one started.

        *force* is the manual verb: it checks paused shows too, because
        somebody who pressed Refresh has said which shows they mean.
        """
        if self._safe_mode:
            self._announce("Subscribed feeds are not checked in Safe Mode.")
            return False
        if self._task_manager is None:
            return False

        def _work(**_kwargs: Any) -> list[tuple[str, int]]:
            return refresh_subscribed_feeds(force=force)

        def _ok(_op: str, result: object) -> None:
            found = list(result) if isinstance(result, list) else []
            if not found and not announce_when_empty:
                return
            # Quiet hours (11.9) hold back the *automatic* summary only. A
            # check somebody pressed a key for -- announce_when_empty, the
            # manual path -- always answers, because they asked.
            if not announce_when_empty:
                from quill.core.quiet_hours import Kind
                from quill.ui.quiet_hours_ui import held_back

                if held_back(Kind.NEW_EPISODE):
                    return
            self._announce(refresh_policy.summarise_check(found))

        def _failed(_op: str, error: BaseException) -> None:
            logger.exception("Podcast refresh failed", exc_info=error)
            # A failure is written down whether or not it is spoken (11.5):
            # a background check that broke at 3 a.m. is exactly the thing
            # Recent Problems exists to still have at breakfast.
            from quill.core import problem_log
            from quill.core.paths import app_data_dir

            problem_log.record_problem(
                app_data_dir(),
                problem_log.KIND_FEED,
                "Subscribed feeds",
                str(error) or error.__class__.__name__,
            )
            if announce_when_empty:
                self._announce(f"Subscribed feeds could not be checked. {error}.")

        self._task_manager.submit(
            "radio-podcast-refresh", _work, on_success=_ok, on_failure=_failed
        )
        return True


def refresh_subscribed_feeds(
    *, force: bool = False, safe_mode: bool = False
) -> list[tuple[str, int]]:
    """Fetch every eligible subscribed feed and fold it into the shared library.

    Returns ``(show title, new episode count)`` for every show checked, which
    is what the caller turns into one spoken sentence.

    The merge is exactly the one Radio already performs when you *open* a show
    (``browse_libraries._sync_subscribed_episodes``): ``merge_episodes`` keeps
    local state -- played, position, notes -- untouched, and the library is
    saved once at the end rather than once per feed. One bad feed never stops
    the rest: a show that will not load is a show reported as nothing new, and
    the next check tries it again.

    Runs on a worker thread. Nothing here touches wx.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import feed_auth, feed_reader
    from quill.core.podcasts.subscriptions import load_library, merge_episodes, save_library

    data_dir = app_data_dir()
    library = load_library(data_dir)
    found: list[tuple[str, int]] = []
    gained = 0
    for show in refresh_policy.shows_to_refresh(list(getattr(library, "shows", []) or [])):
        title = str(getattr(show, "title", "") or getattr(show, "feed_url", ""))
        try:
            username, password = feed_auth.auth_for_url(show, show.feed_url)
            info = feed_reader.fetch_and_parse_feed(
                show.feed_url, username=username, password=password, safe_mode=safe_mode
            )
            count = merge_episodes(show, info.episodes)
            if not info.tags.is_empty:
                show.tags = info.tags
        except Exception:  # noqa: BLE001 - one bad feed never stops the rest
            logger.exception("Podcast refresh failed for %s", title)
            continue
        gained += count
        found.append((title, count))
    if gained:
        save_library(data_dir, library)
    return found


__all__ = ["PodcastRefreshMonitor", "refresh_subscribed_feeds"]
