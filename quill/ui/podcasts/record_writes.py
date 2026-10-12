"""Hand QUILL Cast's small record writes to the background record queue.

Split from main_frame_podcasts under GATE-11. Inside QUILL Cast (a host with a
``_cast_ui_lifetime``) the listening history and the place shared with Quill
Radio are written off the UI thread through ``record_tasks``; QUILL itself
writes them inline. Each function answers whether it queued the write, so the
mixin falls through to the inline write when it did not.
"""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir
from quill.core.podcasts import history as podcast_history


def _queues_records(host: Any) -> bool:
    return getattr(host, "_cast_ui_lifetime", None) is not None


def queue_history_save(host: Any) -> bool:
    """Queue a snapshot of the podcast history record; False when not in Cast."""
    if not _queues_records(host):
        return False
    import copy

    from quill.ui.podcasts import record_tasks

    data_dir = app_data_dir()
    snapshot = copy.deepcopy(host._podcast_history)
    record_tasks.submit(
        host, "cast_history", lambda: podcast_history.save_history(data_dir, snapshot)
    )
    return True


def queue_shared_place(
    host: Any, show: object, episode: object, ms: int, *, finished: bool
) -> bool:
    """Queue the place Quill Radio reads (11.11); False when not in Cast."""
    if not _queues_records(host):
        return False
    from types import SimpleNamespace

    from quill.ui.podcasts import record_tasks
    from quill.ui.podcasts.shared_place import share_place

    source = SimpleNamespace(feed_url=str(getattr(show, "feed_url", "") or ""))
    target = SimpleNamespace(
        audio_url=str(getattr(episode, "audio_url", "") or ""),
        title=str(getattr(episode, "title", "") or ""),
    )
    data_dir = app_data_dir()
    record_tasks.submit(
        host,
        "shared_positions",
        lambda: share_place(source, target, ms, finished=finished, data_dir=data_dir, strict=True),
    )
    return True
