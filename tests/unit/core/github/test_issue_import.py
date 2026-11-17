"""Issues in, from a spreadsheet or from lines (GitHub PRD 22.7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.github import issue_import as ii
from quill.core.workbench.spreadsheet import read_spreadsheet


def test_columns_are_matched_by_name_and_the_rest_named() -> None:
    mapping, ignored = ii.import_mapping(["Summary", "Description", "Tags", "Owner", "Due"])
    assert mapping == {
        "summary": "title",
        "description": "body",
        "tags": "labels",
        "owner": "assignees",
    }
    assert ignored == ["due"]
    lines = ii.mapping_lines(mapping, ignored)
    assert lines[0] == "Column summary fills title."
    assert lines[-1] == "Left out, matching no field: due."


def test_a_sheet_without_a_title_column_says_so() -> None:
    mapping, ignored = ii.import_mapping(["Body"])
    assert "No column is the title" in ii.mapping_lines(mapping, ignored)[-1]


def test_the_plan_says_each_row_and_why_one_is_skipped() -> None:
    rows = [
        {"Title": "Crash on save", "Labels": "bug, p1", "Milestone": "1.0"},
        {"Title": "", "Body": "orphan"},
        {"Title": "Later", "Milestone": "Someday"},
        {"Title": "x" * 300},
    ]
    plan = ii.import_plan(rows, milestones=["1.0"])
    assert [row.sentence for row in plan] == [
        "Row 2: Crash on save (labels bug, p1; milestone 1.0)",
        "Row 3: skipped, it has no title.",
        "Row 4: skipped, this repository has no milestone called Someday.",
        "Row 5: skipped, its title is longer than GitHub's 256 characters.",
    ]


def test_the_payload_is_what_github_takes() -> None:
    row = ii.import_plan(
        [
            {
                "Title": "Crash",
                "Body": "Steps",
                "Labels": "bug; p1",
                "Assignees": "@ada, grace",
                "Milestone": "1.0",
                "Type": "Bug",
            }
        ],
        milestones=["1.0"],
    )[0]
    assert ii.issue_payload(row, {"1.0": 7}) == {
        "title": "Crash",
        "body": "Steps",
        "labels": ["bug", "p1"],
        "assignees": ["ada", "grace"],
        "milestone": 7,
        "type": "Bug",
    }
    bare = ii.import_plan([{"Title": "Only"}])[0]
    assert ii.issue_payload(bare) == {"title": "Only"}


def test_lines_lose_their_markers_and_blanks() -> None:
    text = "- [ ] Write the guide\n\n* Fix the parser\r\n1. Ship it\n2) Celebrate\n   plain line"
    assert ii.titles_from_lines(text) == [
        "Write the guide",
        "Fix the parser",
        "Ship it",
        "Celebrate",
        "plain line",
    ]


def test_the_shared_reader_reads_csv_and_excel(tmp_path: Path) -> None:
    Workbook = pytest.importorskip("openpyxl").Workbook

    csv_path = tmp_path / "issues.csv"
    csv_path.write_text("﻿Title,Labels\nOne,bug\n,\nTwo,\n", encoding="utf-8")
    assert read_spreadsheet(csv_path) == [
        {"title": "One", "labels": "bug"},
        {"title": "Two", "labels": ""},
    ]
    book = Workbook()
    book.active.append(["Title", "Body"])
    book.active.append(["Three", None])
    xlsx = tmp_path / "issues.xlsx"
    book.save(str(xlsx))
    assert read_spreadsheet(xlsx) == [{"title": "Three", "body": ""}]
