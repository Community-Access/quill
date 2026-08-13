"""The cross-show Play Queue (Phase 4, docs/planning/podcasts.md §Queue).

Pure operations over ``PodcastLibrary.queue`` (an ordered list of
:class:`~quill.core.podcasts.models.QueueItem`); the caller persists via
``save_library`` after mutating. Reordering deliberately offers both a
single-slot nudge (Move Up/Down) and mark-and-move (place a marked item
directly above/below another) -- the same accessible-reordering pattern
QUILL's Interactive Rebase commit list uses, because arrowing an item
twenty slots one nudge at a time is keyboard-hostile.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem, now_iso
from quill.core.podcasts.subscriptions import PodcastLibrary


def _index_of(library: PodcastLibrary, show_id: str, episode_guid: str) -> int:
    for i, item in enumerate(library.queue):
        if item.show_id == show_id and item.episode_guid == episode_guid:
            return i
    return -1


def add_to_queue(library: PodcastLibrary, show_id: str, episode_guid: str) -> bool:
    """Append an episode to the queue. False when it is already queued."""
    if _index_of(library, show_id, episode_guid) != -1:
        return False
    library.queue.append(QueueItem(show_id=show_id, episode_guid=episode_guid, added_at=now_iso()))
    return True


def play_next(library: PodcastLibrary, show_id: str, episode_guid: str) -> None:
    """Put an episode at the front of the queue (moving it if already queued).

    Moving an item keeps its original ``added_at``: reordering the queue is
    not the same as re-adding, and Play Next must not quietly reset an
    episode's expiry clock.
    """
    existing = _index_of(library, show_id, episode_guid)
    if existing != -1:
        item = library.queue.pop(existing)
    else:
        item = QueueItem(show_id=show_id, episode_guid=episode_guid, added_at=now_iso())
    library.queue.insert(0, item)


def queue_groups(library: PodcastLibrary) -> list[tuple[PodcastShow, list[int]]]:
    """The queue clustered by podcast: ``(show, [queue indices])``.

    Groups appear in the order their first episode appears in the queue, so
    "the show whose turn is next" is the first group. Powers the Play Queue
    dialog's Group by Podcast view and its move-the-whole-group actions --
    a flat queue of forty items from four shows is a list nobody can hold in
    their head, but four groups is.
    """
    order: list[str] = []
    indices: dict[str, list[int]] = {}
    for index, item in enumerate(library.queue):
        if item.show_id not in indices:
            indices[item.show_id] = []
            order.append(item.show_id)
        indices[item.show_id].append(index)
    groups: list[tuple[PodcastShow, list[int]]] = []
    for show_id in order:
        show = library.find_show(show_id)
        if show is not None:
            groups.append((show, indices[show_id]))
    return groups


def move_group(library: PodcastLibrary, show_id: str, *, where: str) -> int:
    """Move every queue slot belonging to *show_id* as one block.

    ``where`` is ``"top"``, ``"up"``, ``"down"``, or ``"bottom"``. Up/down
    step past the neighbouring *group*, not the neighbouring item, so one
    keystroke moves a show past another show rather than nudging it one slot
    into the middle of someone else's block. Returns how many slots moved
    (0 when the show has none, or the move would fall off the end).
    """
    mine = [item for item in library.queue if item.show_id == show_id]
    if not mine:
        return 0
    others = [item for item in library.queue if item.show_id != show_id]
    if where == "top":
        library.queue = [*mine, *others]
        return len(mine)
    if where == "bottom":
        library.queue = [*others, *mine]
        return len(mine)
    order = [sid for sid, _ in ((s.id, None) for s, _ in queue_groups(library))]
    if show_id not in order:
        return 0
    position = order.index(show_id)
    target = position - 1 if where == "up" else position + 1
    if not (0 <= target < len(order)):
        return 0
    order[position], order[target] = order[target], order[position]
    by_show: dict[str, list[QueueItem]] = {}
    for item in library.queue:
        by_show.setdefault(item.show_id, []).append(item)
    reordered: list[QueueItem] = []
    for sid in order:
        reordered.extend(by_show.get(sid, []))
    # Slots whose show has gone (stale) never appear in queue_groups; keep
    # them at the end rather than dropping them behind the listener's back.
    known = set(order)
    reordered.extend(item for item in library.queue if item.show_id not in known)
    library.queue = reordered
    return len(mine)


def remove_at(library: PodcastLibrary, index: int) -> bool:
    if 0 <= index < len(library.queue):
        del library.queue[index]
        return True
    return False


def clear_queue(library: PodcastLibrary) -> int:
    """Empty the queue; returns how many items were removed."""
    removed = len(library.queue)
    library.queue.clear()
    return removed


def move(library: PodcastLibrary, index: int, delta: int) -> int:
    """Nudge the item at *index* by *delta* slots; returns its new index
    (unchanged when the move would fall off either end)."""
    target = index + delta
    if not (0 <= index < len(library.queue)) or not (0 <= target < len(library.queue)):
        return index
    item = library.queue.pop(index)
    library.queue.insert(target, item)
    return target


def move_relative_to(
    library: PodcastLibrary, marked_index: int, anchor_index: int, *, above: bool
) -> int:
    """Mark-and-move: place *marked_index*'s item directly above/below the
    item at *anchor_index*; returns the marked item's new index."""
    if not (0 <= marked_index < len(library.queue)):
        return marked_index
    if not (0 <= anchor_index < len(library.queue)) or marked_index == anchor_index:
        return marked_index
    item = library.queue.pop(marked_index)
    if marked_index < anchor_index:
        anchor_index -= 1
    target = anchor_index if above else anchor_index + 1
    library.queue.insert(target, item)
    return target


def resolve(library: PodcastLibrary, item: QueueItem) -> tuple[PodcastShow, PodcastEpisode] | None:
    """The live show/episode behind a queue slot, or None when either is
    gone (an unsubscribed show, a pruned episode) -- callers skip, never
    crash, on a stale slot."""
    show = library.find_show(item.show_id)
    if show is None:
        return None
    episode = show.find_episode(item.episode_guid)
    if episode is None:
        return None
    return (show, episode)


def pop_next_playable(library: PodcastLibrary) -> tuple[PodcastShow, PodcastEpisode] | None:
    """Consume queue slots from the front until one resolves; None when the
    queue is empty or every remaining slot is stale (stale slots are
    dropped as they are encountered, so the queue self-heals)."""
    while library.queue:
        item = library.queue.pop(0)
        resolved = resolve(library, item)
        if resolved is not None:
            return resolved
    return None


def pop_next_after(
    library: PodcastLibrary, show_id: str, episode_guid: str
) -> tuple[PodcastShow, PodcastEpisode] | None:
    """What plays after *this* episode -- the queue in its true order.

    Playing an episode from the middle of the queue (or from a show's own
    list) and then advancing from the queue's *head* is a real bug and an
    infuriating one: you pick episode nine, it finishes, and you are thrown
    back to episode one. If the finished episode is in the queue, it is
    removed and the slot that was after it plays; otherwise this is an
    ordinary advance from the front.

    Found by reading Earshot's #327, which had exactly this shape.
    """
    index = _index_of(library, show_id, episode_guid)
    if index == -1:
        return pop_next_playable(library)
    del library.queue[index]
    while index < len(library.queue):
        item = library.queue.pop(index)
        resolved = resolve(library, item)
        if resolved is not None:
            return resolved
    # Nothing after it resolved; fall back to whatever is still ahead of it.
    return pop_next_playable(library)
