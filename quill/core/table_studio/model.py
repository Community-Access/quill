"""Format-neutral table data model for Table Studio (wx-free).

The model owns all data; no UI widget holds a copy. Every mutation goes through
a model method, and listeners are notified after the fact (they must not mutate
the model). Ported from the table_studio_proto prototype. Serializes to Markdown
and HTML with proper header scopes.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

# ── Enumerations ──────────────────────────────────────────────────────────────


class Alignment(Enum):
    DEFAULT = "default"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ContentKind(Enum):
    TEXT = auto()
    MULTILINE = auto()
    NUMERIC = auto()
    BOOLEAN = auto()
    DATE = auto()
    READ_ONLY = auto()
    COMPLEX = auto()


class Change(Enum):
    CELL_VALUE = "cell_value"
    ROW_INSERTED = "row_inserted"
    ROW_DELETED = "row_deleted"
    ROW_MOVED = "row_moved"
    COL_INSERTED = "col_inserted"
    COL_DELETED = "col_deleted"
    COL_MOVED = "col_moved"
    STRUCTURE = "structure"
    HEADER_LABEL = "header_label"  # col-header override edited
    ANNOUNCE_CONFIG = "announce_config"  # AnnounceConfig replaced


# ── Value objects ─────────────────────────────────────────────────────────────


@dataclass
class TableCell:
    cell_id: str
    row_id: str
    col_id: str
    content: str = ""
    kind: ContentKind = ContentKind.TEXT
    editable: bool = True
    row_span: int = 1
    col_span: int = 1

    @property
    def is_blank(self) -> bool:
        return not self.content.strip()

    @property
    def is_multiline(self) -> bool:
        return "\n" in self.content


@dataclass
class TableRow:
    row_id: str
    cells: dict[str, TableCell] = field(default_factory=dict)
    is_header: bool = False
    label: str = ""


@dataclass
class TableColumn:
    col_id: str
    label: str = ""
    alignment: Alignment = Alignment.DEFAULT
    width_hint: int = 120
    is_row_header: bool = False
    kind: str = "text"


@dataclass
class HeaderConfig:
    first_col_is_header: bool = False
    header_col_ids: list[str] = field(default_factory=list)


@dataclass
class AnnounceConfig:
    """Controls which contextual labels screen readers hear during navigation.

    Mirrors the Freedom Scientific JAWS table verbosity options
    (Insert+F6 → Table Reading Options).

    col_headers / row_headers accept: "off" | "always" | "changed"
      "off"     — never announce the header, just value
      "always"  — announce every cell (traditional behaviour)
      "changed" — JAWS default: announce only when the header is different
                  from the previously announced cell's header
    coordinates — prepend "Row N, Column M" to each cell announcement
    page_size   — rows skipped per Page Up / Page Down in Detail View
    """

    col_headers: str = "changed"  # off | always | changed
    row_headers: str = "changed"  # off | always | changed
    coordinates: bool = False
    page_size: int = 10


# ── Model ─────────────────────────────────────────────────────────────────────

Listener = Callable[[Change, dict], None]


class TableDocumentModel:
    """
    Single source of truth for table content and structure.

    UI panels observe via listeners registered with add_listener().
    Listeners receive (Change, dict-of-kwargs); they must not mutate the model.
    """

    def __init__(self, caption: str = "", doc_format: str = "markdown"):
        self.model_id: str = str(uuid.uuid4())
        self.caption: str = caption
        self.summary: str = ""
        self.doc_format: str = doc_format
        self.columns: list[TableColumn] = []
        self.rows: list[TableRow] = []
        self.header_config: HeaderConfig = HeaderConfig()
        self.announce_config: AnnounceConfig = AnnounceConfig()
        # col_id → override label set by the user (overrides column.label for
        # announcements and serialisation; empty string = "use source label")
        self.col_label_overrides: dict[str, str] = {}
        # set when the model was loaded from a CSV file on disk
        self.csv_source_path: str | None = None
        self.csv_delimiter: str = ","
        self._listeners: list[Listener] = []

    # ── Listener management ────────────────────────────────────────────────

    def add_listener(self, fn: Listener) -> None:
        self._listeners.append(fn)

    def remove_listener(self, fn: Listener) -> None:
        try:
            self._listeners.remove(fn)
        except ValueError:
            pass  # already removed: removal is idempotent by design

    def _emit(self, change: Change, **kw: object) -> None:
        for fn in list(self._listeners):
            try:
                fn(change, kw)
            except Exception:  # noqa: BLE001
                # One failing listener must not block notifying the others.
                pass

    # ── Dimensions ────────────────────────────────────────────────────────

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.columns)

    # ── Cell access ───────────────────────────────────────────────────────

    def cell(self, row_idx: int, col_idx: int) -> TableCell | None:
        if 0 <= row_idx < len(self.rows) and 0 <= col_idx < len(self.columns):
            return self.rows[row_idx].cells.get(self.columns[col_idx].col_id)
        return None

    def value(self, row_idx: int, col_idx: int) -> str:
        c = self.cell(row_idx, col_idx)
        return c.content if c else ""

    def set_value(self, row_idx: int, col_idx: int, v: str) -> bool:
        c = self.cell(row_idx, col_idx)
        if c is None or not c.editable:
            return False
        old = c.content
        c.content = v
        self._emit(Change.CELL_VALUE, row_idx=row_idx, col_idx=col_idx, old=old, new=v)
        return True

    def is_editable(self, row_idx: int, col_idx: int) -> bool:
        c = self.cell(row_idx, col_idx)
        return c is not None and c.editable

    # ── Header helpers ────────────────────────────────────────────────────

    def col_header(self, col_idx: int) -> str:
        """Return the effective column header label.

        User-defined overrides (stored in col_label_overrides) take priority
        over the column's source label.  This is the canonical label used by
        the formatter, serialisers, and the list-ctrl column headers.
        """
        if 0 <= col_idx < len(self.columns):
            col = self.columns[col_idx]
            override = self.col_label_overrides.get(col.col_id)
            if override:  # non-None and non-empty
                return override
            return col.label or f"Column {col_idx + 1}"
        return f"Column {col_idx + 1}"

    def set_col_label_override(self, col_idx: int, label: str) -> None:
        """Set a user-corrected column header label."""
        if 0 <= col_idx < len(self.columns):
            col_id = self.columns[col_idx].col_id
            self.col_label_overrides[col_id] = label.strip()
            self._emit(Change.HEADER_LABEL, col_idx=col_idx, label=label)

    def clear_col_label_override(self, col_idx: int) -> None:
        """Remove a user-corrected label, reverting to the source label."""
        if 0 <= col_idx < len(self.columns):
            col_id = self.columns[col_idx].col_id
            self.col_label_overrides.pop(col_id, None)
            self._emit(Change.HEADER_LABEL, col_idx=col_idx, label=None)

    def set_announce_config(self, config: AnnounceConfig) -> None:
        self.announce_config = config
        self._emit(Change.ANNOUNCE_CONFIG)

    def row_header(self, row_idx: int) -> str:
        if self.header_config.first_col_is_header and self.columns:
            v = self.value(row_idx, 0)
            if v:
                return v
        return f"Row {row_idx + 1}"

    # ── Row operations ────────────────────────────────────────────────────

    def _new_row(self) -> TableRow:
        row_id = str(uuid.uuid4())
        row = TableRow(row_id=row_id)
        for col in self.columns:
            row.cells[col.col_id] = TableCell(
                cell_id=str(uuid.uuid4()),
                row_id=row_id,
                col_id=col.col_id,
            )
        return row

    def insert_row(self, at: int) -> str:
        row = self._new_row()
        at = max(0, min(at, len(self.rows)))
        self.rows.insert(at, row)
        self._emit(Change.ROW_INSERTED, row_id=row.row_id, at=at)
        return row.row_id

    def delete_row(self, idx: int) -> bool:
        if not (0 <= idx < len(self.rows)):
            return False
        row_id = self.rows[idx].row_id
        del self.rows[idx]
        self._emit(Change.ROW_DELETED, row_id=row_id, idx=idx)
        return True

    def move_row(self, frm: int, to: int) -> bool:
        n = len(self.rows)
        if not (0 <= frm < n and 0 <= to < n and frm != to):
            return False
        row = self.rows.pop(frm)
        self.rows.insert(to, row)
        self._emit(Change.ROW_MOVED, frm=frm, to=to)
        return True

    # ── Column operations ─────────────────────────────────────────────────

    def _new_col(self, label: str = "") -> TableColumn:
        col_id = str(uuid.uuid4())
        return TableColumn(col_id=col_id, label=label or f"Column {len(self.columns) + 1}")

    def insert_col(self, at: int, label: str = "") -> str:
        col = self._new_col(label)
        at = max(0, min(at, len(self.columns)))
        self.columns.insert(at, col)
        for row in self.rows:
            row.cells[col.col_id] = TableCell(
                cell_id=str(uuid.uuid4()),
                row_id=row.row_id,
                col_id=col.col_id,
            )
        self._emit(Change.COL_INSERTED, col_id=col.col_id, at=at)
        return col.col_id

    def delete_col(self, idx: int) -> bool:
        if not (0 <= idx < len(self.columns)):
            return False
        col_id = self.columns[idx].col_id
        del self.columns[idx]
        for row in self.rows:
            row.cells.pop(col_id, None)
        self._emit(Change.COL_DELETED, col_id=col_id, idx=idx)
        return True

    def move_col(self, frm: int, to: int) -> bool:
        n = len(self.columns)
        if not (0 <= frm < n and 0 <= to < n and frm != to):
            return False
        col = self.columns.pop(frm)
        self.columns.insert(to, col)
        self._emit(Change.COL_MOVED, frm=frm, to=to)
        return True

    # ── Sorting ───────────────────────────────────────────────────────────

    def sort_by_column(self, col_idx: int, *, ascending: bool = True) -> bool:
        """Sort the rows in place by one column's values.

        Numeric-looking values sort numerically; everything else sorts as a
        case-insensitive string. Blanks sort last regardless of direction.
        """
        if not (0 <= col_idx < len(self.columns)):
            return False
        col_id = self.columns[col_idx].col_id

        def key(row: TableRow) -> tuple:
            cell = row.cells.get(col_id)
            text = (cell.content if cell else "").strip()
            if not text:
                return (2, 0.0, "")  # blanks last
            try:
                return (0, float(text.replace(",", "")), "")
            except ValueError:
                return (1, 0.0, text.casefold())

        self.rows.sort(key=key, reverse=not ascending)
        self._emit(Change.STRUCTURE, sorted_col=col_idx, ascending=ascending)
        return True

    # ── Header configuration ──────────────────────────────────────────────

    def set_first_column_as_row_header(self, enabled: bool) -> None:
        """Mark the first column as row headers, so exports use <th scope="row">."""
        self.header_config.first_col_is_header = enabled
        if self.columns:
            self.columns[0].is_row_header = enabled
        self._emit(Change.STRUCTURE, first_col_is_header=enabled)

    def has_row_header(self) -> bool:
        return self.header_config.first_col_is_header

    def promote_first_row_to_header(self) -> bool:
        """Use the first data row's values as the column headers, then drop it.

        For a CSV whose header row was read as data — makes row 1 the real
        header (its text becomes each column's label override).
        """
        if not self.rows or not self.columns:
            return False
        first = self.rows[0]
        for col in self.columns:
            cell = first.cells.get(col.col_id)
            label = (cell.content if cell else "").strip()
            if label:
                self.col_label_overrides[col.col_id] = label
        del self.rows[0]
        self._emit(Change.STRUCTURE, promoted_header=True)
        return True

    # ── Serialization ─────────────────────────────────────────────────────

    def to_markdown(self) -> str:
        if not self.columns:
            return ""
        # Width from the rendered header (col_header includes user overrides),
        # not the source label — an override longer than the label misaligned
        # the emitted table (#802 review).
        col_w = [max(len(self.col_header(ci)), 3) for ci in range(len(self.columns))]
        for row in self.rows:
            for ci, col in enumerate(self.columns):
                cell = row.cells.get(col.col_id)
                if cell:
                    col_w[ci] = max(col_w[ci], len(cell.content.replace("\n", " ")))

        def pipe_row(vals: list) -> str:
            return "| " + " | ".join(v.ljust(col_w[i]) for i, v in enumerate(vals)) + " |"

        lines = [pipe_row([self.col_header(ci) for ci in range(len(self.columns))])]
        delims = []
        for i, col in enumerate(self.columns):
            w = col_w[i]
            if col.alignment == Alignment.CENTER:
                delims.append(":" + "-" * max(1, w - 2) + ":")
            elif col.alignment == Alignment.RIGHT:
                delims.append("-" * max(1, w - 1) + ":")
            else:
                delims.append("-" * w)
        lines.append("| " + " | ".join(delims) + " |")
        for row in self.rows:
            vals = []
            for col in self.columns:
                c = row.cells.get(col.col_id)
                v = (c.content if c else "").replace("\n", " ").replace("|", "\\|")
                vals.append(v)
            lines.append(pipe_row(vals))
        return "\n".join(lines)

    def to_html(self) -> str:
        # Every user-controlled field is escaped: a cell containing "<" or "&"
        # must render as text, not break the markup or inject elements into
        # the document the table is inserted into (#802 review).
        from html import escape

        lines = ["<table>"]
        if self.caption:
            lines.append(f"  <caption>{escape(self.caption)}</caption>")
        lines.append("  <thead>\n    <tr>")
        for ci in range(len(self.columns)):
            lines.append(f'      <th scope="col">{escape(self.col_header(ci))}</th>')
        lines.append("    </tr>\n  </thead>")
        lines.append("  <tbody>")
        for row in self.rows:
            lines.append("    <tr>")
            for ci, col in enumerate(self.columns):
                cell = row.cells.get(col.col_id)
                v = escape(cell.content if cell else "")
                if self.header_config.first_col_is_header and ci == 0:
                    lines.append(f'      <th scope="row">{v}</th>')
                else:
                    lines.append(f"      <td>{v}</td>")
            lines.append("    </tr>")
        lines.append("  </tbody>\n</table>")
        return "\n".join(lines)

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def from_lists(
        cls,
        headers: list[str],
        rows: list[list[str]],
        caption: str = "",
        first_col_is_header: bool = False,
        alignments: list[Alignment] | None = None,
        doc_format: str = "markdown",
    ) -> TableDocumentModel:
        m = cls(caption=caption, doc_format=doc_format)

        for i, h in enumerate(headers):
            col = m._new_col(h)
            if alignments and i < len(alignments):
                col.alignment = alignments[i]
            if first_col_is_header and i == 0:
                col.is_row_header = True
            m.columns.append(col)

        if first_col_is_header:
            m.header_config.first_col_is_header = True

        for rd in rows:
            row_id = str(uuid.uuid4())
            row = TableRow(row_id=row_id)
            for i, col in enumerate(m.columns):
                v = rd[i] if i < len(rd) else ""
                # The first column may be a row header (is_row_header / read-only
                # MSAA role), but its cells stay editable so F2 can rename them.
                row.cells[col.col_id] = TableCell(
                    cell_id=str(uuid.uuid4()),
                    row_id=row_id,
                    col_id=col.col_id,
                    content=v,
                    editable=True,
                    kind=ContentKind.TEXT,
                )
            m.rows.append(row)

        return m
