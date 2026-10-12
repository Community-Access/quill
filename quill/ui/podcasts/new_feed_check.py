"""Check only the feeds an import has just subscribed.

Split from main_frame_podcasts under GATE-11. ``PodcastsMixin`` keeps
``_start_new_podcast_feed_check`` as a one-line method because the OPML import
window and the Feed Check monitor reach it by name on whatever host they were
handed, and tests replace it there; the work itself lives here.
"""

from __future__ import annotations

from typing import Any


def start_new_feed_check(
    host: Any,
    show_ids: list[str],
    *,
    action: str,
    only_if_automatic_checks_enabled: bool = False,
) -> None:
    """Refresh just the feeds a completed import has newly subscribed."""
    if only_if_automatic_checks_enabled:
        settings = getattr(host, "settings", None) or getattr(host, "_podcast_history", None)
        if not bool(getattr(settings, "podcast_check_enabled", False)):
            return
    monitor = getattr(host, "_podcast_check_monitor", None)
    if monitor is None or not show_ids:
        return
    if monitor.is_checking:
        host._announce(
            f"{action}: feeds were added, but another feed check is already in progress."
        )
        return
    started = monitor.check_now(
        force=True,
        defer_start=True,
        show_ids={str(show_id) for show_id in show_ids},
    )
    if not started:
        return
    from quill.ui.podcasts import check_run

    ids = list(getattr(monitor, "last_started_ids", []))
    check_run.start(host, ids, action=action)
    monitor.start_queued()


def check_start_failed(host: Any, show_id: str) -> None:
    """Count a feed whose worker could not be submitted as a failed check."""
    from quill.ui.podcasts import check_run

    show = host._podcast_library.find_show(show_id)
    check_run.step(
        host,
        show_id,
        failed_title=str(getattr(show, "title", "") or show_id),
    )
