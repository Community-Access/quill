"""Tests for the Help Status page's podcast activity summary builders --
pure, no wx."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.status_report import download_task_rows, podcast_status_rows
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, *, played: bool = False) -> PodcastEpisode:
    return PodcastEpisode(guid=guid, title=guid, audio_url=f"https://x/{guid}.mp3", played=played)


def test_podcast_status_rows_counts_subscribed_and_local_shows() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Subscribed", is_local=False))
    library.add_show(PodcastShow(id="s2", title="Local", is_local=True))

    rows = podcast_status_rows(library, now_playing="", downloads_active=0)

    values = {(section, setting): value for section, setting, value in rows}
    assert values[("Podcasts", "Subscribed shows")] == "1"
    assert values[("Podcasts", "Local shows")] == "1"


def test_podcast_status_rows_sums_unheard_across_shows() -> None:
    library = PodcastLibrary()
    library.add_show(
        PodcastShow(
            id="s1", title="A", episodes=[_episode("e1", played=False), _episode("e2", played=True)]
        )
    )
    library.add_show(PodcastShow(id="s2", title="B", episodes=[_episode("e3", played=False)]))

    rows = podcast_status_rows(library, now_playing="", downloads_active=0)

    values = {(section, setting): value for section, setting, value in rows}
    assert values[("Podcasts", "Unheard episodes")] == "2"


def test_podcast_status_rows_reports_now_playing_and_defaults() -> None:
    library = PodcastLibrary()

    idle_rows = podcast_status_rows(library, now_playing="", downloads_active=0)
    playing_rows = podcast_status_rows(library, now_playing="Playing: Example", downloads_active=2)

    idle_values = {(section, setting): value for section, setting, value in idle_rows}
    playing_values = {(section, setting): value for section, setting, value in playing_rows}
    assert idle_values[("Podcasts", "Now playing")] == "Nothing playing"
    assert playing_values[("Podcasts", "Now playing")] == "Playing: Example"
    assert playing_values[("Podcasts", "Downloads in progress")] == "2"


def test_podcast_status_rows_reports_queue_length() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="A", episodes=[_episode("e1")]))
    library.queue_episode("s1", "e1")

    rows = podcast_status_rows(library, now_playing="", downloads_active=0)

    values = {(section, setting): value for section, setting, value in rows}
    assert values[("Podcasts", "Play Queue")] == "1 episode(s)"


def test_download_task_rows_resolves_episode_titles_and_progress() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Show", episodes=[_episode("g1")]))
    library.shows[0].episodes[0].title = "Episode One"

    queue = PodcastDownloadQueue()
    try:
        item = DownloadItem(
            item_id="item1",
            show_id="s1",
            episode_guid="g1",
            url="https://x/e.mp3",
            destination=Path("e.mp3"),
            status="downloading",
            bytes_downloaded=50,
            total_bytes=100,
            started_at="2026-07-13T00:00:00+00:00",
        )
        queue._items["item1"] = item  # direct injection: avoid a real network fetch
        queue._order.append("item1")

        rows = download_task_rows(queue, library)

        assert len(rows) == 1
        task, status, progress, started_at, finished_at = rows[0]
        assert task == "Download: Episode One"
        assert status == "Downloading"
        assert progress == "50% (50/100 bytes)"
        assert started_at == "2026-07-13T00:00:00+00:00"
        assert finished_at == ""
    finally:
        queue.shutdown()


def test_download_task_rows_falls_back_to_guid_for_unknown_episode() -> None:
    library = PodcastLibrary()
    queue = PodcastDownloadQueue()
    try:
        item = DownloadItem(
            item_id="item1",
            show_id="missing-show",
            episode_guid="g1",
            url="https://x/e.mp3",
            destination=Path("e.mp3"),
            status="failed",
        )
        queue._items["item1"] = item
        queue._order.append("item1")

        rows = download_task_rows(queue, library)

        assert rows[0][0] == "Download: g1"
        assert rows[0][1] == "Failed"
        assert rows[0][2] == "-"
    finally:
        queue.shutdown()
