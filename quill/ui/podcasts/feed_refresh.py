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
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import feed_auth
from quill.core.podcasts.subscriptions import merge_episodes


def refresh_feed(host: Any, show_id: str) -> None:
    from quill.core.podcasts import feed_reader

    show = host._podcast_library.find_show(show_id)
    # Pause is "leave this show alone" for the *automatic* paths only --
    # the background check already filters paused shows before it gets
    # here (check_monitor.refresh_all), so this one is the manual verb and
    # must always work. A pause that could strand a show behind a dead
    # Refresh would be a trap; see core/podcasts/refresh_policy.py.
    if show is None or not show.feed_url or host._safe_mode:
        return
    username, password = feed_auth.auth_for_url(show, show.feed_url)

    def _do_refresh(**_kwargs: object) -> feed_reader.FeedInfo:
        return feed_reader.fetch_and_parse_feed(
            show.feed_url, username=username, password=password, safe_mode=host._safe_mode
        )

    def _on_success(_op: str, info: feed_reader.FeedInfo) -> None:
        known = {episode.guid for episode in show.episodes}
        republished: list[str] = []
        if not info.tags.is_empty:
            show.tags = info.tags
        new_count = merge_episodes(show, info.episodes, republished=republished)
        fresh = [episode for episode in show.episodes if episode.guid not in known]
        queued = host._podcast_route_new_episodes(show, fresh)
        host._podcast_resurface_republished(show, republished)
        host._save_podcast_library()
        if host._podcast_manager_dialog is not None:
            host._podcast_manager_dialog.refresh_tree()
        if new_count:
            # "Let results interrupt speech" is the third leg of the shared
            # monitor policy: force=True raises the announcement to WARNING,
            # which is the severity that cuts across current speech.
            #
            # ...unless quiet hours are in force (11.9). The episodes still
            # arrive, and are still queued and downloaded; what is held
            # back is the sentence about them, which is the part that wakes
            # somebody up.
            from quill.core.quiet_hours import Kind
            from quill.ui.quiet_hours_ui import held_back

            if not held_back(Kind.NEW_EPISODE):
                host._announce(
                    host._podcast_new_episode_message(show, new_count, queued),
                    force=host._podcast_check_monitor.interrupt_speech,
                )
                host._podcast_notify_new_episodes(show, fresh)
        # Always Sync is now one value of the auto-download policy
        # (effective_auto_download_count == -1), so the single
        # acquisition pass below covers both -- calling the old backfill
        # as well would queue the same items twice and say so twice.
        host._podcast_apply_auto_download(show)
        # Aging the queue and trimming the Inbox belong right after new
        # episodes arrive: that is the moment the counts actually change.
        host.podcast_run_maintenance()

    from quill.ui.podcasts.show_actions import announce_if_feed_auth_failure

    def _on_failure(_op: str, exc: BaseException) -> None:
        announce_if_feed_auth_failure(exc, show, announce=host._announce)
        # Written down as well as spoken (11.5): a feed that failed while
        # you were in another window said its piece to nobody, and until
        # Recent Problems existed there was nowhere to go and look.
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(
            app_data_dir(),
            problem_log.KIND_FEED,
            show.title or show.feed_url,
            str(exc) or exc.__class__.__name__,
            target=show.id,
        )

    host._task_manager.submit(
        "podcast-refresh",
        _do_refresh,
        on_success=_on_success,
        on_failure=_on_failure,
    )
