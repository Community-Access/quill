"""Plain workflow run and job records shared by GitHub workbench views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubWorkflowRun:
    """A GitHub Actions workflow run."""

    name: str
    status: str
    conclusion: str = ""
    branch: str = ""
    event: str = ""
    created_at: str = ""
    url: str = ""
    run_number: int = 0
    id: int = 0
    run_attempt: int = 0
    head_sha: str = ""


def map_workflow_run(row: Any) -> GitHubWorkflowRun:
    """Map a PyGithub workflow-run row for both list and direct-reference reads."""
    created_at = getattr(row, "created_at", None)
    isoformat = getattr(created_at, "isoformat", None)
    if callable(isoformat):
        try:
            created_at = isoformat()
        except Exception:  # noqa: BLE001 - keep a readable row on malformed dates
            created_at = ""
    try:
        run_id = int(getattr(row, "id", 0) or 0)
    except (TypeError, ValueError):
        run_id = 0
    try:
        run_number = int(getattr(row, "run_number", 0) or 0)
    except (TypeError, ValueError):
        run_number = 0
    try:
        run_attempt = int(getattr(row, "run_attempt", 0) or 0)
    except (TypeError, ValueError):
        run_attempt = 0
    return GitHubWorkflowRun(
        name=str(getattr(row, "name", "") or ""),
        status=str(getattr(row, "status", "") or ""),
        conclusion=str(getattr(row, "conclusion", "") or ""),
        branch=str(getattr(row, "head_branch", "") or ""),
        event=str(getattr(row, "event", "") or ""),
        created_at=str(created_at or ""),
        url=str(getattr(row, "html_url", "") or ""),
        run_number=run_number,
        id=run_id,
        run_attempt=run_attempt,
        head_sha=str(getattr(row, "head_sha", "") or ""),
    )


@dataclass(frozen=True, slots=True)
class GitHubWorkflowStep:
    """One Actions step, used to show which step failed before opening a log."""

    name: str
    status: str
    conclusion: str = ""
    number: int = 0
    started_at: str = ""
    completed_at: str = ""


@dataclass(frozen=True, slots=True)
class GitHubWorkflowAnnotation:
    """One check-run annotation, kept as plain text for the workbench."""

    path: str
    start_line: int
    end_line: int
    level: str
    title: str
    message: str
    details: str = ""


@dataclass(frozen=True, slots=True)
class GitHubWorkflowJob:
    """One job's status and identifier, used for the separate text-log request."""

    name: str
    status: str
    conclusion: str = ""
    started_at: str = ""
    completed_at: str = ""
    url: str = ""
    id: int = 0
    steps: tuple[GitHubWorkflowStep, ...] = ()
    head_sha: str = ""
    check_run_id: int = 0
