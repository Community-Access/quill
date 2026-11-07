"""Pull-request review and diff entry points for the GitHub Items viewer."""

from __future__ import annotations

from quill.core.github.items_provider import GitHubItem, GitHubPullDiff


class GitHubItemsReviewMixin:
    """Open the selected pull request's native review and diff surfaces."""

    def _on_review(self) -> None:
        index = self._list.GetFirstSelected()
        model = self._rows[index] if 0 <= index < len(self._rows) else None
        if not isinstance(model, GitHubItem) or not model.is_pr:
            self._announce("Select a pull request row first; Review works on PRs.")
            return
        from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog

        GitHubPullReviewDialog(
            self.dialog,
            self._provider,
            self._repo,
            model.number,
            announce_cb=self._announce,
        ).show()

    def _show_diff_dialog(self, diff: GitHubPullDiff) -> None:
        from quill.ui.github_pr_diff_dialog import GitHubPullDiffDialog

        if not diff.files:
            self._set_status("This pull request has no changed files to compare.")
            return
        self._set_status(f"{len(diff.files)} changed files.")
        GitHubPullDiffDialog(
            self.dialog,
            self._provider,
            self._repo,
            diff,
            announce_cb=self._announce,
            ai_acquire=self._ai_acquire,
        ).show()


__all__ = ["GitHubItemsReviewMixin"]
