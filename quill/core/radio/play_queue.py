"""A play queue for the recordings list -- shuffle, repeat, stop after current.

``winamp_keys.py`` deliberately left three keys unbound (#1344)::

    Shuffle (``R``), repeat (``S``) and stop-after-current (``Ctrl+V``) are
    deliberately absent: all three describe a play queue, and the recordings
    player does not have one yet.

This is that queue. Binding the keys to something that only pretended to work
would have been worse than leaving them unbound, so the order is: build the
model, then bind.

**Why an explicit order list rather than picking at random each time.** With
shuffle on, "random next" eventually plays the same recording twice before it
plays some others at all, and -- worse for this audience -- ``Z`` cannot go
back to what you just heard, because nothing recorded where you had been. So
shuffle here is a *permutation*, generated once: every item plays once before
any repeats, and previous is the exact inverse of next. That is what listeners
mean by shuffle, and it is the only version that keeps ``B`` and ``Z`` honest.

**Repeat-one repeats on a natural end, not on Next.** A track that ended
repeats; pressing ``B`` still moves on. Anything else makes Next look broken.

**Stop-after-current outranks repeat.** It is a one-shot the listener asked
for just now, so it wins over a standing preference and clears itself when it
fires -- it never survives to surprise the next session.

**Not to be confused with** :mod:`quill.core.audio_studio.play_queue`, which
shares the module name and the class name and is a different thing: that one is
a *persisted list of books to play through*, with add/remove/dedup-by-path and
a wrapping ``next_entry``. This one owns no content at all -- it is the
**order** a list the caller already has should be played in, addressed by row
index, and it is what shuffle and repeat are properties of. Neither is a
generalization of the other, and merging them would mean one object answering
both "what is queued?" and "in what order?" for two surfaces that disagree
about the first question.

wx-free, strict-typed, no randomness unless a shuffler is handed in (so the
tests state the order literally).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

#: Play to the end of the list and stop.
REPEAT_OFF = "off"
#: Wrap from the last item back to the first, forever.
REPEAT_ALL = "all"
#: Replay the item that just ended.
REPEAT_ONE = "one"

#: Cycle order for the ``S`` key.
REPEAT_MODES: tuple[str, ...] = (REPEAT_OFF, REPEAT_ALL, REPEAT_ONE)

#: What each mode is called out loud. Whole words, because "repeat: all" read
#: aloud is a label and a value with nothing joining them.
REPEAT_LABELS: dict[str, str] = {
    REPEAT_OFF: "Repeat off",
    REPEAT_ALL: "Repeat all recordings",
    REPEAT_ONE: "Repeat this recording",
}

#: Nothing to play.
NO_ROW = -1


def normalize_repeat_mode(raw: object) -> str:
    """A stored repeat mode made safe for this build.

    A settings file written by a later version (or edited by hand) can name a
    mode this build has never heard of; reading that back as "off" is the only
    answer that cannot surprise anybody.
    """
    text = str(raw or "").strip().lower()
    return text if text in REPEAT_MODES else REPEAT_OFF


def next_repeat_mode(mode: str) -> str:
    """The mode ``S`` moves to from *mode* (unknown modes restart the cycle)."""
    try:
        index = REPEAT_MODES.index(mode)
    except ValueError:
        return REPEAT_MODES[0]
    return REPEAT_MODES[(index + 1) % len(REPEAT_MODES)]


@dataclass(slots=True)
class PlayQueue:
    """The order the recordings list plays in, and what happens at the end."""

    shuffle: bool = False
    repeat: str = REPEAT_OFF
    #: One-shot: stop when the current recording ends, then clear itself.
    stop_after_current: bool = False
    #: The play order as row indexes. Identity while shuffle is off.
    order: list[int] = field(default_factory=list)

    # -- building the order ------------------------------------------------

    def set_rows(
        self,
        rows: Sequence[int],
        *,
        shuffler: Callable[[list[int]], None] | None = None,
    ) -> None:
        """Take the playable rows, in list order, and build the play order.

        Called whenever the list is rebuilt (a new recording finished, one was
        deleted) and whenever shuffle is toggled. With shuffle off the order is
        simply the rows as shown, so the queue is invisible until asked for.
        """
        items = list(rows)
        if self.shuffle and len(items) > 1:
            shuffle_in_place = shuffler or random.shuffle
            shuffle_in_place(items)
        self.order = items

    def set_rows_if_changed(
        self,
        rows: Sequence[int],
        *,
        shuffler: Callable[[list[int]], None] | None = None,
    ) -> bool:
        """Rebuild the order only when the *set* of rows actually changed.

        The recordings list refreshes on a timer, and rebuilding on every tick
        would reshuffle the order every second or so -- which would silently
        undo the whole reason shuffle is a fixed permutation: ``Z`` would stop
        going back to what you just heard, and items would repeat before
        others had played at all.

        Compared as a set, because the same recordings in a different *list*
        order (the list re-sorted) is not new content to shuffle.
        """
        if set(rows) == set(self.order):
            return False
        self.set_rows(rows, shuffler=shuffler)
        return True

    def toggle_shuffle(
        self,
        rows: Sequence[int],
        *,
        shuffler: Callable[[list[int]], None] | None = None,
    ) -> bool:
        """Flip shuffle and rebuild the order. Returns the new state."""
        self.shuffle = not self.shuffle
        self.set_rows(rows, shuffler=shuffler)
        return self.shuffle

    def cycle_repeat(self) -> str:
        """Advance the repeat mode and return the new one."""
        self.repeat = next_repeat_mode(self.repeat)
        return self.repeat

    def toggle_stop_after_current(self) -> bool:
        """Flip the one-shot and return the new state."""
        self.stop_after_current = not self.stop_after_current
        return self.stop_after_current

    # -- moving through it -------------------------------------------------

    def _position_of(self, row: int) -> int:
        try:
            return self.order.index(row)
        except ValueError:
            return NO_ROW

    def _step(self, row: int, direction: int) -> int:
        if not self.order:
            return NO_ROW
        position = self._position_of(row)
        if position == NO_ROW:
            # Nothing (or something no longer in the list) is playing: start
            # at whichever end the listener is heading towards.
            return self.order[0] if direction > 0 else self.order[-1]
        target = position + direction
        if 0 <= target < len(self.order):
            return self.order[target]
        if self.repeat == REPEAT_ALL:
            return self.order[target % len(self.order)]
        return NO_ROW

    def next_row(self, current: int) -> int:
        """The row ``B`` moves to, or :data:`NO_ROW` at the end.

        Repeat-one is deliberately ignored here: pressing Next while one
        recording is set to repeat must still move on, or Next looks broken.
        """
        return self._step(current, 1)

    def previous_row(self, current: int) -> int:
        """The row ``Z`` moves to, or :data:`NO_ROW` at the start."""
        return self._step(current, -1)

    def row_after_finishing(self, current: int) -> int:
        """What plays when *current* ends on its own, or :data:`NO_ROW`.

        This is the only path the standing preferences apply to, and the order
        of the three is the point: the one-shot the listener just asked for
        beats the standing repeat setting, and repeat-one beats moving on.
        """
        if self.stop_after_current:
            self.stop_after_current = False
            return NO_ROW
        if self.repeat == REPEAT_ONE:
            return current
        return self._step(current, 1)


__all__ = [
    "NO_ROW",
    "REPEAT_ALL",
    "REPEAT_LABELS",
    "REPEAT_MODES",
    "REPEAT_OFF",
    "REPEAT_ONE",
    "PlayQueue",
    "next_repeat_mode",
    "normalize_repeat_mode",
]
