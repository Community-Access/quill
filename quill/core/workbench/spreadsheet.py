"""Reading a spreadsheet for an import, in every Workbench (2026-11-17).

Moved from the WordPress Workbench (its Import Posts from a Spreadsheet) so the
GitHub Workbench's Import Issues reads the same files the same way: a CSV
file (UTF-8, with or without its byte-order mark) or an Excel workbook's first
sheet, the first row naming the columns.

wx-free and strict-typed.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

__all__ = ["SPREADSHEET_WILDCARD", "header_name", "numbered_rows", "read_spreadsheet"]

SPREADSHEET_WILDCARD = (
    "Spreadsheets (*.xlsx;*.csv)|*.xlsx;*.xlsm;*.csv|Excel workbook (*.xlsx)|*.xlsx;*.xlsm|"
    "CSV (*.csv)|*.csv"
)


def header_name(text: str) -> str:
    """A column heading as the importers compare it: lower case, spaces for _."""
    return " ".join(str(text).strip().lower().replace("_", " ").split())


def read_spreadsheet(path: Path) -> list[dict[str, str]]:
    """Each row of a CSV or Excel file as {column: text}, columns named by the header."""
    return [row for _number, row in numbered_rows(path)]


def numbered_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    """:func:`read_spreadsheet`'s rows with the row number the spreadsheet shows.

    The header is row 1; a blank row is skipped but still counted, so "row 5"
    in a preview is row 5 in Excel.
    """
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        book = load_workbook(str(path), read_only=True, data_only=True)
        sheet = book.active
        values = [
            ["" if cell is None else str(cell) for cell in row]
            for row in sheet.iter_rows(values_only=True)
        ]
        book.close()
    else:
        text = path.read_text(encoding="utf-8-sig")
        values = [list(row) for row in csv.reader(io.StringIO(text))]
    if not values:
        return []
    header = [header_name(h) for h in values[0]]
    return [
        (
            number,
            {
                header[i]: cell.strip()
                for i, cell in enumerate(row)
                if i < len(header) and header[i]
            },
        )
        for number, row in enumerate(values[1:], start=2)
        if any(cell.strip() for cell in row)
    ]
