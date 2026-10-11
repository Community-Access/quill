"""Remove a subscription's local references and restore only its own Undo delta."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from quill.core.podcasts.models import ExpiredEntry, QueueItem
from quill.core.podcasts.models_filters import EpisodeFilterConfiguration

if TYPE_CHECKING:
    from quill.core.podcasts.subscriptions import PodcastLibrary


@dataclass
class ShowCuration:
    copies: list[str | None] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    overrides: dict[str, object] = field(default_factory=dict)
    check_state: dict[str, object] = field(default_factory=dict)
    filters: EpisodeFilterConfiguration | None = None
    review: str | None = None
    exceptions: list[str] = field(default_factory=list)
    assignments: dict[str, str] = field(default_factory=dict)
    queue: list[tuple[int, QueueItem]] = field(default_factory=list)
    expired: list[tuple[int, ExpiredEntry]] = field(default_factory=list)
    playlists: dict[str, list[tuple[int, QueueItem]]] = field(default_factory=dict)


def capture(library: PodcastLibrary, show_id: str) -> ShowCuration:
    prefix = f"{show_id}\n"
    return ShowCuration(
        copies=list(library.show_folder_copies.get(show_id, [])),
        labels=list(library.show_labels.get(show_id, [])),
        overrides=copy.deepcopy(library.scope_overrides.get(f"show:{show_id}", {})),
        check_state=copy.deepcopy(library.show_check_state.get(show_id, {})),
        filters=copy.deepcopy(library.episode_filters.get(show_id)),
        review=library.episode_filter_reviews.get(show_id),
        exceptions=list(library.episode_filter_exceptions.get(show_id, [])),
        assignments={
            key: value for key, value in library.inbox_assignments.items() if key.startswith(prefix)
        },
        queue=[
            (index, item) for index, item in enumerate(library.queue) if item.show_id == show_id
        ],
        expired=[
            (index, item)
            for index, item in enumerate(library.recently_expired)
            if item.show_id == show_id
        ],
        playlists={
            playlist.id: [
                (index, item)
                for index, item in enumerate(playlist.items)
                if item.show_id == show_id
            ]
            for playlist in library.playlists
            if playlist.kind == "manual"
        },
    )


def clear(library: PodcastLibrary, show_ids: set[str]) -> None:
    library.queue[:] = [item for item in library.queue if item.show_id not in show_ids]
    library.recently_expired[:] = [
        item for item in library.recently_expired if item.show_id not in show_ids
    ]
    for playlist in library.playlists:
        playlist.items[:] = [item for item in playlist.items if item.show_id not in show_ids]
    library.inbox_assignments = {
        key: value
        for key, value in library.inbox_assignments.items()
        if key.partition("\n")[0] not in show_ids
    }
    for show_id in show_ids:
        library.show_folder_copies.pop(show_id, None)
        library.show_labels.pop(show_id, None)
        library.scope_overrides.pop(f"show:{show_id}", None)
        library.show_check_state.pop(show_id, None)
        library.episode_filters.pop(show_id, None)
        library.episode_filter_reviews.pop(show_id, None)
        library.episode_filter_exceptions.pop(show_id, None)


def _restore_queue(target: list[QueueItem], removed: list[tuple[int, QueueItem]]) -> None:
    keys = {(item.show_id, item.episode_guid) for item in target}
    for index, item in removed:
        key = (item.show_id, item.episode_guid)
        if key not in keys:
            target.insert(min(index, len(target)), item)
            keys.add(key)


def restore(library: PodcastLibrary, show_id: str, removed: ShowCuration) -> None:
    show = library.find_show(show_id)
    copies = [
        folder
        for folder in removed.copies
        if (show is None or folder != show.folder_id)
        and (folder is None or library.find_folder(folder))
    ]
    if copies:
        library.show_folder_copies.setdefault(show_id, copies)
    if removed.labels:
        library.show_labels.setdefault(show_id, removed.labels)
    if removed.overrides:
        library.scope_overrides.setdefault(f"show:{show_id}", removed.overrides)
    if removed.check_state:
        library.show_check_state.setdefault(show_id, removed.check_state)
    if removed.filters is not None:
        library.episode_filters.setdefault(show_id, removed.filters)
    if removed.review is not None:
        library.episode_filter_reviews.setdefault(show_id, removed.review)
    if removed.exceptions:
        library.episode_filter_exceptions.setdefault(show_id, removed.exceptions)
    inbox_ids = {folder.id for folder in library.inbox_folders}
    for key, value in removed.assignments.items():
        if not value or value in inbox_ids:
            library.inbox_assignments.setdefault(key, value)
    _restore_queue(library.queue, removed.queue)
    known = {(item.show_id, item.episode_guid) for item in library.recently_expired}
    for index, item in removed.expired:
        if (item.show_id, item.episode_guid) not in known:
            library.recently_expired.insert(min(index, len(library.recently_expired)), item)
            known.add((item.show_id, item.episode_guid))
    for playlist_id, entries in removed.playlists.items():
        playlist = library.find_playlist(playlist_id)
        if playlist is not None and playlist.kind == "manual":
            _restore_queue(playlist.items, entries)
