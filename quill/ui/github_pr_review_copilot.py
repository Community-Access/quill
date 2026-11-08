"""Request Copilot Review, in the pull request review window.

On the pull request's context menu (Shift+F10 on the outline), beside Request
Reviewers. It asks GitHub to add Copilot code review as a reviewer, off the UI
thread through the window's ``_run_action``, and says what GitHub confirmed:
when GitHub leaves Copilot off the reviewer list, which is how an account or
repository without Copilot code review answers, the window says that plainly
instead of reporting a request that never happened.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubPullReviewCopilotMixin"]


class GitHubPullReviewCopilotMixin:
    """The Copilot review row and its handler for ``GitHubPullReviewDialog``."""

    def _append_copilot_entries(self, add: Callable[..., None]) -> None:
        add(
            "Request Copilot Review",
            self._request_copilot_review,
            enabled=self._reviewers_btn.IsEnabled(),
        )

    def _request_copilot_review(self, _event: object) -> None:
        if not self._client.can_write:
            self._announce("Sign in to GitHub to ask Copilot for a review.")
            return
        provider = self._client._provider
        repo, number = self._repo, self._number
        self._run_action(lambda: provider.request_copilot_review(repo, number), "")
