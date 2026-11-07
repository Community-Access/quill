"""Paste a GitHub URL and continue in the shared native workbench."""

from __future__ import annotations

import webbrowser

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubWorkflowRun,
)
from quill.core.github.references import (
    GitHubReference,
    GitHubReferenceError,
    parse_github_reference,
)
from quill.core.github.workflows import GitHubWorkflow
from quill.ui.github_items_view import (
    VIEW_BRANCHES,
    VIEW_COMMITS,
    VIEW_ISSUES,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEW_WORKFLOWS,
    VIEWS,
)


class GitHubReferenceMixin:
    """Route copied references from Items in both QUILL and QUILL Lite."""

    def _load_reference_rows(self, repo: str, view: str, rows: list[object]) -> list[object]:
        reference = self._initial_reference
        if reference is None or reference.repository.casefold() != repo.casefold():
            return rows
        if (
            view == VIEW_ISSUES
            and reference.kind in {"issue", "pull_request"}
            and reference.number is not None
        ):
            target = self._provider.fetch_item(repo, reference.number)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (
                        isinstance(row, GitHubItem)
                        and row.number == target.number
                        and row.is_pr == target.is_pr
                    )
                ),
            ]
        elif view == VIEW_BRANCHES and reference.kind == "branch":
            target = self._provider.fetch_branch_by_name(repo, reference.ref)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (isinstance(row, GitHubBranch) and row.name == target.name)
                ),
            ]
        elif view == VIEW_COMMITS and reference.kind == "commit":
            target = self._provider.fetch_commit_by_sha(repo, reference.ref)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (
                        isinstance(row, GitHubCommit)
                        and row.sha.casefold() == target.sha.casefold()
                    )
                ),
            ]
        elif view == VIEW_RELEASES and reference.kind == "release" and reference.ref:
            target = self._provider.fetch_release_by_tag(repo, reference.ref)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (isinstance(row, GitHubRelease) and row.tag == target.tag)
                ),
            ]
        elif (
            view == VIEW_RUNS and reference.kind == "workflow_run" and reference.number is not None
        ):
            target = self._provider.fetch_workflow_run_by_id(repo, reference.number)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (isinstance(row, GitHubWorkflowRun) and row.id == target.id)
                ),
            ]
        elif view == VIEW_WORKFLOWS and reference.kind == "workflow":
            target = self._provider.fetch_workflow_by_reference(repo, reference.ref)
            rows = [
                target,
                *(
                    row
                    for row in rows
                    if not (isinstance(row, GitHubWorkflow) and row.id == target.id)
                ),
            ]
        return rows

    def _on_open_reference(self, _event: object) -> None:
        wx = self._wx
        dialog = wx.TextEntryDialog(
            self.dialog,
            "Paste a GitHub URL or enter owner/repo:",
            "Open GitHub Reference",
        )
        dialog.SetName("GitHub URL or owner and repository")
        try:
            if self._show_modal(dialog, "Open GitHub Reference") != wx.ID_OK:
                return
            value = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        try:
            reference = parse_github_reference(value)
        except GitHubReferenceError as exc:
            self._set_status(str(exc))
            self._announce(str(exc))
            return

        if reference.kind == "file" and self._open_file_reference_cb is not None:
            self._open_file_reference_cb(reference.url)
            return
        native_kinds = {
            "repository",
            "issue",
            "pull_request",
            "discussion",
            "branch",
            "commit",
            "release",
            "workflow",
            "workflow_run",
        }
        if reference.kind not in native_kinds or (reference.kind == "branch" and reference.path):
            self._open_reference_in_browser(reference)
            return
        if reference.kind == "discussion":
            if not self._provider.is_authenticated or reference.number is None:
                self._open_reference_in_browser(reference)
                return
            from quill.ui.github_explore_dialog import GitHubExploreDialog

            GitHubExploreDialog(
                self.dialog,
                self._provider,
                initial_repo=reference.repository,
                initial_view="discussions",
                initial_discussion=reference.number,
                announce_cb=self._announce,
                on_start_issue_worktree=self._start_issue_worktree_cb,
            ).show()
            return

        self._apply_initial_reference(reference)

    def _apply_initial_reference(self, reference: GitHubReference) -> None:
        self._initial_reference = reference
        self._repo_ctrl.SetValue(reference.repository)
        self._search_query = ""
        self._search_ctrl.ChangeValue("")
        self._quick_filter_query = ""
        self._quick_filter_ctrl.ChangeValue("")
        self._page = 1
        self._drill_branch = None
        self._drill_release = None

        self._view = {
            "branch": VIEW_BRANCHES,
            "commit": VIEW_COMMITS,
            "release": VIEW_RELEASES,
            "workflow": VIEW_WORKFLOWS,
            "workflow_run": VIEW_RUNS,
        }.get(reference.kind, VIEW_ISSUES)
        self._show = {
            "issue": "issues",
            "pull_request": "prs",
        }.get(reference.kind, "both")
        self._state = "all" if reference.kind in {"issue", "pull_request"} else "open"

        self._view_choice.SetSelection(
            next(index for index, (key, _label) in enumerate(VIEWS) if key == self._view)
        )
        self._show_choice.SetSelection({"both": 0, "issues": 1, "prs": 2}[self._show])
        self._state_choice.SetSelection({"open": 0, "closed": 1, "all": 2}[self._state])
        self._rebuild_columns()
        self._apply_filter_enablement()
        self._on_load(None)

    def _select_initial_reference(self) -> None:
        reference = self._initial_reference
        if reference is None or reference.repository.casefold() != self._repo.casefold():
            return
        if reference.kind == "release" and not reference.ref:
            self._announce("Showing repository releases.")
            return
        if reference.kind in {"issue", "pull_request"}:
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubItem)
                    and row.number == reference.number
                    and (reference.kind == "issue" or row.is_pr)
                ),
                -1,
            )
        elif reference.kind == "branch":
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubBranch) and row.name == reference.ref
                ),
                -1,
            )
        elif reference.kind == "commit":
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubCommit)
                    and row.sha.casefold().startswith(reference.ref.casefold())
                ),
                -1,
            )
        elif reference.kind == "release":
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubRelease) and row.tag == reference.ref
                ),
                -1,
            )
        elif reference.kind == "workflow_run":
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubWorkflowRun) and row.id == reference.number
                ),
                -1,
            )
        elif reference.kind == "workflow":
            target_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if isinstance(row, GitHubWorkflow)
                    and (
                        row.path.casefold() == reference.ref.casefold()
                        or row.path.casefold().endswith("/" + reference.ref.casefold())
                    )
                ),
                -1,
            )
        else:
            return
        if target_index < 0:
            self._announce(
                f"Could not find the linked {reference.kind.replace('_', ' ')} "
                "in the loaded results. Use View more or open the link in GitHub."
            )
            return
        row = self._rows[target_index]
        self._list.SetFocus()
        self._list.Select(target_index)
        self._list.Focus(target_index)
        self._show_detail(target_index)
        if reference.kind == "pull_request" or (isinstance(row, GitHubItem) and row.is_pr):
            self._wx.CallAfter(self._on_review)
        elif reference.kind == "branch":
            self._announce(f"Selected branch {reference.ref}.")
        elif isinstance(row, GitHubCommit):
            self._announce(f"Opened commit {row.short_sha}.")
        elif isinstance(row, GitHubRelease):
            self._announce(f"Opened release {row.tag}.")
        elif isinstance(row, GitHubWorkflowRun):
            self._announce(f"Opened workflow run {row.id}.")
        elif isinstance(row, GitHubWorkflow):
            self._announce(f"Opened workflow {row.name}.")
        else:
            label = "pull request" if row.is_pr else "issue"
            self._announce(f"Opened {label} #{row.number}: {row.title}")

    def _open_reference_in_browser(self, reference: GitHubReference) -> None:
        wx = self._wx
        kind = reference.kind.replace("_", " ")
        dialog = wx.MessageDialog(
            self.dialog,
            f"This {kind} link does not have a native view in this workbench.\n\n"
            "Open it in your default browser? QUILL will not attach your GitHub token.",
            "Open GitHub Reference in Browser",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        )
        try:
            if self._show_modal(dialog, "Open GitHub Reference in Browser") != wx.ID_YES:
                return
        finally:
            dialog.Destroy()
        if webbrowser.open(reference.url, new=2):
            self._announce(f"Opened {kind} in your browser.")
        else:
            self._set_status("Could not open the GitHub link in your default browser.")
