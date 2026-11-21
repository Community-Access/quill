"""A new download folder takes the waiting downloads with it (Chris Nova, 2026-11-20)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from quill.core.podcasts.download_folder_change import follow_new_folder
from quill.core.podcasts.download_queue import PodcastDownloadQueue


@pytest.fixture
def queue() -> Iterator[PodcastDownloadQueue]:
    q = PodcastDownloadQueue()
    q.pause_all()  # nothing starts: every item stays waiting for the test
    try:
        yield q
    finally:
        q.shutdown()


def _enqueue(q: PodcastDownloadQueue, item_id: str, destination: Path) -> None:
    q.enqueue(
        item_id,
        show_id="s",
        episode_guid=item_id,
        url=f"https://example.invalid/{item_id}.mp3",
        destination=destination,
    )


def test_waiting_downloads_move_to_the_new_folder(
    queue: PodcastDownloadQueue, tmp_path: Path
) -> None:
    old, new = tmp_path / "old", tmp_path / "Quill Cast Downloads"
    _enqueue(queue, "a", old / "Show" / "One.mp3")
    _enqueue(queue, "b", old / "Show" / "Two.mp3")

    said = follow_new_folder(queue, old, new)

    assert [item.destination for item in queue.snapshot()] == [
        new / "Show" / "One.mp3",
        new / "Show" / "Two.mp3",
    ]
    assert said == f"2 downloads waiting will now save to {new}."


def test_a_part_written_download_resumes_where_it_is(
    queue: PodcastDownloadQueue, tmp_path: Path
) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    partial = old / "Show" / "One.mp3"
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"first half")
    _enqueue(queue, "a", partial)
    _enqueue(queue, "b", old / "Show" / "Two.mp3")

    said = follow_new_folder(queue, old, new)

    first, second = queue.snapshot()
    assert first.destination == partial  # its bytes are not lost or copied
    assert second.destination == new / "Show" / "Two.mp3"
    assert said == (
        f"1 download waiting will now save to {new}. "
        "1 download already started finishes in the old folder."
    )


def test_downloads_elsewhere_and_finished_ones_are_left_alone(
    queue: PodcastDownloadQueue, tmp_path: Path
) -> None:
    old, new, other = tmp_path / "old", tmp_path / "new", tmp_path / "other"
    _enqueue(queue, "a", other / "One.mp3")
    _enqueue(queue, "b", old / "Two.mp3")
    queue.cancel_item("b")

    assert follow_new_folder(queue, old, new) == ""
    assert [item.destination for item in queue.snapshot()] == [other / "One.mp3", old / "Two.mp3"]


def test_nothing_is_said_when_the_folder_did_not_change(
    queue: PodcastDownloadQueue, tmp_path: Path
) -> None:
    _enqueue(queue, "a", tmp_path / "One.mp3")
    assert follow_new_folder(queue, tmp_path, tmp_path) == ""
    assert follow_new_folder(None, tmp_path, tmp_path / "new") == ""
    assert follow_new_folder(queue, None, tmp_path) == ""
