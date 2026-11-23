"""Lists that stay still (FUX-06): which row the reader lands on, and what is said.

The wx half is :mod:`quill.ui.list_stay_still`, which puts the selection, the
focused item and the scroll position back without touching keyboard focus.
This half is pure, so every app answers the same two questions the same way:

* **Which row?** The reader's own item, found by identity (an id, an address,
  a path -- never a row number). When it has gone, the row that moved up into
  its place, or the last row when the list got shorter: the shared rule in
  :func:`quill.core.activity.restore_index`.
* **What is said?** Nothing, when the item is still there: the screen reader
  already reads a selection change, and nothing about the row changed. One
  plain sentence when it has gone, or when a filter now hides it, so a reader
  who hears a different row knows why.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from quill.core.activity import restore_index

__all__ = ["Landing", "land", "change_rows", "gone_sentence", "hidden_sentence"]


@dataclass(frozen=True)
class Landing:
    """Where the reader lands after a refill: the row, and whether it is theirs."""

    index: int
    kept: bool


def land(keys: Sequence[str], wanted: str | None, previous: int) -> Landing:
    """The row to put the reader on after a list was refilled.

    *keys* are the new rows' identities in order, *wanted* the identity the
    reader was on (``None`` when they were on nothing) and *previous* the row
    number it had. ``kept`` is False only when the reader *was* on something
    and it is no longer in the list.
    """
    index = restore_index(keys, wanted, previous)
    kept = wanted is None or (0 <= index < len(keys) and keys[index] == wanted)
    return Landing(index=index, kept=kept)


def change_rows(
    old: Sequence[str],
    new: Sequence[str],
    *,
    delete: Callable[[int], None],
    insert: Callable[[int, int], None],
    update: Callable[[int, int], None],
    pin: str | None = None,
) -> None:
    """Turn a list showing *old* keys into one showing *new*, row by row.

    Rows that stay are updated in place (``update(row, new_index)``); only the
    rows that left are deleted (``delete(row)``) and only the ones that arrived
    are inserted (``insert(row, new_index)``). A native list then keeps the
    reader's row as the *same* item -- still selected, still focused -- and a
    screen reader has nothing to say, where clearing and refilling destroys
    the item they were on and reads its replacement. Work runs from the end of
    the list backwards, so every row number given is the list's current one.

    *pin* is the reader's own key. When it is in both lists the two halves
    either side of it are matched separately, so even a re-sorted list keeps
    the reader's row as the same item instead of deleting and re-inserting it.
    """
    old, new = list(old), list(new)
    if pin is not None and old.count(pin) == 1 and new.count(pin) == 1:
        at_old, at_new = old.index(pin), new.index(pin)
        rest = {"delete": delete, "insert": insert, "update": update}
        _match(old[at_old + 1 :], new[at_new + 1 :], at_old + 1, at_new + 1, **rest)
        update(at_old, at_new)
        _match(old[:at_old], new[:at_new], 0, 0, **rest)
        return
    _match(old, new, 0, 0, delete=delete, insert=insert, update=update)


def _match(
    old: list[str],
    new: list[str],
    row0: int,
    new0: int,
    *,
    delete: Callable[[int], None],
    insert: Callable[[int, int], None],
    update: Callable[[int, int], None],
) -> None:
    """:func:`change_rows` for one stretch starting at screen row *row0*."""
    matcher = SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
        i1, i2, j1, j2 = i1 + row0, i2 + row0, j1 + new0, j2 + new0
        if tag == "equal":
            for offset in range(i2 - i1):
                update(i1 + offset, j1 + offset)
            continue
        for row in range(i2 - 1, i1 - 1, -1):
            delete(row)
        for offset, new_index in enumerate(range(j1, j2)):
            insert(i1 + offset, new_index)


def gone_sentence(name: str) -> str:
    """Said once when the item the reader was on has left the list."""
    name = name.strip()
    if not name:
        return "The item you were on is no longer in the list."
    return f"{name} is no longer in the list."


def hidden_sentence(name: str) -> str:
    """Said once when a filter the reader chose hides the item they were on."""
    name = name.strip()
    if not name:
        return "The item you were on is not shown with this filter."
    return f"{name} is not shown with this filter."
