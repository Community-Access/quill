"""Following a running Actions job, a step at a time (GitHub PRD 22.12).

GitHub streams a running job's log only to its own web page; the REST log
arrives when the job ends. What the API does give while it runs is each
step's status, so Follow This Job polls the job and says what changed: a step
starting, a step finishing and how, and the job ending. :func:`progress_sentence`
is the answer to "how far along is it?" at any moment.

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.workflow_models import GitHubWorkflowJob, GitHubWorkflowStep

__all__ = ["FOLLOW_SECONDS", "finished", "progress_sentence", "step_changes"]

#: How often a followed job is read again. GitHub's own page updates about as often.
FOLLOW_SECONDS = 10

_OUTCOMES = {
    "success": "succeeded",
    "failure": "failed",
    "cancelled": "was cancelled",
    "skipped": "was skipped",
    "timed_out": "timed out",
    "neutral": "finished",
    "action_required": "needs someone to act",
}


def _outcome(conclusion: str) -> str:
    return _OUTCOMES.get(conclusion.casefold(), conclusion.casefold() or "finished")


def finished(job: GitHubWorkflowJob) -> bool:
    return job.status.casefold() == "completed"


def _done(step: GitHubWorkflowStep) -> bool:
    return step.status.casefold() == "completed"


def _running(step: GitHubWorkflowStep) -> bool:
    return step.status.casefold() == "in_progress"


def step_changes(before: GitHubWorkflowJob | None, after: GitHubWorkflowJob) -> tuple[str, ...]:
    """What changed between two reads of one job, one sentence per change, in order."""
    was = {step.number: step for step in (before.steps if before is not None else ())}
    said: list[str] = []
    for step in after.steps:
        old = was.get(step.number)
        name = f"Step {step.number}, {step.name},"
        if _done(step) and (old is None or not _done(old)):
            said.append(f"{name} {_outcome(step.conclusion)}.")
        elif _running(step) and (old is None or not _running(old)):
            said.append(f"{name} started.")
    if finished(after) and (before is None or not finished(before)):
        said.append(f"{after.name} {_outcome(after.conclusion)}. Load Log reads its whole log.")
    return tuple(said)


def progress_sentence(job: GitHubWorkflowJob) -> str:
    """How far along *job* is: the step running, and how many are done of how many."""
    total = len(job.steps)
    done = sum(1 for step in job.steps if _done(step))
    if finished(job):
        return f"{job.name} {_outcome(job.conclusion)}, all {total} steps done."
    if job.status.casefold() in ("queued", "waiting", "pending", "requested"):
        return f"{job.name} is {job.status.casefold()}; no step has started."
    running = next((step for step in job.steps if _running(step)), None)
    where = (
        f"On step {running.number} of {total}, {running.name}"
        if running is not None
        else f"{done} of {total} steps done"
    )
    failed = [step.name for step in job.steps if step.conclusion.casefold() == "failure"]
    tail = f"; failed so far: {', '.join(failed)}" if failed else ""
    return f"{job.name}: {where}; {done} done{tail}."
