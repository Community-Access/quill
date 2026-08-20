"""Where the cursor goes after a row is deleted.

Two of Quill Radio's list managers answered this differently, and both answered
it wrongly (found 2026-08-19):

* **Recordings Manager** restored the selection *by identity* after a refresh.
  A deleted row has no identity left, so nothing was selected and nothing was
  focused -- a listener was left in a list with no cursor at all, and arrowing
  started again from the top.
* **Favorites Manager** fell through to "select the first item". Deleting the
  fortieth favourite read out the first one, with focus still in the tree, so
  the listener lost their place entirely.

Neither is what a sighted user gets, and neither is what a listener expects: the
cursor should stay where it *was*, which after a deletion means the row that took
the deleted one's place -- or the new last row, when the deleted one was last.

Pure and wx-free so both managers can share one answer and a test can pin it.
"""

from __future__ import annotations


def index_after_removal(removed_index: int, remaining: int) -> int | None:
    """The row to select once the row at *removed_index* is gone.

    *remaining* is the count **after** the removal. Returns ``None`` when the
    list is now empty, which is a different fact from "select row 0" and worth
    saying out loud rather than leaving as a silent no-op.

    >>> index_after_removal(3, 10)   # the row that moved up into its place
    3
    >>> index_after_removal(9, 9)    # it was last; the new last row
    8
    >>> index_after_removal(0, 0)    # nothing left
    """
    if remaining <= 0:
        return None
    return min(max(removed_index, 0), remaining - 1)


def neighbour_key(keys: list[str], removed: str) -> str | None:
    """The key to land on once *removed* is gone from *keys*.

    The tree version of :func:`index_after_removal`: a ``wx.TreeCtrl`` is
    rebuilt wholesale on every change, so the caller cannot ask for "row 3"
    afterwards -- it has to know *which item* to look for. Takes the display
    order **before** the removal and returns the next item, or the previous one
    when the removed item was last.

    ``None`` means the removed item was the only one.
    """
    try:
        index = keys.index(removed)
    except ValueError:
        return None
    after = keys[index + 1 :]
    if after:
        return after[0]
    before = keys[:index]
    return before[-1] if before else None
