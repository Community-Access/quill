"""Workflow run, workflow and branch actions the GitHub Workbench does itself.

GitHub PRD section 5. Jobs and Logs, What Failed, Re-run Failed Jobs Only,
Cancel Run, Delete Run, Approve Run from a Fork, Review Pending Deployments,
View Artifacts and Combined Check Status on a run; Runs on a workflow; and
Commits, Compare Branches and Delete Branch on a branch. Each calls the
provider method or opens the window GitHub Items did, parented to the
Workbench.

Every write asks first (deleting a branch asks for its name typed back), runs
off the UI thread, and says one outcome: what GitHub confirmed.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubBranch, GitHubWorkflow, GitHubWorkflowRun

__all__ = ["RUN_REASONS", "RUN_VERBS", "GitHubWorkbenchRunsMixin"]

RUN_VERBS: dict[str, frozenset[str]] = {
    "jobs": frozenset({"run"}),
    "what_failed": frozenset({"run"}),
    "rerun_failed": frozenset({"run"}),
    "cancel_run": frozenset({"run"}),
    "delete_run": frozenset({"run"}),
    "approve_fork": frozenset({"run"}),
    "pending_deployments": frozenset({"run"}),
    "artifacts": frozenset({"run"}),
    "check_status": frozenset({"run"}),
    "workflow_runs": frozenset({"workflow"}),
    "branch_commits": frozenset({"branch"}),
    "compare": frozenset({"branch"}),
    "delete_branch": frozenset({"branch"}),
}

RUN_REASONS: dict[str, str] = {
    "jobs": "This run has no GitHub run number to read jobs for.",
    "check_status": "This run has no commit to read checks for.",
    "delete_branch": "GitHub does not let anyone delete the repository's default branch.",
}


def _run_words(run: GitHubWorkflowRun) -> str:
    name = run.name or "workflow run"
    return f"run #{run.run_number}, {name}" if run.run_number else name


class GitHubWorkbenchRunsMixin:
    """Runs, workflows and branches, for the GitHub provider."""

    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _repo_for: Callable[[Any], str]
    _parent: Callable[[], Any]

    # -- can it run? -------------------------------------------------------------

    def _fits_run(self, row: object) -> bool:
        return isinstance(row, GitHubWorkflowRun) and bool(row.id)

    _fits_jobs = _fits_run
    _fits_what_failed = _fits_run
    _fits_artifacts = _fits_run

    def _fits_check_status(self, row: object) -> bool:
        return isinstance(row, GitHubWorkflowRun) and bool(row.head_sha)

    def _fits_run_write(self, row: object) -> bool:
        return self.signed_in and self._fits_run(row)

    _fits_rerun_failed = _fits_run_write
    _fits_cancel_run = _fits_run_write
    _fits_delete_run = _fits_run_write
    _fits_approve_fork = _fits_run_write
    _fits_pending_deployments = _fits_run_write

    def _fits_delete_branch(self, row: object) -> bool:
        return (
            self.signed_in
            and isinstance(row, GitHubBranch)
            and not (row.default_branch and row.default_branch == row.name)
        )

    # -- runs: windows -------------------------------------------------------------

    def _do_jobs(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        from quill.ui.github_workflow_jobs_dialog import WorkflowJobsDialog

        WorkflowJobsDialog(
            self._parent(),
            self.items,
            repo=self._repo_for(ref),
            run_id=row.id,
            run_label=f"#{row.run_number} {row.name}",
            run_attempt=row.run_attempt,
            head_sha=row.head_sha,
            run_url=row.url,
            announce_cb=self._say,
        ).show()

    def _do_what_failed(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        from quill.ui.github_run_digest_dialog import RunFailureDigestDialog

        RunFailureDigestDialog(
            self._parent(),
            self.items,
            repo=self._repo_for(ref),
            run_id=row.id,
            run_label=_run_words(row),
            announce_cb=self._say,
        ).show()

    def _do_pending_deployments(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        from quill.ui.github_pending_deployments_dialog import PendingDeploymentsDialog

        PendingDeploymentsDialog(
            self._parent(),
            self.items,
            repo=self._repo_for(ref),
            run_id=row.id,
            run_label=_run_words(row),
            announce_cb=self._say,
        ).show()

    def _do_artifacts(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        from quill.ui.github_artifacts_dialog import ArtifactsDialog

        label = f"#{row.run_number} - {row.name}" if row.name else f"#{row.run_number}"
        ArtifactsDialog(
            self._parent(),
            self.items,
            repo=self._repo_for(ref),
            run_id=row.id,
            run_label=label,
            run_url=row.url,
            announce_cb=self._say,
        ).show()

    def _do_check_status(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        repo, sha = self._repo_for(ref), row.head_sha
        self._background(
            "read the commit's checks",
            lambda: self.items.fetch_combined_check_status(repo, sha),
            lambda status: self._say(f"Commit {sha[:7]}: {status.one_line()}"),
        )

    # -- runs: writes ------------------------------------------------------------------

    def _do_rerun_failed(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        repo, words = self._repo_for(ref), _run_words(row)
        if not self._confirm(
            "Re-run Failed Jobs", f"Re-run only the failed jobs of {words} in {repo}?"
        ):
            return
        run_id = row.id
        self._background(
            "re-run the failed jobs",
            lambda: self.items.rerun_failed_jobs(repo, run_id),
            lambda _r: self._say(f"GitHub started a re-run of the failed jobs of {words}."),
        )

    def _do_cancel_run(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        repo, words, run_id = self._repo_for(ref), _run_words(row), row.id
        if not self._confirm("Cancel Run", f"Cancel {words} in {repo}?"):
            return
        self._background(
            "cancel the run",
            lambda: self.items.cancel_workflow_run(repo, run_id),
            lambda _r: (
                self._say(f"GitHub accepted the cancel request and is stopping {words}."),
                self.frame.reload(),
            ),
        )

    def _do_delete_run(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        repo, words, run_id = self._repo_for(ref), _run_words(row), row.id
        outcome = row.conclusion or row.status
        question = (
            f"Delete {words}"
            + (f" on branch {row.branch}" if row.branch else "")
            + (f" ({outcome})" if outcome else "")
            + f" from {repo}? Its logs and artifacts are deleted with it, "
            "and this cannot be undone."
        )
        if not self._confirm("Delete Workflow Run", question):
            return
        self._background(
            "delete the run",
            lambda: self.items.delete_workflow_run(repo, run_id),
            lambda _r: (self._say(f"Deleted {words}."), self.frame.reload()),
        )

    def _do_approve_fork(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        repo, words, run_id = self._repo_for(ref), _run_words(row), row.id
        if not self._confirm(
            "Approve Fork Run",
            f"Approve {words} from a fork so it runs in {repo}? Approve only code you have "
            "read: it runs with this repository's workflow permissions.",
        ):
            return
        self._background(
            "approve the run",
            lambda: self.items.approve_fork_run(repo, run_id),
            lambda _r: self._say(f"GitHub approved {words}; it will start shortly."),
        )

    # -- workflows ---------------------------------------------------------------------

    def _do_workflow_runs(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflow)
        self._go_filtered(  # type: ignore[attr-defined]
            "repository", "runs", self._repo_for(ref), row.name
        )

    # -- branches ------------------------------------------------------------------------

    def _do_branch_commits(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubBranch)
        repo, branch = self._repo_for(ref), row.name

        def show(commits: list[Any]) -> None:
            if not commits:
                self._say(f"{branch} has no commits to list.")
                return
            from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

            def url(index: int) -> str:
                return str(commits[index].url) if index >= 0 else ""

            def browse(index: int) -> None:
                if url(index) and not webbrowser.open(url(index), new=2):
                    self._say("Could not open this in your browser.")

            def comments(index: int) -> None:
                if index >= 0:
                    self._do_commit_comments(ref, commits[index])  # type: ignore[attr-defined]

            WorkbenchListDialog(
                self._parent(),
                f"Commits on {branch}",
                [
                    f"{c.short_sha} {c.message.splitlines()[0] if c.message else ''}, "
                    f"{c.author}, {c.date}"
                    for c in commits
                ],
                list_name=f"Commits on {branch}",
                list_help="The branch's commits, newest first. Enter opens one on GitHub.",
                detail=lambda i: f"{commits[i].message}\n\n{commits[i].sha}\n{commits[i].url}",
                actions=(
                    ("&Open on GitHub", "Open the commit in your browser.", browse),
                    ("Commit &Comments...", "Comments on the commit and its lines.", comments),
                    (
                        "Copy &Link",
                        "Copy the commit's address.",
                        lambda i: self.frame.copy_text(url(i)),
                    ),
                ),
                copy_text=self.frame.copy_text,
            ).show()

        self._background(
            "read the branch's commits",
            lambda: list(self.items.fetch_commits(repo, branch=branch)),
            show,
        )

    def _do_compare(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubBranch)
        repo, head = self._repo_for(ref), row.name
        base = self._ask_text(
            "Compare Branches",
            f"Compare {head} against which base branch:",
            value=row.default_branch or "main",
        )
        if not base:
            return

        def show(comparison: Any) -> None:
            from quill.ui.github_compare_branches_dialog import GitHubCompareBranchesDialog

            GitHubCompareBranchesDialog(
                self._parent(), self.items, repo, comparison, announce_cb=self._say
            ).show()

        self._background(
            "compare the branches", lambda: self.items.compare_branches(repo, base, head), show
        )

    def _do_delete_branch(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubBranch)
        repo, name = self._repo_for(ref), row.name
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self._parent(),
            title="Confirm Branch Deletion",
            message=(
                f"Delete branch {name!r} from {repo}? This cannot be undone from QUILL. "
                "Type the branch name to confirm."
            ),
            expected=name,
        ).show():
            return
        token = getattr(self.items, "token", None) or ""

        def work() -> None:
            from quill.core.github.repo_admin import GitHubRepoAdminProvider

            admin = GitHubRepoAdminProvider(token)
            try:
                admin.delete_branch(repo, name)
            finally:
                admin.close()

        self._background(
            "delete the branch",
            work,
            lambda _r: (self._say(f"Deleted branch {name}."), self.frame.reload()),
        )
