"""Queue Expiration and Recently Expired (1.1.0).

The migration test is the one that matters most: a queue written before this
release has no ``added_at`` at all, and reading that as "infinitely old"
would empty every listener's queue on the first launch after updating.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.podcasts import expiration
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library(*, limit_days: int = 0) -> tuple[PodcastLibrary, PodcastShow, PodcastEpisode]:
    episode = PodcastEpisode(guid="e1", title="Episode One", audio_url="https://x/1.mp3")
    show = PodcastShow(id="s1", title="Show One", feed_url="https://x/feed", episodes=[episode])
    library = PodcastLibrary(shows=[show])
    if limit_days:
        library.apply_show_override(show, queue_age_limit_days=limit_days)
    return library, show, episode


def _ago(days: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def test_unstamped_queue_items_are_treated_as_added_now() -> None:
    library, show, episode = _library(limit_days=1)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))

    stamped = expiration.stamp_missing_added_at(library)

    assert stamped == 1
    assert library.queue[0].added_at
    # And crucially: the very next expiry pass keeps it.
    assert expiration.expire_stale_queue_items(library) == []
    assert len(library.queue) == 1


def test_stamping_never_overwrites_a_real_timestamp() -> None:
    library, show, episode = _library()
    original = _ago(3)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid, added_at=original))

    assert expiration.stamp_missing_added_at(library) == 0
    assert library.queue[0].added_at == original


def test_an_over_age_item_moves_to_recently_expired() -> None:
    library, show, episode = _library(limit_days=2)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid, added_at=_ago(5)))

    expired = expiration.expire_stale_queue_items(library)

    assert len(expired) == 1
    assert library.queue == []
    assert [e.episode_guid for e in library.recently_expired] == ["e1"]
    # Expiring is a queue action, never a delete: the episode is untouched.
    assert show.episodes == [episode]


def test_no_limit_means_nothing_ever_expires() -> None:
    library, show, episode = _library(limit_days=0)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid, added_at=_ago(400)))

    assert expiration.expire_stale_queue_items(library) == []
    assert len(library.queue) == 1


def test_a_younger_item_stays() -> None:
    library, show, episode = _library(limit_days=7)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid, added_at=_ago(2)))

    assert expiration.expire_stale_queue_items(library) == []
    assert len(library.queue) == 1


def test_a_stale_slot_is_dropped_rather_than_recorded() -> None:
    library, _show, _episode = _library(limit_days=1)
    library.queue.append(QueueItem(show_id="gone", episode_guid="also-gone", added_at=_ago(9)))

    expiration.expire_stale_queue_items(library)

    assert library.queue == []
    assert library.recently_expired == []


def test_restore_puts_it_back_with_a_fresh_timestamp() -> None:
    library, show, episode = _library(limit_days=1)
    library.recently_expired.append(
        ExpiredEntry(show_id=show.id, episode_guid=episode.guid, expired_at=_ago(1))
    )

    assert expiration.restore_expired(library, show.id, episode.guid) is True
    assert library.recently_expired == []
    assert len(library.queue) == 1
    # Freshly stamped, so restoring does not immediately re-expire it.
    assert expiration.expire_stale_queue_items(library) == []


def test_restore_all_restores_everything() -> None:
    library, show, _episode = _library()
    show.episodes.append(PodcastEpisode(guid="e2", title="Two", audio_url="https://x/2.mp3"))
    for guid in ("e1", "e2"):
        library.recently_expired.append(
            ExpiredEntry(show_id=show.id, episode_guid=guid, expired_at=_ago(1))
        )

    assert expiration.restore_all_expired(library) == 2
    assert len(library.queue) == 2
    assert library.recently_expired == []


def test_sweep_drops_entries_past_the_hold_window_and_deletes_the_file(tmp_path) -> None:
    library, show, episode = _library()
    media = tmp_path / "one.mp3"
    media.write_bytes(b"audio")
    episode.downloaded_path = str(media)
    library.recently_expired.append(
        ExpiredEntry(
            show_id=show.id,
            episode_guid=episode.guid,
            expired_at=_ago(expiration.RECENTLY_EXPIRED_HOLD_DAYS + 1),
        )
    )

    dropped, deleted = expiration.sweep_recently_expired(library)

    assert len(dropped) == 1
    assert deleted == 1
    assert not media.exists()
    assert episode.downloaded_path == ""
    # Still in the library -- only the local copy went.
    assert show.episodes == [episode]


def test_sweep_keeps_an_entry_still_inside_the_hold_window(tmp_path) -> None:
    library, show, episode = _library()
    media = tmp_path / "one.mp3"
    media.write_bytes(b"audio")
    episode.downloaded_path = str(media)
    library.recently_expired.append(
        ExpiredEntry(show_id=show.id, episode_guid=episode.guid, expired_at=_ago(1))
    )

    dropped, deleted = expiration.sweep_recently_expired(library)

    assert dropped == []
    assert deleted == 0
    assert media.exists()


def test_forget_leaves_the_downloaded_file_alone(tmp_path) -> None:
    library, show, episode = _library()
    media = tmp_path / "one.mp3"
    media.write_bytes(b"audio")
    episode.downloaded_path = str(media)
    library.recently_expired.append(
        ExpiredEntry(show_id=show.id, episode_guid=episode.guid, expired_at=_ago(1))
    )

    assert expiration.forget_expired(library, show.id, episode.guid) is True
    assert library.recently_expired == []
    assert media.exists()
    assert library.queue == []


@pytest.mark.parametrize("stamp", ["", "not a date", "2026-13-45"])
def test_an_unreadable_timestamp_never_expires_anything(stamp: str) -> None:
    library, show, episode = _library(limit_days=1)
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid, added_at=stamp))

    assert expiration.expire_stale_queue_items(library) == []
    assert len(library.queue) == 1
