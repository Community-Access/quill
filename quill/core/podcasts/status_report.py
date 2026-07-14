"""Pure summary builders for the Help > Application Status page's Podcasts
activity: a library-at-a-glance row set, and per-download task rows. wx-free
so this is unit-testable without constructing any dialog; ``main_frame.py``
only calls these and appends the results to its existing status/task rows.
"""

from __future__ import annotations

from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.podcasts.sorting import unheard_count
from quill.core.podcasts.subscriptions import PodcastLibrary

_DOWNLOAD_STATUS_LABELS = {
    "queued": "Queued",
    "downloading": "Downloading",
    "paused": "Paused",
    "completed": "Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
}


def podcast_status_rows(
    library: PodcastLibrary,
    *,
    now_playing: str,
    downloads_active: int,
) -> list[tuple[str, str, str]]:
    """``(category, setting, value)`` rows summarizing the whole podcast
    library at a glance, for HelpStatusDialog's Status tab."""
    subscribed = sum(1 for show in library.shows if not show.is_local)
    local = sum(1 for show in library.shows if show.is_local)
    unheard = sum(unheard_count(show) for show in library.shows)
    return [
        ("Podcasts", "Subscribed shows", str(subscribed)),
        ("Podcasts", "Local shows", str(local)),
        ("Podcasts", "Unheard episodes", str(unheard)),
        ("Podcasts", "Now playing", now_playing or "Nothing playing"),
        ("Podcasts", "Play Queue", f"{len(library.queue)} episode(s)"),
        ("Podcasts", "Downloads in progress", str(downloads_active)),
    ]


def _format_download_progress(item: DownloadItem) -> str:
    if item.total_bytes > 0:
        percent = min(100, round(item.bytes_downloaded * 100 / item.total_bytes))
        return f"{percent}% ({item.bytes_downloaded:,}/{item.total_bytes:,} bytes)"
    if item.bytes_downloaded:
        return f"{item.bytes_downloaded:,} bytes"
    return "-"


def download_task_rows(
    download_queue: PodcastDownloadQueue, library: PodcastLibrary
) -> list[tuple[str, str, str, str, str]]:
    """``(task, status, progress, started, finished)`` rows for every episode
    download the queue currently knows about, most-recently-enqueued first --
    so the Help Status page shows real download activity, not just a count."""
    rows: list[tuple[str, str, str, str, str]] = []
    for item in reversed(download_queue.snapshot()):
        show = library.find_show(item.show_id)
        episode = show.find_episode(item.episode_guid) if show is not None else None
        title = episode.title if episode is not None else item.episode_guid
        rows.append((
            f"Download: {title}",
            _DOWNLOAD_STATUS_LABELS.get(item.status, item.status.title()),
            _format_download_progress(item),
            item.started_at,
            item.finished_at,
        ))
    return rows
