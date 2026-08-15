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

from datetime import UTC, datetime, timedelta

from quill.core.podcasts.models import PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id


def in_inbox(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether *show*'s episodes belong in the Inbox.

    The one place that answers it, and the whole of the opt-out mode. Under
    ``include`` -- the default, and everything Cast has ever done -- a show is in
    the Inbox because it was marked. Under ``exclude`` the same mark means the
    opposite: **every** show is in the Inbox except the ones marked to stay out.

    One flag read two ways rather than a second per-show field, because two
    fields can disagree and a listener would have no way to tell which won.
    """
    mode = str(getattr(library.settings, "inbox_mode", "include") or "include").lower()
    if mode == "exclude":
        return not show.route_to_inbox
    return bool(show.route_to_inbox)


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


def file_episodes(
    library: PodcastLibrary,
    pairs: list[tuple[PodcastShow, PodcastEpisode]],
    folder_id: str | None,
) -> tuple[int, list[str]]:
    """File a whole selection at once. Returns ``(filed, shows_remembered)``.

    Triage is the Inbox's entire job, and triage is something people do to a
    handful of episodes at a time -- so filing one at a time was the surface
    that made a forty-episode Inbox unusable. The remembered-default rule is
    unchanged and still per show: the *first* manual placement of an episode
    from a show sets that show's default, so filing thirty episodes of one show
    sets it once and says so once, rather than thirty times.
    """
    filed = 0
    remembered: list[str] = []
    for show, episode in pairs:
        if file_episode(library, show, episode, folder_id):
            remembered.append(show.title)
        filed += 1
    return filed, remembered


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
    marked Route to Inbox, minus anything an Inbox cap has trimmed out
    (which stays unplayed in its show's own list -- see :func:`trim_inbox`)."""
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        if not in_inbox(library, show):
            continue
        for episode in show.episodes:
            if episode.played:
                continue
            if library.inbox_assignments.get(inbox_key(show.id, episode.guid)) == TRIMMED_MARKER:
                continue
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


# -- Inbox caps (1.1.0) ------------------------------------------------------
#
# An Inbox that holds every unplayed episode of every routed show forever is
# not a triage surface, it is a second library. Two caps -- a count and an
# age -- keep it to the size a person can actually work through.
#
# Trimming is NOT deleting. A trimmed episode leaves the Inbox and stays
# exactly where it already was: unplayed, in its show's own episode list,
# with its downloaded file intact. And three kinds of episode are never
# trimmed at all, which is the difference between a helpful cap and a
# data-loss bug:
#
#   - anything already started (a saved position),
#   - anything in the Play Queue (you have said you want it),
#   - anything manually filed into an Inbox folder (you have curated it).
#
# The mechanism is one entry in ``library.inbox_assignments``: the same
# "explicitly out of the Inbox" marker manual unfiling uses, written with a
# sentinel so a trim can be told apart from a manual placement.

#: Marks an episode the cap removed, so trims can be counted and undone
#: without touching a manual filing.
TRIMMED_MARKER = "\x00trimmed"


def _episode_moment(episode: PodcastEpisode) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((episode.published or "").strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def is_trimmed(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Whether an Inbox cap (rather than the listener) removed this episode."""
    return library.inbox_assignments.get(inbox_key(show.id, episode.guid)) == TRIMMED_MARKER


def inbox_caps(library: PodcastLibrary, show: PodcastShow) -> tuple[int, int]:
    """``(max episodes, age limit hours)`` in force for *show*; 0 = no cap."""
    settings = library.effective_settings(show)
    return (
        max(0, int(settings.inbox_max_episodes)),
        max(0, int(settings.inbox_age_limit_hours)),
    )


def resurface_republished(
    library: PodcastLibrary,
    show: PodcastShow,
    republished_guids: list[str],
) -> list[PodcastEpisode]:
    """Bring re-published episodes back to the Inbox. Returns what returned.

    When a publisher re-issues an episode -- a corrected file, a re-cut, one
    pulled and reissued -- an episode the Inbox had already trimmed is, as far
    as the listener is concerned, new again. It used to stay gone: the trim
    marker was permanent and a refresh only ever refreshed metadata in place,
    so the corrected version sat in the show's list where nobody was looking.

    **The three exemptions are the same three everything else in this module
    uses**, and they are what keep this from being annoying:

    * **played** -- you are finished with it; a re-cut does not un-finish it;
    * **started** (``position_ms > 0``) -- you are in the middle of it, and
      having it reappear as though it were new would misrepresent your own
      history with it;
    * **queued** -- you already decided when to hear it, and the Inbox is for
      episodes awaiting that decision.

    A **manually filed** episode is also left alone: an assignment that is not
    the trim marker is the listener's own filing, and a publisher's re-issue is
    not a reason to overrule it.

    Only the trim marker is cleared. Nothing is moved, marked, or re-ordered,
    and an episode that was never trimmed is already in the Inbox and needs no
    help.
    """
    if not republished_guids or not in_inbox(library, show):
        return []

    queued = {(item.show_id, item.episode_guid) for item in library.queue}
    wanted = set(republished_guids)
    returned: list[PodcastEpisode] = []
    for episode in show.episodes:
        if episode.guid not in wanted:
            continue
        if episode.played or episode.position_ms > 0:
            continue
        if (show.id, episode.guid) in queued:
            continue
        key = inbox_key(show.id, episode.guid)
        if library.inbox_assignments.get(key) != TRIMMED_MARKER:
            continue  # never trimmed, or filed by hand -- either way, leave it
        del library.inbox_assignments[key]
        returned.append(episode)
    return returned


def trim_inbox(
    library: PodcastLibrary, *, now: datetime | None = None
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Apply every show's Inbox caps; returns what left the Inbox.

    Run after a refresh. Exempt episodes (started, queued, or manually filed)
    are skipped entirely -- they do not even count toward the episode cap,
    so a queue full of long-form episodes can never push a fresh one out.
    """
    moment = now or datetime.now(UTC)
    queued = {(item.show_id, item.episode_guid) for item in library.queue}
    trimmed: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        if not in_inbox(library, show):
            continue
        max_episodes, age_hours = inbox_caps(library, show)
        if max_episodes <= 0 and age_hours <= 0:
            continue
        candidates: list[PodcastEpisode] = []
        for episode in show.episodes:
            if episode.played or episode.position_ms > 0:
                continue
            if (show.id, episode.guid) in queued:
                continue
            key = inbox_key(show.id, episode.guid)
            assigned = library.inbox_assignments.get(key)
            if assigned is not None and assigned != TRIMMED_MARKER:
                continue  # manually filed or manually unfiled: the listener's call
            if assigned == TRIMMED_MARKER:
                continue  # already out
            candidates.append(episode)
        candidates.sort(key=lambda e: (e.published, e.title), reverse=True)
        cutoff = moment - timedelta(hours=age_hours) if age_hours > 0 else None
        for index, episode in enumerate(candidates):
            too_many = max_episodes > 0 and index >= max_episodes
            stamped = _episode_moment(episode)
            too_old = cutoff is not None and stamped is not None and stamped < cutoff
            if not (too_many or too_old):
                continue
            library.inbox_assignments[inbox_key(show.id, episode.guid)] = TRIMMED_MARKER
            trimmed.append((show, episode))
    return trimmed


def untrim_episode(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Put a cap-trimmed episode back in the Inbox; True when it was trimmed."""
    key = inbox_key(show.id, episode.guid)
    if library.inbox_assignments.get(key) != TRIMMED_MARKER:
        return False
    del library.inbox_assignments[key]
    return True
