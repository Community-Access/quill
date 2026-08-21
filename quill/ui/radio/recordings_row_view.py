"""How a Recordings row is built, filled and kept in step.

Split out of ``recordings_manager_dialog`` under GATE-11, along the same seam
``results_view`` follows for Find Stations: *getting* recordings on one side,
*presenting* them on the other. Everything here answers "what does this row
say?" -- which columns exist, in what order, and what goes in each of them.

That seam is where the configurable columns landed. Once a listener can reorder
and hide columns, ``SetItem(row, 2, ...)`` is a promise about a position nobody
can keep, so every cell is produced by id and written through the shared
column view. The one-dictionary-per-entry shape is what lets the in-place diff,
the no-op fast path and the fill all read the same answer.
"""

from __future__ import annotations

from quill.core.media.list_columns import ColumnDef
from quill.core.radio.recordings_index import (
    STATUS_RECORDING,
    RecordingEntry,
    format_elapsed,
)
from quill.ui.media.list_columns_view import build_columns, columns_for, set_row

#: This list's id in Radio's column catalogue. Defined here rather than in the
#: dialog because this is where the row is built, and a fill site that names its
#: own surface is one that cannot fill somebody else's columns.
SURFACE = "radio.recordings"


class RecordingsRowViewMixin:
    """Row presentation for :class:`RecordingsManagerDialog`."""

    def _build_columns(self) -> None:
        """Give the list the columns the listener chose, in their order.

        View > Choose Columns... owns which columns exist; a report row is read
        out column by column, so that choice is the sentence every row speaks.
        """
        self._columns: list[ColumnDef] = columns_for("radio", SURFACE)
        build_columns(self._list, self._columns)

    def _cells(self, entry: RecordingEntry) -> dict[str, str]:
        """Every cell *entry* could show, keyed by column id.

        Used by the diff, by the no-op fast path and by the fill, so all three
        always agree -- and keyed rather than positional for the reason the
        module docstring gives.
        """
        if entry.status == STATUS_RECORDING and entry.started_at is not None:
            when = f"elapsed {format_elapsed(entry.started_at)}"
        elif entry.modified is not None:
            when = entry.modified.strftime("%Y-%m-%d %H:%M")
        else:
            when = entry.detail
        # A capture with no chosen length carries a disk-safety cap rather than
        # a plan, and showing that number as a length would announce an
        # intention nobody expressed.
        length = f"{entry.scheduled_minutes} min" if entry.duration_requested else ""
        return {
            "name": entry.name,
            "status": entry.status,
            "size": entry.size_display,
            "when": when,
            "length": length,
        }

    def _set_row(self, row: int, entry: RecordingEntry) -> None:
        """Update row *row* in place to match *entry* (R1 -- no rebuild)."""
        set_row(self._list, row, self._columns, self._cells(entry))
