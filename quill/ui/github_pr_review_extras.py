"""Review window additions: one-line summary, since-my-review filter, timeline,
reactions and pending line comments.

The summary sentence sits at the top of the window and is said once when the
review opens. "Changed since my last review" narrows the outline's files to
the ones that changed since the commit you last reviewed. Pending line
comments, added from the diff, are listed in the outline until Compose Review
sends them with the review; each can be edited or deleted first.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.line_comment_drafts import LineCommentDraftStore, PendingLineComment
from quill.core.github.pr_summary import PullSummary
from quill.ui.dialog_contract import dialog_alive, show_modal_dialog

if TYPE_CHECKING:
    from quill.core.github.items_provider_review import ChangesSinceReview


class GitHubPullReviewExtrasMixin:
    """Handlers for the Wave 2 review controls; the dialog builds the controls."""

    def _init_review_extras(self) -> None:
        self._summary_info: PullSummary | None = None
        self._summary_spoken = False
        self._since_files: frozenset[str] | None = None
        self._since_head = ""
        self._since_generation = 0
        self._line_comment_store = LineCommentDraftStore.load(
            getattr(self._client._provider, "token", None)
        )

    # -- pending line comments ----------------------------------------

    def _pending_comments(self) -> tuple[PendingLineComment, ...]:
        return self._line_comment_store.pending(self._repo, self._number)

    def _on_pending_changed(self) -> None:
        # The diff viewer saved through its own store; read the file again.
        self._line_comment_store = LineCommentDraftStore.load(
            getattr(self._client._provider, "token", None)
        )
        if self._state is not None and dialog_alive(self.dialog):
            self._render_outline()

    def _selected_pending(self) -> PendingLineComment | None:
        kind, index = self._node_kind()
        pending = self._pending_comments()
        return pending[index] if kind == "pending" and 0 <= index < len(pending) else None

    def _edit_pending(self, _event: object) -> None:
        comment = self._selected_pending()
        if comment is None:
            self._announce("Select a pending line comment first.")
            return
        wx = self._wx
        dialog = wx.TextEntryDialog(
            self.dialog,
            f"Comment on {comment.anchor.describe()}:",
            "Edit Pending Comment",
            value=comment.body,
            style=wx.TextEntryDialogStyle | wx.TE_MULTILINE,
        )
        try:
            if show_modal_dialog(dialog, "Edit Pending Comment", announce=self._announce) != (
                wx.ID_OK
            ):
                return
            body = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not body:
            self._announce("A comment needs some text; it was not changed.")
            return
        if not self._line_comment_store.update(self._repo, self._number, comment.id, body):
            self._announce("Could not save the change on this device.")
            return
        self._announce("Pending comment changed. It is still not sent.")
        self._render_outline()

    def _delete_pending(self, _event: object) -> None:
        comment = self._selected_pending()
        if comment is None:
            self._announce("Select a pending line comment first.")
            return
        if not self._confirm(
            f"Delete the pending comment on {comment.anchor.describe()}? It was never sent, "
            "so it cannot be recovered.",
            "Delete Pending Comment",
        ):
            return
        if not self._line_comment_store.remove(self._repo, self._number, comment.id):
            self._announce("Could not delete the pending comment.")
            return
        self._announce("Pending comment deleted.")
        self._render_outline()

    # -- one-line summary ---------------------------------------------

    def _fetch_summary(self, head_ref: str) -> PullSummary | None:
        """Worker-thread helper: the summary, or None when it cannot be read."""
        provider = self._client._provider
        fetch = getattr(provider, "fetch_pull_summary", None)
        if fetch is None or not getattr(provider, "is_authenticated", False):
            return None
        try:
            return fetch(self._repo, self._number, head_ref=head_ref)
        except GitHubItemsError as exc:
            return PullSummary(self._repo, self._number, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - the rest of the review still loads
            return PullSummary(self._repo, self._number, error=f"unexpected error: {exc}")

    def _apply_summary(self, summary: PullSummary | None) -> str:
        """Show the sentence; return it the first time, so the caller says it once."""
        self._summary_info = summary
        if summary is None:
            self._one_line.SetLabel("Sign in to GitHub to hear the one-line summary.")
            return ""
        sentence = summary.sentence()
        self._one_line.SetLabel(sentence)
        if self._summary_spoken:
            return ""
        self._summary_spoken = True
        return sentence

    # -- changed since my last review ---------------------------------

    def _toggle_since_filter(self, _event: object) -> None:
        self._since_generation += 1
        if not self._since_check.GetValue():
            self._since_files = None
            self._since_head = ""
            self._render_outline()
            self._announce("Showing every changed file.")
            return
        if self._state is None or not self._state.head_sha:
            self._since_check.SetValue(False)
            self._announce("The review is still loading; try again in a moment.")
            return
        fetch = getattr(self._client._provider, "fetch_changes_since_my_review", None)
        if fetch is None or not self._client.can_write:
            self._since_check.SetValue(False)
            self._announce("Sign in to GitHub to compare with your last review.")
            return
        self._start_since_load(fetch, self._state.head_sha)

    def _start_since_load(self, fetch: object, head: str) -> None:
        generation = self._since_generation
        self._status.SetLabel("Comparing with your last review…")

        def worker() -> None:
            try:
                result = fetch(self._repo, self._number, head)  # type: ignore[operator]
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._since_failed, generation, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - visible, never swallowed
                self._wx.CallAfter(self._since_failed, generation, f"Unexpected error: {exc}")
                return
            self._wx.CallAfter(self._since_loaded, generation, head, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: compare read.

    def _since_loaded(self, generation: int, head: str, result: ChangesSinceReview) -> None:
        if not dialog_alive(self.dialog) or generation != self._since_generation:
            return  # the box was changed again, or the dialog closed, meanwhile
        if not self._since_check.GetValue():
            return
        sentence = result.sentence()
        if not result.reviewed or result.commit_missing:
            self._since_files = None
        else:
            self._since_files = frozenset(result.files)
        self._since_head = head
        self._render_outline()
        self._status.SetLabel(sentence)
        self._announce(sentence)

    def _since_failed(self, generation: int, message: str) -> None:
        if not dialog_alive(self.dialog) or generation != self._since_generation:
            return
        self._since_check.SetValue(False)
        self._since_files = None
        self._status.SetLabel(f"Could not compare with your last review. {message}")
        self._announce(f"Could not compare with your last review. {message}")

    def _recheck_since_filter(self) -> None:
        """After a refresh: compare again if the head moved under an active filter."""
        if self._state is None or not self._since_check.GetValue():
            return
        if self._since_head and self._since_head != self._state.head_sha:
            fetch = getattr(self._client._provider, "fetch_changes_since_my_review", None)
            if fetch is not None:
                self._since_generation += 1
                self._start_since_load(fetch, self._state.head_sha)

    # -- timeline and reactions ---------------------------------------

    def _open_timeline(self, _event: object) -> None:
        from quill.ui.github_timeline_dialog import GitHubTimelineDialog

        GitHubTimelineDialog(
            self.dialog,
            self._client._provider,
            self._repo,
            self._number,
            kind="pull request",
            announce_cb=self._announce,
        ).show()

    def _react_to_pull(self, _event: object) -> None:
        from quill.ui.github_reactions_ui import start_reaction_flow

        start_reaction_flow(
            self.dialog,
            self._client._provider,
            self._repo,
            "issue",
            self._number,
            what=f"pull request #{self._number}",
            announce=self._announce,
        )

    def _react_to_thread_comment(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "thread" or not 0 <= index < len(self._threads):
            self._announce("Select a review conversation first.")
            return
        comments = self._threads[index].comments
        chosen = comments[0]
        if len(comments) > 1:
            wx = self._wx
            labels = [
                f"{comment.author}: {(comment.body.strip().splitlines() or [''])[0][:70]}"
                for comment in comments
            ]
            dialog = wx.SingleChoiceDialog(
                self.dialog, "Which comment do you want to react to?", "React", labels
            )
            try:
                if show_modal_dialog(dialog, "React", announce=self._announce) != wx.ID_OK:
                    return
                picked = dialog.GetSelection()
            finally:
                dialog.Destroy()
            if not 0 <= picked < len(comments):
                return
            chosen = comments[picked]
        from quill.ui.github_reactions_ui import start_reaction_flow

        start_reaction_flow(
            self.dialog,
            self._client._provider,
            self._repo,
            "review_comment",
            chosen.id,
            what=f"{chosen.author}'s comment",
            announce=self._announce,
            on_done=self._refresh,
        )


__all__ = ["GitHubPullReviewExtrasMixin"]
