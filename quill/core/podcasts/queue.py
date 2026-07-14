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

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
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
    library.queue.append(QueueItem(show_id=show_id, episode_guid=episode_guid))
    return True


def play_next(library: PodcastLibrary, show_id: str, episode_guid: str) -> None:
    """Put an episode at the front of the queue (moving it if already queued)."""
    existing = _index_of(library, show_id, episode_guid)
    if existing != -1:
        item = library.queue.pop(existing)
    else:
        item = QueueItem(show_id=show_id, episode_guid=episode_guid)
    library.queue.insert(0, item)


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
