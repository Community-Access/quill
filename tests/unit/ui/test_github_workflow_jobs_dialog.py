"""Workflow job details keep step, annotation, and revision evidence readable."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.workflow_models import (
    GitHubWorkflowAnnotation,
    GitHubWorkflowJob,
    GitHubWorkflowStep,
)
from quill.ui.github_workflow_jobs_dialog import WorkflowJobsDialog


def _job() -> GitHubWorkflowJob:
    return GitHubWorkflowJob(
        name="build",
        status="completed",
        conclusion="failure",
        id=7,
        head_sha="abc123",
        check_run_id=7,
        steps=(
            GitHubWorkflowStep(
                name="Run tests",
                status="completed",
                conclusion="failure",
                number=3,
            ),
        ),
    )


def test_job_details_name_failing_step_and_current_run_provenance() -> None:
    dialog = SimpleNamespace(
        _run_label="#42 CI",
        _run_attempt=2,
        _selected_attempt=2,
        _head_sha="abc123",
        _run_url="https://github.com/owner/repo/actions/runs/42",
    )

    detail = WorkflowJobsDialog._job_details(dialog, _job())

    assert "Run: #42 CI" in detail
    assert "Run attempt: 2" in detail
    assert "Head SHA: abc123" in detail
    assert "3. Run tests: failure" in detail


def test_render_detail_preserves_annotations_and_log_together() -> None:
    class _Detail:
        value = ""

        def SetValue(self, value: str) -> None:
            self.value = value

    detail = _Detail()
    annotation = GitHubWorkflowAnnotation(
        path="src/app.py",
        start_line=10,
        end_line=11,
        level="warning",
        title="Review marker",
        message="Check this branch.",
        details="The changed line needs a null guard.",
    )
    dialog = SimpleNamespace(
        _job_details=lambda _job: "Run: #42 CI",
        _annotations=(annotation,),
        _annotations_truncated=True,
        _loaded_log="failed test output",
        _detail=detail,
    )

    WorkflowJobsDialog._render_detail(dialog, _job())

    assert "src/app.py:10-11 [warning] Review marker: Check this branch." in detail.value
    assert "Showing the first 100 annotations" in detail.value
    assert "Details: The changed line needs a null guard." in detail.value
    assert "failed test output" in detail.value


def test_attempt_choice_loads_the_selected_prior_attempt() -> None:
    reloads: list[str] = []
    dialog = SimpleNamespace(
        _attempt_choice=SimpleNamespace(GetSelection=lambda: 1),
        _attempt_numbers=[3, 2, 1],
        _selected_attempt=3,
        _reload=lambda: reloads.append("reload"),
    )

    WorkflowJobsDialog._on_attempt_changed(dialog, None)

    assert dialog._selected_attempt == 2
    assert reloads == ["reload"]
