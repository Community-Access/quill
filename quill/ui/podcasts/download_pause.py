"""Pausing and resuming the whole podcast download queue, counted (11.4).

"Paused all podcast downloads" was true and unhelpful: it did not say whether
that was nothing or forty things, and it did not say that the one already
mid-transfer keeps going to the end -- which it does.

Extracted from ``main_frame_podcasts.py`` under GATE-11.
"""

from __future__ import annotations


def podcast_pause_all_downloads(host) -> None:
    """Stop starting new transfers, and say how many that leaves waiting.

    "Paused all podcast downloads" was true and unhelpful (11.4): it did
    not say whether that was nothing, or forty things, or that the one
    mid-transfer keeps going to the end -- which it does.
    """
    queue = host._podcast_download_queue
    waiting = sum(1 for item in queue.snapshot() if item.status == "queued")
    running = queue.active_count()
    queue.pause_all()
    if not waiting and not running:
        host._announce("Downloads paused. Nothing was waiting.")
        return
    parts = [f"{waiting} waiting"]
    if running:
        parts.append(f"{running} already transferring, which will finish")
    host._announce("Downloads paused: " + ", ".join(parts) + ".")


def podcast_resume_all_downloads(host) -> None:
    """Start the queue again, and say how many it picks back up."""
    queue = host._podcast_download_queue
    waiting = sum(1 for item in queue.snapshot() if item.status in ("queued", "paused"))
    queue.resume_all()
    if not waiting:
        host._announce("Downloads resumed. Nothing was waiting.")
        return
    host._announce(f"Downloads resumed: {waiting} waiting.")
