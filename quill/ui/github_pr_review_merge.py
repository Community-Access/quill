"""Auto-merge, the merge queue, combined check status and check re-requests in Review.

Reached from the review window's Auto-Merge and Queue button and from the
pull request's context menu (Shift+F10 on the outline). Each write asks
first, runs off the UI thread through the dialog's ``_run_action``, and says
the sentence :mod:`quill.core.github.merge_automation` built from GitHub's
reply -- never a success GitHub did not confirm.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.merge_automation import (
    MERGE_METHODS,
    dequeue_pull_request,
    disable_auto_merge,
    enable_auto_merge,
    enqueue_pull_request,
)
from quill.core.github.review_errors import GitHubReviewError
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubPullReviewMergeMixin"]


class GitHubPullReviewMergeMixin:
    """Merge automation and check actions for ``GitHubPullReviewDialog``."""

    def _append_merge_entries(self, add: Callable[..., None]) -> None:
        can_change = self._merge_btn.IsEnabled()
        add("Enable Auto-Merge...", self._enable_auto_merge, enabled=can_change)
        add("Disable Auto-Merge...", self._disable_auto_merge, enabled=can_change)
        add("Add to Merge Queue...", self._enqueue, enabled=can_change)
        add("Remove from Merge Queue...", self._dequeue, enabled=can_change)
        add("Combined Check Status", self._combined_status, enabled=self._state is not None)

    def _show_merge_menu(self, _event: object) -> None:
        wx = self._wx
        menu = wx.Menu()

        def add(label: str, handler: object, *, enabled: bool = True) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Enable(item_id, enabled)
            menu.Bind(wx.EVT_MENU, handler, id=item_id)

        self._append_merge_entries(add)
        try:
            self._merge_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _review_provider(self) -> object:
        return self._client._provider

    def _enable_auto_merge(self, _event: object) -> None:
        wx = self._wx
        labels = list(MERGE_METHODS)
        title = "Enable Auto-Merge"
        dialog = wx.SingleChoiceDialog(
            self.dialog,
            f"GitHub merges pull request #{self._number} by itself once its required "
            "reviews and checks pass. Merge method:",
            title,
            labels,
        )
        try:
            if self._show_native(dialog, title) != wx.ID_OK:
                return
            method = labels[dialog.GetSelection()]
        finally:
            dialog.Destroy()
        repo, number = self._repo, self._number
        self._run_action(
            lambda: enable_auto_merge(self._review_provider(), repo, number, method), ""
        )

    def _disable_auto_merge(self, _event: object) -> None:
        if not self._confirm(
            f"Turn off auto-merge for pull request #{self._number}?", "Disable Auto-Merge"
        ):
            return
        repo, number = self._repo, self._number
        self._run_action(lambda: disable_auto_merge(self._review_provider(), repo, number), "")

    def _enqueue(self, _event: object) -> None:
        if not self._confirm(
            f"Add pull request #{self._number} to the merge queue? GitHub merges it "
            "when the queue's checks pass.",
            "Add to Merge Queue",
        ):
            return
        repo, number = self._repo, self._number
        self._run_action(lambda: enqueue_pull_request(self._review_provider(), repo, number), "")

    def _dequeue(self, _event: object) -> None:
        if not self._confirm(
            f"Remove pull request #{self._number} from the merge queue?",
            "Remove from Merge Queue",
        ):
            return
        repo, number = self._repo, self._number
        self._run_action(lambda: dequeue_pull_request(self._review_provider(), repo, number), "")

    def _rerequest_selected_check(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "check" or not 0 <= index < len(self._checks):
            self._announce("Select a check first.")
            return
        check = self._checks[index]
        if check.check_run_id <= 0:
            self._announce(
                f"{check.name} is a commit status, not a check run; it cannot be re-requested."
            )
            return
        if not self._confirm(f"Ask GitHub to run {check.name} again?", "Re-request Check"):
            return
        repo, check_id, name = self._repo, check.check_run_id, check.name

        def action() -> str:
            try:
                self._client._provider.rerequest_check_run(repo, check_id)
            except GitHubItemsError as exc:
                raise GitHubReviewError(str(exc.args[0]) if exc.args else str(exc)) from exc
            return f"GitHub queued {name} to run again."

        self._run_action(action, "")

    def _combined_status(self, _event: object) -> None:
        state = self._state
        if state is None or not state.head_sha:
            self._announce("Load the pull request first.")
            return
        self._status_token = getattr(self, "_status_token", 0) + 1
        token = self._status_token
        policy = state.merge_policy
        repo, sha, base = self._repo, state.head_sha, state.base_ref
        provider = self._client._provider
        self._status.SetLabel("Reading combined check status…")

        def worker() -> None:
            required: tuple[str, ...] = ()
            note = ""
            try:
                if policy is not None:
                    required = policy.active_required_checks
                elif base:
                    from quill.core.github.merge_policy import fetch_merge_policy

                    required = fetch_merge_policy(provider, repo, base).active_required_checks
            except Exception:  # noqa: BLE001 - fall back to all checks, and say so
                note = " Required checks could not be read, so this counts every check."
            try:
                line = provider.fetch_combined_check_status(repo, sha, required=required).one_line()
            except GitHubItemsError as exc:
                line = str(exc.args[0]) if exc.args else str(exc)
            self._wx.CallAfter(self._combined_status_ready, token, line + note)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: explicit status read.

    def _combined_status_ready(self, token: int, line: str) -> None:
        if token != getattr(self, "_status_token", 0) or not dialog_alive(self.dialog):
            return
        self._status.SetLabel(line)
        self._announce(line)
