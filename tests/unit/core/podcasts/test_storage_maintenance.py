from __future__ import annotations

import copy
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.podcasts import playback_cache, retention
from quill.core.podcasts import storage_maintenance as storage
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    cache = tmp_path / "playback-cache"
    cache.mkdir()
    (cache / "stream.mp3.part").write_bytes(b"x" * 17)
    monkeypatch.setattr(playback_cache, "cache_root", lambda: cache)
    episodes = []
    for number in range(3):
        path = tmp_path / f"e{number}.mp3"
        path.write_bytes(b"x" * (100 + number))
        episodes.append(
            PodcastEpisode(
                guid=f"e{number}",
                title=f"Episode {number}",
                audio_url="https://example.test/audio",
                published=(datetime.now(UTC) - timedelta(days=30 + number)).isoformat(),
                downloaded_path=str(path),
                played=number == 0,
            )
        )
    show = PodcastShow(id="show", title="Show", episodes=episodes)
    result = PodcastLibrary(shows=[show])
    result.apply_show_override(show, download_retention_days=1)
    return result


def test_planning_reuses_policy_without_deleting_or_leaking_hooks(library, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("A proposal must never delete a file")

    def hook(_path):
        return False

    def observer(_episode, _path):
        return None

    old_hook = retention.set_delete_hook(hook)
    old_observer = retention.set_delete_observer(observer)
    try:
        monkeypatch.setattr(Path, "unlink", forbidden)
        proposal = storage.plan_storage(copy.deepcopy(library), mode="free")
        assert len(proposal.downloads) == 3
        assert proposal.size == 303
        assert all(episode.downloaded_path for episode in library.shows[0].episodes)
        assert retention._delete_hook.get() is hook
        assert retention._delete_observer.get() is observer
    finally:
        retention.set_delete_hook(old_hook)
        retention.set_delete_observer(old_observer)


def test_usage_stats_each_download_once_and_prepares_both_filters(library, monkeypatch):
    original = Path.stat
    counts = {}
    paths = {episode.downloaded_path for episode in library.shows[0].episodes}

    def stat(path, **kwargs):
        if str(path) in paths:
            counts[str(path)] = counts.get(str(path), 0) + 1
        return original(path, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    result = storage.storage_usage(copy.deepcopy(library))
    assert result.files == 3
    assert result.size == 303
    assert result.streamed_size == 17
    assert result.rows[0].files == 3
    assert result.unheard_rows[0].unheard_files == 2
    assert result.unheard_rows[0].unheard_size == 203
    assert set(counts.values()) == {1}


def test_an_unreadable_stream_cache_is_not_reported_as_zero(library, monkeypatch):
    def denied(_path):
        raise PermissionError("The cache could not be inspected")

    monkeypatch.setattr(os, "scandir", denied)
    with pytest.raises(PermissionError, match="cache could not be inspected"):
        storage.storage_usage(copy.deepcopy(library))


@pytest.mark.parametrize("protected", ["queued", "started", "pinned", "transfer", "expired"])
def test_planning_protects_download_commitments(library, protected):
    episode = library.shows[0].episodes[1]
    key = ("show", episode.guid)
    extra = ()
    if protected == "queued":
        library.queue.append(QueueItem(*key))
    elif protected == "started":
        episode.position_ms = 1500
    elif protected == "pinned":
        library.extra_settings["storage_pinned"] = True
    elif protected == "transfer":
        extra = (key,)
    else:
        library.recently_expired.append(
            ExpiredEntry(*key, expired_at=datetime.now(UTC).isoformat())
        )
    proposal = storage.plan_storage(copy.deepcopy(library), mode="free", protected=extra)
    assert not any(key in target.references for target in proposal.downloads)


def test_a_newly_expired_queue_download_keeps_its_seven_day_hold(library):
    library.apply_show_override(library.shows[0], queue_age_limit_days=1)
    library.queue.append(
        QueueItem("show", "e1", added_at=(datetime.now(UTC) - timedelta(days=5)).isoformat())
    )
    proposal = storage.plan_storage(copy.deepcopy(library), mode="maintenance")
    assert proposal.queue[0].expired.episode_guid == "e1"
    assert not any(("show", "e1") in target.references for target in proposal.downloads)


def test_sweep_does_not_delete_a_download_that_was_requeued(library):
    library.recently_expired.append(
        ExpiredEntry("show", "e1", expired_at=(datetime.now(UTC) - timedelta(days=10)).isoformat())
    )
    library.queue.append(QueueItem("show", "e1", added_at=datetime.now(UTC).isoformat()))
    proposal = storage.plan_storage(copy.deepcopy(library), mode="maintenance")
    assert not proposal.expired
    assert not any(("show", "e1") in target.references for target in proposal.downloads)


def test_sweep_proposes_an_unqueued_download_after_its_hold(library):
    library.recently_expired.append(
        ExpiredEntry("show", "e1", expired_at=(datetime.now(UTC) - timedelta(days=10)).isoformat())
    )
    proposal = storage.plan_storage(copy.deepcopy(library), mode="maintenance")
    assert len(proposal.expired) == 1
    assert proposal.expired[0].before.episode_guid == "e1"
    swept = [target for target in proposal.downloads if target.reason == "expired"]
    assert len(swept) == 1
    assert swept[0].references == (("show", "e1"),)
    assert Path(swept[0].path).exists()


def test_active_transfer_protection_survives_queue_expiration(library):
    moment = datetime.now(UTC)
    library.apply_show_override(library.shows[0], queue_age_limit_days=1)
    library.queue.append(QueueItem("show", "e1", added_at=(moment - timedelta(days=5)).isoformat()))
    library.recently_expired.append(
        ExpiredEntry("show", "e1", expired_at=(moment - timedelta(days=10)).isoformat())
    )
    proposal = storage.plan_storage(
        copy.deepcopy(library), mode="maintenance", protected=(("show", "e1"),), now=moment
    )
    assert proposal.queue[0].expired.episode_guid == "e1"
    assert not proposal.expired
    assert not any(("show", "e1") in target.references for target in proposal.downloads)


def test_storage_pin_does_not_turn_downloads_into_fake_inbox_queue_members(library):
    show = library.shows[0]
    show.route_to_inbox = True
    library.apply_show_override(show, inbox_max_episodes=1)
    library.extra_settings["storage_pinned"] = True
    proposal = storage.plan_storage(copy.deepcopy(library), mode="maintenance")
    assert not proposal.downloads
    assert [change.key for change in proposal.inbox] == [("show", "e2")]


def test_delete_uses_file_identity_and_does_not_count_a_replacement(library):
    target = storage.plan_storage(copy.deepcopy(library), mode="free").downloads[0]
    Path(target.path).write_bytes(b"a newly downloaded replacement")
    result = storage.delete_files((target,))
    assert result[0].status == "changed"
    assert result[0].size == 0
    assert Path(target.path).read_bytes() == b"a newly downloaded replacement"


def test_delete_failure_and_missing_file_are_not_successful_counts(library, monkeypatch):
    targets = storage.plan_storage(copy.deepcopy(library), mode="free").downloads
    Path(targets[1].path).unlink()
    original = Path.unlink

    def unlink(path, **kwargs):
        if str(path) == targets[0].path:
            raise PermissionError("In use")
        return original(path, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    results = storage.delete_files(targets)
    assert [result.status for result in results] == ["failed", "missing", "removed"]
    assert sum(result.size for result in results) == targets[2].size
    assert all(episode.downloaded_path for episode in library.shows[0].episodes)


def test_unreadable_sizes_are_reported_and_never_used_for_eviction(library, monkeypatch):
    original = Path.stat
    path = library.shows[0].episodes[1].downloaded_path

    def stat(candidate, **kwargs):
        if str(candidate) == path:
            raise PermissionError("In use")
        return original(candidate, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    report = storage.storage_usage(copy.deepcopy(library))
    proposal = storage.plan_storage(copy.deepcopy(library), mode="free")
    assert report.unreadable == proposal.unreadable == 1
    assert not any(target.path == path for target in proposal.downloads)


def test_confirmed_removal_cannot_expand_to_a_new_download(library, tmp_path):
    proposal = storage.plan_storage(copy.deepcopy(library), mode="show", show_id="show")
    path = tmp_path / "new.mp3"
    path.write_bytes(b"new audio")
    library.shows[0].episodes.append(
        PodcastEpisode(
            guid="new", title="New", audio_url="https://example.test/new", downloaded_path=str(path)
        )
    )
    current = storage.plan_storage(
        copy.deepcopy(library), mode="show", show_id="show", allowed=proposal.downloads
    )
    assert len(current.downloads) == 3
    assert not any(target.path == str(path) for target in current.downloads)
