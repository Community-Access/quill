"""Map a bounded workflow-job listing into the shared GitHub models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.workflow_models import GitHubWorkflowJob, GitHubWorkflowStep


def list_jobs(
    repo: Any,
    run_id: int,
    *,
    attempt_number: int | None,
    limit: int,
    take: Callable[[Any, int], list[Any]],
    safe_str: Callable[[Any], str],
    iso: Callable[[Any], str],
) -> list[GitHubWorkflowJob]:
    """Return one run's bounded jobs and their available step summaries."""
    run = repo.get_workflow_run(run_id)
    if attempt_number is not None:
        if attempt_number <= 0:
            raise ValueError("Workflow attempt numbers must be positive.")
        run = run.get_attempt(attempt_number)
    rows = take(run.jobs(), limit)
    return [
        GitHubWorkflowJob(
            name=safe_str(getattr(row, "name", "")),
            status=safe_str(getattr(row, "status", "")),
            conclusion=safe_str(getattr(row, "conclusion", "")),
            started_at=iso(getattr(row, "started_at", None)),
            completed_at=iso(getattr(row, "completed_at", None)),
            url=safe_str(getattr(row, "html_url", "")),
            id=int(getattr(row, "id", 0) or 0),
            steps=tuple(
                GitHubWorkflowStep(
                    name=safe_str(getattr(step, "name", "")),
                    status=safe_str(getattr(step, "status", "")),
                    conclusion=safe_str(getattr(step, "conclusion", "")),
                    number=int(getattr(step, "number", 0) or 0),
                    started_at=iso(getattr(step, "started_at", None)),
                    completed_at=iso(getattr(step, "completed_at", None)),
                )
                for step in (getattr(row, "steps", ()) or ())
            ),
            head_sha=safe_str(getattr(row, "head_sha", "")),
            check_run_id=int(getattr(row, "id", 0) or 0),
        )
        for row in rows
    ]
