"""Cancel UI preparations and invalidate worker delivery before Cast disappears."""

from __future__ import annotations

import logging
from typing import Any

from quill.ui.surface_lifetime import destroy_event_matches, lifetime_for

logger = logging.getLogger(__name__)


def cancel_preparations(host: Any) -> None:
    from quill.ui.podcasts.library_tree_updates import cancel_tree_update

    cancel_tree_update(host)
    cancel_view = getattr(host, "_cancel_cast_view_preparation", None)
    if callable(cancel_view):
        cancel_view()
    retirement = getattr(host, "_cast_view_retirement_pool", None)
    if retirement is not None:
        retirement.shutdown(wait=False, cancel_pending=False)
    for name in (
        "_cast_notes_later",
        "_cast_close_later",
        "_podcast_save_timer",
        "_podcast_snapshot_later",
        "_podcast_maintenance_later",
    ):
        timer = getattr(host, name, None)
        if timer is not None:
            timer.Stop()
            setattr(host, name, None)
    for name in ("_cast_episode_snapshot", "_podcast_maintenance_snapshot"):
        job = getattr(host, name, None)
        if job is not None:
            job.cancel()
            setattr(host, name, None)


def install(host: Any) -> None:
    host._cast_closed = False
    host._cast_closing = False
    host._cast_ui_lifetime = lifetime_for(host.frame)
    get_id = getattr(host.frame, "GetId", None)
    frame_id = get_id() if callable(get_id) else None

    def destroyed(event: Any) -> None:
        if destroy_event_matches(event, host.frame, frame_id):
            host._cast_closed = True
            host._cast_ui_lifetime.invalidate()
            from quill.ui.undo_last_ui import deactivate

            deactivate(host)
            try:
                cancel_preparations(host)
                from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

                shutdown_feed_checks(host)
                for name in (
                    "_task_manager",
                    "_podcast_save_pool",
                    "_podcast_record_tasks",
                    "_cast_close_pool",
                    "_cast_undo_file_pool",
                ):
                    pool = getattr(host, name, None)
                    if pool is not None:
                        pool.shutdown(wait=False, cancel_pending=False)
            except Exception:
                logger.exception("Could not finish Cast's destroyed-window cleanup")
        event.Skip()

    host.frame.Bind(host._wx.EVT_WINDOW_DESTROY, destroyed)
