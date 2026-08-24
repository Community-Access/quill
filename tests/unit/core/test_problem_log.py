"""11.5: a failure that was spoken once still exists an hour later.

Announcements are transient by design. The one place this family was not
screen-reader-first was that a spoken failure missed was gone for good; this
log is where it goes instead.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import problem_log


def test_a_recorded_problem_comes_back_newest_first(tmp_path: Path) -> None:
    problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "The Daily", "404 Not Found")
    problem_log.record_problem(
        tmp_path, problem_log.KIND_DOWNLOAD, "Episode 412", "connection reset"
    )
    rows = problem_log.load_problems(tmp_path)
    assert [r.subject for r in rows] == ["Episode 412", "The Daily"]
    assert rows[0].kind == problem_log.KIND_DOWNLOAD


def test_the_same_failure_still_happening_keeps_one_row(tmp_path: Path) -> None:
    """A feed checked every fifteen minutes must not fill the window itself."""
    for _ in range(6):
        problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "The Daily", "404 Not Found")
    assert len(problem_log.load_problems(tmp_path)) == 1


def test_a_different_reason_is_a_different_fact(tmp_path: Path) -> None:
    problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "The Daily", "404 Not Found")
    problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "The Daily", "timed out")
    assert len(problem_log.load_problems(tmp_path)) == 2


def test_the_log_is_bounded(tmp_path: Path) -> None:
    for index in range(problem_log.MAX_PROBLEMS + 25):
        problem_log.record_problem(tmp_path, problem_log.KIND_FEED, f"Show {index}", "failed")
    rows = problem_log.load_problems(tmp_path)
    assert len(rows) == problem_log.MAX_PROBLEMS
    assert rows[0].subject == f"Show {problem_log.MAX_PROBLEMS + 24}", "newest survives"


def test_a_row_reads_as_one_sentence_in_the_order_you_need_it(tmp_path: Path) -> None:
    problem = problem_log.Problem(
        kind=problem_log.KIND_STREAM,
        subject="WQXR",
        reason="dropped and could not be reconnected after 3 attempts",
        when="2026-08-24T12:03:00+00:00",
    )
    label = problem.row_label()
    assert label.startswith("Stream, WQXR, dropped and could not be reconnected")
    assert label.count(",") >= 3, "kind, subject, reason, time"


def test_a_row_with_an_unreadable_time_still_reads(tmp_path: Path) -> None:
    problem = problem_log.Problem(kind="feed", subject="X", reason="broke", when="not a time")
    assert problem.when_display() == ""
    assert problem.row_label() == "Feed, X, broke"


def test_clearing_says_how_many_went(tmp_path: Path) -> None:
    for index in range(4):
        problem_log.record_problem(tmp_path, problem_log.KIND_FEED, f"S{index}", "failed")
    assert problem_log.clear_problems(tmp_path) == 4
    assert problem_log.load_problems(tmp_path) == []


def test_a_missing_or_corrupt_file_is_an_empty_log_not_a_crash(tmp_path: Path) -> None:
    assert problem_log.load_problems(tmp_path) == []
    problem_log.store_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert problem_log.load_problems(tmp_path) == []


def test_rows_without_a_subject_or_a_reason_are_dropped_on_read(tmp_path: Path) -> None:
    problem_log.save_problems(tmp_path, [])
    problem_log.store_path(tmp_path).write_text(
        '{"version": 1, "problems": [{"kind": "feed"}, '
        '{"kind": "feed", "subject": "X", "reason": "y"}]}',
        encoding="utf-8",
    )
    rows = problem_log.load_problems(tmp_path)
    assert [r.subject for r in rows] == ["X"]


def test_the_summary_counts_by_kind(tmp_path: Path) -> None:
    problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "A", "x")
    problem_log.record_problem(tmp_path, problem_log.KIND_FEED, "B", "y")
    problem_log.record_problem(tmp_path, problem_log.KIND_STREAM, "C", "z")
    summary = problem_log.summary(problem_log.load_problems(tmp_path))
    assert summary == "3 recent problems: 2 feed, 1 stream."


def test_an_empty_log_says_so_rather_than_announcing_a_zero(tmp_path: Path) -> None:
    assert problem_log.summary([]).startswith("No recent problems.")
    assert problem_log.report_text([]) == "No recent problems."


def test_a_compound_target_round_trips(tmp_path: Path) -> None:
    problem_log.record_problem(
        tmp_path,
        problem_log.KIND_DOWNLOAD,
        "Episode 1",
        "failed",
        target="show-7" + problem_log.TARGET_SEP + "guid-3",
    )
    row = problem_log.load_problems(tmp_path)[0]
    show_id, _sep, guid = row.target.partition(problem_log.TARGET_SEP)
    assert (show_id, guid) == ("show-7", "guid-3")
