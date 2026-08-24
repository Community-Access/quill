"""Saving a Play Queue order and putting it back (list.md 2.3).

A lineup is "the order I listen in on a Tuesday": four shows, in a sequence
that took a minute to arrange and is gone the moment the queue is used for
something else. Rebuilding it by hand every week is the kind of work an app
should be doing.

**A lineup is a manual playlist.** Not a new store, not a new record type: a
manual playlist is already *a named, ordered list of episode references*, which
is exactly and entirely what a lineup is. Giving the same thing a second name
is how this codebase ends up with two ideas that drift -- and it would cost the
feature everything the playlists branch already does: rename, delete, appear in
the tree, travel in an export. What is new here is the two **verbs**.

**Apply moves; it never replaces.** The queue somebody has now is a decision
they made, and a lineup is not a licence to throw it away:

* every episode from the lineup that is available and unplayed moves to the
  **front**, in the lineup's order, whether it was already queued or not;
* everything else in the queue **stays**, in the order it was already in, after
  them;
* an episode that has since been played, or has left the library, is **skipped**
  -- and counted, because "applied 3, skipped 2" is the difference between a
  lineup that worked and one that quietly half-worked.

That last rule is the reason this returns a :class:`~quill.core.counted.Counted`
rather than a bool. A silent apply on a five-episode lineup where three
episodes were played last week looks identical to one that worked.

wx-free, strict-typed, pure over the library. The caller saves.
"""

from __future__ import annotations

from quill.core.counted import Counted
from quill.core.podcasts.models import QueueItem, now_iso
from quill.core.podcasts.models_playlists import Playlist
from quill.core.podcasts.subscriptions import PodcastLibrary

#: What a lineup is skipped for, in the words the tally reads out.
SKIPPED_REASON = "already played or no longer in the library"


def save_lineup(library: PodcastLibrary, name: str, *, lineup_id: str = "") -> Playlist | None:
    """Snapshot the queue's current order under *name*. None for an empty queue.

    An empty lineup is refused rather than saved: applying one would do
    nothing, and a name in the list that does nothing is worse than the
    absence of a name.

    Saving over an existing lineup replaces its items rather than adding a
    second entry with the same name -- somebody re-saving "Tuesday" means
    *this* is Tuesday now.
    """
    title = str(name or "").strip()
    if not title or not library.queue:
        return None
    items = [
        QueueItem(item.show_id, item.episode_guid, added_at=item.added_at) for item in library.queue
    ]
    existing = _find_by_name(library, title)
    if existing is not None:
        existing.items = items
        return existing
    playlist = Playlist(
        id=lineup_id or f"lineup-{len(library.playlists) + 1}-{title.lower().replace(' ', '-')}",
        name=title,
        kind="manual",
        items=items,
    )
    library.add_playlist(playlist)
    return playlist


def apply_lineup(library: PodcastLibrary, playlist: Playlist) -> Counted:
    """Move the lineup's available unplayed episodes to the front, in order.

    Pure over *library*: mutates ``library.queue`` and returns the tally. The
    caller saves and announces.
    """
    wanted: list[QueueItem] = []
    skipped = 0
    seen: set[tuple[str, str]] = set()
    for item in playlist.items:
        key = (item.show_id, item.episode_guid)
        if key in seen:
            continue
        seen.add(key)
        if not _is_available_unplayed(library, item):
            skipped += 1
            continue
        wanted.append(item)

    if not wanted:
        return Counted(
            done=0,
            skipped=skipped,
            skipped_because=SKIPPED_REASON,
            nothing_because=(
                "this lineup has no episodes yet"
                if not playlist.items
                else "every episode in this lineup is " + SKIPPED_REASON
            ),
            _eligible=len(playlist.items),
        )

    front_keys = {(item.show_id, item.episode_guid) for item in wanted}
    # The rest keeps its own order. A lineup rearranges the front of the
    # queue; it is not an instruction about anything it does not mention.
    rest = [item for item in library.queue if (item.show_id, item.episode_guid) not in front_keys]
    stamped_at = now_iso()
    front: list[QueueItem] = []
    for item in wanted:
        existing = _queued(library, item)
        # A slot that was already queued keeps the age it had: Queue
        # Expiration measures how long something has been waiting, and
        # reordering is not waiting less.
        front.append(
            existing
            if existing is not None
            else QueueItem(item.show_id, item.episode_guid, added_at=stamped_at)
        )
    library.queue = front + rest
    return Counted(
        done=len(front),
        skipped=skipped,
        skipped_because=SKIPPED_REASON,
        _eligible=len(playlist.items),
    )


def lineup_names(library: PodcastLibrary) -> list[str]:
    """Every saved lineup, by name, in the order they are stored."""
    return [p.name for p in library.playlists if p.kind == "manual"]


def find_lineup(library: PodcastLibrary, name: str) -> Playlist | None:
    return _find_by_name(library, str(name or "").strip())


def _find_by_name(library: PodcastLibrary, name: str) -> Playlist | None:
    folded = name.casefold()
    for playlist in library.playlists:
        if playlist.kind == "manual" and playlist.name.casefold() == folded:
            return playlist
    return None


def _queued(library: PodcastLibrary, item: QueueItem) -> QueueItem | None:
    for queued in library.queue:
        if (queued.show_id, queued.episode_guid) == (item.show_id, item.episode_guid):
            return queued
    return None


def _is_available_unplayed(library: PodcastLibrary, item: QueueItem) -> bool:
    """Whether this reference still names something worth playing.

    Played is the interesting half: a lineup is a running order, and putting
    an episode somebody finished back at the front of the queue is the app
    disagreeing with them about what they have done.
    """
    show = library.find_show(item.show_id)
    if show is None:
        return False
    episode = show.find_episode(item.episode_guid)
    if episode is None:
        return False
    return not bool(getattr(episode, "played", False))


__all__ = [
    "SKIPPED_REASON",
    "apply_lineup",
    "find_lineup",
    "lineup_names",
    "save_lineup",
]
