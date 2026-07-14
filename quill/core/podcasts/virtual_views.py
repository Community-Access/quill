"""Pure aggregation logic for Podcasts' virtual views: pinned tree nodes
that cut across the real folder tree (Favorites, New Episodes, Continue
Listening). wx-free so the Podcast Manager dialog's tree-building code
doesn't have to carry this logic itself, and so it's unit-testable without
constructing any UI.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Pinned leaf nodes (aggregate episode lists): (view id, label).
VIRTUAL_VIEWS: tuple[tuple[str, str], ...] = (
    ("new_episodes", "New Episodes"),
    ("continue_listening", "Continue Listening"),
    ("inbox", "Inbox"),
)


def favorite_shows(library: PodcastLibrary) -> list[PodcastShow]:
    """Every show with ``is_favorite`` set, regardless of its real folder --
    Favorites is a flag, not a folder, so a show never has to choose
    between being properly filed and being starred."""
    return [show for show in library.shows if show.is_favorite]


def virtual_view_pairs(
    library: PodcastLibrary, view_id: str
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """``(show, episode)`` pairs for one of :data:`VIRTUAL_VIEWS` -- kept as
    real pairs (not a bare episode list) since these aggregate across shows."""
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        for episode in show.episodes:
            if view_id == "new_episodes" and not episode.played:
                pairs.append((show, episode))
            elif view_id == "continue_listening" and episode.position_ms > 0 and not episode.played:
                pairs.append((show, episode))
            elif view_id == "inbox" and show.route_to_inbox and not episode.played:
                pairs.append((show, episode))
    return pairs
