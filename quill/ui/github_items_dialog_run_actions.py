"""Workflow run actions in the GitHub Items viewer's Workflow runs view.

What Failed (Ctrl+Shift+W), Re-run Failed Jobs Only, Cancel Run, Delete Run,
Approve Run from a Fork, Review Pending Deployments and Combined Check Status.
Each is reached from the Actions button's menu and the row's context menu
(Shift+F10), and every write asks first, then says only what GitHub
confirmed. Split from ``github_items_dialog.py`` to keep it inside GATE-11.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubItemsError
from quill.ui.github_items_view import VIEW_RUNS

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubRunActionsUiMixin"]


def _run_words(model: object) -> str:
    number = getattr(model, "run_number", 0)
    name = getattr(model, "name", "") or "workflow run"
    return f"run #{number}, {name}" if number else name


class GitHubRunActionsUiMixin:
    """Selected-run actions for ``GitHubItemsDialog``."""

    def _add_run_actions(self, add: Callable[[str, Callable[[], None]], None]) -> None:
        """Add the Wave 1 run actions to a menu builder (Actions menu or context menu)."""
        add("What Failed...\tCtrl+Shift+W", self._show_failure_digest)
        add("Combined Check Status", self._show_combined_status)
        if not self._provider.is_authenticated:
            return
        add("Re-run Failed Jobs Only", self._rerun_failed_jobs)
        add("Cancel Run...", self._cancel_selected_run)
        add("Delete Run...", self._delete_selected_run)
        add("Review Pending Deployments...", self._review_pending_deployments)
        add("Approve Run from a Fork...", self._approve_fork_run)

    def _selected_run(self) -> object | None:
        selected = self._selected_indices()
        if self._view != VIEW_RUNS or len(selected) != 1:
            self._announce("Select one workflow run first.")
            return None
        model = self._rows[selected[0]]
        if not getattr(model, "id", 0):
            self._announce("This workflow run has no GitHub run ID.")
            return None
        return model

    def _show_failure_digest(self) -> None:
        model = self._selected_run()
        if model is None:
            return
        from quill.ui.github_run_digest_dialog import RunFailureDigestDialog

        RunFailureDigestDialog(
            self.dialog,
            self._provider,
            repo=self._repo,
            run_id=model.id,
            run_label=_run_words(model),
            announce_cb=self._announce,
        ).show()

    def _review_pending_deployments(self) -> None:
        model = self._selected_run()
        if model is None:
            return
        from quill.ui.github_pending_deployments_dialog import PendingDeploymentsDialog

        PendingDeploymentsDialog(
            self.dialog,
            self._provider,
            repo=self._repo,
            run_id=model.id,
            run_label=_run_words(model),
            announce_cb=self._announce,
        ).show()

    def _run_in_background(self, work: Callable[[], str], then_reload: bool = False) -> None:
        wx = self._wx

        def worker() -> None:
            try:
                message = work()
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, str(exc.args[0]) if exc.args else str(exc))
                return
            wx.CallAfter(self._run_action_done, message, then_reload)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented run action.

    def _run_action_done(self, message: str, then_reload: bool) -> None:
        self._set_status(message)
        if then_reload:
            self._reload()

    def _confirmed_run(self, question: str, title: str) -> object | None:
        model = self._selected_run()
        if model is None:
            return None
        if not self._confirm_action(question.format(run=_run_words(model), repo=self._repo), title):
            self._announce("Cancelled; nothing was sent to GitHub.")
            return None
        return model

    def _rerun_failed_jobs(self) -> None:
        model = self._confirmed_run(
            "Re-run only the failed jobs of {run} in {repo}?", "Re-run Failed Jobs"
        )
        if model is None:
            return
        repo, run_id, words = self._repo, model.id, _run_words(model)
        self._set_status(f"Asking GitHub to re-run the failed jobs of {words}...")

        def work() -> str:
            self._provider.rerun_failed_jobs(repo, run_id)
            return f"GitHub started a re-run of the failed jobs of {words}."

        self._run_in_background(work)

    def _cancel_selected_run(self) -> None:
        model = self._confirmed_run("Cancel {run} in {repo}?", "Cancel Run")
        if model is None:
            return
        repo, run_id, words = self._repo, model.id, _run_words(model)

        def work() -> str:
            self._provider.cancel_workflow_run(repo, run_id)
            return f"GitHub accepted the cancel request and is stopping {words}. Refresh to check."

        self._run_in_background(work)

    def _delete_selected_run(self) -> None:
        model = self._selected_run()
        if model is None:
            return
        branch = getattr(model, "branch", "")
        outcome = getattr(model, "conclusion", "") or getattr(model, "status", "")
        question = (
            f"Delete {_run_words(model)}"
            + (f" on branch {branch}" if branch else "")
            + (f" ({outcome})" if outcome else "")
            + f" from {self._repo}? Its logs and artifacts are deleted with it, "
            "and this cannot be undone."
        )
        if not self._confirm_action(question, "Delete Workflow Run"):
            self._announce("Cancelled; the run was not deleted.")
            return
        repo, run_id, words = self._repo, model.id, _run_words(model)

        def work() -> str:
            self._provider.delete_workflow_run(repo, run_id)
            return f"Deleted {words}."

        self._run_in_background(work, then_reload=True)

    def _approve_fork_run(self) -> None:
        model = self._confirmed_run(
            "Approve {run} from a fork so it runs in {repo}? Approve only code you have "
            "read: it runs with this repository's workflow permissions.",
            "Approve Fork Run",
        )
        if model is None:
            return
        repo, run_id, words = self._repo, model.id, _run_words(model)

        def work() -> str:
            self._provider.approve_fork_run(repo, run_id)
            return f"GitHub approved {words}; it will start shortly."

        self._run_in_background(work)

    def _show_combined_status(self) -> None:
        model = self._selected_run()
        if model is None:
            return
        sha = getattr(model, "head_sha", "")
        if not sha:
            self._announce("This run has no commit to read checks for.")
            return
        repo = self._repo
        self._set_status("Reading the commit's checks...", announce=False)

        def work() -> str:
            status = self._provider.fetch_combined_check_status(repo, sha)
            return f"Commit {sha[:7]}: {status.one_line()}"

        self._run_in_background(work)
