"""What the Problems pane shows and says (quill.core.problems.pane), no wx."""

from __future__ import annotations

from quill.core.problems.model import CheckReport, Problem
from quill.core.problems.pane import (
    ALL_SOURCES,
    PaneFilter,
    count_sentence,
    filter_problems,
    pane_row,
    source_choices,
)

PROBLEMS = (
    Problem(1, 2, "error", "Unclosed tag", "HTML"),
    Problem(3, 1, "warning", "Skipped heading level", "Markdown"),
    Problem(5, 4, "info", "Long line", ""),
    Problem(9, 1, "error", "Bad value", "HTML"),
)
REPORT = CheckReport(language="html", problems=PROBLEMS, checked_with=("HTML",))


def test_all_shows_everything_with_report_indices() -> None:
    shown = filter_problems(PROBLEMS, PaneFilter())
    assert [index for index, _p in shown] == [0, 1, 2, 3]


def test_errors_and_warnings_drop_only_info() -> None:
    shown = filter_problems(PROBLEMS, PaneFilter(show="warnings"))
    assert [index for index, _p in shown] == [0, 1, 3]


def test_errors_only_keeps_the_report_index_of_each() -> None:
    shown = filter_problems(PROBLEMS, PaneFilter(show="errors"))
    assert [index for index, _p in shown] == [0, 3]


def test_source_filter_and_an_unnamed_source() -> None:
    assert [i for i, _p in filter_problems(PROBLEMS, PaneFilter(source="HTML"))] == [0, 3]
    assert [i for i, _p in filter_problems(PROBLEMS, PaneFilter(source="Checker"))] == [2]


def test_an_unknown_show_key_shows_everything() -> None:
    assert len(filter_problems(PROBLEMS, PaneFilter(show="nonsense"))) == 4


def test_source_choices_are_first_seen_and_never_empty() -> None:
    assert source_choices(REPORT) == (ALL_SOURCES, "HTML", "Markdown", "Checker")
    assert source_choices(None) == (ALL_SOURCES,)


def test_a_row_reads_severity_place_message_and_source() -> None:
    assert pane_row(PROBLEMS[0]) == "Error, line 1, column 2: Unclosed tag (HTML)"
    assert pane_row(PROBLEMS[2]) == "Info, line 5, column 4: Long line (Checker)"


def test_the_count_sentence_is_short_and_says_what_is_hidden() -> None:
    assert count_sentence(0) == "No problems"
    assert count_sentence(1) == "1 problem"
    assert count_sentence(3) == "3 problems"
    assert count_sentence(3, 3) == "3 problems"
    assert count_sentence(4, 2) == "4 problems, 2 shown"


def test_combined_reports_name_each_document_and_remember_the_origin() -> None:
    from quill.core.problems.pane import combine_reports

    other = CheckReport(
        language="json", problems=(Problem(2, 1, "error", "Bad", "JSON"),), checked_with=("JSON",)
    )
    combined, origins = combine_reports([(0, "page.html", REPORT), (3, "data.json", other)])
    assert len(combined.problems) == len(PROBLEMS) + 1
    assert combined.problems[-1].document == "data.json"
    assert origins[-1] == (3, other.problems[0])
    assert set(combined.checked_with) == {"HTML", "JSON"}
    assert pane_row(combined.problems[-1]) == "data.json: Error, line 2, column 1: Bad (JSON)"
    empty, none = combine_reports([])
    assert empty.problems == () and none == []
