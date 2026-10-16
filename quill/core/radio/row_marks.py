"""Mark many rows, then delete them with one question (xradio2 4.10).

Period marks the row under the cursor and says how many are marked; the row
reads "(marked)" while you keep arrowing; Delete then removes every marked row
after **one** confirmation that says how many ("Delete 5 stations?"). This is
the shape GATE-BULK-COUNT already asks of a verb that touches many rows: it
says how many, before and after.

The marks are a set of stable row keys (a favourite's key, a recording's path),
never positions, because the lists that hold them are rebuilt wholesale on
every change. :meth:`RowMarks.keep_only` drops marks whose row has gone, so a
count can never include something that is no longer there.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.core.counted import plural

__all__ = [
    "MARK_SUFFIX",
    "RowMarks",
    "delete_question",
    "deleted_sentence",
    "landing_after",
    "marked_label",
]

#: What a marked row's text ends with. Words, not a symbol: a screen reader
#: says a word, and a check-mark glyph is read differently by every reader.
MARK_SUFFIX = " (marked)"


class RowMarks:
    """The keys of the rows somebody has marked, in the order they marked them."""

    def __init__(self) -> None:
        self._keys: list[str] = []

    def __len__(self) -> int:
        return len(self._keys)

    def __contains__(self, key: object) -> bool:
        return key in self._keys

    @property
    def keys(self) -> list[str]:
        return list(self._keys)

    def toggle(self, key: str) -> bool:
        """Mark *key*, or unmark it if it was marked. Returns whether it is now marked."""
        if not key:
            return False
        if key in self._keys:
            self._keys.remove(key)
            return False
        self._keys.append(key)
        return True

    def clear(self) -> int:
        """Unmark everything; returns how many were marked."""
        count = len(self._keys)
        self._keys.clear()
        return count

    def keep_only(self, existing: Iterable[str]) -> None:
        """Forget marks on rows that are no longer in the list."""
        alive = set(existing)
        self._keys = [key for key in self._keys if key in alive]

    def toggle_sentence(self, marked: bool) -> str:
        """What to say after a toggle: the new state and the running count.

        The row's own name is not repeated -- the reader has just said it, and
        it is about to say it again with "(marked)" on the end.
        """
        state = "Marked" if marked else "Unmarked"
        if not self._keys:
            return f"{state}. Nothing marked."
        return f"{state}. {len(self._keys)} marked."


def landing_after(order: list[str], current: str | None, removed: Iterable[str]) -> str | None:
    """Where the cursor goes once *removed* are gone.

    The row it was on when that survives; otherwise the next surviving row
    after it, then the nearest one before it; ``None`` when nothing is left.
    Worked out before the removal, because the list is rebuilt afterwards.
    """
    gone = set(removed)
    survivors = [key for key in order if key not in gone]
    if not survivors:
        return None
    if current is None or current not in order:
        return survivors[0]
    if current not in gone:
        return current
    index = order.index(current)
    after = [key for key in order[index + 1 :] if key not in gone]
    if after:
        return after[0]
    before = [key for key in order[:index] if key not in gone]
    return before[-1] if before else None


def marked_label(label: str, marked: bool) -> str:
    """A row's text with the mark on the end when it carries one."""
    return f"{label}{MARK_SUFFIX}" if marked else label


def delete_question(count: int, noun: str) -> str:
    """``Delete 5 stations?`` -- the one confirmation a marked delete asks."""
    return f"Delete {plural(count, noun)}?"


def deleted_sentence(count: int, noun: str, *, failed: int = 0) -> str:
    """What is said afterwards. Every clause carries a number (GATE-BULK-COUNT)."""
    said = f"Deleted {plural(count, noun)}."
    if failed:
        said += f" {plural(failed, noun)} could not be deleted."
    return said
