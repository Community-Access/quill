"""Group actions on a Play Queue selection (ear.md R5).

The queue list has read a multiple selection since list.md 2.4, and Remove was
the only thing that did anything with one. These are the rest: move a block to
either end, sort it by date, shuffle it.

**Every function returns the moved items' new indexes**, and that return value is
the reason this module exists rather than the operations being inlined. The UI
has to put the selection back where the items went: without it, Move to Top on
three rows leaves one row selected, and a second press moves one item while the
listener believes they are moving three. Silent, and it is the kind of wrong that
only shows up after the damage.

Two shared rules:

* **A selection keeps its own order.** Moving three rows to the top puts them at
  the top *in the order they were in*, not reversed and not sorted. The listener
  arranged them; a move is not a re-arrangement.
* **Everything not selected keeps its order too.** Nothing here is a full
  re-sort of the queue -- a group action touches the block and leaves the run
  around it alone.

wx-free, strict-typed. Indexes in, indexes out; the caller owns the list control
and the announcement.
"""

from __future__ import annotations

import random
from typing import Any

from quill.core.podcasts.queue import resolve

__all__ = [
    "move_selection",
    "shuffle_selection",
    "sort_selection_by_date",
]


def _valid(library: Any, indexes: list[int]) -> list[int]:
    """*indexes* that exist, de-duplicated, in ascending order.

    A stale index is somebody else's bug arriving here, and the honest answer is
    to ignore it rather than to raise: a group action that half-worked because
    one row had already gone is worse than one that worked on what was there.
    """
    size = len(library.queue)
    return sorted({index for index in indexes if 0 <= index < size})


def move_selection(library: Any, indexes: list[int], *, where: str) -> list[int]:
    """Move the selected slots to ``"top"`` or ``"bottom"``, keeping their order.

    Returns their new indexes, which for a move are always contiguous: a block
    at one end of the queue.
    """
    valid = _valid(library, indexes)
    if not valid:
        return []
    moving = [library.queue[index] for index in valid]
    # Back to front, so each removal cannot renumber the ones still to come.
    for index in reversed(valid):
        del library.queue[index]
    if where == "top":
        library.queue[0:0] = moving
        return list(range(len(moving)))
    library.queue.extend(moving)
    start = len(library.queue) - len(moving)
    return list(range(start, len(library.queue)))


def _published(library: Any, item: Any) -> str:
    """The episode's published date, or ``""`` when the slot is stale.

    An empty string sorts before every real date, which puts slots that cannot
    be resolved at the start of an oldest-first sort. They are about to be
    dropped by the next step through the queue anyway, and inventing a date for
    them would put them somewhere arbitrary instead of somewhere predictable.
    """
    resolved = resolve(library, item)
    if resolved is None:
        return ""
    _show, episode = resolved
    return str(getattr(episode, "published", "") or "")


def sort_selection_by_date(library: Any, indexes: list[int], *, newest_first: bool) -> list[int]:
    """Sort just the selected slots by date, **in the positions they occupy**.

    The positions are the invariant: sorting rows 2, 5 and 9 rearranges what is
    in those three places and touches nothing else. Sorting them into a
    contiguous block instead would silently reorder the whole run around them,
    which is not what "sort these" means to anyone.
    """
    valid = _valid(library, indexes)
    if len(valid) < 2:
        return valid
    chosen = [library.queue[index] for index in valid]
    chosen.sort(key=lambda item: _published(library, item), reverse=newest_first)
    for position, item in zip(valid, chosen, strict=True):
        library.queue[position] = item
    return valid


def shuffle_selection(
    library: Any, indexes: list[int], *, rng: random.Random | None = None
) -> list[int]:
    """Shuffle the selected slots among the positions they occupy.

    *rng* is injectable so a test can assert a shuffle actually permuted rather
    than asserting against chance.
    """
    valid = _valid(library, indexes)
    if len(valid) < 2:
        return valid
    chosen = [library.queue[index] for index in valid]
    (rng or random).shuffle(chosen)
    for position, item in zip(valid, chosen, strict=True):
        library.queue[position] = item
    return valid
