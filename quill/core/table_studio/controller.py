"""Active-cell state, spoken-cell formatting, and structural commands (wx-free).

The controller sits between the model (data) and the UI: it tracks the active
cell, formats accessible cell descriptions at three verbosity profiles
(Concise / Standard / Detailed) with JAWS-style "changed header" announcing, and
dispatches row/column commands to the model. Ported from the table_studio_proto
prototype.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.table_studio.model import Change, TableDocumentModel

# ── Spoken-cell formatter ─────────────────────────────────────────────────────


class SpokenCellFormatter:
    """
    Composes accessible cell descriptions at configurable verbosity.

    PRD §8.4 defines Standard, Detailed, and Concise profiles.
    The formatter is intentionally separate from the controller so it can be
    unit-tested and swapped independently.
    """

    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"

    def __init__(self, verbosity: str = STANDARD):
        self.verbosity = verbosity

    def cell(
        self,
        model: TableDocumentModel,
        row: int,
        col: int,
        include_position: bool = True,
        prev_col_hdr: str = "",
        prev_row_hdr: str = "",
    ) -> str:
        """Return the full spoken description for one cell.

        prev_col_hdr / prev_row_hdr are the headers from the *previous* cell
        and are used to implement the "changed" announce mode: a header is
        omitted when it is identical to the one already in the listener's ear.
        The active col_headers / row_headers mode (off | always | changed) is
        taken from model.announce_config, so the Reading Settings dialog fully
        controls this behaviour.
        """
        c = model.cell(row, col)
        col_hdr = model.col_header(col)
        value = (c.content if c else "").replace("\n", " ") or "Blank"
        editable = c.editable if c else False
        edit_tag = "" if editable else ", read only"

        row_hdr = model.row_header(row)
        ac = model.announce_config

        # Decide which contextual labels to include
        include_col = ac.col_headers == "always" or (
            ac.col_headers == "changed" and col_hdr != prev_col_hdr
        )
        include_row = (
            model.header_config.first_col_is_header
            and row_hdr != f"Row {row + 1}"
            and (
                ac.row_headers == "always"
                or (ac.row_headers == "changed" and row_hdr != prev_row_hdr)
            )
        )
        # "off" disables the label entirely
        if ac.col_headers == "off":
            include_col = False
        if ac.row_headers == "off":
            include_row = False

        # Optional coordinate prefix, independent of verbosity profile.
        coord = f"Row {row + 1}, column {col + 1}" if ac.coordinates else ""

        # ── Concise ───────────────────────────────────────────────────────
        if self.verbosity == self.CONCISE:
            parts = [coord] if coord else []
            if include_col:
                parts.append(col_hdr)
            parts.append(value)
            return ", ".join(parts)

        # ── Standard ──────────────────────────────────────────────────────
        if self.verbosity == self.STANDARD:
            parts = [coord] if coord else []
            if include_row:
                parts.append(row_hdr)
            if include_col:
                parts.append(col_hdr)
            parts.append(value + edit_tag)
            return ", ".join(parts)

        # ── Detailed (always includes coordinates) ─────────────────────────
        pos = f"Row {row + 1} of {model.row_count}, column {col + 1} of {model.col_count}"
        hdr_parts = []
        if include_row:
            hdr_parts.append(row_hdr)
        if include_col:
            hdr_parts.append(col_hdr)
        hdr_str = ", ".join(hdr_parts)
        if hdr_str:
            return f"{pos}. {hdr_str}. {value}{edit_tag}"
        return f"{pos}. {value}{edit_tag}"

    def table_entry(self, model: TableDocumentModel) -> str:
        """Announce on entering the table."""
        cap = model.caption or "Table"
        return f"{cap}. {model.row_count} rows, {model.col_count} columns."

    def operation(self, op: str, **ctx: object) -> str:
        """Return a spoken result for a structural operation."""
        msgs = {
            "row_inserted": "Row inserted.",
            "row_deleted": "Row deleted.",
            "row_moved_up": "Row moved up.",
            "row_moved_down": "Row moved down.",
            "col_inserted": "Column inserted.",
            "col_deleted": "Column deleted.",
            "col_moved_left": "Column moved left.",
            "col_moved_right": "Column moved right.",
            "cell_committed": "Edit committed.",
            "cell_cancelled": "Edit cancelled.",
            "no_rows": "Cannot delete the only row.",
            "no_cols": "Cannot delete the only column.",
        }
        return msgs.get(op, op)


# ── Controller ────────────────────────────────────────────────────────────────


class TableController:
    """
    Manages active-cell state, in-progress cell edits, and all model commands.

    The announce_callback receives spoken strings; call it after every user
    action. The update_callbacks fire after any model or cursor change so that
    UI panels can refresh themselves.
    """

    def __init__(self, model: TableDocumentModel, verbosity: str = SpokenCellFormatter.STANDARD):
        self.model: TableDocumentModel = model
        self.formatter: SpokenCellFormatter = SpokenCellFormatter(verbosity)
        self._active_row: int = 0
        self._active_col: int = 0
        self._cell_draft: str | None = None
        self._editing: bool = False

        self._announce_cb: Callable[[str], None] | None = None
        self._update_cbs: list[Callable[[], None]] = []
        # Track the last-announced headers for "changed" announce mode
        self._prev_col_hdr: str = ""
        self._prev_row_hdr: str = ""

        model.add_listener(self._on_model_change)

    # ── External wiring ────────────────────────────────────────────────────

    def set_announce_callback(self, fn: Callable[[str], None]) -> None:
        self._announce_cb = fn

    def add_update_callback(self, fn: Callable[[], None]) -> None:
        self._update_cbs.append(fn)

    def _announce(self, text: str) -> None:
        if self._announce_cb:
            self._announce_cb(text)

    def _request_update(self) -> None:
        for fn in self._update_cbs:
            try:
                fn()
            except Exception:  # noqa: BLE001
                # UI update callbacks are best-effort; a failing one must not
                # break editing or the other callbacks.
                pass

    # ── Active cell ────────────────────────────────────────────────────────

    @property
    def active_row(self) -> int:
        return self._active_row

    @property
    def active_col(self) -> int:
        return self._active_col

    def set_active_cell(self, row: int, col: int, announce: bool = True) -> None:
        row = max(0, min(row, max(self.model.row_count - 1, 0)))
        col = max(0, min(col, max(self.model.col_count - 1, 0)))
        changed = row != self._active_row or col != self._active_col
        # Capture prev headers *before* updating active cell (for "changed" mode)
        prev_col = self._prev_col_hdr
        prev_row = self._prev_row_hdr
        self._active_row = row
        self._active_col = col
        if announce and changed and self.model.row_count:
            msg = self.formatter.cell(
                self.model,
                row,
                col,
                prev_col_hdr=prev_col,
                prev_row_hdr=prev_row,
            )
            self._announce(msg)
        if self.model.row_count:
            self._prev_col_hdr = self.model.col_header(col)
            self._prev_row_hdr = self.model.row_header(row)
        self._request_update()

    def active_cell_description(self) -> str:
        return self.formatter.cell(self.model, self._active_row, self._active_col)

    def active_cell_value(self) -> str:
        return self.model.value(self._active_row, self._active_col)

    # ── Cell editing ───────────────────────────────────────────────────────

    def begin_edit(self) -> str:
        """Start editing the active cell. Returns its current content."""
        c = self.model.cell(self._active_row, self._active_col)
        if c and c.editable:
            self._editing = True
            self._cell_draft = c.content
            return c.content
        return ""

    def update_draft(self, value: str) -> None:
        self._cell_draft = value

    def commit_edit(self) -> bool:
        if not self._editing or self._cell_draft is None:
            return False
        ok = self.model.set_value(self._active_row, self._active_col, self._cell_draft)
        self._editing = False
        self._cell_draft = None
        if ok:
            self._announce(self.formatter.operation("cell_committed"))
        return ok

    def cancel_edit(self) -> None:
        self._editing = False
        self._cell_draft = None
        self._announce(self.formatter.operation("cell_cancelled"))
        self._request_update()

    @property
    def is_editing(self) -> bool:
        return self._editing

    # ── Row operations ─────────────────────────────────────────────────────

    def insert_row_above(self) -> None:
        self.model.insert_row(self._active_row)
        self._announce(self.formatter.operation("row_inserted"))

    def insert_row_below(self) -> None:
        at = self._active_row + 1
        self.model.insert_row(at)
        self.set_active_cell(at, self._active_col, announce=False)
        self._announce(self.formatter.operation("row_inserted"))

    def can_delete_row(self) -> bool:
        return self.model.row_count > 1

    def delete_active_row(self) -> None:
        if self.model.row_count <= 1:
            self._announce(self.formatter.operation("no_rows"))
            return
        self.model.delete_row(self._active_row)
        new = min(self._active_row, self.model.row_count - 1)
        self.set_active_cell(new, self._active_col, announce=True)
        self._announce(self.formatter.operation("row_deleted"))

    def can_move_row_up(self) -> bool:
        return self._active_row > 0

    def can_move_row_down(self) -> bool:
        return self._active_row < self.model.row_count - 1

    def move_row_up(self) -> None:
        if self.can_move_row_up():
            self.model.move_row(self._active_row, self._active_row - 1)
            self._active_row -= 1
            self._announce(self.formatter.operation("row_moved_up"))
            self._request_update()
        else:
            self._announce("Already at the first row.")

    def move_row_down(self) -> None:
        if self.can_move_row_down():
            self.model.move_row(self._active_row, self._active_row + 1)
            self._active_row += 1
            self._announce(self.formatter.operation("row_moved_down"))
            self._request_update()
        else:
            self._announce("Already at the last row.")

    # ── Column operations ──────────────────────────────────────────────────

    def insert_col_before(self) -> None:
        self.model.insert_col(self._active_col)
        self._announce(self.formatter.operation("col_inserted"))

    def insert_col_after(self) -> None:
        at = self._active_col + 1
        self.model.insert_col(at)
        self.set_active_cell(self._active_row, at, announce=False)
        self._announce(self.formatter.operation("col_inserted"))

    def can_delete_col(self) -> bool:
        return self.model.col_count > 1

    def delete_active_col(self) -> None:
        if self.model.col_count <= 1:
            self._announce(self.formatter.operation("no_cols"))
            return
        self.model.delete_col(self._active_col)
        new = min(self._active_col, self.model.col_count - 1)
        self.set_active_cell(self._active_row, new, announce=True)
        self._announce(self.formatter.operation("col_deleted"))

    def can_move_col_left(self) -> bool:
        return self._active_col > 0

    def can_move_col_right(self) -> bool:
        return self._active_col < self.model.col_count - 1

    def move_col_left(self) -> None:
        if self.can_move_col_left():
            self.model.move_col(self._active_col, self._active_col - 1)
            self._active_col -= 1
            self._announce(self.formatter.operation("col_moved_left"))
            self._request_update()
        else:
            self._announce("Already at the leftmost column.")

    def move_col_right(self) -> None:
        if self.can_move_col_right():
            self.model.move_col(self._active_col, self._active_col + 1)
            self._active_col += 1
            self._announce(self.formatter.operation("col_moved_right"))
            self._request_update()
        else:
            self._announce("Already at the rightmost column.")

    # ── Model listener ─────────────────────────────────────────────────────

    def _on_model_change(self, change: Change, kwargs: dict) -> None:
        self._request_update()
