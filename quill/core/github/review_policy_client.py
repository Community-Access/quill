"""On-demand repository policy reads for the pull-request review client."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Protocol

from quill.core.github.merge_policy import (
    GitHubMergePolicy,
    GitHubPullQueueState,
    fetch_merge_policy,
)
from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_graphql import ReviewGraphQLError, fetch_pull_queue_state


class _ProviderAccess(Protocol):
    _provider: Any

    def _pull(self, full_name: str, number: int) -> Any: ...


class PullReviewPolicyMixin:
    """Load branch rulesets and queue evidence only when a user asks to check."""

    def fetch_head_sha(self: _ProviderAccess, full_name: str, number: int) -> str:
        """Read the latest PR head so a saved review cannot target stale diff silently."""
        pull = self._pull(full_name, number)
        head = getattr(pull, "head", None)
        sha = str(getattr(head, "sha", "") or "") if head is not None else ""
        if not sha:
            raise GitHubReviewError("GitHub did not return the pull request's current head SHA.")
        return sha

    def fetch_merge_policy_context(
        self: _ProviderAccess,
        full_name: str,
        number: int,
        base_branch: str,
        *,
        expected_head_sha: str,
    ) -> tuple[GitHubMergePolicy, GitHubPullQueueState | None]:
        """Return branch policy and current queue state, preserving partial warnings."""
        policy = fetch_merge_policy(self._provider, full_name, base_branch)
        warnings = list(policy.warnings)
        queue_state: GitHubPullQueueState | None = None
        token = getattr(self._provider, "token", None)
        if token:
            try:
                queue_state = fetch_pull_queue_state(token, full_name, number)
            except ReviewGraphQLError as exc:
                warnings.append(f"Merge-queue status could not be read: {exc}")
        elif policy.active_merge_queue_required:
            warnings.append("Sign in to read whether this pull request is in the merge queue.")
        if queue_state and expected_head_sha and queue_state.head_sha != expected_head_sha:
            warnings.append("The pull request head changed while policy was loading; refresh.")
        if tuple(warnings) != policy.warnings:
            policy = replace(policy, warnings=tuple(warnings))
        return policy, queue_state


__all__ = ["PullReviewPolicyMixin"]
