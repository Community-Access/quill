"""Group actions on a Play Queue selection (ear.md R5).

The queue list has read a multiple selection since list.md 2.4 and Remove was the
only thing that used one. These are the rest: move a block to either end, sort it
by date, shuffle it, and play it as a run.

**The selection is restored at the items' new positions, and that is not a
nicety.** Move to Top on three rows used to be impossible to write correctly
without it: the reload lands on one row, so a second press moves one item while
the listener believes they are moving three. Silent, and it only shows up after
the damage. Every function here ends by reselecting the block.

**What is announced, and what is not.** A screen reader reads the row the
selection lands on by itself, so the row text is never spoken. What it cannot do
is *count* a selection -- so the count is the whole announcement, and only when
there is more than one row: for a single row the reader's own row read plus the
position already in the label carries it entirely.

Dialog functions rather than methods, matching :mod:`quill.ui.podcasts.folder_commands`:
the dialog keeps its line count and each action is callable with a fake dialog.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.queue_selection import (
    move_selection,
    shuffle_selection,
    sort_selection_by_date,
)

__all__ = [
    "move_to_bottom",
    "move_to_top",
    "play_selection",
    "shuffle_selected",
    "sort_selected_by_date",
]


def _selection(dialog: Any) -> list[int]:
    """The selected queue indexes, or ``[]`` after saying that there are none."""
    indexes = dialog._selected_indexes()
    if not indexes:
        dialog._announce("Nothing is selected.")
    return indexes


def _after(dialog: Any, moved: list[int], sentence: str) -> None:
    """Reload, restore the block, then speak -- in that order, always.

    The order is load-bearing. A routine announcement does not interrupt, so a
    sentence spoken *before* the selection moves is cut off by the reader's own
    focus utterance; spoken after, it queues behind it and is heard.
    """
    dialog._on_library_changed()
    dialog._reload(select_many=moved)
    if sentence:
        dialog._announce(sentence)


def move_to_top(dialog: Any) -> None:
    indexes = _selection(dialog)
    if not indexes:
        return
    moved = move_selection(dialog._library, indexes, where="top")
    _after(dialog, moved, f"Moved {len(moved)} to top" if len(moved) > 1 else "")


def move_to_bottom(dialog: Any) -> None:
    indexes = _selection(dialog)
    if not indexes:
        return
    moved = move_selection(dialog._library, indexes, where="bottom")
    _after(dialog, moved, f"Moved {len(moved)} to bottom" if len(moved) > 1 else "")


def sort_selected_by_date(dialog: Any, *, newest_first: bool) -> None:
    """Sort the selected slots in the positions they already occupy.

    The direction is announced as well as the count, because neither is knowable
    from one row -- and a sort whose direction the listener has to infer from the
    first row is a sort they have to check.
    """
    indexes = _selection(dialog)
    if not indexes:
        return
    touched = sort_selection_by_date(dialog._library, indexes, newest_first=newest_first)
    if len(touched) < 2:
        _after(dialog, touched, "")
        return
    order = "newest first" if newest_first else "oldest first"
    _after(dialog, touched, f"Sorted {len(touched)}, {order}")


def shuffle_selected(dialog: Any) -> None:
    """Shuffle the selected slots among their own positions.

    The one action whose result cannot be inferred from any single row, so the
    count is doing real work here even more than elsewhere.
    """
    indexes = _selection(dialog)
    if not indexes:
        return
    touched = shuffle_selection(dialog._library, indexes)
    _after(dialog, touched, f"Shuffled {len(touched)}" if len(touched) > 1 else "")


def play_selection(dialog: Any) -> None:
    """Play the first selected slot; the rest follow in order (R5).

    "The rest follow" needs no work beyond moving the block to the front: the
    queue *is* the running order, and R4 means the playing episode keeps its
    place in it, so playing the top of a block plays the block.
    """
    indexes = _selection(dialog)
    if not indexes:
        return
    if len(indexes) > 1:
        move_selection(dialog._library, indexes, where="top")
        dialog._on_library_changed()
        dialog._reload(select_many=list(range(len(indexes))))
    dialog._on_play_now()
