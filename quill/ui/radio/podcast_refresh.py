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
from typing import Any, NamedTuple

from quill.core.podcasts import episode_alerts, refresh_policy

logger = logging.getLogger(__name__)

#: The timer never fires faster than this, whatever the interval says. A
#: guard against a stored value that survived a units change.
_MIN_TICK_MS = 60_000


def _load_shared_library() -> Any:
    """The shared podcast library, loaded fresh.

    The monitor's default library provider. Fresh rather than cached for the
    same reason the history is: QUILL Cast may have changed the cadence since
    this app started, and the whole point of moving these settings into the
    library was that both apps see one value.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library

    return load_library(app_data_dir())


class FeedCheck(NamedTuple):
    """What one checked feed came back with.

    A named row rather than a bare tuple: this grew from (title, count) to
    carry the alert mode and the show id in 3.1.0, and position is not a
    readable way to say which of four strings is which.

    *alert* is resolved on the worker, so the UI thread never re-walks the
    settings chain per show; *show_id* is what a notification opens.
    """

    title: str
    new_count: int
    alert: str
    show_id: str


class PodcastRefreshMonitor:
    """Runs the subscribed-feed check on Radio's own cadence."""

    def __init__(
        self,
        parent: Any,
        *,
        history_provider: Any,
        announce: Any,
        library_provider: Any = None,
        task_manager: Any,
        safe_mode: bool = False,
        wx: Any = None,
    ) -> None:
        if wx is None:
            import wx as wx_module

            wx = wx_module
        self._wx = wx
        self._history_provider = history_provider
        #: The shared podcast library, for the cadence and the alert modes
        #: both apps read (3.1.0). Injectable for the same reason
        #: history_provider is: a monitor whose settings come off disk is a
        #: monitor no test can pin down.
        self._library_provider = library_provider or _load_shared_library
        self._announce = announce
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._running = False
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

    # -- policy ---------------------------------------------------------------

    def _settings(self) -> Any:
        """Radio's own history record, or ``None`` before there is one.

        Read fresh every time rather than cached at construction: Preferences
        writes the record, and a monitor holding a stale copy would keep the
        old cadence until the next restart.

        Radio's own record still decides **whether this app** runs the check
        (on_launch, and the pre-3.1.0 cadence this migrates). *How often* and
        *what to say* moved to the shared library settings in 3.1.0, because
        those are facts about the podcasts rather than about which app is
        open -- and keeping them here meant turning the check on in Cast did
        nothing in Radio.
        """
        try:
            return self._history_provider()
        except Exception:  # noqa: BLE001 - a missing record is not an error
            return None

    def _interval_minutes(self) -> int:
        """Minutes between automatic checks -- the value BOTH apps read.

        The shared library setting is the answer. Radio's own
        ``podcast_refresh_minutes`` is honoured as a migration: somebody who
        chose a cadence in Radio before 3.1.0 keeps it, and it is copied into
        the shared setting the first time this runs, so the two agree from
        then on rather than drifting the way they had been.
        """
        shared = self._shared_interval()
        if shared > 0:
            return shared
        return refresh_policy.normalize_interval(
            getattr(self._settings(), "podcast_refresh_minutes", 0)
        )

    def _shared_interval(self) -> int:
        """The library-wide cadence, or 0. Never raises."""
        try:
            library = self._library_provider()
            return episode_alerts.interval_for_show(library.settings)
        except Exception:  # noqa: BLE001 - unreadable settings means 0
            return 0

    def _adopt_shared_interval(self, minutes: int) -> None:
        """Copy a pre-3.1.0 Radio cadence into the shared setting, once."""
        try:
            from quill.core.paths import app_data_dir
            from quill.core.podcasts.subscriptions import load_library, save_library

            data_dir = app_data_dir()
            library = load_library(data_dir)
            if episode_alerts.interval_for_show(library.settings) > 0:
                return  # somebody already set the shared one; leave it alone
            library.settings.check_interval_minutes = minutes
            save_library(data_dir, library)
        except Exception:  # noqa: BLE001 - a migration is never worth a launch
            logger.debug("Could not adopt the Radio cadence", exc_info=True)

    def _on_launch(self) -> bool:
        return bool(getattr(self._settings(), "podcast_refresh_on_launch", False))

    def describe(self) -> str:
        """The policy as one sentence, for Preferences and the status readout."""
        if self._safe_mode:
            return "Subscribed feeds are not checked in Safe Mode."
        return refresh_policy.describe_schedule(
            self._interval_minutes(), on_launch=self._on_launch()
        )

    # -- lifecycle ------------------------------------------------------------

    def _migrate_legacy_cadence(self) -> None:
        """Copy a pre-3.1.0 Radio cadence into the shared setting, once.

        In apply() rather than in the getter that reads it: a property that
        writes a file is a property nobody expects to, and apply() is already
        the moment settings are (re-)read.
        """
        if self._shared_interval() > 0:
            return  # the shared value is set; leave it alone
        legacy = refresh_policy.normalize_interval(
            getattr(self._settings(), "podcast_refresh_minutes", 0)
        )
        if legacy > 0:
            self._adopt_shared_interval(legacy)

    def apply(self) -> bool:
        """Re-read the settings and start or stop the timer. Returns whether it runs.

        Called at startup and again whenever Preferences is saved, so changing
        the cadence takes effect without a restart.
        """
        self.stop()
        if self._safe_mode:
            return False
        self._migrate_legacy_cadence()
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
        self._check_youtube_channels()
        return True

    def _check_youtube_channels(self) -> None:
        """Followed YouTube channels with the bell on ride the same schedule."""
        from quill.ui.radio import youtube_channel_alerts_ui

        youtube_channel_alerts_ui.check_in_background(
            self._task_manager,
            safe_mode=self._safe_mode,
            minutes=self._interval_minutes(),
            consented=bool(getattr(self._settings(), "youtube_consented", False)),
        )

    def _on_timer(self, event: Any) -> None:
        # One wx.Timer per frame shares EVT_TIMER with every other timer bound
        # to the same parent, so identity has to be checked before acting.
        if event.GetId() != self._timer.GetId():
            event.Skip()
            return
        self.check_now(announce_when_empty=False)
        self._check_youtube_channels()

    # -- the check ------------------------------------------------------------

    def _anything_to_check(self) -> bool:
        """Whether an automatic check has any show to ask about at all.

        Reads the shared library, so a listener subscribed to nothing -- or
        who has set every show to never -- costs nothing on every tick.
        Unreadable library means yes: the check itself reports the problem
        properly, and silently skipping would hide it.
        """
        try:
            # Through the provider, not off disk: the provider IS the shared
            # library, and reading around it made this guard answer about a
            # different library than the one the cadence came from.
            library = self._library_provider()
            return episode_alerts.anything_to_check(
                list(getattr(library, "shows", []) or []),
                library.effective_settings,
                # The library's own global, the same one the worker uses:
                # a per-show 0 is an opt-out only against a global yes.
                # Asking with the *effective* cadence (which may come from
                # the legacy Radio setting) made every show look opted out.
                global_minutes=self._shared_interval(),
            )
        except Exception:  # noqa: BLE001 - let the real check report it
            return True

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
        if not force and not self._anything_to_check():
            # Subscribed to nothing, or everything set to never. An app that
            # wakes up to do nothing is still an app that woke up: no thread,
            # no request, no battery.
            return False

        def _work(**_kwargs: Any) -> list[FeedCheck] | None:
            # None means "the other app just did this" -- see refresh_policy.is_due.
            return refresh_subscribed_feeds(
                force=force,
                safe_mode=self._safe_mode,
                only_if_due_minutes=None if force else self._interval_minutes(),
            )

        def _ok(_op: str, result: object) -> None:
            if result is None:
                return  # the other app checked inside this interval; nothing to say
            found = list(result) if isinstance(result, list) else []
            # **The count, not the row count.** ``found`` carries a row for
            # every show that was checked, including the ones with nothing
            # new -- so "did anything happen?" is the sum, not whether the
            # list is empty. Testing the list meant an automatic check
            # announced "No new episodes." every fifteen minutes to anybody
            # with at least one subscription (reported 2026-08-24, within
            # minutes of it being wired up).
            gained = sum(row.new_count for row in found)
            # The alerts first: a notification is the thing somebody asked
            # for, and the spoken summary below is held back by quiet hours
            # while the recorded list deliberately is not -- being quiet
            # about something is not the same as never having been told.
            _raise_alerts(found)
            if not gained and not announce_when_empty:
                return
            # Quiet hours (11.9) hold back the *automatic* summary only. A
            # check somebody pressed a key for -- announce_when_empty, the
            # manual path -- always answers, because they asked.
            if not announce_when_empty:
                from quill.core.quiet_hours import Kind
                from quill.ui.quiet_hours_ui import held_back

                if held_back(Kind.NEW_EPISODE):
                    return
            self._announce(refresh_policy.summarise_check([(r.title, r.new_count) for r in found]))

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


def _raise_alerts(found: list[FeedCheck]) -> None:
    """Turn a finished check into whatever each show's alert mode asked for.

    Per show, because the mode is per show: one podcast can be worth a
    notification while nine others are worth a line in a list you read when
    you feel like it. That is the whole point of having three modes.

    **The record comes first and is never skipped for a show that wanted
    one.** The desktop notification and the sound are the louder half on
    top, and they are the half quiet hours may hold back -- a list entry
    cannot wake anybody, so holding it back would only lose the news.

    One sound at most, however many shows arrived: nine chimes for one
    check is an alarm, not information. Never raises -- a check that found
    episodes has already done the useful part.
    """
    from quill.core import notification_targets
    from quill.core.notifications import add_notice
    from quill.core.podcasts import episode_alerts

    loud: list[tuple[str, int, str]] = []
    for title, count, alert, show_id in found:
        if count <= 0 or not episode_alerts.wants_list_entry(alert):
            continue
        plural = "episodes" if count != 1 else "episode"
        try:
            add_notice(
                app="Quill Radio",
                title=f"{count} new {plural}",
                body=title,
                # Prefixed, so Enter on the row knows it has a podcast and
                # not a station. Bare ids written before 3.1.0 shipped still
                # read as shows -- see notification_targets.parse.
                target=notification_targets.for_show(show_id),
            )
        except Exception:  # noqa: BLE001 - the episodes still arrived
            logger.debug("Could not record a new-episode notice", exc_info=True)
        if episode_alerts.wants_desktop_notice(alert):
            loud.append((title, count, plural))
    if not loud:
        return
    _notify_loudly(loud)


def _notify_loudly(loud: list[tuple[str, int, str]]) -> None:
    """The desktop notification and the one sound, for the shows that asked.

    Quiet hours apply here and only here: this is the half that interrupts.
    """
    from quill.core.quiet_hours import Kind
    from quill.ui.quiet_hours_ui import held_back

    try:
        if held_back(Kind.NEW_EPISODE):
            return
    except Exception:  # noqa: BLE001 - unknown quiet hours never lose the news
        pass
    if len(loud) == 1:
        title, count, plural = loud[0]
        heading, body = f"{count} new {plural}", title
    else:
        total = sum(count for _t, count, _p in loud)
        heading = f"{total} new episodes"
        body = ", ".join(t for t, _c, _p in loud[:3])
        if len(loud) > 3:
            body += f" and {len(loud) - 3} more"
    try:
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.CAST_NEW_EPISODES)
    except Exception:  # noqa: BLE001 - a missing clip is not a failure
        pass
    try:
        from quill.ui.toast import show_toast

        show_toast(heading, body)
    except Exception:  # noqa: BLE001 - news that cannot be shown is recorded anyway
        logger.debug("New-episode toast could not be shown", exc_info=True)


def refresh_subscribed_feeds(
    *,
    force: bool = False,
    safe_mode: bool = False,
    only_if_due_minutes: int | None = None,
) -> list[tuple[str, int]] | None:
    """Fetch every eligible subscribed feed and fold it into the shared library.

    Returns ``(show title, new episode count)`` for every show checked, which
    is what the caller turns into one spoken sentence -- or ``None`` when
    *only_if_due_minutes* is given and the shared stamp says another app
    already checked inside that interval. ``None`` is deliberately not an
    empty list: "nothing new" and "somebody else just did this" are different
    facts, and only the first is worth saying.

    The merge is exactly the one Radio already performs when you *open* a show
    (``browse_libraries._sync_subscribed_episodes``): ``merge_episodes`` keeps
    local state -- played, position, notes -- untouched, and the library is
    saved once at the end rather than once per feed. One bad feed never stops
    the rest: a show that will not load is a show reported as nothing new, and
    the next check tries it again.

    Runs on a worker thread. Nothing here touches wx.
    """
    import time

    from quill.core.paths import app_data_dir
    from quill.core.podcasts import feed_auth, feed_reader
    from quill.core.podcasts.subscriptions import load_library, merge_episodes, save_library

    data_dir = app_data_dir()
    library = load_library(data_dir)
    now = time.time()
    if only_if_due_minutes is not None:
        if not refresh_policy.is_due(library.last_auto_check, only_if_due_minutes, now):
            return None
        # Claimed *before* the work, not after: two apps whose timers fire in
        # the same second must not both decide they are the one, and the
        # fetches take seconds during which the other would still see the old
        # stamp. The stamp records that the feeds were asked, so it is right
        # even when the answer turns out to be nothing.
        library.last_auto_check = refresh_policy.stamp_now(now)
        save_library(data_dir, library)
    found: list[FeedCheck] = []
    gained = 0
    #: A first read adds episodes without counting them as new, and those
    #: still have to be saved.
    seeded = False
    shows = list(getattr(library, "shows", []) or [])
    # *force* has to reach here, not just the docstring: it is the whole
    # difference between "check the shows on the schedule" and "check the
    # shows I just asked about, paused ones included".
    # Which shows, resolved through the chain rather than one global switch:
    # a show whose own (or whose folder's) interval is 0 is left alone while
    # the rest keep their cadence, and *force* reaches every one of them
    # because somebody who pressed Refresh has said which shows they mean.
    for show in episode_alerts.shows_worth_checking(
        shows,
        library.effective_settings,
        force=force,
        # The library's OWN global, not this caller's cadence: a per-show 0
        # is an opt-out only when there is a global yes for it to be an
        # exception to. Passing the cadence here made the shipped default
        # (global 0) refuse every show.
        global_minutes=episode_alerts.interval_for_show(library.settings),
    ):
        title = str(getattr(show, "title", "") or getattr(show, "feed_url", ""))
        try:
            username, password = feed_auth.auth_for_url(show, show.feed_url)
            info = feed_reader.fetch_and_parse_feed(
                show.feed_url, username=username, password=password, safe_mode=safe_mode
            )
            # A show's first read is a starting point, not news (check.md bug
            # 2): a podcast imported from an OPML file has no episodes yet, and
            # its whole back catalogue is not "new episodes" to alert about.
            first_read = not show.episodes
            count = merge_episodes(show, info.episodes)
            if first_read:
                seeded = seeded or bool(show.episodes)
                count = 0
            if not info.tags.is_empty:
                show.tags = info.tags
        except Exception:  # noqa: BLE001 - one bad feed never stops the rest
            logger.exception("Podcast refresh failed for %s", title)
            continue
        gained += count
        alert = episode_alerts.alert_for_show(library.effective_settings(show))
        found.append(
            FeedCheck(
                title=title,
                new_count=count,
                alert=alert,
                show_id=str(getattr(show, "id", "") or ""),
            )
        )
    if gained or seeded:
        save_library(data_dir, library)
    return found


__all__ = ["FeedCheck", "PodcastRefreshMonitor", "refresh_subscribed_feeds"]
