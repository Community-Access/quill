"""Short rows for braille (GitHub PRD 22.4 and F1, GH-R-114).

The option makes a list one column whose text is the row shaped for a
braille display: the number and title first, no column names, short words.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

from quill.core.github.workbench_help_text import PREF_HELP
from quill.core.github.workbench_prefs import WorkbenchPrefs
from quill.core.workbench.braille_rows import (
    ABBREVIATIONS,
    BRAILLE_COLUMN,
    abbreviations_help,
    braille_row,
)

TODAY = dt.date(2026, 11, 19)
ISSUE_COLUMNS = ("number", "type", "state", "title", "author", "updated", "labels", "comments")


def test_the_number_and_title_come_first_with_no_column_names() -> None:
    cells = ["42", "pull request", "closed", "Crash on start", "ada", "2026-11-09", "bug", "3"]
    row = braille_row(cells, ISSUE_COLUMNS, today=TODAY)
    assert row == "#42 Crash on start; PR; cl; ada; 9 Nov; bug; 3c"
    for name in ISSUE_COLUMNS:
        assert f"{name}:" not in row.lower()


def test_empty_and_zero_cells_say_nothing_and_old_years_are_kept() -> None:
    cells = ["7", "issue", "open", "Docs", "", "2024-03-01", "", "0"]
    assert braille_row(cells, ISSUE_COLUMNS, today=TODAY) == "#7 Docs; iss; open; 1 Mar 24"


def test_a_commit_and_a_run_lead_with_what_names_them() -> None:
    commit = braille_row(
        ["abc1234", "ada", "2026-11-18", "Fix the thing"],
        ("short_sha", "author", "date", "message"),
        today=TODAY,
    )
    assert commit == "abc1234 Fix the thing; ada; 18 Nov"
    run = braille_row(
        ["ci", "completed", "failure", "main", "push", "12"],
        ("name", "status", "conclusion", "branch", "event", "run_number"),
    )
    assert run == "ci; done; fail; main; push; run 12"


def test_a_title_is_never_cut_short() -> None:
    title = "A very long title that is much longer than one forty cell braille display line"
    assert title in braille_row(["1", "", "", title], ISSUE_COLUMNS[:4], today=TODAY)


def test_the_option_is_off_by_default_and_f1_lists_the_abbreviations() -> None:
    assert WorkbenchPrefs().braille_rows is False
    assert PREF_HELP["braille_rows"][0] == "Lists"
    words = abbreviations_help()
    for long, short in ABBREVIATIONS.items():
        assert f"{short} for {long}" in words


def test_the_workbench_list_becomes_one_braille_column(monkeypatch) -> None:
    """The GitHub provider shows one column when the option is on, and the real ones when off."""
    from quill.ui.github_workbench_view import GitHubWorkbenchViewMixin

    class GitHubItem(SimpleNamespace):
        pass

    item = GitHubItem()
    monkeypatch.setattr(
        "quill.ui.github_items_view.row_cells",
        lambda _row, columns, full: [
            {"number": "42", "title": "Crash"}.get(c, "") for c in columns
        ],
    )
    view = GitHubWorkbenchViewMixin()
    for on, expected in ((True, (BRAILLE_COLUMN,)), (False, ("number", "title"))):
        monkeypatch.setattr(
            "quill.core.github.workbench_prefs.load_prefs",
            lambda on=on: WorkbenchPrefs(braille_rows=on),
        )
        columns = view.shaped_columns(("number", "title"))
        assert columns == expected
    view.shaped_columns(("number", "title"))
    assert view.shaped_cells(item, (BRAILLE_COLUMN,)) == ["#42 Crash"]
    assert view.shaped_cells(item, ("number", "title")) == ["42", "Crash"]
    # One column is already short: it stays as it is.
    monkeypatch.setattr(
        "quill.core.github.workbench_prefs.load_prefs", lambda: WorkbenchPrefs(braille_rows=True)
    )
    assert view.shaped_columns(("result",)) == ("result",)
