"""A library folder as a place you listen from, not just a place shows are filed.

Cast has had the folder tree for a long time -- create, rename, delete, nest to
any depth, file a show into one -- and has never had a single action *on* a
folder. Grep for "play all" across ``core/podcasts`` and ``ui/podcasts``
returned nothing. So forty shows filed into "News" made the list tidier and did
nothing at all for the listening.

**A folder means its whole subtree.** ``News`` and ``News/Local`` are two
folders that read as one tree, and playing "News" while the six shows in
``News/Local`` sat unplayed would be the wrong answer to the question that was
asked. One walk (:func:`subtree_show_ids`) is what everything else here reuses,
so no two actions can disagree about what a folder contains.

**"Play all unplayed" cannot mean every unplayed episode.** A folder of forty
shows holds hundreds, and a queue of hundreds is not a queue. It means the
newest unplayed episode of each show -- which is what somebody choosing a folder
is actually asking for: one round of what is new.

**Reordering is not drag and drop.** Move Up and Move Down on a folder, with the
new position announced, because a folder tree rearranged by mouse is a folder
tree that cannot be rearranged at all by somebody using a screen reader.

wx-free, strict-typed, pure. Nothing here plays, saves, or announces: the caller
owns all three.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.podcasts.models import PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "describe_folder",
    "folder_show_pairs",
    "latest_unplayed_per_show",
    "move_folder",
    "reorder_folder",
    "shows_in_folder",
    "subtree_folder_ids",
    "subtree_show_ids",
    "unplayed_in_folder",
]


def subtree_folder_ids(library: PodcastLibrary, folder_id: str) -> list[str]:
    """*folder_id* and every folder beneath it, breadth first.

    Cycle-safe: a folder tree that has somehow become a ring -- a hand-edited
    file, or a bug in something that moved one -- must not hang the app, and
    every walk in this module goes through here.
    """
    # A folder id nobody has is not a folder with nothing in it: it is not a
    # folder, and every caller reads the empty list as "there is no such
    # place". Without this, exporting a deleted folder writes a valid, empty
    # OPML document rather than saying there was nothing to export.
    if not folder_id or _find(library, folder_id) is None:
        return []
    seen: set[str] = {folder_id}
    ordered = [folder_id]
    queue = [folder_id]
    while queue:
        current = queue.pop(0)
        for folder in getattr(library, "folders", []) or []:
            child = str(getattr(folder, "id", ""))
            if getattr(folder, "parent_folder_id", None) == current and child not in seen:
                seen.add(child)
                ordered.append(child)
                queue.append(child)
    return ordered


def subtree_show_ids(library: PodcastLibrary, folder_id: str) -> list[str]:
    """Every show in *folder_id* or any folder beneath it, in library order."""
    wanted = set(subtree_folder_ids(library, folder_id))
    if not wanted:
        return []
    return [
        str(show.id)
        for show in getattr(library, "shows", []) or []
        if str(getattr(show, "folder_id", "") or "") in wanted
    ]


def shows_in_folder(library: PodcastLibrary, folder_id: str) -> list[PodcastShow]:
    """The show records, rather than their ids."""
    wanted = set(subtree_show_ids(library, folder_id))
    return [show for show in getattr(library, "shows", []) or [] if str(show.id) in wanted]


def _sorted_episodes(library: PodcastLibrary, show: PodcastShow) -> list[PodcastEpisode]:
    """*show*'s episodes in its own effective order.

    Through ``sorting.sort_episodes`` and the show's effective settings rather
    than a local rule, so a folder plays a show in the order that show's own
    list shows it in -- which is the order the listener has already learned.
    """
    from quill.core.podcasts.sorting import sort_episodes

    try:
        mode = str(library.effective_settings(show).episode_sort_mode)
    except Exception:  # noqa: BLE001 - a show with no settings sorts by the default
        mode = "newest"
    return sort_episodes(list(getattr(show, "episodes", []) or []), mode)


def folder_show_pairs(
    library: PodcastLibrary, folder_id: str
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Every episode in the folder, show by show, each show in its own order."""
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in shows_in_folder(library, folder_id):
        pairs.extend((show, episode) for episode in _sorted_episodes(library, show))
    return pairs


def unplayed_in_folder(
    library: PodcastLibrary, folder_id: str
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Every *unplayed* episode in the folder, show by show.

    Unplayed means neither finished nor started: an episode somebody is part
    way through is a decision they have already made, and sweeping it into a
    folder queue would move their place in it.
    """
    return [
        (show, episode)
        for show, episode in folder_show_pairs(library, folder_id)
        if not getattr(episode, "played", False)
        and not int(getattr(episode, "position_ms", 0) or 0)
    ]


def latest_unplayed_per_show(
    library: PodcastLibrary, folder_id: str
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """One episode per show: what "Play all unplayed" has to mean for a folder.

    A folder of forty shows holds hundreds of unplayed episodes, and a queue of
    hundreds is not a queue -- it is a thing somebody has to undo. One round of
    what is new is the request that was actually made.
    """
    chosen: list[tuple[PodcastShow, PodcastEpisode]] = []
    seen: set[str] = set()
    for show, episode in unplayed_in_folder(library, folder_id):
        show_id = str(show.id)
        if show_id in seen:
            continue
        seen.add(show_id)
        chosen.append((show, episode))
    return chosen


def move_folder(library: PodcastLibrary, folder_id: str, new_parent_id: str | None) -> bool:
    """Re-parent a folder. Returns whether anything moved.

    **A folder may not become its own descendant.** Without the guard, moving
    "News" into "News/Local" produces a ring: the tree walk never terminates,
    the shows inside vanish from every view, and nothing in the UI can express
    the state well enough for somebody to undo it.
    """
    folder = _find(library, folder_id)
    if folder is None:
        return False
    parent = (new_parent_id or "") or None
    if parent == folder.parent_folder_id:
        return False
    if parent is not None:
        if parent == folder_id or parent in subtree_folder_ids(library, folder_id):
            return False
        if _find(library, parent) is None:
            return False
    folder.parent_folder_id = parent
    return True


def reorder_folder(library: PodcastLibrary, folder_id: str, delta: int) -> int:
    """Move a folder up or down among its siblings. Returns its new position.

    ``-1`` when nothing moved, so a caller can tell "already at the top" from
    "moved to the top" -- which is the difference between saying nothing and
    saying where somebody now is.
    """
    folder = _find(library, folder_id)
    if folder is None or not delta:
        return -1
    siblings = [
        row
        for row in getattr(library, "folders", []) or []
        if getattr(row, "parent_folder_id", None) == folder.parent_folder_id
    ]
    siblings.sort(key=lambda row: (int(getattr(row, "sort_order", 0) or 0), str(row.name)))
    try:
        position = siblings.index(folder)
    except ValueError:
        return -1
    target = position + (1 if delta > 0 else -1)
    if not (0 <= target < len(siblings)):
        return -1
    siblings.insert(target, siblings.pop(position))
    # Renumbered from zero every time rather than swapping two values: a
    # hand-edited file can hold duplicate or absent orders, and a swap would
    # preserve them forever.
    for index, row in enumerate(siblings):
        row.sort_order = index
    return target


def describe_folder(library: PodcastLibrary, folder_id: str) -> str:
    """A folder row as a whole sentence: "News, folder, 6 podcasts, 12 new".

    One line, because a screen reader reads a row's own text, and a tree that
    makes somebody open a folder to find out whether it is worth opening has
    charged them for the question.
    """
    folder = _find(library, folder_id)
    if folder is None:
        return ""
    shows = len(subtree_show_ids(library, folder_id))
    unplayed = len(unplayed_in_folder(library, folder_id))
    said = f"{folder.name}, folder, {shows} podcast{'' if shows == 1 else 's'}"
    if unplayed:
        said += f", {unplayed} new"
    return said


def _find(library: PodcastLibrary, folder_id: str) -> Any:
    for folder in getattr(library, "folders", []) or []:
        if str(getattr(folder, "id", "")) == folder_id:
            return folder
    return None
