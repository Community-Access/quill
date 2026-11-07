"""The Problem shape, the sentences, and which checkers a document gets."""

from __future__ import annotations

from pathlib import Path

from quill.core.problems import (
    CheckReport,
    Problem,
    check_document,
    describe_problem,
    language_key,
    offset_for,
    problem_after,
    summarize,
)
from quill.core.problems.model import list_row, normalize_severity, sort_problems

TEXT = "one\ntwo\nthree\n"
PROBLEMS = (
    Problem(1, 2, "error", "first"),
    Problem(2, 1, "warning", "second"),
    Problem(3, 3, "info", "third"),
)


def test_offset_for_clamps_to_the_line_and_the_text() -> None:
    assert offset_for(TEXT, 2, 1) == 4
    assert offset_for(TEXT, 2, 99) == 7
    assert offset_for(TEXT, 99, 1) == len(TEXT)
    assert offset_for(TEXT, 0, 0) == 0


def test_problem_after_walks_and_wraps() -> None:
    assert problem_after(PROBLEMS, TEXT, 0, forward=True) == 0
    assert problem_after(PROBLEMS, TEXT, 1, forward=True) == 1
    assert problem_after(PROBLEMS, TEXT, len(TEXT), forward=True) == 0
    assert problem_after(PROBLEMS, TEXT, 0, forward=False) == 2
    assert problem_after(PROBLEMS, TEXT, 5, forward=False) == 1
    assert problem_after((), TEXT, 0, forward=True) is None


def test_sentences() -> None:
    assert describe_problem(PROBLEMS[0], 0, 3) == "Problem 1 of 3, line 1, column 2, error: first"
    assert list_row(Problem(4, 5, "warning", "msg", "ruff")) == (
        "Line 4, column 5, warning: msg (ruff)"
    )
    report = CheckReport("JSON", PROBLEMS, ("JSON",))
    assert summarize(report) == "3 problems: 1 error, 1 warning, 1 info."
    assert summarize(CheckReport("JSON", (), ("JSON",))) == "No problems found."
    assert summarize(CheckReport("Go", (), (), ("No checker installed for Go",))) == (
        "No checker installed for Go."
    )


def test_severity_words_fold_into_three() -> None:
    assert normalize_severity("Fatal Error") == "error"
    assert normalize_severity("warn") == "warning"
    assert normalize_severity("note") == "info"
    assert normalize_severity("style") == "info"
    assert normalize_severity(None) == "error"


def test_sort_problems_orders_and_drops_duplicates() -> None:
    doubled = [PROBLEMS[2], PROBLEMS[0], PROBLEMS[0]]
    assert sort_problems(doubled) == (PROBLEMS[0], PROBLEMS[2])


def test_language_key_from_profile_and_file_name() -> None:
    assert language_key("Python", Path("a.py")) == "python"
    assert language_key("JSON", Path("a.jsonc")) == "jsonc"
    assert language_key("JSON", Path(".vscode/settings.json")) == "jsonc"
    assert language_key("Plain text", None) == "plain"
    assert language_key(None, None) == "plain"


def test_check_document_built_in_only_never_starts_a_process() -> None:
    def no_tool(_name: str) -> str | None:
        raise AssertionError("looked for an outside tool")

    report = check_document('{"a":', language="json", outside=False, which=no_tool)
    assert report.checked_with == ("JSON",)
    assert len(report.problems) == 1


def test_check_document_says_when_nothing_can_check() -> None:
    report = check_document("x", language="plain", which=lambda _n: None)
    assert summarize(report) == "No checker for Plain."
    go = check_document("package main", language="go", which=lambda _n: None)
    assert summarize(go) == "No checker installed for Go."


def test_xhtml_is_checked_as_xml_and_as_html() -> None:
    report = check_document(
        "<html><body><img src='a'/></body></html>",
        language="html",
        path=Path("page.xhtml"),
        outside=False,
    )
    assert report.checked_with == ("XML", "HTML")
    assert [p.message for p in report.problems] == ["Image has no alt text"]
