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

    #: Where the feed actually landed, when the server moved it. Reported by
    #: the fetch rather than acted on there: rewriting a subscription's stored
    #: address is a per-podcast decision (7.20).
    redirected_to: list[str] = []

    def _do_refresh(**_kwargs: object) -> feed_reader.FeedInfo:
        return feed_reader.fetch_and_parse_feed(
            show.feed_url,
            username=username,
            password=password,
            safe_mode=host._safe_mode,
            redirected_to=redirected_to,
        )

    def _on_success(_op: str, info: feed_reader.FeedInfo) -> None:
        known = {episode.guid for episode in show.episodes}
        republished: list[str] = []
        if not info.tags.is_empty:
            show.tags = info.tags
        merge_episodes(show, info.episodes, republished=republished)
        arrived = [episode for episode in show.episodes if episode.guid not in known]
        # Episode Filters are consulted here, before anything routes -- and
        # each route asks for *its own* scope, because a listener who wants a
        # segment kept out of the queue but still announced has said something
        # coherent and this is where it is honoured. A podcast with no filter
        # gets the arrived list back for every scope, so nothing below this
        # line can tell the difference.
        outcome = host._podcast_filter_new_episodes(show, arrived)
        fresh = host._podcast_filter_scope(show, outcome, "notify")
        new_count = len(fresh)
        queued = host._podcast_route_new_episodes(
            show, host._podcast_filter_scope(show, outcome, "queue")
        )
        # Routing without committing to an order: a podcast can name a manual
        # playlist its new episodes join as they arrive (7.16).
        host._podcast_file_to_default_playlist(show, fresh)
        host._podcast_resurface_republished(show, republished)
        # Per-podcast bookkeeping (7.1, 7.19): when this feed was last read,
        # when it last carried something, and the failure run this success
        # ends. It decides when the *next* check is due and when the two
        # notices fire; it never decides whether to check at all.
        from quill.core.podcasts import check_state

        check_state.record_success(host._podcast_library, show, new_episodes=len(arrived))
        _follow_redirect(host, show, redirected_to)
        # A podcast that has stopped publishing does not announce it, and an
        # absence is precisely the thing nobody notices. Latched, so an hourly
        # check does not say it hourly (7.19).
        quiet = check_state.quiet_notice(host._podcast_library, show)
        if quiet:
            host._announce(quiet)
        host._save_podcast_library()
        if host._podcast_manager_dialog is not None:
            host._podcast_manager_dialog.refresh_tree()
        if new_count or outcome.any_filtered:
            # "Let results interrupt speech" is the third leg of the shared
            # monitor policy: force=True raises the announcement to WARNING,
            # which is the severity that cuts across current speech.
            #
            # ...unless quiet hours are in force (11.9). The episodes still
            # arrive, and are still queued and downloaded; what is held
            # back is the sentence about them, which is the part that wakes
            # somebody up. The filter's own sentences ride the same gate for
            # the same reason -- and the Needs review warning is *stored*
            # either way, so a background check that raised it at 3 a.m. is
            # still waiting in Podcast Settings in the morning.
            #
            # One podcast may be let through by name -- for a live or news feed
            # somebody asked to be told about. It widens quiet hours for this
            # announcement only; every other kind of background news is still
            # held back, and no podcast is let through unless it was named.
            from quill.core.podcasts.show_policy import may_speak_in_quiet_hours
            from quill.core.quiet_hours import Kind
            from quill.ui.quiet_hours_ui import held_back

            allowed = may_speak_in_quiet_hours(host._podcast_library, show)
            if allowed or not held_back(Kind.NEW_EPISODE):
                if new_count:
                    host._announce(
                        host._podcast_new_episode_message(show, new_count, queued),
                        force=host._podcast_check_monitor.interrupt_speech,
                    )
                    host._podcast_notify_new_episodes(show, fresh)
                host._podcast_announce_episode_filter(show, outcome)
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
        # A run of failures earns one sentence, not one per check (7.19). Cast
        # keeps trying either way -- the notice says so, because "this feed has
        # failed" otherwise reads as "and I have given up".
        from quill.core.podcasts import check_state

        check_state.record_failure(host._podcast_library, show)
        notice = check_state.failure_notice(host._podcast_library, show)
        if notice:
            host._announce(notice, force=True)
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
