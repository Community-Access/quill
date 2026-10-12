"""Build isolated podcast-feed snapshots and prepare their refresh results."""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Any

SNAPSHOT_EPISODES_PER_TURN = 128


@dataclass(slots=True)
class _PreparedRefresh:
    library: Any
    show_id: str
    read: Any
    outcome: Any
    fresh: list[Any]
    queued: int
    returned: list[Any]
    queue_additions: list[Any]
    assignment_changes: dict[str, str | None]
    assignment_before: dict[str, str]
    playlist_additions: dict[str, list[Any]]
    auto_download: list[Any]
    episode_before: set[str] | None = None


def _snapshot_for_refresh(
    library: Any, show: Any, *, copied_show: Any | None = None
) -> tuple[Any, dict[str, str], dict[str, set[tuple[str, str]]]]:
    """Copy only the feed's working set; never expose live model objects to a worker."""
    from quill.core.podcasts.subscriptions import PodcastLibrary

    snapshot = PodcastLibrary()
    snapshot.shows = [copied_show if copied_show is not None else copy.deepcopy(show)]
    snapshot.settings = copy.deepcopy(library.settings)
    snapshot.last_auto_check = library.last_auto_check
    snapshot.extra_settings = copy.deepcopy(library.extra_settings)
    snapshot.show_labels = {show.id: list(library.show_labels.get(show.id, []))}
    snapshot.folders = copy.deepcopy(library.folders)
    snapshot.scope_overrides = copy.deepcopy(library.scope_overrides)
    snapshot.show_check_state = {show.id: copy.deepcopy(library.show_check_state.get(show.id, {}))}
    snapshot.episode_filters = (
        {show.id: copy.deepcopy(library.episode_filters[show.id])}
        if show.id in library.episode_filters
        else {}
    )
    snapshot.episode_filter_reviews = (
        {show.id: copy.deepcopy(library.episode_filter_reviews[show.id])}
        if show.id in library.episode_filter_reviews
        else {}
    )
    snapshot.episode_filter_exceptions = (
        {show.id: list(library.episode_filter_exceptions[show.id])}
        if show.id in library.episode_filter_exceptions
        else {}
    )
    snapshot.queue = copy.deepcopy([item for item in library.queue if item.show_id == show.id])
    snapshot.recently_expired = copy.deepcopy([
        entry for entry in library.recently_expired if entry.show_id == show.id
    ])
    snapshot.inbox_folders = copy.deepcopy(library.inbox_folders)
    inbox_prefix = f"{show.id}\n"
    snapshot.inbox_assignments = {
        key: value
        for key, value in library.inbox_assignments.items()
        if key.startswith(inbox_prefix)
    }
    from quill.core.podcasts.show_policy import default_playlist

    playlist_name = default_playlist(library, show)
    relevant_playlists = (
        [
            playlist
            for playlist in library.playlists
            if playlist.name == playlist_name and playlist.kind == "manual"
        ]
        if playlist_name
        else []
    )
    snapshot.playlists = copy.deepcopy(relevant_playlists)
    if not isinstance(snapshot, PodcastLibrary):
        raise TypeError("Podcast library snapshot has an unexpected type")

    assignment_before = dict(snapshot.inbox_assignments)
    playlist_items_before = {
        playlist.id: {(item.show_id, item.episode_guid) for item in playlist.items}
        for playlist in snapshot.playlists
    }
    return snapshot, assignment_before, playlist_items_before


def _copy_show_for_refresh(
    host: Any,
    show: Any,
    *,
    completed: Any,
    failed: Any,
) -> None:
    """Copy a large episode list over short UI turns before giving it to a worker."""
    episodes = list(show.episodes)
    if len(episodes) <= SNAPSHOT_EPISODES_PER_TURN:
        try:
            completed(copy.deepcopy(show))
        except Exception as error:
            failed(error)
        return

    try:
        copied_show = copy.copy(show)
        for item in fields(show):
            if item.name != "episodes":
                setattr(copied_show, item.name, copy.deepcopy(getattr(show, item.name)))
        copied_show.episodes = []
    except Exception as error:
        failed(error)
        return

    wx = getattr(host, "_wx", None)
    call_later = getattr(wx, "CallLater", None)
    if not callable(call_later):
        failed(RuntimeError("Cannot schedule a responsive feed snapshot without wx.CallLater"))
        return

    timers = host.__dict__.setdefault("_podcast_feed_snapshot_timers", [])
    offset = 0

    def copy_batch() -> None:
        nonlocal offset
        try:
            end = min(offset + SNAPSHOT_EPISODES_PER_TURN, len(episodes))
            copied_show.episodes.extend(copy.deepcopy(episodes[offset:end]))
            offset = end
        except Exception as error:
            failed(error)
            return
        if offset < len(episodes):
            schedule_batch()
            return
        completed(copied_show)

    def schedule_batch() -> None:
        timer_holder: list[Any] = []

        def run_batch() -> None:
            if timer_holder:
                timer = timer_holder[0]
                timers[:] = [active for active in timers if active is not timer]
            copy_batch()

        try:
            timer = call_later(1, run_batch)
        except Exception as error:
            failed(error)
            return
        timer_holder.append(timer)
        timers.append(timer)

    schedule_batch()


def _prepare_refresh(
    library: Any,
    show_id: str,
    info: Any,
    notes: Any,
    *,
    assignment_before: dict[str, str],
    playlist_items_before: dict[str, set[tuple[str, str]]],
    safe_mode: bool,
) -> _PreparedRefresh:
    """Merge and decide feed routes using a detached model on a worker."""
    from quill.core.podcasts import (
        acquisition,
        episode_filter_maintenance,
        feed_read,
        inbox,
    )

    show = library.find_show(show_id)
    if show is None:
        raise ValueError(f"Podcast {show_id!r} disappeared from the refresh snapshot")
    queue_start = len(library.queue)
    episode_before = {episode.guid for episode in show.episodes}
    read = feed_read.record_success(library, show, info, notes)
    outcome = episode_filter_maintenance.route_refresh(library, show, read.arrived)
    fresh = outcome.for_scope("notify", episode_filter_maintenance.governs(library, show, "notify"))
    queue_fresh = outcome.for_scope(
        "queue", episode_filter_maintenance.governs(library, show, "queue")
    )
    queued = acquisition.route_new_episodes(library, show, queue_fresh)

    from quill.core.podcasts.models import QueueItem
    from quill.core.podcasts.show_policy import default_playlist, republished_as_new

    playlist_name = default_playlist(library, show)
    if playlist_name and fresh:
        target = next(
            (
                playlist
                for playlist in library.playlists
                if playlist.name == playlist_name and playlist.kind == "manual"
            ),
            None,
        )
        if target is not None:
            known = {(item.show_id, item.episode_guid) for item in target.items}
            for episode in fresh:
                key = (show.id, episode.guid)
                if key not in known:
                    target.items.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
                    known.add(key)

    returned = (
        inbox.resurface_republished(library, show, read.republished)
        if republished_as_new(library, show)
        else []
    )

    auto_download_guids: list[str] = []
    if not safe_mode and not show.paused:
        queued_guids = frozenset(
            item.episode_guid for item in library.queue if item.show_id == show.id
        )
        inbox_guids = frozenset(
            episode.guid
            for inbox_show, episode in inbox.inbox_pairs(library)
            if inbox_show.id == show.id
        )
        auto_download_guids = [
            episode.guid
            for episode in acquisition.episodes_to_auto_download(
                library, show, queued_guids=queued_guids, inbox_guids=inbox_guids
            )
        ]

    assignment_changes = {
        key: library.inbox_assignments.get(key)
        for key, previous in assignment_before.items()
        if library.inbox_assignments.get(key) != previous
    }
    playlist_additions: dict[str, list[Any]] = {}
    for playlist in library.playlists:
        before = playlist_items_before.get(playlist.id, set())
        additions = [
            item for item in playlist.items if (item.show_id, item.episode_guid) not in before
        ]
        if additions:
            playlist_additions[playlist.id] = additions

    return _PreparedRefresh(
        library=library,
        show_id=show_id,
        read=read,
        outcome=outcome,
        fresh=fresh,
        queued=queued,
        returned=returned,
        queue_additions=library.queue[queue_start:],
        assignment_changes=assignment_changes,
        assignment_before=assignment_before,
        playlist_additions=playlist_additions,
        auto_download=[
            episode
            for guid in auto_download_guids
            if (episode := show.find_episode(guid)) is not None
        ],
        episode_before=episode_before,
    )


def _same_routing(live: Any, working: Any, show_id: str) -> bool:
    current = live.find_show(show_id)
    original = working.find_show(show_id)
    if current is None or original is None:
        return False
    return (
        live.effective_settings(current) == working.effective_settings(original)
        and current.folder_id == original.folder_id
        and current.paused == original.paused
        and current.route_to_inbox == original.route_to_inbox
        and current.inbox_default_folder_id == original.inbox_default_folder_id
        and current.auto_queue == original.auto_queue
        and live.extra_settings == working.extra_settings
        and live.scope_overrides == working.scope_overrides
        and live.episode_filters.get(show_id) == working.episode_filters.get(show_id)
        and live.episode_filter_exceptions.get(show_id)
        == working.episode_filter_exceptions.get(show_id)
    )
