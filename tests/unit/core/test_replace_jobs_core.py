"""Saved replace jobs: what a job does, and how it is stored (quill/core/replace_jobs.py)."""

from __future__ import annotations

import json

import pytest

from quill.core.replace_jobs import (
    SAMPLE_JOBS,
    ReplaceJob,
    ReplaceJobError,
    ReplaceStep,
    describe_run,
    describe_step,
    load_replace_jobs,
    run_job,
    save_replace_jobs,
    step_error,
    unique_job_name,
)


def test_steps_run_in_order_each_on_the_result_of_the_last() -> None:
    job = ReplaceJob("chain", [ReplaceStep("cat", "dog"), ReplaceStep("dog", "bird")])

    text, counts = run_job("cat and dog", job)

    assert text == "bird and bird"
    assert counts == [1, 2]


def test_a_plain_step_replaces_exactly_what_was_typed() -> None:
    job = ReplaceJob("path", [ReplaceStep("old", r"C:\new\1")])

    text, _counts = run_job("old", job)

    assert text == r"C:\new\1"


def test_a_regular_expression_step_uses_groups_and_line_anchors() -> None:
    job = ReplaceJob("swap", [ReplaceStep(r"^(\w+) (\w+)$", r"\2 \1", regex=True)])

    text, counts = run_job("one two\nthree four", job)

    assert text == "two one\nfour three"
    assert counts == [2]


def test_match_case_is_honoured_and_off_by_default() -> None:
    loose = ReplaceJob("loose", [ReplaceStep("word", "X")])
    strict = ReplaceJob("strict", [ReplaceStep("word", "X", match_case=True)])

    assert run_job("Word word", loose)[0] == "X X"
    assert run_job("Word word", strict)[0] == "Word X"


def test_a_bad_pattern_stops_the_job_before_any_step_runs() -> None:
    job = ReplaceJob("broken", [ReplaceStep("a", "b"), ReplaceStep("(", "", regex=True)])

    with pytest.raises(ReplaceJobError, match="Step 2 of broken"):
        run_job("a", job)


def test_a_missing_group_reference_is_reported_not_raised_raw() -> None:
    job = ReplaceJob("groups", [ReplaceStep("a", r"\3", regex=True)])

    with pytest.raises(ReplaceJobError, match="Step 1 of groups"):
        run_job("a", job)


def test_step_error_names_what_is_wrong() -> None:
    assert step_error(ReplaceStep("")) == "Find what is empty."
    assert "not valid" in step_error(ReplaceStep("[", regex=True))
    assert step_error(ReplaceStep("[")) == ""  # plain text: a bracket is a bracket


def test_the_samples_work_as_shipped() -> None:
    by_name = {job.name: job for job in SAMPLE_JOBS}

    assert run_job("a  b \nc", by_name["Tidy spaces"])[0] == "a b\nc"
    assert run_job("\u201chi\u201d", by_name["Straighten quote marks"])[0] == '"hi"'
    assert run_job("a\n\n\n\nb", by_name["Close up blank lines"])[0] == "a\n\nb"


def test_no_file_yet_means_the_samples(tmp_path) -> None:
    jobs = load_replace_jobs(tmp_path / "replace_jobs.json")

    assert [job.name for job in jobs] == [job.name for job in SAMPLE_JOBS]


def test_saving_and_loading_round_trip(tmp_path) -> None:
    path = tmp_path / "replace_jobs.json"
    jobs = [ReplaceJob("mine", [ReplaceStep("x", "y", regex=True, match_case=True)])]

    save_replace_jobs(path, jobs)

    assert load_replace_jobs(path) == jobs
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == 1


def test_an_empty_saved_list_stays_empty(tmp_path) -> None:
    """Deleting every job is a choice, not a reason to bring the samples back."""
    path = tmp_path / "replace_jobs.json"
    save_replace_jobs(path, [])

    assert load_replace_jobs(path) == []


def test_damaged_entries_are_skipped_not_fatal(tmp_path) -> None:
    path = tmp_path / "replace_jobs.json"
    path.write_text(
        json.dumps({"jobs": [{"name": ""}, "junk", {"name": "ok", "steps": [{"find": "a"}, 3]}]}),
        encoding="utf-8",
    )

    assert load_replace_jobs(path) == [ReplaceJob("ok", [ReplaceStep("a")])]


def test_unique_names_ignore_case_and_the_job_being_renamed() -> None:
    jobs = [ReplaceJob("Tidy"), ReplaceJob("Other")]

    assert not unique_job_name("tidy", jobs)
    assert unique_job_name("tidy", jobs, ignore=0)
    assert not unique_job_name("  ", jobs)


def test_the_sentences_a_listener_hears() -> None:
    job = ReplaceJob("Tidy", [ReplaceStep("a"), ReplaceStep("b")])

    assert describe_run(job, [3, 0], in_selection=True) == (
        "Tidy: 3 replacements in the selection. Step 2 found nothing"
    )
    assert describe_run(job, [0, 0], in_selection=False) == "Tidy: nothing to replace"
    assert describe_step(ReplaceStep(" ", "", regex=True)) == (
        "Find space, replace with nothing (regular expression)"
    )
    assert describe_step(ReplaceStep("\t", " ")) == "Find tab, replace with space"
