"""Bounded mapping for optional GitHub Actions check-run annotations."""

from __future__ import annotations

from itertools import islice
from typing import Any

from quill.core.github.workflow_models import GitHubWorkflowAnnotation

DEFAULT_ANNOTATION_LIMIT = 100
_TEXT_LIMIT = 2000


def _text(value: object, *, limit: int = _TEXT_LIMIT) -> str:
    value = str(value or "")
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def list_annotations(
    repo: Any, check_run_id: int, *, limit: int = DEFAULT_ANNOTATION_LIMIT
) -> tuple[tuple[GitHubWorkflowAnnotation, ...], bool]:
    """Return up to *limit* annotations and whether more were available."""
    if check_run_id <= 0:
        raise ValueError("A positive check-run ID is required.")
    if limit < 1 or limit > DEFAULT_ANNOTATION_LIMIT:
        raise ValueError(f"Choose an annotation limit from 1 to {DEFAULT_ANNOTATION_LIMIT}.")
    check_run = repo.get_check_run(check_run_id)
    rows = list(islice(check_run.get_annotations(), limit + 1))
    truncated = len(rows) > limit
    return (
        tuple(
            GitHubWorkflowAnnotation(
                path=_text(getattr(row, "path", ""), limit=512),
                start_line=max(0, int(getattr(row, "start_line", 0) or 0)),
                end_line=max(0, int(getattr(row, "end_line", 0) or 0)),
                level=_text(getattr(row, "annotation_level", ""), limit=32),
                title=_text(getattr(row, "title", ""), limit=256),
                message=_text(getattr(row, "message", "")),
                details=_text(getattr(row, "raw_details", "")),
            )
            for row in rows[:limit]
        ),
        truncated,
    )
