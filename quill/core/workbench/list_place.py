"""Where the Workbench list keeps your place when it is filled again: words only, no wx.

A screen reader reads the focused row of a list whenever its selection or its
focus changes. Refilling the list after Mark Read, a refresh or a filter used
to select row 0 and then focus it: two changes, so JAWS read the row twice,
and it was the wrong row, because the place you were at was lost. The frame
now asks :func:`landing_index` for the row you were on (the same item, by its
identity, wherever it moved) and selects and focuses it in one change; and
when nothing in the list changed it does not rewrite the list at all
(:func:`same_cells`), so a refresh that found nothing new says nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["landing_index", "row_identity", "same_cells"]

#: The attributes that say which item a row is, in order of trust.
_IDENTITY_FIELDS = ("url", "html_url", "key", "sha", "id", "number", "name", "tag")


def row_identity(row: object) -> str:
    """A string that stays the same for the same item across loads; ``""`` if none."""
    kind = type(row).__name__
    for field in _IDENTITY_FIELDS:
        value = getattr(row, field, None)
        if value not in (None, "", 0):
            return f"{kind}:{field}:{value}"
    return ""


def landing_index(old_rows: Sequence[object], old_index: int, new_rows: Sequence[object]) -> int:
    """The row to select after the list is filled with *new_rows*.

    The item that was at *old_index* in *old_rows*, wherever it is now; if it
    is gone (Mark Done removed it), the row now at the same position, or the
    last row; and row 0 when there was no place to keep. -1 for an empty list.
    """
    if not new_rows:
        return -1
    if not 0 <= old_index < len(old_rows):
        return 0
    wanted = row_identity(old_rows[old_index])
    if wanted:
        for index, row in enumerate(new_rows):
            if row_identity(row) == wanted:
                return index
    return min(old_index, len(new_rows) - 1)


def same_cells(before: Sequence[Sequence[str]], after: Sequence[Sequence[str]]) -> bool:
    """Whether two fills would show exactly the same text, row for row."""
    return len(before) == len(after) and all(
        list(a) == list(b) for a, b in zip(before, after, strict=True)
    )
