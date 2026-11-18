"""Following a running Actions job, a step at a time (GitHub PRD 22.12)."""

from __future__ import annotations

from quill.core.github.job_follow import finished, progress_sentence, step_changes
from quill.core.github.workflow_models import GitHubWorkflowJob, GitHubWorkflowStep


def _job(status: str, steps: list[tuple[str, str]], conclusion: str = "") -> GitHubWorkflowJob:
    return GitHubWorkflowJob(
        name="test",
        status=status,
        conclusion=conclusion,
        id=5,
        steps=tuple(
            GitHubWorkflowStep(name=f"step {i}", status=s, conclusion=c, number=i)
            for i, (s, c) in enumerate(steps, start=1)
        ),
    )


def test_a_step_starting_and_finishing_is_said_once_each() -> None:
    first = _job("in_progress", [("completed", "success"), ("in_progress", ""), ("queued", "")])
    later = _job(
        "in_progress", [("completed", "success"), ("completed", "failure"), ("in_progress", "")]
    )
    assert step_changes(first, first) == ()
    assert step_changes(first, later) == (
        "Step 2, step 2, failed.",
        "Step 3, step 3, started.",
    )


def test_the_end_of_the_job_is_said_with_where_the_log_is() -> None:
    running = _job("in_progress", [("in_progress", "")])
    done = _job("completed", [("completed", "success")], conclusion="success")
    assert step_changes(running, done)[-1] == "test succeeded. Load Log reads its whole log."
    assert finished(done) and not finished(running)


def test_how_far_along() -> None:
    assert progress_sentence(_job("queued", [("queued", "")])) == (
        "test is queued; no step has started."
    )
    middle = _job("in_progress", [("completed", "failure"), ("in_progress", ""), ("queued", "")])
    assert progress_sentence(middle) == (
        "test: On step 2 of 3, step 2; 1 done; failed so far: step 1."
    )
    done = _job("completed", [("completed", "success")] * 2, conclusion="failure")
    assert progress_sentence(done) == "test failed, all 2 steps done."
