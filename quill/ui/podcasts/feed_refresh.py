"""Refreshing one podcast feed: fetch, merge, route, and record a failure.

Extracted from ``main_frame_podcasts.py`` under GATE-11 -- eighty lines of
one concern in the largest podcast mixin, and the concern grew again when
11.5 gave a failed refresh somewhere to be written down and 11.9 gave the
success announcement a quiet window to respect.

Three rules the shape follows, all of them older than the extraction:

* **Pause never blocks this path.** Pause means "leave this show alone" for
  the *automatic* checks; a Refresh somebody pressed always works, because a
  pause that could strand a show behind a dead verb would be a trap.
* **A failure is written down as well as spoken** (11.5). A feed that failed
  while the listener was in another window said its piece to nobody.
* **The new-episode announcement respects quiet hours** (11.9). The episodes
  still arrive, are still queued and still download; only the sentence waits.

What a read *does to the record* -- merging, the first-read baseline, the real
"last published" date, an empty feed, the validators for next time -- is
``quill/core/podcasts/feed_read.py``, wx-free and tested (check.md bugs 2, 3
and 9). This module routes what that returns.

Feed checks run on **their own small pool** (check.md bug 10). A Refresh All
Now over a 1,300-show library took 22 minutes on the four shared workers, and
every other background job -- a download starting, a transcript, a search --
waited behind it. Now a big check can be slow without the rest of the app
being stuck behind it.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from quill import __version__
from quill.core.net import ssl_trust_configured
from quill.core.podcasts import feed_auth
from quill.ui.podcasts.feed_refresh_snapshot import (
    SNAPSHOT_EPISODES_PER_TURN,
    _copy_show_for_refresh,
    _prepare_refresh,
    _PreparedRefresh,
    _same_routing,
    _snapshot_for_refresh,
)

logger = logging.getLogger(__name__)

#: Feed checks in flight at once, on their own pool. Responsiveness wins over
#: completion speed: two requests at a time keep a manual sweep from saturating
#: a listener's connection or competing heavily with playback and other work.
FEED_CHECK_WORKERS = 2


def feed_check_pool(host: Any) -> Any:
    """The task manager feed checks run on: their own, made on first use.

    A host that is not running the real task manager (a test double) keeps
    using its own, so every wiring test still sees the submission.
    """
    pool = getattr(host, "_podcast_feed_tasks", None)
    if pool is not None:
        return pool
    from quill.stability.task_manager import TaskManager

    shared = host._task_manager
    if type(shared) is not TaskManager:
        return shared
    pool = TaskManager(max_workers=FEED_CHECK_WORKERS)
    host._podcast_feed_tasks = pool
    return pool


def _commit_prepared_refresh(host: Any, prepared: _PreparedRefresh) -> Any | None:
    """Synchronous adapter for small hosts; production uses the yielding commit."""
    from quill.ui.podcasts.refresh_commit import commit_steps

    steps = commit_steps(host, prepared)
    while True:
        try:
            next(steps)
        except StopIteration as result:
            return result.value


def _enqueue_prepared_auto_downloads(host: Any, show: Any, episodes: list[Any]) -> int:
    from quill.ui.podcasts.show_actions import enqueue_episode_download

    started = 0
    for episode in episodes:
        item_id = f"{show.id}:{episode.guid}"
        if host._podcast_download_queue.get(item_id) is not None:
            continue
        enqueue_episode_download(
            host._podcast_download_queue,
            host._podcast_download_root(),
            show,
            episode,
            item_id=item_id,
            library=host._podcast_library,
        )
        started += 1
    return started


def shutdown_feed_checks(host: Any) -> None:
    """On close: stop the feed-check pool, dropping checks not yet started."""
    host._podcast_feed_generation = host.__dict__.get("_podcast_feed_generation", 0) + 1
    for cancel in list(host.__dict__.get("_podcast_feed_commit_cancellations", [])):
        cancel()
    for timer in host.__dict__.get("_podcast_feed_snapshot_timers", []):
        stop = getattr(timer, "Stop", None)
        if callable(stop):
            stop()
    host.__dict__.pop("_podcast_feed_snapshot_timers", None)
    host.__dict__.pop("_podcast_refresh_snapshot_pending", None)
    host.__dict__.pop("_podcast_refresh_snapshots", None)
    pool = host.__dict__.pop("_podcast_feed_tasks", None)
    if pool is not None:
        pool.shutdown(wait=False, cancel_pending=True)


def _follow_redirect(host: Any, show: Any, redirected_to: list[str]) -> None:
    """Update a podcast's stored address when it asked to, and it may.

    Off by default and per podcast, because it is a security-shaped decision
    dressed as a convenience: a feed that has genuinely moved is saved by it,
    and a feed that has been taken over is not something to follow silently.
    **A saved username and password are never carried to a new host** -- a
    private feed that moves is re-authenticated deliberately, not by a
    redirect.
    """
    from quill.core.podcasts.show_policy import follows_redirects

    landed = redirected_to[-1] if redirected_to else ""
    if not landed or landed == show.feed_url:
        return
    if not follows_redirects(host._podcast_library, show):
        return
    from urllib.parse import urlparse

    moved_host = urlparse(landed).netloc != urlparse(show.feed_url).netloc
    if moved_host and show.feed_username:
        host._announce(
            f"{show.title} has moved to another host. Its address was left alone "
            "because it has a saved sign-in, which is never carried to a new "
            "host -- open Feed Credentials to move it deliberately."
        )
        return
    show.feed_url = landed
    host._announce(f"{show.title} has permanently moved; its feed address was updated.")


def _record(host: Any, kind: str, *, title: str, body: str, show: Any) -> None:
    """Queue an opted-in notice without putting filesystem work on wx."""
    from quill.core import notification_targets
    from quill.core.podcasts import notices
    from quill.ui.podcasts import record_tasks

    history = getattr(host, "_podcast_history", None)
    if history is None or not notices.wants(history, kind):
        return
    copied_history = copy.copy(history)
    target = notification_targets.for_show(show.id)

    def write() -> None:
        if not notices.record(copied_history, kind, title=title, body=body, target=target):
            raise OSError("The feed notification could not be saved")

    record_tasks.submit(host, "feed-notice", write)


def _belongs_to_check_run(host: Any, show_id: str) -> bool:
    run = getattr(host, "_check_run", None)
    return run is not None and show_id in getattr(run, "pending", ())


def _schedule_manager_refresh(host: Any) -> None:
    """Coalesce expensive manager rebuilds from closely spaced feed results."""
    if host.__dict__.get("_podcast_manager_refresh_pending", False):
        return
    manager = getattr(host, "_podcast_manager_dialog", None)
    if manager is None:
        return
    host._podcast_manager_refresh_pending = True

    def refresh() -> None:
        host._podcast_manager_refresh_pending = False
        current = getattr(host, "_podcast_manager_dialog", None)
        if current is not None:
            current.refresh_tree()

    wx = host.__dict__.get("_wx")
    call_later = getattr(wx, "CallLater", None) if wx is not None else None
    if callable(call_later):
        call_later(50, refresh)
    else:
        refresh()


def refresh_feed(host: Any, show_id: str) -> None:
    from quill.core.podcasts import feed_reader

    show = host._podcast_library.find_show(show_id)
    generation = host.__dict__.get("_podcast_feed_generation", 0)

    def active() -> bool:
        return (
            generation == host.__dict__.get("_podcast_feed_generation", 0)
            and not host.__dict__.get("_cast_closing", False)
            and not host.__dict__.get("_cast_closed", False)
        )

    # Pause is "leave this show alone" for the *automatic* paths only --
    # the background check already filters paused shows before it gets
    # here (check_monitor.refresh_all), so this one is the manual verb and
    # must always work. A pause that could strand a show behind a dead
    # Refresh would be a trap; see core/podcasts/refresh_policy.py.
    if show is None or not show.feed_url or host._safe_mode:
        from quill.ui.podcasts import check_run

        reason = (
            "Podcast no longer in the library"
            if show is None
            else "Podcast has no feed address"
            if not show.feed_url
            else "Safe Mode prevents feed checks"
        )
        check_run.step(host, show_id, failed_title=reason)
        return
    username, password = feed_auth.auth_for_url(show, show.feed_url)
    from quill.core.podcasts import feed_read

    feed_url = show.feed_url
    safe_mode = bool(host._safe_mode)
    #: Where the feed now lives, when the server said so **permanently** (301
    #: or 308 on every hop; check.md bug 4). Reported by the fetch rather than
    #: acted on there: rewriting a subscription's stored address is a
    #: per-podcast decision (7.20).
    redirected_to: list[str] = []
    #: The stored ETag / Last-Modified go out, and this response's come back.
    notes = feed_read.notes_for(host._podcast_library, show)

    snapshot_key = (str(show.id), id(show), feed_url)
    snapshots = host.__dict__.setdefault("_podcast_refresh_snapshots", {})
    cached_snapshot = snapshots.pop(snapshot_key, None)
    if cached_snapshot is not None:
        snapshot, assignment_before, playlist_items_before = cached_snapshot
    elif len(show.episodes) > SNAPSHOT_EPISODES_PER_TURN:
        pending = host.__dict__.setdefault("_podcast_refresh_snapshot_pending", set())
        if snapshot_key in pending:
            return
        pending.add(snapshot_key)

        def _snapshot_ready(copied_show: Any) -> None:
            pending.discard(snapshot_key)
            if not active():
                return
            try:
                snapshots[snapshot_key] = _snapshot_for_refresh(
                    host._podcast_library, show, copied_show=copied_show
                )
            except Exception as error:
                _snapshot_failed(error)
                return
            refresh_feed(host, show_id)

        def _snapshot_failed(error: BaseException) -> None:
            pending.discard(snapshot_key)
            if not active():
                return
            logger.error(
                "Could not snapshot feed results",
                exc_info=(type(error), error, error.__traceback__),
            )
            host._announce(f"Could not prepare a refresh for {show.title}. {error}")
            from quill.ui.podcasts import check_run

            check_run.step(host, str(show.id), failed_title=str(show.title))

        _copy_show_for_refresh(
            host,
            show,
            completed=_snapshot_ready,
            failed=_snapshot_failed,
        )
        return
    else:
        snapshot, assignment_before, playlist_items_before = _snapshot_for_refresh(
            host._podcast_library, show
        )

    from quill.ui.podcasts import check_run

    check_run.started(host, show_id, str(show.title))

    def _do_refresh(**_kwargs: object) -> feed_reader.FeedInfo:
        return feed_reader.fetch_and_parse_feed(
            feed_url,
            username=username,
            password=password,
            safe_mode=safe_mode,
            redirected_to=redirected_to,
            notes=notes,
        )

    def _schedule_prepare(
        working_library: Any,
        before_assignments: dict[str, str],
        before_playlist_items: dict[str, set[tuple[str, str]]],
        info: feed_reader.FeedInfo,
        *,
        previous_episode_before: set[str] | None = None,
    ) -> None:
        def _prepare(**_kwargs: object) -> _PreparedRefresh:
            prepared = _prepare_refresh(
                working_library,
                str(show.id),
                info,
                notes,
                assignment_before=before_assignments,
                playlist_items_before=before_playlist_items,
                safe_mode=safe_mode,
            )
            if prepared.episode_before is not None and previous_episode_before is not None:
                prepared.episode_before.update(previous_episode_before)
            return prepared

        def _prepared(_operation: str, prepared: _PreparedRefresh) -> None:
            if not active():
                return
            current_show = host._podcast_library.find_show(str(show.id))
            if current_show is not show or current_show.feed_url != feed_url:
                check_run.step(host, str(show.id))
                return
            if not _same_routing(host._podcast_library, prepared.library, str(show.id)):

                def copied(updated_show: Any) -> None:
                    if not active():
                        return
                    current = host._podcast_library.find_show(str(show.id))
                    if current is not show or current.feed_url != feed_url:
                        check_run.step(host, str(show.id))
                        return
                    updated, assignments, playlists = _snapshot_for_refresh(
                        host._podcast_library, current, copied_show=updated_show
                    )
                    _schedule_prepare(
                        updated,
                        assignments,
                        playlists,
                        info,
                        previous_episode_before=prepared.episode_before,
                    )

                _copy_show_for_refresh(
                    host,
                    current_show,
                    completed=copied,
                    failed=lambda error: _prepare_failed("podcast-refresh-snapshot", error),
                )
                return
            from quill.ui.podcasts.refresh_commit import commit

            commit(
                host,
                prepared,
                active=lambda: (
                    active()
                    and host._podcast_library.find_show(str(show.id)) is show
                    and show.feed_url == feed_url
                ),
                completed=lambda current_show: _committed(prepared, current_show),
                failed=lambda error: _prepare_failed("podcast-refresh-commit", error),
            )

        def _committed(prepared: _PreparedRefresh, current_show: Any) -> None:
            if not active():
                return
            if current_show is None:
                from quill.ui.podcasts import check_run

                check_run.step(host, str(show.id))
                return

            read = prepared.read
            fresh = prepared.fresh
            outcome = prepared.outcome
            returned = prepared.returned
            belongs_to_check_run = _belongs_to_check_run(host, str(show.id))
            from quill.core.podcasts import check_state

            _follow_redirect(host, current_show, redirected_to)
            quiet = check_state.quiet_notice(host._podcast_library, current_show)
            if quiet and not read.baseline:
                host._announce(quiet)
                _record(
                    host,
                    "gone_quiet",
                    title="Gone quiet",
                    body=current_show.title,
                    show=current_show,
                )
            new_count = len(fresh)
            if new_count:
                _record(
                    host,
                    "new_episode",
                    title=f"{new_count} new episode{'' if new_count == 1 else 's'}",
                    body=current_show.title,
                    show=current_show,
                )
            if returned:
                host._announce(host._podcast_republished_message(current_show, returned))
            from quill.ui.podcasts.save_snapshot import save_show

            save_show(host, str(current_show.id))
            if not belongs_to_check_run:
                _schedule_manager_refresh(host)

            if new_count or outcome.any_filtered:
                from quill.core.podcasts.show_policy import may_speak_in_quiet_hours
                from quill.core.quiet_hours import Kind
                from quill.ui.quiet_hours_ui import held_back

                allowed = may_speak_in_quiet_hours(host._podcast_library, current_show)
                if allowed or not held_back(Kind.NEW_EPISODE):
                    if new_count:
                        host._announce(
                            host._podcast_new_episode_message(
                                current_show, new_count, prepared.queued
                            ),
                            force=host._podcast_check_monitor.interrupt_speech,
                        )
                        host._podcast_notify_new_episodes(current_show, fresh)
                    host._podcast_announce_episode_filter(current_show, outcome)

            started = _enqueue_prepared_auto_downloads(host, current_show, prepared.auto_download)
            if started:
                host._announce(
                    f"Downloading {started} episode(s) of {current_show.title} automatically"
                )
            from quill.ui.podcasts import check_run

            check_run.step(host, str(show.id), new_episodes=new_count)
            if not belongs_to_check_run:
                host.podcast_run_maintenance()

        def _prepare_failed(_operation: str, error: BaseException) -> None:
            if not active():
                return
            logger.error(
                "Could not prepare feed results",
                exc_info=(type(error), error, error.__traceback__),
            )
            host._announce(f"Could not process the refreshed feed for {show.title}. {error}")
            from quill.ui.podcasts import check_run

            check_run.step(host, str(show.id), failed_title=str(show.title))

        feed_check_pool(host).submit(
            "podcast-refresh-merge",
            _prepare,
            on_success=_prepared,
            on_failure=_prepare_failed,
        )

    def _on_success(_op: str, info: feed_reader.FeedInfo) -> None:
        if not active():
            return
        current = host._podcast_library.find_show(show_id)
        if current is not show or current.feed_url != feed_url:
            from quill.ui.podcasts import check_run

            check_run.step(host, show_id)
            return
        _schedule_prepare(snapshot, assignment_before, playlist_items_before, info)

    from quill.ui.podcasts.show_actions import announce_if_feed_auth_failure

    def _on_failure(_op: str, exc: BaseException) -> None:
        if not active():
            return
        from quill.ui.podcasts import check_run

        current = host._podcast_library.find_show(show_id)
        if current is not show or current.feed_url != feed_url:
            check_run.step(host, show_id)
            return
        announce_if_feed_auth_failure(exc, show, announce=host._announce)
        from quill.core.podcasts import check_state

        problem = feed_read.record_failure(
            host._podcast_library, show, exc, had_credentials=bool(username)
        )
        host._save_podcast_library()
        logger.info(
            "Feed check failed for %s: %s [QUILL %s; truststore injected=%s]",
            feed_url,
            problem.detail,
            __version__,
            ssl_trust_configured(),
        )
        notice = check_state.failure_notice(host._podcast_library, show)
        if notice:
            host._announce(notice, force=True)
            _record(host, "feed_failed", title="Feed keeps failing", body=show.title, show=show)
        from quill.core import problem_log
        from quill.core.paths import app_data_dir
        from quill.ui.podcasts import record_tasks

        data_dir = app_data_dir()
        title = show.title or feed_url
        record_tasks.submit(
            host,
            "feed-problem",
            lambda: problem_log.record_problem(
                data_dir, problem_log.KIND_FEED, title, problem.sentence, target=show_id
            ),
        )
        check_run.step(host, str(show.id), failed_title=str(show.title))

    feed_check_pool(host).submit(
        "podcast-refresh",
        _do_refresh,
        on_success=_on_success,
        on_failure=_on_failure,
    )


def check_all_feeds(
    host: Any,
    *,
    announce: Any = None,
    safe_mode: bool | None = None,
) -> int:
    """Check every subscribed feed now, paused shows included, and say how many.

    One implementation for the Podcast Manager's Check All Feeds and the
    palette's Check All Feeds Now. The count comes up front, because this
    verb's result arrives show by show: "checking three feeds" says when it is
    finished, where "checking" does not. A check already running is answered
    rather than doubled. The feeds themselves are paced by the monitor
    (``check_monitor.MAX_REFRESHES_IN_FLIGHT``) and the run is followed in Feed
    Check (``check_run``).
    """
    say = announce or host._announce
    monitor = getattr(host, "_podcast_check_monitor", None)
    if safe_mode is None:
        safe_mode = bool(getattr(host, "_safe_mode", False))
    if monitor is None or safe_mode:
        say("Feeds cannot be checked right now.")
        return 0
    if getattr(monitor, "is_checking", False):
        say("A feed check is already in progress.")
        return 0
    started = int(monitor.check_now(force=True, defer_start=True) or 0)
    if not started:
        say("You follow no podcast with a feed to check.")
        return 0
    say(f"Checking {started:,} feed{'' if started == 1 else 's'}...")
    from quill.ui.podcasts import check_run

    check_run.start(host, list(getattr(monitor, "last_started_ids", [])))
    start_queued = getattr(monitor, "start_queued", None)
    if callable(start_queued):
        call_after = getattr(getattr(host, "_wx", None), "CallAfter", None)
        if callable(call_after):
            call_after(start_queued)
        else:
            start_queued()
    return started


def stop_feed_checks(host: Any, *, announce: bool = True) -> bool:
    """Stop the check of many feeds in progress, if there is one.

    Spoken when somebody asked (Feed Check's own end sentence says how far it
    got); silent when the app is closing.
    """
    monitor = getattr(host, "_podcast_check_monitor", None)
    run = getattr(host, "_check_run", None)
    checking = bool(getattr(monitor, "is_checking", False))
    if run is None and not checking:
        if announce:
            host._announce("No feed check is running.")
        return False
    if run is not None:
        from quill.ui.podcasts import check_run

        check_run.cancel_remaining(host)
    else:
        shutdown_feed_checks(host)
        cancel_all = getattr(monitor, "cancel_all", None)
        if callable(cancel_all):
            cancel_all()
        if announce:
            host._announce("Feed check stopped.")
    return True
