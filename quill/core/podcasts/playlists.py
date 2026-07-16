"""Saved playlists (Phase 5): resolving a Smart Playlist's rules against the
library, and resolving a manual Playlist's stored episode references.
Mirrors ``podcasts.queue``'s split from ``models.py`` (data class there,
operations here) and reuses ``podcasts.sorting``'s private sort-key builder
so a Smart Playlist orders its results exactly like every other episode
list in the app. wx-free, strict-typed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from quill.core.podcasts.sorting import _episode_sort_key, _parse_published

if TYPE_CHECKING:
    from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary


def new_playlist_id() -> str:
    return uuid.uuid4().hex


def resolve_playlist(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """The playlist's current episode list: resolved live from ``rules``
    for a Smart Playlist, or the stored ``items`` (self-healing -- a
    reference to a since-unsubscribed show or vanished episode simply drops
    out) for a manual one."""
    if playlist.kind == "smart":
        return _resolve_smart(library, playlist)
    return _resolve_manual(library, playlist)


def _resolve_manual(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    result: list[tuple[PodcastShow, PodcastEpisode]] = []
    for item in playlist.items:
        show = library.find_show(item.show_id)
        if show is None:
            continue
        episode = show.find_episode(item.episode_guid)
        if episode is None:
            continue
        result.append((show, episode))
    return result


def _resolve_smart(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    rules = playlist.rules
    show_filter = set(rules.show_ids) if rules.show_ids else None
    cutoff = (
        datetime.now(UTC) - timedelta(days=rules.published_within_days)
        if rules.published_within_days > 0
        else None
    )
    min_seconds = rules.min_duration_minutes * 60
    max_seconds = rules.max_duration_minutes * 60
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        if show_filter is not None and show.id not in show_filter:
            continue
        for episode in show.episodes:
            if rules.episode_status == "unplayed" and episode.played:
                continue
            if rules.episode_status == "played" and not episode.played:
                continue
            if rules.episode_status == "in_progress" and not (
                episode.position_ms > 0 and not episode.played
            ):
                continue
            if min_seconds > 0 and episode.duration_seconds < min_seconds:
                continue
            if max_seconds > 0 and episode.duration_seconds > max_seconds:
                continue
            if cutoff is not None:
                published = _parse_published(episode.published)
                if published <= 0 or published < cutoff.timestamp():
                    continue
            pairs.append((show, episode))
    key, reverse = _episode_sort_key(rules.sort_mode)
    return sorted(pairs, key=lambda pair: key(pair[1]), reverse=reverse)
