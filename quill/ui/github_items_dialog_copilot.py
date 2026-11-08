"""Assign to Copilot on an issue, and Commit Comments on a commit, in GitHub Items.

**Assign to Copilot** (an issue's context menu) first asks GitHub, off the UI
thread, whether the Copilot coding agent can be assigned in this repository.
When it cannot, the window says why in plain words and nothing is sent; when it
can, QUILL asks before handing the issue over, and says it is assigned only
when GitHub's reply lists Copilot. The check carries a generation token, so a
slow answer cannot open a question after a newer one.

**Commit Comments** (a commit's context menu) opens the commit's comments,
where a new one goes on the whole commit or on a file line.

QUILL and QUILL Lite share this, as they share the viewer.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.copilot import CopilotAssignment
from quill.core.github.items_provider import GitHubCommit, GitHubItem

__all__ = ["GitHubItemsCopilotMixin"]


class GitHubItemsCopilotMixin:
    """Context-menu rows and handlers for the Copilot agent and commit comments."""

    def _add_copilot_and_commit_actions(self, add: Any, model: object) -> None:
        signed_in = self._provider.is_authenticated
        if isinstance(model, GitHubItem) and not model.is_pr and signed_in:
            add(
                f"Assign #{model.number} to Copilot...",
                lambda item=model: self._assign_to_copilot(item),
            )
        if isinstance(model, GitHubCommit):
            add("Commit Comments...", lambda item=model: self._open_commit_comments(item))

    def _assign_to_copilot(self, model: GitHubItem) -> None:
        repo, number = self._repo, model.number

        def check() -> CopilotAssignment:
            return self._provider.check_copilot_assignment(repo, number)

        self._housekeeping_run(
            check,
            self._copilot_checked,
            latest_only=True,
            busy=f"Asking GitHub whether Copilot can take issue #{number}...",
        )

    def _copilot_checked(self, assignment: CopilotAssignment) -> None:
        wx = self._wx
        title = "Assign to Copilot"
        if refusal := assignment.refusal():
            self._set_status(refusal, announce=False)
            with wx.MessageDialog(
                self.dialog, refusal, title, wx.OK | wx.ICON_INFORMATION
            ) as dialog:
                self._show_modal(dialog, title)
            return
        with wx.MessageDialog(
            self.dialog,
            assignment.confirmation(),
            title,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) as dialog:
            if self._show_modal(dialog, title) != wx.ID_YES:
                self._announce("Cancelled; nothing was sent to GitHub.")
                return
        self._housekeeping_write(
            lambda: self._provider.assign_issue_to_copilot(assignment), then_reload=True
        )

    def _open_commit_comments(self, model: GitHubCommit) -> None:
        from quill.ui.github_commit_comments_dialog import GitHubCommitCommentsDialog

        GitHubCommitCommentsDialog(
            self.dialog, self._provider, self._repo, model.sha, announce_cb=self._announce
        ).show()
