"""Native outline menus and actions for pull-request review."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.pr_review import GitHubReviewError
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from collections.abc import Callable


class GitHubPullReviewMenusMixin:
    """Outline context menu, clipboard, navigation, and review write actions."""

    def _show_node_menu(self, _event: object) -> None:
        wx = self._wx
        if _event is not None and _event.GetEventObject() is self._outline:
            position = _event.GetPosition()
            if position != wx.DefaultPosition:
                item, _flags = self._outline.HitTest(self._outline.ScreenToClient(position))
                if item.IsOk():
                    self._outline.SelectItem(item)
                    self._select_node(None)
        menu, _menu_ids = self._build_node_menu()
        try:
            self._outline.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _build_node_menu(self) -> tuple[object, list[object]]:
        wx = self._wx
        menu = wx.Menu()
        menu_ids: list[object] = []
        kind, index = self._node_kind()

        def add(label: str, handler: object, *, enabled: bool = True) -> None:
            item_id = wx.NewIdRef()
            menu_ids.append(item_id)
            menu.Append(item_id, label)
            menu.Enable(item_id, enabled)
            menu.Bind(wx.EVT_MENU, handler, id=item_id)

        if kind == "thread" and 0 <= index < len(self._threads):
            thread = self._threads[index]
            add(
                "Reply to Thread...\tCtrl+R",
                self._reply_to_thread,
                enabled=self._reply_btn.IsEnabled(),
            )
            add(
                (
                    "Reopen Thread...\tCtrl+Shift+R"
                    if thread.resolved
                    else "Resolve Thread...\tCtrl+Shift+R"
                ),
                self._change_thread_resolution,
                enabled=bool(thread.node_id)
                and (thread.can_unresolve if thread.resolved else thread.can_resolve),
            )
            add(
                "React to a Comment...",
                self._react_to_thread_comment,
                enabled=self._client.can_write,
            )
            add("Copy Conversation", self._copy_thread)
            add(
                "Copy Thread Link",
                self._copy_thread_link,
                enabled=bool(self._threads[index].root.url),
            )
            add(
                "Open File Differences",
                self._open_thread_file_diff,
                enabled=self._diff is not None and bool(self._threads[index].root.path),
            )
            add(
                "Open Thread on GitHub",
                self._open_thread,
                enabled=bool(self._threads[index].root.url),
            )
        elif kind == "pending":
            add("Edit Pending Comment...", self._edit_pending)
            add("Delete Pending Comment...", self._delete_pending)
        elif kind == "file":
            add("Open File Differences", self._open_file_diff, enabled=self._diff is not None)
            add("Copy File Name", self._copy_file_name)
        elif kind == "check" and 0 <= index < len(self._checks):
            add(
                "Open Check on GitHub",
                self._open_selected_check,
                enabled=bool(self._checks[index].url),
            )
            add("Copy Check Details", self._copy_detail)
            add(
                "Re-request Check...",
                self._rerequest_selected_check,
                enabled=self._client.can_write and self._checks[index].check_run_id > 0,
            )
        else:
            add("Compose Review...", self._submit_review, enabled=self._submit_btn.IsEnabled())
            add(
                "Request Reviewers...",
                self._request_reviewers,
                enabled=self._reviewers_btn.IsEnabled(),
            )
            self._append_copilot_entries(add)
            add(
                self._draft_btn.GetLabel().replace("&", ""),
                self._toggle_draft,
                enabled=self._draft_btn.IsEnabled(),
            )
            add("Update Branch...", self._update_branch, enabled=self._update_btn.IsEnabled())
            self._append_merge_entries(add)
            add("React to Pull Request...", self._react_to_pull, enabled=self._client.can_write)
            add("View Timeline...", self._open_timeline)
            add("Copy Review Summary", self._copy_summary, enabled=self._state is not None)
            add(
                "Copy Pull Request Link",
                self._copy_pr_link,
                enabled=self._state is not None and bool(self._state.url),
            )
            add(
                "Open Pull Request on GitHub",
                self._open_pr,
                enabled=self._state is not None and bool(self._state.url),
            )
        return menu, menu_ids

    def _copy_text(self, value: str, success: str) -> None:
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(value))
        finally:
            wx.TheClipboard.Close()
        self._announce(success if copied else "Could not copy text.")

    def _copy_thread(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "thread" or not 0 <= index < len(self._threads):
            return
        self._copy_text(self._thread_detail.GetValue(), "Copied review conversation.")

    def _copy_file_name(self, _event: object) -> None:
        if self._node_kind()[0] == "file":
            self._copy_text(
                self._outline.GetItemText(self._outline.GetSelection()),
                "Copied file name.",
            )

    def _copy_thread_link(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind == "thread" and 0 <= index < len(self._threads):
            url = self._threads[index].root.url
            if url:
                self._copy_text(url, "Copied review thread link.")

    def _copy_pr_link(self, _event: object) -> None:
        if self._state is not None and self._state.url:
            self._copy_text(self._state.url, "Copied pull request link.")

    def _copy_detail(self, _event: object) -> None:
        self._copy_text(self._thread_detail.GetValue(), "Copied selected details.")

    def _open_file_diff(self, _event: object) -> None:
        if self._node_kind()[0] != "file" or self._diff is None:
            return
        self._show_file_diff(self._outline.GetItemText(self._outline.GetSelection()))

    def _open_thread_file_diff(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind == "thread" and 0 <= index < len(self._threads):
            root = self._threads[index].root
            self._show_file_diff(root.path, line=root.line, side=root.side)

    def _show_file_diff(self, path: str, *, line: int = 0, side: str = "RIGHT") -> None:
        if self._diff is None or not path:
            return
        from quill.ui.github_pr_diff_dialog import GitHubPullDiffDialog

        dialog = GitHubPullDiffDialog(
            self.dialog,
            self._client._provider,
            self._repo,
            self._diff,
            announce_cb=self._announce,
            initial_file=path,
            initial_line=line,
            initial_side=side,
            on_pending_changed=self._on_pending_changed,
        )
        dialog.show()

    def _open_selected_check(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "check" or not 0 <= index < len(self._checks):
            return
        check = self._checks[index]
        if check.url:
            self._announce(
                f"Opened check {check.name} in browser."
                if webbrowser.open(check.url)
                else f"Could not open check {check.name} in a browser."
            )

    def _open_thread(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "thread" or not 0 <= index < len(self._threads):
            return
        url = self._threads[index].root.url
        if url:
            self._announce(
                "Opened review thread in browser."
                if webbrowser.open(url)
                else "Could not open the review thread in a browser."
            )

    def _change_thread_resolution(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "thread" or not 0 <= index < len(self._threads):
            self._announce("Select a review conversation first.")
            return
        thread = self._threads[index]
        target = not thread.resolved
        if not thread.node_id or not (thread.can_resolve if target else thread.can_unresolve):
            self._announce("GitHub does not allow changing this thread's resolution.")
            return
        action = "resolve" if target else "reopen"
        if not self._confirm(
            f"{action.capitalize()} the selected review conversation?", "Review Thread"
        ):
            return
        self._run_action(
            lambda: self._client.change_thread_resolution(thread.node_id, resolved=target),
            "Review conversation resolved." if target else "Review conversation reopened.",
        )

    def _toggle_draft(self, _event: object) -> None:
        if self._state is None:
            self._announce("Review state is not loaded yet.")
            return
        draft = not self._state.draft
        action = "convert to a draft" if draft else "mark ready for review"
        if not self._confirm(f"Do you want to {action}?", "Pull Request Status"):
            return
        self._run_action(
            lambda: self._client.set_draft(self._repo, self._number, draft),
            f"Pull request #{self._number} updated.",
        )

    def _update_branch(self, _event: object) -> None:
        if not self._confirm(
            "Merge the base branch into this pull request's branch?",
            "Update Pull Request Branch",
        ):
            return
        self._run_action(
            lambda: self._client.update_branch(self._repo, self._number),
            f"Branch update requested for pull request #{self._number}.",
        )

    def _open_check(self, _event: object) -> None:
        index = self._check_list.GetSelection()
        if 0 <= index < len(self._checks) and self._checks[index].url:
            check = self._checks[index]
            if webbrowser.open(check.url):
                self._announce(f"Opened check {check.name} in browser.")
            else:
                self._announce(f"Could not open check {check.name} in a browser.")

    def _run_action(self, action: Callable[[], str | None], success_message: str) -> None:
        if self._loading:
            self._announce("Please wait for the current review operation to finish.")
            return
        self._loading = True
        self._status.SetLabel("Sending review action to GitHub…")

        def worker() -> None:
            wx = self._wx
            try:
                extra_message = action()
            except (GitHubReviewError, GitHubItemsError) as exc:
                wx.CallAfter(self._action_finished, None, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - unexpected provider errors must be visible
                wx.CallAfter(self._action_finished, None, f"Unexpected error: {exc}")
                return
            wx.CallAfter(
                self._action_finished,
                success_message + (extra_message or ""),
                None,
            )

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: review write action.

    def _submit_review(self, _event: object) -> None:
        if not self._client.can_write:
            self._announce("Sign in to GitHub to submit a review.")
            return
        from quill.ui.github_review_draft_dialog import GitHubReviewDraftDialog

        self._on_pending_changed()  # pick up comments the diff viewer added
        pending = self._pending_comments()
        current_sha = self._state.head_sha if self._state else ""
        stale = [comment for comment in pending if comment.head_sha != current_sha]
        if stale:
            self._announce(
                f"{len(stale)} pending line comment(s) were written on an older revision. "
                "Delete or rewrite them under Pending line comments, then compose the review."
            )
            return
        extra = {"pending_comment_count": len(pending)} if pending else {}
        draft = GitHubReviewDraftDialog(
            self.dialog,
            draft_store=self._review_draft_store,
            repository=self._repo,
            number=self._number,
            current_head_sha=current_sha,
            announce_cb=self._announce,
            **extra,
        ).show()
        if draft is None:
            return
        if draft.event == "request changes" and not self._confirm(
            "Submit a changes-requested review for this pull request?",
            "Request Changes",
        ):
            return

        def _submit() -> str:
            current_head = self._client.fetch_head_sha(self._repo, self._number)
            if draft.saved_head_sha and current_head != draft.saved_head_sha:
                raise GitHubReviewError(
                    "The pull request head changed while you were composing. "
                    "No review was submitted; reopen the draft against the current diff."
                )
            sent = ""
            if pending and current_head != current_sha:
                raise GitHubReviewError(
                    "The pull request head changed after your line comments were written. "
                    "No review was submitted; refresh and check the pending comments."
                )
            if pending:
                self._client._provider.submit_review_with_comments(
                    self._repo, self._number, draft.event, draft.body, pending, current_head
                )
                plural = "s" if len(pending) != 1 else ""
                sent = f" GitHub took its {len(pending)} line comment{plural} with it."
                if not self._line_comment_store.clear(self._repo, self._number):
                    sent += " They could not be cleared from this device; delete them there."
            else:
                self._client.submit_review(self._repo, self._number, draft.event, draft.body)
            if not self._review_draft_store.delete_review(self._repo, self._number):
                sent += " The review was submitted, but its local draft could not be cleared."
            return sent

        self._run_action(
            _submit,
            f"Review submitted on pull request #{self._number}.",
        )

    def _action_finished(self, success: str | None, error: str | None) -> None:
        if not dialog_alive(self.dialog):
            return
        self._loading = False
        if error is not None:
            self._status.SetLabel(f"Review action failed: {error}")
            self._announce(f"Review action failed: {error}")
            return
        self._status.SetLabel(success or "Review action completed.")
        self._announce(success or "Review action completed.")
        self._refresh()
