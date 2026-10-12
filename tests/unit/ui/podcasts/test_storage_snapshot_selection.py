"""Sparse storage generations preserve the complete storage-policy outcome."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from quill.core.podcasts import inbox
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.storage_maintenance import plan_storage
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.storage_snapshot import StorageCapture, capture_chunks


def _capture(library, *, include_inbox=True):
    captured = StorageCapture(library, PodcastLibrary(), ())
    host = SimpleNamespace(_podcast_controller=None)
    for _item in capture_chunks(host, captured, include_inbox=include_inbox):
        pass
    return captured


def test_unrelated_catalogue_entries_do_not_allocate_duplicate_episode_graphs():
    show = PodcastShow(
        id="show",
        title="Show",
        episodes=[
            PodcastEpisode(guid=str(index), title=str(index), audio_url="") for index in range(2000)
        ],
    )
    show.episodes[0].downloaded_path = "synthetic.mp3"
    library = PodcastLibrary(
        shows=[show],
        queue=[QueueItem("show", "1")],
        recently_expired=[ExpiredEntry("show", "2", "2026-10-01T00:00:00+00:00")],
    )

    captured = _capture(library)

    assert [episode.guid for episode in captured.library.shows[0].episodes] == ["0", "1", "2"]
    assert set(captured.episodes) == {("show", "0"), ("show", "1"), ("show", "2")}
    assert captured.library.shows[0].episodes[0] is not show.episodes[0]
    assert len(show.episodes) == 2000


@pytest.mark.parametrize(
    ("inbox_mode", "route"),
    [("include", True), ("include", False), ("exclude", True), ("exclude", False)],
)
def test_sparse_maintenance_matches_full_queue_expiration_and_inbox_caps(
    inbox_mode, route, tmp_path
):
    moment = datetime(2026, 10, 10, tzinfo=UTC)
    old = (moment - timedelta(days=30)).isoformat()
    path = tmp_path / "synthetic.mp3"
    path.write_bytes(b"synthetic")
    show = PodcastShow(
        id="show",
        title="Show",
        route_to_inbox=route,
        episodes=[
            PodcastEpisode(
                guid=str(index), title=str(index), audio_url="", published=old, played=index == 8
            )
            for index in range(12)
        ],
    )
    show.episodes[0].downloaded_path = str(path)
    show.episodes[7].position_ms = 1000
    library = PodcastLibrary(
        shows=[show],
        queue=[QueueItem("show", "1", added_at=old)],
        recently_expired=[ExpiredEntry("show", "2", old)],
        inbox_assignments={inbox.inbox_key("show", "9"): "manual"},
    )
    library.settings.inbox_mode = inbox_mode
    library.apply_show_override(
        show, inbox_max_episodes=2, inbox_age_limit_hours=0, queue_age_limit_days=1
    )
    captured = _capture(library)

    expected = plan_storage(copy.deepcopy(library), mode="maintenance", now=moment)
    actual = plan_storage(captured.library, mode="maintenance", now=moment)

    assert actual == expected
    assert library.queue[0].episode_guid == "1"
    assert library.inbox_assignments == {inbox.inbox_key("show", "9"): "manual"}
    assert show.episodes[0].downloaded_path == str(path)


def test_downloads_report_excludes_the_full_opt_out_inbox_catalogue():
    show = PodcastShow(
        id="show",
        title="Show",
        episodes=[
            PodcastEpisode(guid=str(index), title=str(index), audio_url="") for index in range(1000)
        ],
    )
    library = PodcastLibrary(shows=[show])
    library.settings.inbox_mode = "exclude"
    library.settings.inbox_max_episodes = 2
    show.episodes[0].downloaded_path = "synthetic.mp3"

    captured = _capture(library, include_inbox=False)

    assert [episode.guid for episode in captured.library.shows[0].episodes] == ["0"]


def test_shared_downloads_and_keep_last_n_match_the_complete_generation(tmp_path):
    moment = datetime(2026, 10, 10, tzinfo=UTC)
    old = (moment - timedelta(days=40)).isoformat()
    path = tmp_path / "shared.mp3"
    path.write_bytes(b"synthetic shared file")
    shows = [
        PodcastShow(
            id=str(index),
            title=str(index),
            episodes=[
                PodcastEpisode(
                    guid="download",
                    title="Downloaded",
                    audio_url="",
                    published=old,
                    downloaded_path=str(path),
                    played=index == 0,
                ),
                PodcastEpisode(guid="catalogue-only", title="Unrelated", audio_url=""),
            ],
        )
        for index in range(2)
    ]
    library = PodcastLibrary(shows=shows)
    for show in shows:
        library.apply_show_override(
            show, download_retention_days=1, retention="keep_last_n", retention_count=1
        )
    captured = _capture(library, include_inbox=False)

    expected = plan_storage(copy.deepcopy(library), mode="free", now=moment)
    actual = plan_storage(captured.library, mode="free", now=moment)

    assert actual == expected
    assert [len(show.episodes) for show in captured.library.shows] == [1, 1]
    assert path.exists()
