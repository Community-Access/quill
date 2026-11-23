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

from quill.core.list_follow import change_rows, gone_sentence, land
from quill.core.media.list_columns import ColumnDef
from quill.core.radio.recordings_index import (
    STATUS_RECORDING,
    STATUS_SCHEDULED,
    RecordingEntry,
    format_elapsed,
)
from quill.core.radio.row_marks import marked_label
from quill.ui.list_stay_still import RowAnchor, restore_report, say_when_settled
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
            # "(marked)" on a row marked for deleting (recordings_marks).
            "name": marked_label(entry.name, entry.id in getattr(self, "_row_marks", ())),
            "status": entry.status,
            "size": entry.size_display,
            "when": when,
            "length": length,
        }

    def _set_row(self, row: int, entry: RecordingEntry) -> None:
        """Update row *row* in place to match *entry* (R1 -- no rebuild)."""
        set_row(self._list, row, self._columns, self._cells(entry))

    def _change_rows(self, snapshot: list[RecordingEntry], pin: str | None) -> None:
        """Make the rows match *snapshot*, inserting and deleting only what changed."""

        def _insert(row: int, new: int) -> None:
            self._list.InsertItem(row, "")
            self._set_row(row, snapshot[new])

        change_rows(
            [entry.id for entry in self._entries],
            [entry.id for entry in snapshot],
            delete=self._list.DeleteItem,
            insert=_insert,
            update=lambda row, new: self._set_row(row, snapshot[new]),
            pin=pin,
        )

    def _keep_reader(
        self,
        anchor: RowAnchor,
        selected: RecordingEntry | None,
        others: list[str],
        *,
        say_gone: bool,
    ) -> None:
        """Put the reader back on *selected* after a refresh (FUX-06).

        By identity, on the same line of the screen, without taking keyboard
        focus. A schedule that fires leaves the list as a Scheduled row and comes
        back as a Recording row of the same station, so the reader follows it
        there and nothing is said. Anything else that left -- a file removed in
        Explorer, a schedule deleted in another window -- lands the reader on the
        row that moved into its place, and the timer's refresh says so once.
        """
        if selected is None:
            return
        entries = list(self._entries)
        keys = [entry.id for entry in entries]
        wanted = selected.id
        if wanted not in keys and selected.status == STATUS_SCHEDULED:
            wanted = next(
                (e.id for e in entries if e.status == STATUS_RECORDING and e.name == selected.name),
                wanted,
            )
        landing = land(keys, wanted, anchor.index)
        if landing.index < 0:
            return
        also = [keys.index(key) for key in others if key in keys]
        restore_report(self._wx, self._list, anchor, landing.index, also=also)
        if not landing.kept and say_gone:
            say_when_settled(self._wx, self._list, self._announce, gone_sentence(selected.name))
