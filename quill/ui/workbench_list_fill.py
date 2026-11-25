"""The Workbench list changes row by row and keeps the reader still (FUX-06).

Refilling a report list row by row preserves native item identity, selection,
focus and scroll position. A row the reader did not ask to refresh is not
rewritten underneath them, while an explicit Refresh may update it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.list_follow import change_rows, land
from quill.core.workbench.list_place import row_identities
from quill.ui.list_stay_still import capture_report, restore_report, selected_rows

__all__ = ["fill_rows"]


def _write(control: Any, row: int, cells: Sequence[str], *, inserted: bool) -> None:
    if inserted:
        control.InsertItem(row, cells[0] if cells else "")
    for column, text in enumerate(cells):
        if column == 0 and inserted:
            continue
        if inserted or control.GetItemText(row, column) != text:
            control.SetItem(row, column, text)


def fill_rows(
    frame: Any, rows: list[object], cells: list[list[str]], landing: int, *, ours: bool
) -> str:
    """Show *rows* and return the first cell of the reader's now-gone row."""
    control = frame.list
    old_ids = row_identities(frame.rows)
    new_ids = row_identities(rows)
    anchor = capture_report(control)
    reader = old_ids[anchor.index] if 0 <= anchor.index < len(old_ids) else None
    others = [old_ids[row] for row in selected_rows(control) if row < len(old_ids)]
    gone = ""
    if reader is not None and reader not in new_ids:
        gone = control.GetItemText(anchor.index, 0)
    if control.GetItemCount() == len(old_ids):

        def _update(row: int, new: int) -> None:
            if ours or new_ids[new] != reader:
                _write(control, row, cells[new], inserted=False)

        change_rows(
            old_ids,
            new_ids,
            delete=control.DeleteItem,
            insert=lambda row, new: _write(control, row, cells[new], inserted=True),
            update=_update,
            pin=reader,
        )
    else:
        control.DeleteAllItems()
        for index, row_cells in enumerate(cells):
            _write(control, index, row_cells, inserted=True)
    frame.rows, frame._shown_cells = rows, cells
    if landing < 0:
        return gone
    if reader is not None and not gone:
        landing = land(new_ids, reader, anchor.index).index
    also = [new_ids.index(key) for key in others if key in new_ids]
    restore_report(frame._wx, control, anchor, landing, also=also)
    return gone
