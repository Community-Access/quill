"""The download queue answers state questions in O(1) and starts in enqueue order (F-09).

The worker thread is stopped first in every test, so nothing is fetched; the
tests then drive ``_next_startable`` -- the worker's own "what next?" -- by hand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.download_queue import PodcastDownloadQueue


@pytest.fixture
def queue() -> PodcastDownloadQueue:
    made = PodcastDownloadQueue(max_concurrent=100)
    made.shutdown()
    made._worker.join(timeout=5)
    return made


def _add(queue: PodcastDownloadQueue, *ids: str) -> None:
    for item_id in ids:
        queue.enqueue(item_id, show_id="s", episode_guid=item_id, url="", destination=Path("x"))


def test_counts_follow_every_transition(queue: PodcastDownloadQueue) -> None:
    _add(queue, "a", "b", "c", "d")
    assert queue.count("queued") == 4
    queue.pause_item("b")
    queue.cancel_item("c")
    assert (queue.count("queued"), queue.count("paused"), queue.count("cancelled")) == (2, 1, 1)
    started = queue._next_startable()
    assert started is not None and started.item_id == "a"
    assert queue.active_count() == 1 and queue.count("queued") == 1
    queue.resume_item("b")
    assert queue.count("queued") == 2 and queue.count("paused") == 0


def test_the_next_download_is_the_oldest_still_queued(queue: PodcastDownloadQueue) -> None:
    _add(queue, "a", "b", "c")
    queue.pause_item("a")
    assert queue._next_startable().item_id == "b"
    queue.resume_item("a")  # back in its original place, ahead of c
    assert queue._next_startable().item_id == "a"
    assert queue._next_startable().item_id == "c"
    assert queue._next_startable() is None


def test_a_reenqueued_item_replaces_its_old_self(queue: PodcastDownloadQueue) -> None:
    _add(queue, "a", "b")
    queue.cancel_item("a")
    _add(queue, "a")
    assert queue.count("queued") == 2 and queue.count("cancelled") == 0
    assert queue._next_startable().item_id == "b"
    assert queue._next_startable().item_id == "a"


def test_a_finished_download_moves_its_count(queue: PodcastDownloadQueue, monkeypatch) -> None:
    from quill.core.podcasts import download_queue as module

    monkeypatch.setattr(module, "_fetch_chunked", lambda *a, **k: "completed")
    _add(queue, "a")
    item = queue._next_startable()
    queue._run_one(item)
    assert queue.count("completed") == 1 and queue.active_count() == 0
