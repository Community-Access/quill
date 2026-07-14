"""Run-on-branch for :class:`~quill.ui.github_items_dialog.GitHubItemsDialog`'s
Workflows view (GHManage parity): Enter on a workflow row, or Actions... >
Run on Branch..., prompts for a branch and dispatches a ``workflow_dispatch``
run.

Split into its own mixin (same sibling-mixin-sharing-self pattern as
:class:`~quill.ui.github_items_dialog_branches.GitHubBranchActionsMixin`) so
``github_items_dialog.py`` stays under its GATE-11 size budget.
"""

from __future__ import annotations

import threading

from quill.core.github.items_provider import GitHubItemsError


class GitHubWorkflowsMixin:
    """Adds "run this workflow on a branch" to ``GitHubItemsDialog``."""

    def _run_selected_workflow(self, workflow: object) -> None:
        if not self._provider.is_authenticated:
            self._announce(
                "Running a workflow needs a signed-in GitHub account; this session is read-only."
            )
            return
        wx = self._wx
        name = getattr(workflow, "name", "workflow")
        workflow_id = str(getattr(workflow, "id", ""))
        with wx.TextEntryDialog(
            self.dialog, f"Run {name!r} on branch:", "Run Workflow", value="main"
        ) as dlg:
            if self._show_modal(dlg, "Run Workflow") != wx.ID_OK:
                return
            ref = dlg.GetValue().strip()
        if not ref:
            return
        if not self._confirm_action(
            f"Run workflow {name!r} on {ref!r} in {self._repo}?", "Confirm Run Workflow"
        ):
            self._announce("Run cancelled.")
            return
        self._set_status(f"Running {name}...")
        repo = self._repo

        def worker() -> None:
            try:
                self._provider.dispatch_workflow(repo, workflow_id, ref)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._set_status, f"Dispatched {name} on {ref}")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented dispatch.


__all__ = ["GitHubWorkflowsMixin"]
