"""The "What failed" digest: failed jobs, steps, annotations, then clean log tails."""

from __future__ import annotations

from quill.core.github.run_failure_digest import (
    build_failure_digest,
    clean_log_line,
    collect_failure_digest,
    step_tail,
)
from quill.core.github.workflow_models import (
    GitHubWorkflowAnnotation,
    GitHubWorkflowJob,
    GitHubWorkflowStep,
)

LOG = "\n".join([
    "2026-11-07T10:00:00.1000000Z ##[group]Run actions/checkout@v4",
    "2026-11-07T10:00:01.2000000Z checked out",
    "2026-11-07T10:00:02.0000000Z ##[endgroup]",
    "2026-11-07T10:00:05.0000000Z \x1b[31mFAILED\x1b[0m tests/test_a.py::test_one",
    "2026-11-07T10:00:06.0000000Z ##[error]Process completed with exit code 1.",
    "2026-11-07T10:00:07.0000000Z ##[debug]noise",
    "",
])

STEP_OK = GitHubWorkflowStep(
    "Checkout",
    "completed",
    "success",
    1,
    "2026-11-07T10:00:00+00:00",
    "2026-11-07T10:00:02+00:00",
)
STEP_BAD = GitHubWorkflowStep(
    "Run tests",
    "completed",
    "failure",
    2,
    "2026-11-07T10:00:03+00:00",
    "2026-11-07T10:00:07+00:00",
)


def _job(name: str = "build", conclusion: str = "failure", job_id: int = 11) -> GitHubWorkflowJob:
    return GitHubWorkflowJob(
        name=name,
        status="completed",
        conclusion=conclusion,
        id=job_id,
        check_run_id=job_id,
        steps=(STEP_OK, STEP_BAD) if conclusion == "failure" else (STEP_OK,),
    )


def test_clean_line_strips_stamps_colour_and_names_markers() -> None:
    assert clean_log_line("2026-11-07T10:00:05.123Z \x1b[1;31mboom\x1b[0m") == "boom"
    assert clean_log_line("2026-11-07T10:00:05Z ##[error]bad") == "ERROR: bad"
    assert clean_log_line("##[warning]careful") == "WARNING: careful"


def test_step_tail_takes_only_lines_inside_the_step_window() -> None:
    tail, matched = step_tail(LOG, STEP_BAD)
    assert matched is True
    assert tail == [
        "FAILED tests/test_a.py::test_one",
        "ERROR: Process completed with exit code 1.",
    ]


def test_step_tail_falls_back_to_the_end_of_the_job() -> None:
    no_times = GitHubWorkflowStep("Run tests", "completed", "failure", 2)
    tail, matched = step_tail(LOG, no_times, lines=2)
    assert matched is False
    assert tail[-1] == "ERROR: Process completed with exit code 1."


def test_digest_orders_jobs_then_steps_then_annotations_then_logs() -> None:
    from quill.core.github.run_failure_digest import FailedJobEvidence

    note = GitHubWorkflowAnnotation("src/a.py", 12, 12, "failure", "Assertion", "1 != 2")
    text = build_failure_digest(
        "run #4, CI", [FailedJobEvidence(_job(), (note,), "", LOG, "")], total_jobs=3
    )
    lines = text.splitlines()
    assert lines[:2] == ["What failed in run #4, CI", "1 of 3 jobs failed."]
    order = [
        text.index("Job 1 of 1: build (failure)"),
        text.index("Failed steps: step 2, Run tests."),
        text.index("  src/a.py:12: failure: Assertion: 1 != 2"),
        text.index("Last 2 log lines of step 2, Run tests:"),
        text.index("  FAILED tests/test_a.py::test_one"),
    ]
    assert order == sorted(order)
    assert "\x1b" not in text and "2026-11-07T" not in text


def test_digest_says_when_nothing_failed() -> None:
    assert build_failure_digest("run #4", [], total_jobs=2).endswith("No jobs failed in this run.")


class _Provider:
    token = "tok"

    def fetch_workflow_jobs(self, repo: str, run_id: int, **_kw):
        return [_job(), _job("lint", "success", 12), _job("docs", "failure", 13)]

    def fetch_workflow_job_annotations(self, repo: str, check_run_id: int):
        if check_run_id == 13:
            raise RuntimeError("no permission")
        return (), False


def test_collect_keeps_one_jobs_gap_visible_and_skips_passing_jobs() -> None:
    def fetch_log(token, repo, job_id):
        if job_id == 13:
            raise RuntimeError("log expired")
        return LOG

    text = collect_failure_digest(_Provider(), "o/r", 4, "run #4", fetch_log=fetch_log)
    assert "2 of 3 jobs failed." in text
    assert "lint" not in text
    assert "Annotations unavailable: no permission" in text
    assert "Log unavailable: log expired" in text
    assert "FAILED tests/test_a.py::test_one" in text
