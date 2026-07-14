"""The Inbox: a local curation layer that organizes *episodes*, not shows.

A show marked ``route_to_inbox`` has its unplayed episodes appear in the
Inbox regardless of where the show itself is filed in the library folder
tree. Inside the Inbox, episodes can be filed into Inbox-only folders (a
second, independent nested tree — ``PodcastLibrary.inbox_folders``), and the
first manual placement of an episode from a given show is remembered
(``PodcastShow.inbox_default_folder_id``) so future episodes from that show
auto-file into the same folder; Forget Remembered Folder reverts to manual
filing. The whole layer is deliberately excluded from OPML in both
directions — there is no OPML equivalent for local curation.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id


def inbox_key(show_id: str, episode_guid: str) -> str:
    """The assignment-map key for one episode."""
    return f"{show_id}\n{episode_guid}"


def add_inbox_folder(
    library: PodcastLibrary, name: str, *, parent_folder_id: str | None = None
) -> PodcastFolder:
    folder = PodcastFolder(id=new_id(), name=name, parent_folder_id=parent_folder_id)
    library.inbox_folders.append(folder)
    return folder


def find_inbox_folder(library: PodcastLibrary, folder_id: str) -> PodcastFolder | None:
    for folder in library.inbox_folders:
        if folder.id == folder_id:
            return folder
    return None


def effective_inbox_folder_id(
    library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode
) -> str | None:
    """Where this episode lives inside the Inbox: a manual filing wins, then
    the show's remembered folder; None is the Inbox's own top level. A
    remembered/assigned folder that no longer exists reads as unfiled rather
    than making the episode vanish."""
    key = inbox_key(show.id, episode.guid)
    if key in library.inbox_assignments:
        assigned = library.inbox_assignments[key]
        if assigned and find_inbox_folder(library, assigned) is not None:
            return assigned
        return None  # explicitly unfiled, or the folder is gone
    remembered = show.inbox_default_folder_id
    if remembered and find_inbox_folder(library, remembered) is not None:
        return remembered
    return None


def file_episode(
    library: PodcastLibrary,
    show: PodcastShow,
    episode: PodcastEpisode,
    folder_id: str | None,
) -> bool:
    """Manually file *episode* into an Inbox folder (None = back to the
    Inbox top level). The first manual placement of an episode from a show
    is remembered as that show's default; returns True when this call was
    the one that set the remembered folder (so the UI can say so)."""
    key = inbox_key(show.id, episode.guid)
    if folder_id is None:
        # An explicit "unfile" must override a remembered default, so it is
        # stored as an assignment rather than merely deleted.
        library.inbox_assignments[key] = ""
        return False
    library.inbox_assignments[key] = folder_id
    if show.inbox_default_folder_id is None:
        show.inbox_default_folder_id = folder_id
        return True
    return False


def rename_inbox_folder(library: PodcastLibrary, folder_id: str, new_name: str) -> bool:
    folder = find_inbox_folder(library, folder_id)
    name = new_name.strip()
    if folder is None or not name:
        return False
    folder.name = name
    return True


def _inbox_subtree_ids(library: PodcastLibrary, folder_id: str) -> set[str]:
    subtree = {folder_id}
    grew = True
    while grew:
        grew = False
        for folder in library.inbox_folders:
            if folder.parent_folder_id in subtree and folder.id not in subtree:
                subtree.add(folder.id)
                grew = True
    return subtree


def delete_inbox_folder(library: PodcastLibrary, folder_id: str) -> bool:
    """Delete an Inbox folder and its subfolders; everything filed inside
    moves up to the deleted folder's parent (or the Inbox top level).

    Episodes are never removed — the Inbox only organizes them — so unlike
    the library's :meth:`PodcastLibrary.delete_folder` there is no
    destructive contents option here. Manual filings and remembered per-show
    defaults pointing into the deleted subtree are repointed to the parent
    (an assignment repointed to the top level becomes an explicit unfile, so
    it keeps overriding any remembered folder).
    """
    folder = find_inbox_folder(library, folder_id)
    if folder is None:
        return False
    subtree = _inbox_subtree_ids(library, folder_id)
    parent_id = folder.parent_folder_id
    for key, assigned in list(library.inbox_assignments.items()):
        if assigned in subtree:
            library.inbox_assignments[key] = parent_id or ""
    for show in library.shows:
        if show.inbox_default_folder_id in subtree:
            show.inbox_default_folder_id = parent_id
    library.inbox_folders = [f for f in library.inbox_folders if f.id not in subtree]
    return True


def forget_remembered_folder(show: PodcastShow) -> None:
    """Stop auto-filing this show's future episodes; existing manual
    placements are kept."""
    show.inbox_default_folder_id = None


def inbox_pairs(library: PodcastLibrary) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Every episode currently in the Inbox: unplayed episodes of shows
    marked Route to Inbox."""
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        if not show.route_to_inbox:
            continue
        for episode in show.episodes:
            if not episode.played:
                pairs.append((show, episode))
    return pairs


def inbox_pairs_in_folder(
    library: PodcastLibrary, folder_id: str | None
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """The Inbox episodes whose effective folder is *folder_id* (None = the
    Inbox's unfiled top level)."""
    result: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show, episode in inbox_pairs(library):
        if effective_inbox_folder_id(library, show, episode) == folder_id:
            result.append((show, episode))
    return result
