"""Rich, configurable sorting for podcast episodes and shows.

Pure functions -- no mutation, no I/O -- so the UI layer can call them
directly on whatever list it already has in hand. wx-free, strict-typed.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

EPISODE_SORT_MODES = (
    "date_newest",
    "date_oldest",
    "title_az",
    "duration_longest",
    "duration_shortest",
    "unplayed_first",
)

SHOW_SORT_MODES = ("title_az", "unheard_first", "recently_updated")


def _parse_published(published: str) -> float:
    """Best-effort RFC 2822 (typical RSS pubDate) parse to a sortable epoch
    timestamp; unparseable or empty dates sort as the oldest possible."""
    if not published:
        return 0.0
    try:
        return parsedate_to_datetime(published).timestamp()
    except (TypeError, ValueError):
        return 0.0


def sort_episodes(episodes: list[PodcastEpisode], mode: str) -> list[PodcastEpisode]:
    """Return a new list of *episodes* sorted by *mode* (unknown modes fall
    back to ``date_newest``)."""
    if mode == "date_oldest":
        return sorted(episodes, key=lambda e: _parse_published(e.published))
    if mode == "title_az":
        return sorted(episodes, key=lambda e: e.title.casefold())
    if mode == "duration_longest":
        return sorted(episodes, key=lambda e: e.duration_seconds, reverse=True)
    if mode == "duration_shortest":
        return sorted(episodes, key=lambda e: e.duration_seconds)
    if mode == "unplayed_first":
        return sorted(episodes, key=lambda e: (e.played, -_parse_published(e.published)))
    # "date_newest" and any unrecognized mode.
    return sorted(episodes, key=lambda e: _parse_published(e.published), reverse=True)


def _most_recent_episode_timestamp(show: PodcastShow) -> float:
    if not show.episodes:
        return 0.0
    return max(_parse_published(e.published) for e in show.episodes)


def _unheard_count(show: PodcastShow) -> int:
    return sum(1 for e in show.episodes if not e.played)


def sort_shows(shows: list[PodcastShow], mode: str) -> list[PodcastShow]:
    """Return a new list of *shows* sorted by *mode* (unknown modes fall back
    to ``title_az``)."""
    if mode == "unheard_first":
        return sorted(shows, key=lambda s: (-_unheard_count(s), s.title.casefold()))
    if mode == "recently_updated":
        return sorted(shows, key=lambda s: _most_recent_episode_timestamp(s), reverse=True)
    # "title_az" and any unrecognized mode.
    return sorted(shows, key=lambda s: s.title.casefold())
