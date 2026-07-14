"""CSV load/save for Table Studio (wx-free, stdlib only).

Reads a CSV into a :class:`TableDocumentModel` (first row as headers, delimiter
auto-detected) and writes a model back out. Kept separate from the UI so the
round-trip is unit-testable without wx.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from quill.core.table_studio.model import TableDocumentModel

_DELIMITERS = ("\t", ";", "|", ",")


def sniff_delimiter(sample: str) -> str:
    """Best-effort delimiter from a text sample (tab / semicolon / pipe / comma)."""
    best = ","
    for delimiter in _DELIMITERS:
        if sample.count(delimiter) > sample.count(best):
            best = delimiter
    return best


def parse_csv_text(
    text: str, *, caption: str = "", delimiter: str | None = None
) -> TableDocumentModel:
    """Parse CSV ``text`` into a model. Raises ``ValueError`` when it is empty."""
    delimiter = delimiter or sniff_delimiter(text[:4096])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = [row for row in reader]
    if not all_rows:
        raise ValueError("The CSV is empty.")
    headers = all_rows[0]
    data = all_rows[1:]
    model = TableDocumentModel.from_lists(headers=headers, rows=data, caption=caption)
    model.csv_delimiter = delimiter
    return model


def load_csv(path: str | Path) -> TableDocumentModel:
    """Load a CSV file into a model (UTF-8, BOM-tolerant); auto-detects delimiter."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    model = parse_csv_text(text, caption=p.stem)
    model.csv_source_path = str(p)
    return model


def to_csv_text(model: TableDocumentModel, *, delimiter: str | None = None) -> str:
    """Serialize a model back to CSV text (headers + rows)."""
    delimiter = delimiter or (model.csv_delimiter or ",")
    out = io.StringIO()
    writer = csv.writer(out, delimiter=delimiter, lineterminator="\n")
    writer.writerow([model.col_header(ci) for ci in range(model.col_count)])
    for row_idx in range(model.row_count):
        writer.writerow([model.value(row_idx, ci) for ci in range(model.col_count)])
    return out.getvalue()


def save_csv(model: TableDocumentModel, path: str | Path, *, delimiter: str | None = None) -> None:
    """Write a model to ``path`` as CSV (UTF-8)."""
    Path(path).write_text(to_csv_text(model, delimiter=delimiter), encoding="utf-8")


__all__ = ["load_csv", "parse_csv_text", "save_csv", "sniff_delimiter", "to_csv_text"]
