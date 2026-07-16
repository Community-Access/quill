"""Rich, configurable sorting for podcast episodes and shows.

Pure functions -- no mutation, no I/O -- so the UI layer can call them
directly on whatever list it already has in hand. wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

if TYPE_CHECKING:
    from quill.core.podcasts.subscriptions import PodcastLibrary

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


def _episode_sort_key(mode: str) -> tuple[Callable[[PodcastEpisode], Any], bool]:
    """(key function, reverse) for *mode* -- shared by :func:`sort_episodes`
    and :func:`sort_pairs` so a cross-show view sorts identically to a
    single show's own episode list."""
    if mode == "date_oldest":
        return (lambda e: _parse_published(e.published), False)
    if mode == "title_az":
        return (lambda e: e.title.casefold(), False)
    if mode == "duration_longest":
        return (lambda e: e.duration_seconds, True)
    if mode == "duration_shortest":
        return (lambda e: e.duration_seconds, False)
    if mode == "unplayed_first":
        return (lambda e: (e.played, -_parse_published(e.published)), False)
    # "date_newest" and any unrecognized mode.
    return (lambda e: _parse_published(e.published), True)


def sort_episodes(episodes: list[PodcastEpisode], mode: str) -> list[PodcastEpisode]:
    """Return a new list of *episodes* sorted by *mode* (unknown modes fall
    back to ``date_newest``)."""
    key, reverse = _episode_sort_key(mode)
    return sorted(episodes, key=key, reverse=reverse)


def sort_pairs(
    library: PodcastLibrary,
    pairs: list[tuple[PodcastShow, PodcastEpisode]],
    *,
    view_mode: str,
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Sort/group cross-show ``(show, episode)`` pairs for a virtual view
    (Inbox, New Episodes, Continue Listening, Favorites) or an Inbox folder,
    per *view_mode* (``PodcastSettings.episode_list_view_mode``):

    - ``"flat"``: one stream across every show, sorted by the library's
      global ``episode_sort_mode`` only. Per-show sort overrides do not
      apply here -- there is no single well-defined order once different
      shows compare by different keys.
    - ``"grouped"``/``"folders"``: pairs grouped contiguously by show (shows
      ordered by title); each show's own episodes sorted by *that show's*
      effective sort mode (its own override, or the library default) --
      read one podcast's backlog at a time, oldest-to-newest or
      newest-to-oldest, independently per podcast. ``"folders"`` presents
      this same grouping as real tree nodes instead of a flat list (see
      manager_phase4.py); the grouping/sorting itself is identical.
    """
    if view_mode == "flat":
        key, reverse = _episode_sort_key(library.settings.episode_sort_mode)
        return sorted(pairs, key=lambda pair: key(pair[1]), reverse=reverse)
    by_show: dict[str, list[tuple[PodcastShow, PodcastEpisode]]] = {}
    show_by_id: dict[str, PodcastShow] = {}
    for show, episode in pairs:
        by_show.setdefault(show.id, []).append((show, episode))
        show_by_id[show.id] = show
    result: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show_id in sorted(by_show, key=lambda sid: show_by_id[sid].title.casefold()):
        show = show_by_id[show_id]
        key, reverse = _episode_sort_key(library.effective_settings(show).episode_sort_mode)
        result.extend(sorted(by_show[show_id], key=lambda pair: key(pair[1]), reverse=reverse))
    return result


def _most_recent_episode_timestamp(show: PodcastShow) -> float:
    if not show.episodes:
        return 0.0
    return max(_parse_published(e.published) for e in show.episodes)


def unheard_count(show: PodcastShow) -> int:
    """Unplayed episodes in *show* -- shared by tree labels, sorting, and the
    Status page's podcast rows (status_report.py)."""
    return sum(1 for e in show.episodes if not e.played)


# Backward-compat private alias (pre-Phase-4 internal name).
_unheard_count = unheard_count


def sort_shows(shows: list[PodcastShow], mode: str) -> list[PodcastShow]:
    """Return a new list of *shows* sorted by *mode* (unknown modes fall back
    to ``title_az``)."""
    if mode == "unheard_first":
        return sorted(shows, key=lambda s: (-_unheard_count(s), s.title.casefold()))
    if mode == "recently_updated":
        return sorted(shows, key=lambda s: _most_recent_episode_timestamp(s), reverse=True)
    # "title_az" and any unrecognized mode.
    return sorted(shows, key=lambda s: s.title.casefold())
