"""Rearranging a playlist: every edit as a pure function over a list.

The Local Media window lets somebody move one item or twelve, nudge them a row
at a time or send them straight to the top, cut them and paste them somewhere
else, and sort the lot -- all from the keyboard. Every one of those is a small
piece of list arithmetic that is easy to get subtly wrong (a block of three
moved down past the end; a selection with a gap in it), so it lives here, wx-free
and tested without a window.

Conventions shared by every function:

* **Selections are row indexes**, in any order and possibly with gaps. They are
  normalised (sorted, de-duplicated, out-of-range dropped) on the way in.
* **A moved block keeps its own order**, and closes up its gaps: moving rows 2
  and 5 down by one leaves them adjacent at 3 and 4. That is what every media
  player does, and it is what a listener who selected them expects to hear.
* **Nothing is mutated.** Each function returns a new list and the new indexes
  of whatever it moved, so the window can put the selection back exactly where
  the items went -- and say so.

The sentences are here too, because the screen reader cannot say them: it
announces the row the cursor is on, never that the row just changed place.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence

from quill.core.radio.local_media import MediaItem
from quill.core.radio.natural_order import natural_key

__all__ = [
    "SORT_KEYS",
    "insert_at",
    "move_by",
    "move_to",
    "moved_sentence",
    "normalize",
    "remove_at",
    "restore_order",
    "sort_items",
]

#: The one-time sorts, ``(key, label)`` in the order Sort Playlist offers them.
#: One-time on purpose: a playlist is an order somebody chose, so a sort is an
#: edit (undoable like any other), never a view that keeps re-sorting under them.
SORT_KEYS: tuple[tuple[str, str], ...] = (
    ("title", "Title"),
    ("artist", "Artist, then album"),
    ("album", "Album, then track order"),
    ("file", "File name"),
    ("folder", "Folder, then file name"),
    ("length", "Length, shortest first"),
    ("added", "Date added, oldest first"),
    ("random", "Random order"),
)


def normalize(selected: Sequence[int], count: int) -> list[int]:
    """The selection as sorted, unique, in-range row indexes (pure)."""
    return sorted({index for index in selected if 0 <= index < count})


def move_by[T](
    items: Sequence[T], selected: Sequence[int], delta: int
) -> tuple[list[T], list[int]]:
    """Move the selected rows *delta* places (negative is up), as a block.

    The block stops at the top or the bottom rather than wrapping: Move Up on
    the first row is a no-op the caller can announce ("Already at the top"),
    which is far easier to follow than an item vanishing to the far end.
    """
    rows = normalize(selected, len(items))
    if not rows or delta == 0:
        return list(items), rows
    first_target = max(0, min(rows[0] + delta, len(items) - len(rows)))
    return move_to(items, rows, first_target)


def move_to[T](
    items: Sequence[T], selected: Sequence[int], position: int
) -> tuple[list[T], list[int]]:
    """Move the selected rows so the first of them lands at row *position*.

    *position* is counted in the list as it will be once the block is placed,
    and is clamped, so Move to Top is ``0`` and Move to Bottom is anything at
    or past the end.
    """
    rows = normalize(selected, len(items))
    if not rows:
        return list(items), []
    chosen = set(rows)
    block = [items[index] for index in rows]
    rest = [item for index, item in enumerate(items) if index not in chosen]
    target = max(0, min(int(position), len(rest)))
    result = rest[:target] + block + rest[target:]
    return result, list(range(target, target + len(block)))


def remove_at[T](
    items: Sequence[T], selected: Sequence[int]
) -> tuple[list[T], list[tuple[int, T]]]:
    """The list without the selected rows, and ``(row, item)`` for each removed.

    The removed pairs are what an undo needs to put each one back where it was.
    """
    rows = normalize(selected, len(items))
    chosen = set(rows)
    removed = [(index, items[index]) for index in rows]
    kept = [item for index, item in enumerate(items) if index not in chosen]
    return kept, removed


def insert_at[T](items: Sequence[T], new: Sequence[T], position: int) -> tuple[list[T], list[int]]:
    """*new* inserted before row *position* (clamped), and their new rows."""
    target = max(0, min(int(position), len(items)))
    result = list(items[:target]) + list(new) + list(items[target:])
    return result, list(range(target, target + len(new)))


def restore_order(items: Sequence[MediaItem], order: Sequence[int]) -> list[MediaItem]:
    """*items* rearranged into the id *order* an earlier edit started from.

    The inverse of any move, paste or sort, and the reason undo addresses items
    by id: items removed since are simply absent, and items added since keep
    their place after the ones the old order names -- so undoing an old step
    never loses a newer one.
    """
    by_id = {item.id: item for item in items}
    restored = [by_id.pop(item_id) for item_id in order if item_id in by_id]
    restored.extend(item for item in items if item.id in by_id)
    return restored


def _sort_key(key: str) -> Callable[[MediaItem], tuple[object, ...]]:
    if key == "artist":
        return lambda item: (
            natural_key(item.artist or "￿"),
            natural_key(item.album),
            natural_key(item.file_name),
        )
    if key == "album":
        return lambda item: (natural_key(item.album or "￿"), natural_key(item.file_name))
    if key == "file":
        return lambda item: natural_key(item.file_name)
    if key == "folder":
        return lambda item: (natural_key(item.folder), natural_key(item.file_name))
    if key == "length":
        return lambda item: (item.duration_seconds <= 0, item.duration_seconds)
    if key == "added":
        return lambda item: (item.added_at, item.id)
    return lambda item: natural_key(item.display_title)


def sort_items(
    items: Sequence[MediaItem],
    key: str,
    *,
    shuffler: Callable[[list[MediaItem]], None] | None = None,
) -> list[MediaItem]:
    """*items* sorted once by *key* (one of :data:`SORT_KEYS`).

    Stable, so items that tie keep the order the listener gave them. Unknown
    lengths sort last rather than first: "shortest first" that opens on a row
    of files whose length nobody knows is not what was asked for.
    """
    result = list(items)
    if key == "random":
        (shuffler or random.shuffle)(result)
        return result
    result.sort(key=_sort_key(key))
    return result


def sort_label(key: str) -> str:
    """The spoken name of a sort key, for "Sorted by title"."""
    for candidate, label in SORT_KEYS:
        if candidate == key:
            return label.split(",")[0].lower()
    return key


def moved_sentence(rows: Sequence[int], total: int) -> str:
    """Where a move left things, said once: "Moved to 3 of 12." (pure).

    Positions are one-based, because that is how the reader counts rows. A
    block says its first and last row, which is all anybody needs to find it.
    """
    if not rows or total <= 0:
        return ""
    if len(rows) == 1:
        return f"Moved to {rows[0] + 1} of {total}."
    return f"Moved {len(rows)} items to {rows[0] + 1} to {rows[-1] + 1} of {total}."
