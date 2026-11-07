"""Conservative pull-request status summary model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.github.merge_policy import GitHubMergePolicy, GitHubPullQueueState

if TYPE_CHECKING:
    from quill.core.github.pr_review import GitHubCheckRun, GitHubReview


@dataclass(frozen=True, slots=True)
class GitHubPullReviewState:
    """Everything the review header bar shows, in one fetch."""

    number: int
    title: str
    state: str
    draft: bool
    merged: bool
    mergeable: bool | None
    mergeable_state: str
    base_ref: str
    head_ref: str
    head_sha: str
    author: str = ""
    url: str = ""
    requested_reviewers: tuple[str, ...] = ()
    reviews: tuple[GitHubReview, ...] = ()
    checks: tuple[GitHubCheckRun, ...] = ()
    thread_count: int = 0
    outdated_thread_count: int = 0
    unresolved_thread_count: int = 0
    reviews_complete: bool = True
    checks_complete: bool = True
    threads_complete: bool = True
    data_warnings: tuple[str, ...] = ()
    merge_policy: GitHubMergePolicy | None = None
    merge_queue_state: GitHubPullQueueState | None = None

    @property
    def review_decision(self) -> str:
        """The latest standing review per reviewer, folded to one phrase."""
        if not self.reviews_complete:
            return "unknown (review data incomplete)"
        latest: dict[str, str] = {}
        for review in self.reviews:
            if review.state in ("APPROVED", "CHANGES_REQUESTED"):
                latest[review.reviewer] = review.state
            elif review.state == "DISMISSED":
                latest.pop(review.reviewer, None)
        approvals = sum(1 for state in latest.values() if state == "APPROVED")
        blocks = sum(1 for state in latest.values() if state == "CHANGES_REQUESTED")
        if blocks:
            return f"changes requested by {blocks}"
        if approvals:
            return f"approved by {approvals}"
        return "review pending"

    @property
    def approval_count(self) -> int | None:
        """Count the latest standing approvals when the review list is complete."""
        if not self.reviews_complete:
            return None
        latest: dict[str, str] = {}
        for review in self.reviews:
            if review.state in ("APPROVED", "CHANGES_REQUESTED"):
                latest[review.reviewer] = review.state
            elif review.state == "DISMISSED":
                latest.pop(review.reviewer, None)
        return sum(state == "APPROVED" for state in latest.values())

    @property
    def checks_summary(self) -> str:
        """Count successful, failing, running, and other observed check runs."""
        if not self.checks:
            return "no checks" if self.checks_complete else "check results incomplete"
        passed = sum(1 for check in self.checks if check.conclusion == "success")
        failed = sum(
            1
            for check in self.checks
            if check.status == "completed"
            and check.conclusion
            in ("failure", "timed_out", "cancelled", "action_required", "error")
        )
        running = sum(1 for check in self.checks if check.status != "completed")
        other = len(self.checks) - passed - failed - running
        parts = []
        if passed:
            parts.append(f"{passed} passed")
        if failed:
            parts.append(f"{failed} failed")
        if running:
            parts.append(f"{running} running")
        if other:
            parts.append(f"{other} other")
        summary = ", ".join(parts)
        return summary + (" (partial results)" if not self.checks_complete else "")

    @property
    def merge_readiness(self) -> str:
        """Conservative local advisory; GitHub remains authoritative for policy."""
        if self.merged:
            return "Merged (reported by GitHub)."
        if self.state == "closed":
            return "Closed without merging (reported by GitHub)."
        if self.state != "open":
            return "Merge readiness unknown: GitHub pull request state is unavailable."
        if self.draft:
            return "Draft — not ready for review (reported by GitHub)."
        if self.mergeable_state == "behind":
            return "GitHub reports that this branch is behind its base branch."
        if self.mergeable is False or self.mergeable_state == "dirty":
            return "GitHub reports merge conflicts with the base branch."
        if self.mergeable_state == "blocked":
            return "GitHub reports this pull request is blocked by repository policy."
        if self.mergeable_state == "unstable":
            return "GitHub reports an unstable merge state; check results need attention."
        if self.mergeable is None or self.mergeable_state != "clean":
            return "Merge readiness unknown: GitHub has not reported a stable clean state."
        if (
            self.merge_policy is None
            and self.checks
            and any(
                check.status != "completed" or check.conclusion != "success"
                for check in self.checks
            )
        ):
            return (
                "One or more check runs are pending or not successful; "
                "GitHub determines which checks are required."
            )
        if not self.checks_complete or not self.reviews_complete or not self.threads_complete:
            return "Merge readiness unknown: review or check data is incomplete."
        if self.merge_policy is not None:
            policy = self.merge_policy
            if not policy.complete:
                return "Merge readiness unknown: repository policy data is incomplete."
            if self.merge_policy.active_required_approvals:
                approvals = self.approval_count
                if approvals is None:
                    return "Merge readiness unknown: review data is incomplete."
                if approvals < policy.active_required_approvals:
                    missing = policy.active_required_approvals - approvals
                    return f"Repository policy requires {missing} more approval(s)."
                if self.review_decision.startswith("changes requested"):
                    return "Repository policy is blocked by a review requesting changes."
            required_checks = policy.active_required_checks
            if required_checks:
                observed = {
                    name: [check for check in self.checks if check.name == name]
                    for name in required_checks
                }
                missing_checks = [name for name, checks in observed.items() if not checks]
                if missing_checks:
                    return "Required check results are missing: " + ", ".join(missing_checks) + "."
                unsuccessful = [
                    name
                    for name, checks in observed.items()
                    if any(
                        check.status != "completed" or check.conclusion != "success"
                        for check in checks
                    )
                ]
                if unsuccessful:
                    return "Required checks need attention: " + ", ".join(unsuccessful) + "."
            codeowners_warning = ""
            if policy.active_codeowners_required:
                codeowners_warning = (
                    "Merge readiness unknown: CODEOWNERS approval is required, but "
                    "the required owners' review has not been verified."
                )
                if not policy.codeowners_path:
                    codeowners_warning = (
                        "Merge readiness unknown: CODEOWNERS approval is required, "
                        "but no standard CODEOWNERS file was found."
                    )
            if policy.active_merge_queue_required:
                queue = self.merge_queue_state
                if queue is None or queue.in_merge_queue is None:
                    return "Merge readiness unknown: merge-queue status was not available."
                if queue.head_sha and queue.head_sha != self.head_sha:
                    return (
                        "Merge readiness unknown: the pull request head changed; "
                        "refresh the review."
                    )
                if not queue.merge_queue_enabled:
                    return "Merge readiness unknown: ruleset and merge-queue status disagree."
                if not queue.in_merge_queue:
                    return "Repository policy requires this pull request to enter the merge queue."
                if codeowners_warning:
                    return codeowners_warning
                return "This pull request is in the merge queue; GitHub controls when it can merge."
            if codeowners_warning:
                return codeowners_warning
        if self.merge_queue_state and self.merge_queue_state.head_sha != self.head_sha:
            return "Merge readiness unknown: the pull request head changed; refresh the review."
        if self.data_warnings:
            return "Merge readiness unknown: " + "; ".join(self.data_warnings)
        if self.merge_policy is None:
            return (
                "GitHub reports no merge conflict; required reviews and branch protection rules "
                "are not verified here."
            )
        return (
            "GitHub reports no merge conflict; observed required checks and approvals are "
            "satisfied. GitHub remains authoritative for merge eligibility."
        )

    def summary_text(self) -> str:
        """The Copy Review Summary text: one readable paragraph block."""
        lines = [
            f"PR #{self.number}: {self.title}",
            f"{self.head_ref} into {self.base_ref}, by {self.author}",
            f"Head revision: {self.head_sha or 'unknown'}",
            self.merge_readiness,
            f"Reviews: {self.review_decision}",
            f"Checks: {self.checks_summary}",
            f"Review threads: {self.thread_count}"
            + (f" ({self.outdated_thread_count} outdated)" if self.outdated_thread_count else "")
            + (" (partial results)" if not self.threads_complete else ""),
            "Merge status is advisory; GitHub is authoritative for repository rules.",
        ]
        if self.data_warnings:
            lines.append("Data status: incomplete")
            lines.extend(f"Data note: {warning}" for warning in self.data_warnings)
        else:
            lines.append("Data status: all requested review data loaded.")
        if self.unresolved_thread_count:
            lines.append(f"Unresolved conversations: {self.unresolved_thread_count}")
        if self.requested_reviewers:
            lines.append("Awaiting review from: " + ", ".join(self.requested_reviewers))
        if self.merge_policy is not None:
            lines.append(self.merge_policy.summary_text())
        if self.merge_queue_state is not None:
            queue = self.merge_queue_state
            lines.append(
                "Merge queue: "
                + (
                    "enabled"
                    if queue.merge_queue_enabled
                    else "not enabled"
                    if queue.merge_queue_enabled is False
                    else "unknown"
                )
                + (
                    ", pull request is queued"
                    if queue.in_merge_queue
                    else ", pull request is not queued"
                    if queue.in_merge_queue is False
                    else ""
                )
                + (", auto-merge is enabled" if queue.auto_merge_enabled else "")
            )
        if self.url:
            lines.append(self.url)
        return "\n".join(lines)


__all__ = ["GitHubPullReviewState"]
