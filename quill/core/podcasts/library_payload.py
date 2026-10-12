"""Detached JSON generations, with the same on-disk shape as the library model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.podcasts.watched_folders import serialise as serialise_watched

if TYPE_CHECKING:
    from quill.core.podcasts.subscriptions import PodcastLibrary


@dataclass(frozen=True, slots=True)
class LibraryPayload:
    data: dict[str, object]


def serialize(library: PodcastLibrary) -> dict[str, object]:
    return {
        "shows": [show.to_dict() for show in library.shows],
        "folders": [folder.to_dict() for folder in library.folders],
        "settings": library.settings.to_dict(),
        "queue": [item.to_dict() for item in library.queue],
        "inbox_folders": [folder.to_dict() for folder in library.inbox_folders],
        "inbox_assignments": dict(library.inbox_assignments),
        "playlists": [playlist.to_dict() for playlist in library.playlists],
        "recently_expired": [entry.to_dict() for entry in library.recently_expired],
        "episode_filters": {
            show_id: config.to_dict() for show_id, config in library.episode_filters.items()
        },
        "episode_filter_reviews": dict(library.episode_filter_reviews),
        "episode_filter_exceptions": {
            show_id: list(guids) for show_id, guids in library.episode_filter_exceptions.items()
        },
        "extra_settings": dict(library.extra_settings),
        "scope_overrides": {
            scope: dict(values) for scope, values in library.scope_overrides.items() if values
        },
        "show_labels": {
            show_id: list(names) for show_id, names in library.show_labels.items() if names
        },
        "show_folder_copies": {
            show_id: list(folders)
            for show_id, folders in library.show_folder_copies.items()
            if folders
        },
        "show_check_state": {
            show_id: dict(state) for show_id, state in library.show_check_state.items() if state
        },
        "onboarding": library.onboarding.to_dict(),
        "last_auto_check": library.last_auto_check,
        "watched_folders": serialise_watched(library.watched_folders),
    }
