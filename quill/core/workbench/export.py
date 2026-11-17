"""Export List, in every Workbench (GitHub PRD 22.7, WordPress PRD 15.10).

The list as it is shown -- its columns, its filter, its rows -- written as an
Excel workbook, a CSV file or a Markdown table (the QUILL table the editor's
table commands read). Moved here from the WordPress Workbench on 2026-11-17 so
the GitHub Workbench writes the same files from the same code.

wx-free and strict-typed.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from pathlib import Path

__all__ = ["EXPORT_WILDCARD", "export_rows", "hidden_columns_sentence", "markdown_table"]

#: The Save dialog's choices, Excel first (what most people open a list in).
EXPORT_WILDCARD = "Excel workbook (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv|Markdown table (*.md)|*.md"


def export_rows(
    path: Path, headings: Sequence[str], rows: Iterable[Sequence[str]], *, kind: str = ""
) -> int:
    """Write *rows* under *headings* to *path* (``.csv``, ``.xlsx`` or ``.md``); the count."""
    data = [list(map(str, row)) for row in rows]
    suffix = kind or path.suffix.lower().lstrip(".")
    if suffix in ("md", "markdown"):
        path.write_text(markdown_table(headings, data), encoding="utf-8", newline="\n")
        return len(data)
    if suffix == "xlsx":
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Workbench"
        sheet.append(list(headings))
        for row in data:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        book.save(str(path))
        return len(data)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(list(headings))
    writer.writerows(data)
    path.write_text(buffer.getvalue(), encoding="utf-8-sig", newline="")
    return len(data)


def markdown_table(headings: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """A Markdown (pipe) table; a pipe or line break inside a cell stays text."""

    def cell(text: object) -> str:
        said = str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r", "")
        return said.replace("\n", "<br>")

    lines = ["| " + " | ".join(cell(h) for h in headings) + " |"]
    lines.append("|" + "|".join(" --- " for _ in headings) + "|")
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def hidden_columns_sentence(shown: Sequence[str], every: Sequence[str]) -> str:
    """``Left out: the columns you have hidden (A, B).`` or ``""``."""
    hidden = [column for column in every if column not in shown]
    return f"Left out: the columns you have hidden ({', '.join(hidden)})." if hidden else ""
