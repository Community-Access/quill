"""Shared coded error for pull-request review reads and actions."""

from __future__ import annotations

from quill.core.error_codes import CodedError


class GitHubReviewError(CodedError):
    """A PR review fetch or action failed (network, auth, API, or refusal)."""

    code = "QUILL-GITHUB-REVIEW-ERROR"


__all__ = ["GitHubReviewError"]
