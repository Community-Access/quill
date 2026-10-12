"""Catch up changed records without restarting a whole-library detached copy."""

from __future__ import annotations

import copy
from collections.abc import Generator
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from quill.core.podcasts.library_payload import LibraryPayload, serialize
from quill.ui.podcasts.library_snapshot import snapshot_chunks
from quill.ui.podcasts.payload_snapshot import show_payload_chunks


@dataclass(frozen=True)
class SaveScope:
    show_id: str
    episode_guid: str | None = None


_scope: ContextVar[SaveScope | None] = ContextVar("podcast_save_scope", default=None)


def save_show(host: Any, show_id: str, *, episode_guid: str | None = None) -> None:
    token = _scope.set(SaveScope(show_id, episode_guid))
    try:
        host._save_podcast_library()
    finally:
        _scope.reset(token)


def current_scope() -> SaveScope | None:
    return _scope.get()


@dataclass
class Changes:
    shows: dict[str, int] = field(default_factory=dict)
    episodes: dict[tuple[str, str], int] = field(default_factory=dict)
    metadata_revision: int = 0

    def record(self, scope: SaveScope) -> None:
        if scope.episode_guid is None:
            self.metadata_revision += 1
            self.shows[scope.show_id] = self.shows.get(scope.show_id, 0) + 1
        else:
            key = (scope.show_id, scope.episode_guid)
            self.episodes[key] = self.episodes.get(key, 0) + 1


def coherent_chunks(
    host: Any, changes: Changes, *, json_payload: bool = False
) -> Generator[None, None, Any]:
    library = host._podcast_library
    if json_payload:
        shows = yield from show_payload_chunks(library)
        snapshot = None
    else:
        snapshot = yield from snapshot_chunks(library)
        shows = snapshot.shows
    by_id = {
        (show["id"] if json_payload else show.id): index
        for index, show in enumerate(shows)
        if json_payload or hasattr(show, "id")
    }
    episode_indices: dict[str, dict[str, int]] = {}
    while True:
        while changes.shows:
            show_id, version = next(iter(changes.shows.items()))
            if json_payload:
                copied_shows = yield from show_payload_chunks(library, show_ids={show_id})
            else:
                copied = yield from snapshot_chunks(library, show_ids={show_id}, shows_only=True)
                copied_shows = copied.shows
            if changes.shows.get(show_id) != version:
                continue
            if not copied_shows or show_id not in by_id:
                raise RuntimeError("The podcast list changed while preparing a scoped save")
            shows[by_id[show_id]] = copied_shows[0]
            episode_indices.pop(show_id, None)
            del changes.shows[show_id]
            yield

        def catch_up_episodes() -> Generator[None]:
            copied_count = 0
            while changes.episodes:
                key, version = next(iter(changes.episodes.items()))
                show_id, guid = key
                if show_id not in by_id:
                    raise RuntimeError("A podcast disappeared while preparing a scoped save")
                source_show = library.find_show(show_id)
                target_show = shows[by_id[show_id]]
                target_episodes = target_show["episodes"] if json_payload else target_show.episodes
                indices = episode_indices.get(show_id)
                if indices is None:
                    indices = {}
                    for index, episode in enumerate(target_episodes):
                        indices[episode["guid"] if json_payload else episode.guid] = index
                        if (index + 1) % 128 == 0:
                            yield
                    episode_indices[show_id] = indices
                source_episode = source_show.find_episode(guid) if source_show is not None else None
                if source_episode is None or guid not in indices:
                    raise RuntimeError("An episode disappeared while preparing a scoped save")
                target_episodes[indices[guid]] = (
                    source_episode.to_dict() if json_payload else copy.deepcopy(source_episode)
                )
                if changes.episodes.get(key) == version:
                    del changes.episodes[key]
                copied_count += 1
                if copied_count % 128 == 0:
                    yield

        yield from catch_up_episodes()
        revision = changes.metadata_revision
        metadata = yield from snapshot_chunks(library, metadata_only=True)
        yield from catch_up_episodes()
        if changes.shows or revision != changes.metadata_revision:
            continue
        if json_payload:
            metadata.shows = []
            data = serialize(metadata)
            data["shows"] = shows
            return LibraryPayload(data)
        metadata.shows = shows
        return metadata
