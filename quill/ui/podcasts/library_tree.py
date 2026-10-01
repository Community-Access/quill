"""The pinned views open (cast-ux-plan P2): a node with a count has children.

Jeff, 2026-09-30: "favorites can not be expanded like podcasts can in the library
view even though it shows a count. why? shouldn't inbox also show items as well that
can be expanded? ... or what about new episodes?"

A node that says "(12)" and cannot be opened is a dead end wearing a number, and
it was every pinned view in the tree: Inbox, New Episodes, Continue Listening and
Favorites all carried counts and none had a single child. Podcasts expanded on
demand through a placeholder; the views were appended bare. So the one structure
the app puts focus on at launch answered Right-arrow with nothing, on exactly the
rows a listener is most likely to try first.

The fix is the mechanism podcasts already use: a placeholder child so the expander
exists, filled the first time the node opens. This module is the filling.

Two decisions:

* **A cross-show list names the podcast on every row.** "Thursday's episode" under
  the Inbox tells a listener nothing about which of forty podcasts it belongs to;
  the Manager's cross-show lists already carry the show name, and the tree does the
  same so the two never disagree.
* **Favorites opens to podcasts, not episodes.** Favorites is a set of shows, and a
  favourited show already expands to its own episodes one level down. Flattening
  its episodes here would show the same episode in two places with two different
  parents, which is the kind of thing that makes a tree untrustworthy.

Also here: what Play means on a view node. Pressing Play on the Inbox plays the
newest unstarted Inbox episode, because that is the only sensible reading of the
gesture and "select a show first" is a refusal dressed as help.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "PLACEHOLDER_VIEW",
    "add_view_placeholder",
    "fill_view_children",
    "first_playable_in_view",
]

#: The tag on a pinned view's unfilled child. Distinct from a podcast's
#: ``("placeholder", show_id)`` so the expand handler can tell them apart.
PLACEHOLDER_VIEW = "placeholder_view"

#: Rows shown under an opened view before a "more" row. The same cap podcasts use,
#: for the same reason: a 4,000-row New Episodes node built eagerly froze the tree.
_ROWS_PER_VIEW = 200


def add_view_placeholder(tree: Any, item: Any, view_id: str, count: int) -> None:
    """Give a view node an expander, when it has anything to expand to."""
    if count <= 0:
        return
    placeholder = tree.AppendItem(item, "Loading...")
    tree.SetItemData(placeholder, (PLACEHOLDER_VIEW, view_id))


def _view_pairs(library: Any, view_id: str) -> list[tuple[Any, Any]]:
    """``(show, episode)`` for a view, newest first -- the order the count promises."""
    from quill.core.podcasts.virtual_views import virtual_view_pairs

    pairs = list(virtual_view_pairs(library, view_id))
    pairs.sort(key=lambda pair: (pair[1].published or "", pair[1].title or ""), reverse=True)
    return pairs


def fill_view_children(host: Any, item: Any, view_id: str) -> None:
    """Replace a view's placeholder with what it counts. Called once, on expand."""
    tree = host._shows_tree
    library = host._podcast_library
    tree.DeleteChildren(item)

    if view_id == "favorites":
        from quill.core.podcasts.sorting import sort_shows, unheard_count
        from quill.core.podcasts.virtual_views import favorite_shows

        for show in sort_shows(favorite_shows(library), library.settings.show_sort_mode):
            count = unheard_count(show)
            label = f"{show.title} ({count} unheard)" if count else show.title
            child = tree.AppendItem(item, label)
            tree.SetItemData(child, ("show", show.id))
            # The same placeholder a podcast gets at the top level, so a favourite
            # opens to its episodes here exactly as it does in its folder.
            if show.episodes:
                more = tree.AppendItem(child, "Loading episodes...")
                tree.SetItemData(more, ("placeholder", show.id))
        return

    pairs = _view_pairs(library, view_id)
    for show, episode in pairs[:_ROWS_PER_VIEW]:
        child = tree.AppendItem(item, f"{episode.title} -- {show.title}")
        tree.SetItemData(child, ("episode", f"{show.id}\x00{episode.guid}"))
    hidden = len(pairs) - _ROWS_PER_VIEW
    if hidden > 0:
        more = tree.AppendItem(item, f"{hidden} more -- use the episode list to see them all")
        tree.SetItemData(more, ("more", ""))


def first_playable_in_view(library: Any, view_id: str) -> tuple[Any, Any] | None:
    """What Play means on a view node: its newest unstarted episode, or ``None``.

    Unstarted rather than merely unplayed, for the reason Play an Unheard Episode
    gives: a resume position means somebody is in the middle of that one, and
    starting it over from a one-press gesture is indistinguishable from losing
    their place. Continue Listening is the exception -- its whole content is
    started episodes, and Play there means "carry on with the most recent".
    """
    if view_id == "favorites":
        from quill.core.podcasts.virtual_views import favorite_shows

        for show in favorite_shows(library):
            for episode in sorted(show.episodes, key=lambda e: e.published or "", reverse=True):
                if not episode.played:
                    return (show, episode)
        return None
    pairs = _view_pairs(library, view_id)
    if view_id == "continue_listening":
        return pairs[0] if pairs else None
    for show, episode in pairs:
        if not episode.played and int(getattr(episode, "position_ms", 0) or 0) <= 0:
            return (show, episode)
    return None
