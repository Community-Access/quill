"""Export List, shared by both Workbenches (GitHub PRD 22.7, WordPress PRD 15.10)."""

from __future__ import annotations

import csv
from pathlib import Path

from quill.core.workbench.export import export_rows, hidden_columns_sentence, markdown_table

HEAD = ["Number", "Title"]
ROWS = [["1", "A | pipe"], ["2", "Two\nlines"]]


def test_csv_opens_in_excel_with_its_bom(tmp_path: Path) -> None:
    path = tmp_path / "list.csv"
    assert export_rows(path, HEAD, ROWS) == 2
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        assert list(csv.reader(handle)) == [HEAD, *ROWS]


def test_excel_freezes_its_heading_row(tmp_path: Path) -> None:
    from openpyxl import load_workbook

    path = tmp_path / "list.xlsx"
    assert export_rows(path, HEAD, ROWS) == 2
    sheet = load_workbook(path).active
    assert [c.value for c in sheet[1]] == HEAD
    assert sheet.freeze_panes == "A2"
    assert sheet.cell(3, 2).value == "Two\nlines"


def test_markdown_keeps_pipes_and_line_breaks_as_text(tmp_path: Path) -> None:
    text = markdown_table(HEAD, ROWS)
    assert text.splitlines() == [
        "| Number | Title |",
        "| --- | --- |",
        "| 1 | A \\| pipe |",
        "| 2 | Two<br>lines |",
    ]
    path = tmp_path / "list.md"
    export_rows(path, HEAD, ROWS)
    assert path.read_text(encoding="utf-8") == text


def test_hidden_columns_are_named() -> None:
    assert hidden_columns_sentence(["Title"], ["Number", "Title", "State"]) == (
        "Left out: the columns you have hidden (Number, State)."
    )
    assert hidden_columns_sentence(["Title"], ["Title"]) == ""
