"""Branches/Workflow-Runs write actions and view-column selection for
:class:`~quill.ui.github_items_dialog.GitHubItemsDialog`.

Split out to keep that module under its GATE-11 size budget -- this mixin
sits alongside ``GitHubItemsDialog`` in its own MRO (the same
sibling-mixin-sharing-self pattern ``MainFrame``'s feature mixins already
use), so every method here reads/writes the parent dialog's own attributes
(``self._repo``, ``self._rows``, ``self._provider``, etc.) with no
constructor of its own.

Covers: **Compare Branches** (Ctrl+Shift+B, read-only, no authenticated
session required), the **Columns...** per-view column-visibility menu,
**Delete Branch**, **Re-run Workflow**, and **View Artifacts...** (the last
three are write/read actions reached from the Actions... menu on a Branches
or Workflow Runs row).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubBranch, GitHubBranchComparison, GitHubItemsError
from quill.ui.github_items_view import VIEW_BRANCHES, VIEW_COLUMNS

if TYPE_CHECKING:
    pass


class GitHubBranchActionsMixin:
    """Adds Compare Branches, Columns..., and branch/run actions to
    ``GitHubItemsDialog``."""

    # ------------------------------------------------------------------
    # Column selection (GHManage parity, Columns... menu)

    def _current_columns(self) -> tuple[str, ...]:
        """The visible column subset for the current view (Columns... menu)."""
        return tuple(self._visible_columns.get(self._view, VIEW_COLUMNS[self._view]))

    def _on_columns_menu(self, _event: object) -> None:
        """Choose which columns are shown for the current view (GHManage parity)."""
        wx = self._wx
        all_columns = VIEW_COLUMNS[self._view]
        current = list(self._visible_columns.get(self._view, all_columns))
        menu = wx.Menu()
        ids: dict[int, str] = {}
        for col in all_columns:
            item_id = wx.NewIdRef()
            item = menu.AppendCheckItem(item_id, col)
            item.Check(col in current)
            ids[int(item_id)] = col

        def _on_toggle(event: object) -> None:
            col = ids.get(int(event.GetId()))
            if col is None:
                return
            visible = list(self._visible_columns.get(self._view, all_columns))
            if col in visible:
                if len(visible) <= 1:
                    self._announce("At least one column must stay visible.")
                    return
                visible.remove(col)
            else:
                visible = [c for c in all_columns if c in visible or c == col]
            self._visible_columns[self._view] = visible
            self._saved.set_columns(self._view, visible)
            self._rebuild_columns()
            self._populate_list()

        menu.Bind(wx.EVT_MENU, _on_toggle)
        try:
            self._columns_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    # ------------------------------------------------------------------
    # Compare Branches (Ctrl+Shift+B): read-only, no authenticated session

    def _on_compare_branches(self) -> None:
        """Ctrl+Shift+B / Compare...: ahead/behind, commits, and changed files
        between two branches. Read-only, so unlike the Batch.../Actions...
        menus this needs no authenticated session (GHManage parity)."""
        wx = self._wx
        if not self._repo:
            self._announce("Load a repository first.")
            return
        if self._view != VIEW_BRANCHES:
            self._announce("Compare Branches works in the Branches view.")
            return
        selected = self._selected_indices()
        default_head = ""
        if len(selected) == 1 and isinstance(self._rows[selected[0]], GitHubBranch):
            default_head = self._rows[selected[0]].name
        with wx.TextEntryDialog(
            self.dialog, "Base branch:", "Compare Branches", value="main"
        ) as dlg:
            if self._show_modal(dlg, "Compare Branches") != wx.ID_OK:
                return
            base = dlg.GetValue().strip()
        if not base:
            return
        with wx.TextEntryDialog(
            self.dialog,
            "Compare against (head branch):",
            "Compare Branches",
            value=default_head,
        ) as dlg:
            if self._show_modal(dlg, "Compare Branches") != wx.ID_OK:
                return
            head = dlg.GetValue().strip()
        if not head:
            return
        self._set_status(f"Comparing {base}...{head}...")
        repo = self._repo

        def worker() -> None:
            try:
                comparison = self._provider.compare_branches(repo, base, head)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._show_compare_dialog, comparison)

        threading.Thread(  # GATE-40-OK: two-branch comparison fetch.
            target=worker, daemon=True
        ).start()

    def _show_compare_dialog(self, comparison: GitHubBranchComparison) -> None:
        from quill.ui.github_compare_branches_dialog import GitHubCompareBranchesDialog

        self._set_status(
            f"{comparison.head} is {comparison.ahead_by} ahead, "
            f"{comparison.behind_by} behind {comparison.base}."
        )
        GitHubCompareBranchesDialog(
            self.dialog, self._provider, self._repo, comparison, announce_cb=self._announce
        ).show()

    # ------------------------------------------------------------------
    # Delete branch / re-run workflow / view artifacts

    def _delete_selected_branch(self) -> None:
        selected = self._selected_indices()
        if len(selected) != 1:
            return
        model = self._rows[selected[0]]
        if not isinstance(model, GitHubBranch):
            return
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self.dialog,
            title="Confirm Branch Deletion",
            message=(
                f"Delete branch {model.name!r} from {self._repo}? This cannot be undone from QUILL."
            ),
            expected=model.name,
        ).show():
            self._announce("Branch deletion cancelled.")
            return
        self._set_status(f"Deleting {model.name}...")
        branch_name = model.name

        def worker() -> None:
            wx = self._wx
            from quill.core.github.repo_admin import GitHubRepoAdminError, GitHubRepoAdminProvider

            provider = GitHubRepoAdminProvider(self._provider.token or "")
            try:
                provider.delete_branch(self._repo, branch_name)
            except GitHubRepoAdminError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            finally:
                provider.close()
            wx.CallAfter(self._on_branch_deleted, branch_name)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented delete.

    def _on_branch_deleted(self, branch_name: str) -> None:
        self._set_status(f"Deleted branch {branch_name}")
        self._reload()

    def _rerun_selected_workflow(self) -> None:
        selected = self._selected_indices()
        if len(selected) != 1:
            return
        model = self._rows[selected[0]]
        run_number = getattr(model, "run_number", 0)
        if not run_number:
            self._announce("Select a workflow run first.")
            return
        if not self._confirm_action(
            f"Re-run workflow run #{run_number} in {self._repo}?", "Confirm Re-run"
        ):
            self._announce("Re-run cancelled.")
            return
        self._set_status(f"Re-running #{run_number}...")

        def worker() -> None:
            wx = self._wx
            try:
                self._provider.rerun_workflow_run(self._repo, run_number)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._set_status, f"Re-run started for #{run_number}")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented re-run.

    def _view_artifacts_for_selected(self) -> None:
        selected = self._selected_indices()
        if len(selected) != 1:
            return
        model = self._rows[selected[0]]
        run_number = getattr(model, "run_number", 0)
        if not run_number:
            self._announce("Select a workflow run first.")
            return
        run_name = getattr(model, "name", "")
        run_url = getattr(model, "url", "")
        from quill.ui.github_artifacts_dialog import ArtifactsDialog

        dlg = ArtifactsDialog(
            self.dialog,
            self._provider,
            repo=self._repo,
            run_id=run_number,
            run_label=f"#{run_number} - {run_name}" if run_name else f"#{run_number}",
            run_url=run_url,
            announce_cb=self._announce,
        )
        dlg.show()


__all__ = ["GitHubBranchActionsMixin"]
