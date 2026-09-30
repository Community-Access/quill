"""Stepping through the Play Queue as a listening run, without consuming it.

QUILL Cast used to *pop* the queue: pressing Play on a slot removed it as it
started, so the queue only ever showed what was coming next. Earshot keeps the
playing episode in place with its row reading "Playing", and it leaves when it
finishes. Jeff chose the Earshot way (ear.md R4), and that choice is what makes
R2 possible at all -- Previous in Queue needs something to go back to.

So this module is the queue read as a **position in a run** rather than a stack
to be emptied:

* :func:`step_next` and :func:`step_previous` find the neighbouring slot without
  removing anything.
* :func:`finish_slot` is the one function that removes, and it is called when an
  episode *finishes* or when Mark as Played and Next says it is done with.
* Either end of the run is a first-class answer, not ``None``. A command that
  did nothing has to be able to say why, because a key that stops working is
  indistinguishable from a key that stopped doing anything
  (:mod:`quill.ui.podcasts.speed` makes the same argument about the ends of the
  speed range).

**The five-second rule** in :func:`step_previous` is what every player does and
what listeners expect without being told: early in an episode Previous means
"the one before", and later it means "start this one again". Five seconds,
because the mistake it exists for -- realising two seconds in that you wanted
the previous one -- happens immediately or not at all.

A stale slot (an unsubscribed show, a pruned episode) is dropped as it is
encountered, so stepping self-heals the queue exactly as the old popping
functions did. That is the one removal this module does on the way past, and it
removes nothing a listener can see.

wx-free, strict-typed. Every function takes the library and returns a result;
nothing here plays anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.podcasts.queue import resolve

__all__ = [
    "RESTART_WITHIN_MS",
    "Step",
    "finish_slot",
    "index_of",
    "queue_position",
    "step_next",
    "step_previous",
]

#: Below this many milliseconds into an episode, Previous means "the previous
#: episode"; at or above it, Previous restarts the one playing.
RESTART_WITHIN_MS = 5000


@dataclass(frozen=True, slots=True)
class Step:
    """What a step command should do next.

    *kind* is one of:

    ``"play"``
        Play *show* / *episode*. The slot is still in the queue.
    ``"restart"``
        Seek the playing episode to zero. Nothing else changes.
    ``"edge"``
        Do nothing, and say *message*: the run has no more in that direction.
    """

    kind: str
    show: Any = None
    episode: Any = None
    message: str = ""

    @property
    def is_edge(self) -> bool:
        return self.kind == "edge"


def index_of(library: Any, show_id: str, episode_guid: str) -> int:
    """Where this episode sits in the queue, or ``-1`` when it is not in it.

    An episode can be playing without being queued at all -- started from a
    show's own list -- and every caller has to cope with that rather than
    assume a position.
    """
    for index, item in enumerate(library.queue):
        if item.show_id == show_id and item.episode_guid == episode_guid:
            return index
    return -1


def queue_position(library: Any, show_id: str, episode_guid: str) -> str:
    """``"3 of 12"`` for a queued episode, or ``""`` when it is not queued.

    For the row text and Player Information, never for speech: a position is
    exactly the kind of state a reader gets from the row it is already reading.
    """
    index = index_of(library, show_id, episode_guid)
    if index == -1:
        return ""
    return f"{index + 1} of {len(library.queue)}"


def _first_resolvable_from(library: Any, start: int) -> Step:
    """The first slot at or after *start* that still resolves.

    Stale slots are deleted as they are met, which is what keeps the queue
    self-healing; *start* stays put because a deletion shifts the rest down onto
    it.
    """
    while start < len(library.queue):
        resolved = resolve(library, library.queue[start])
        if resolved is not None:
            show, episode = resolved
            return Step(kind="play", show=show, episode=episode)
        del library.queue[start]
    return Step(kind="edge", message="End of queue")


def _last_resolvable_before(library: Any, before: int) -> Step:
    """The nearest slot before *before* that still resolves."""
    index = min(before, len(library.queue)) - 1
    while index >= 0:
        resolved = resolve(library, library.queue[index])
        if resolved is not None:
            show, episode = resolved
            return Step(kind="play", show=show, episode=episode)
        del library.queue[index]
        index -= 1
    return Step(kind="edge", message="Start of queue")


def step_next(library: Any, show_id: str, episode_guid: str) -> Step:
    """The slot after the playing episode, without removing anything.

    When the playing episode is not in the queue -- started from a show's own
    list -- "next" means the front of the queue, which is the only reading of it
    that does not require inventing a position.
    """
    index = index_of(library, show_id, episode_guid)
    if index == -1:
        return _first_resolvable_from(library, 0)
    return _first_resolvable_from(library, index + 1)


def step_previous(library: Any, show_id: str, episode_guid: str, position_ms: int) -> Step:
    """Restart the playing episode, or step back one slot.

    The five-second rule first, and deliberately before the queue is consulted:
    an episode playing at 40 minutes restarts whether or not it is queued, which
    is what the key means everywhere else in the world.
    """
    if position_ms >= RESTART_WITHIN_MS:
        return Step(kind="restart")
    index = index_of(library, show_id, episode_guid)
    if index == -1:
        # Not in the run, and under five seconds in: there is no "before" to go
        # to, and restarting would be a lie about having stepped.
        return Step(kind="edge", message="Start of queue")
    return _last_resolvable_before(library, index)


def finish_slot(library: Any, show_id: str, episode_guid: str) -> int:
    """Remove this episode's slot, returning the index it occupied, or ``-1``.

    The index is the return value because it is what the caller needs next: the
    slot that took its place is the next thing to play, and the row to land
    focus on is the one now at that index. Looking it up again afterwards would
    find a different episode.
    """
    index = index_of(library, show_id, episode_guid)
    if index == -1:
        return -1
    del library.queue[index]
    return index


def step_after_finishing(library: Any, show_id: str, episode_guid: str) -> tuple[Step, int]:
    """Mark as Played and Next, as one movement: ``(step, freed_index)``.

    The slot goes first and the next thing is read from the index it vacated, so
    "finish this and start the next" is one decision rather than two that can
    disagree about what "next" meant. *freed_index* is ``-1`` when the episode
    was not queued, in which case the step is an ordinary advance.
    """
    freed = finish_slot(library, show_id, episode_guid)
    if freed == -1:
        return step_next(library, show_id, episode_guid), -1
    return _first_resolvable_from(library, freed), freed
