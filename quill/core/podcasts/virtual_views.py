"""Pure aggregation logic for Podcasts' virtual views: pinned tree nodes
that cut across the real folder tree (Favorites, New Episodes, Continue
Listening). wx-free so the Podcast Manager dialog's tree-building code
doesn't have to carry this logic itself, and so it's unit-testable without
constructing any UI.
"""

from __future__ import annotations

from collections.abc import Iterator

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Pinned leaf nodes (aggregate episode lists): (view id, label).
VIRTUAL_VIEWS: tuple[tuple[str, str], ...] = (
    ("new_episodes", "New Episodes"),
    ("continue_listening", "Continue Listening"),
    ("inbox", "Inbox"),
)

#: Every pinned view a listener can rename, id -> its shipped label. These
#: ship with the app, so they are the one kind of tree node that is *yours*
#: to personalize -- unlike shows and episodes, whose names belong to their
#: feeds. ``recently_expired`` appears in the Podcast Manager only, but a
#: rename still follows it there.
DEFAULT_VIEW_LABELS: dict[str, str] = {
    "favorites": "Favorites",
    **dict(VIRTUAL_VIEWS),
    "recently_expired": "Recently Expired",
}


def view_label(library: PodcastLibrary, view_id: str) -> str:
    """What a pinned view is called right now: the listener's own name for it
    when they set one (``PodcastSettings.view_names``), the shipped label
    otherwise."""
    custom = library.settings.view_names.get(view_id, "").strip()
    return custom or DEFAULT_VIEW_LABELS.get(view_id, view_id)


def set_view_name(library: PodcastLibrary, view_id: str, name: str) -> bool:
    """Give a pinned view a personal name; returns True when anything changed.

    Setting a view's shipped label (or a blank) is a reset, so the settings
    file only ever stores genuine customizations.
    """
    if view_id not in DEFAULT_VIEW_LABELS:
        return False
    wanted = name.strip()
    if not wanted or wanted == DEFAULT_VIEW_LABELS[view_id]:
        return reset_view_name(library, view_id)
    if library.settings.view_names.get(view_id) == wanted:
        return False
    library.settings.view_names[view_id] = wanted
    return True


def reset_view_name(library: PodcastLibrary, view_id: str) -> bool:
    """Back to the shipped label; returns True when a custom name was removed."""
    return library.settings.view_names.pop(view_id, None) is not None


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
    return list(iter_virtual_view_pairs(library, view_id))


def iter_virtual_view_pairs(
    library: PodcastLibrary, view_id: str
) -> Iterator[tuple[PodcastShow, PodcastEpisode]]:
    """Iterate a view once; counts must not build and filter a second catalogue."""
    if view_id == "inbox":
        # Delegated so the Inbox has exactly one definition: notably, an
        # episode an Inbox cap trimmed out is not in the Inbox any more, and
        # a second copy of the rule here would have missed that.
        # ...and through the folder scope (R4), so the tree count, the
        # Manager's list and the window title narrow together. A second
        # place that applied the filter is a place that could forget to.
        from quill.core.podcasts.inbox_scope import iter_inbox_pairs_in_library_folder

        yield from iter_inbox_pairs_in_library_folder(
            library, getattr(library.settings, "inbox_folder_scope", None)
        )
        return
    if view_id == "recently_expired":
        from quill.core.podcasts.expiration import expired_pairs

        yield from expired_pairs(library)
        return
    from quill.core.podcasts.episode_filter_maintenance import hide_predicate
    from quill.core.podcasts.models_filters import SCOPE_VIEWS

    for show in library.shows:
        hidden = hide_predicate(library, show, SCOPE_VIEWS)
        for episode in show.episodes:
            included = (view_id == "new_episodes" and not episode.played) or (
                view_id == "continue_listening" and episode.position_ms > 0 and not episode.played
            )
            if included and (hidden is None or not hidden(episode)):
                yield show, episode
