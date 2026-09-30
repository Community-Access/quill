"""The Inbox, narrowed to one library folder (R4).

The Inbox is a triage surface, and triage has a mood. Somebody sitting down to
clear news at breakfast does not want the eleven-part history series in the same
list, and somebody working through the history series does not want to be
reminded that there are forty news episodes waiting. Earshot's answer is an Inbox
you can point at one folder; this is the same idea with the desktop's advantage,
which is that the filter is a persistent choice rather than a gesture.

The distinction that makes this worth its own module: the Inbox already has a
folder tree, and it is **not this one**. ``PodcastLibrary.inbox_folders`` files
*episodes* inside the Inbox; ``PodcastLibrary.folders`` files *shows* in the
library. This narrows by the second -- "show me the Inbox for News" means the
shows filed under News, wherever their episodes happen to sit inside the Inbox.
Conflating the two would produce a filter that appears to work and quietly
answers a different question.

Two rules:

* **Subfolders count.** A listener who filed Morning News and Evening News under
  News and then asked for the News Inbox means both. A filter that answered only
  the folder's own immediate shows would look broken and be unarguable about it.
* **The filter never hides a count it does not explain.** :func:`scope_label` and
  :func:`empty_state` exist so the window can always say which scope is in force
  -- an Inbox that is empty because of a filter, and says only "empty", is how
  somebody concludes their episodes are gone.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.podcasts.inbox import inbox_pairs
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "ALL",
    "UNFILED",
    "empty_state",
    "folder_ids_with_inbox",
    "inbox_pairs_in_library_folder",
    "scope_label",
    "shows_in_subtree",
]

#: The scope that filters nothing. A sentinel rather than ``None`` because
#: ``None`` already means "the library's top level" for a folder id, and two
#: different nothings in one parameter is how a filter starts showing the wrong
#: rows.
ALL = "\x00all"

#: The shows that are in no folder at all.
UNFILED = "\x00unfiled"


def _subtree_ids(library: PodcastLibrary, folder_id: str) -> set[str]:
    """*folder_id* and every folder beneath it.

    Iterative and bounded by the folder count, so a hand-edited file with a
    parent cycle terminates instead of recursing forever.
    """
    subtree = {folder_id}
    grew = True
    while grew:
        grew = False
        for folder in library.folders:
            if folder.parent_folder_id in subtree and folder.id not in subtree:
                subtree.add(folder.id)
                grew = True
    return subtree


def shows_in_subtree(library: PodcastLibrary, folder_id: str) -> list[PodcastShow]:
    """Every show filed in *folder_id* or any folder beneath it."""
    subtree = _subtree_ids(library, folder_id)
    return [show for show in library.shows if (show.folder_id or "") in subtree]


def inbox_pairs_in_library_folder(
    library: PodcastLibrary, scope: str | None
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """The Inbox, narrowed to one library folder (and its subfolders).

    *scope* is :data:`ALL` for no filter, :data:`UNFILED` for shows in no folder,
    or a folder id. An id that no longer exists answers an **empty list** rather
    than silently falling back to everything: a filter pointing at a deleted
    folder is a filter that is on, and showing the whole Inbox as though it were
    off would misreport what the listener is looking at.
    """
    if scope is None or scope == ALL:
        return inbox_pairs(library)
    if scope == UNFILED:
        return [(show, ep) for show, ep in inbox_pairs(library) if not show.folder_id]
    if library.find_folder(scope) is None:
        return []
    wanted = {show.id for show in shows_in_subtree(library, scope)}
    return [(show, ep) for show, ep in inbox_pairs(library) if show.id in wanted]


def folder_ids_with_inbox(library: PodcastLibrary) -> list[str]:
    """The folder ids worth offering in the chooser, in tree order.

    Only folders that actually contain Inbox episodes, because a chooser listing
    forty folders of which three have anything in them makes the listener find
    the three by trying them. A folder whose *subfolders* have episodes counts,
    since choosing it would show them.
    """
    have: list[str] = []
    for folder in library.folders:
        pairs = inbox_pairs_in_library_folder(library, folder.id)
        if pairs:
            have.append(folder.id)
    return have


def scope_label(library: PodcastLibrary, scope: str | None) -> str:
    """What the window calls the scope in force: "All podcasts", "Not in a
    folder", or the folder's path."""
    if scope is None or scope == ALL:
        return "All podcasts"
    if scope == UNFILED:
        return "Not in a folder"
    from quill.core.podcasts.playing_from import folder_path

    path = folder_path(library, scope)
    return path or "A folder that no longer exists"


def empty_state(library: PodcastLibrary, scope: str | None) -> str:
    """What to show when the filtered Inbox is empty, naming the filter.

    Three different empties, three different sentences. "Nothing here" is true of
    all three and useful in none of them -- the listener's next action is
    different in each, and only one of the three is good news.
    """
    if inbox_pairs_in_library_folder(library, scope):
        return ""
    if scope is None or scope == ALL:
        if inbox_pairs(library):
            return ""
        return (
            "The Inbox is empty. Episodes arrive here from podcasts marked Route "
            "to Inbox, in Podcast Settings."
        )
    label = scope_label(library, scope)
    if inbox_pairs(library):
        return (
            f"Nothing in the Inbox for {label}. The rest of the Inbox is still "
            "there -- choose All podcasts to see it."
        )
    return f"The Inbox is empty, for {label} and everywhere else."
