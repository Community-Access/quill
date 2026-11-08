"""Issue housekeeping in the GitHub Items viewer's context menu (Wave 4).

On an issue or pull request row, a Housekeeping submenu offers Lock
Conversation (with a reason) and Unlock Conversation; on an issue it also
offers Transfer Issue, Pin Issue, Unpin Issue, Set Issue Type and Reorder
Sub-issues. GitHub API Rate Limit (Ctrl+Shift+L) is in the context menu too.

Every write asks first where it cannot be undone from here (a transfer), runs
off the UI thread, and says only what GitHub confirmed. A read that a prompt
waits on (the issue types, the sub-issues) carries a generation token, so a
slow answer cannot open a prompt after a newer one. QUILL and QUILL Lite share
this, as they share the viewer.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from quill.core.github.issue_housekeeping import LOCK_REASONS, GitHubIssueHousekeeping
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubItem
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubItemsHousekeepingMixin"]


def _words(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubItemsHousekeepingMixin:
    """Lock, transfer, pin, issue type, sub-issue order, and the rate-limit readout."""

    def _housekeeping(self) -> GitHubIssueHousekeeping:
        return GitHubIssueHousekeeping(getattr(self._provider, "token", None))

    def _add_issue_housekeeping(self, menu: Any, model: object) -> None:
        """Append a Housekeeping submenu for *model* when it is an issue or PR."""
        if not isinstance(model, GitHubItem) or not self._provider.is_authenticated:
            return
        wx = self._wx
        sub = wx.Menu()
        rows: list[tuple[str, Callable[[], None]]] = [
            ("Lock Conversation...", lambda: self._lock_item(model)),
            ("Unlock Conversation", lambda: self._unlock_item(model)),
        ]
        if not model.is_pr:
            rows += [
                ("Transfer Issue...", lambda: self._transfer_item(model)),
                ("Pin Issue", lambda: self._pin_item(model, True)),
                ("Unpin Issue", lambda: self._pin_item(model, False)),
                ("Set Issue Type...", lambda: self._set_item_type(model)),
                ("Reorder Sub-issues...", lambda: self._reorder_sub_issues(model)),
            ]
        for label, action in rows:
            item_id = wx.NewIdRef()
            sub.Append(item_id, label)
            sub.Bind(wx.EVT_MENU, lambda _event, callback=action: callback(), id=item_id)
        menu.AppendSubMenu(sub, f"Housekeeping for #{model.number}")

    # -- Background ------------------------------------------------------------

    def _housekeeping_run(
        self,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        *,
        latest_only: bool = False,
        busy: str = "",
    ) -> None:
        """Run *work* off the UI thread and hand its result to *done* on it.

        *latest_only* drops an answer that a newer request has superseded (for
        reads a prompt waits on); a write's answer is always said.
        """
        token = getattr(self, "_housekeeping_token", 0) + 1
        self._housekeeping_token = token
        if busy:
            self._set_status(busy, announce=False)

        def finish(result: Any) -> None:
            if not dialog_alive(self.dialog):
                return
            if latest_only and token != self._housekeeping_token:
                return
            if isinstance(result, GitHubItemsError):
                self._set_status(_words(result))
                return
            done(result)

        def worker() -> None:
            try:
                result: Any = work()
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say any provider failure
                result = GitHubItemsError(f"The GitHub action failed: {exc}")
            self._wx.CallAfter(finish, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented action.

    def _housekeeping_write(self, work: Callable[[], str], *, then_reload: bool = False) -> None:
        def said(message: str) -> None:
            self._set_status(message)
            if then_reload:
                self._reload()

        self._housekeeping_run(work, said, busy="Sending to GitHub...")

    # -- Lock --------------------------------------------------------------------

    def _lock_item(self, model: GitHubItem) -> None:
        wx = self._wx
        repo, number = self._repo, model.number
        labels = [label for _key, label in LOCK_REASONS]
        with wx.SingleChoiceDialog(
            self.dialog,
            f"Lock the conversation on #{number}? Only collaborators can comment while it "
            "is locked. Choose the reason GitHub shows:",
            "Lock Conversation",
            labels,
        ) as dialog:
            if self._show_modal(dialog, "Lock Conversation") != wx.ID_OK:
                self._announce("Cancelled; nothing was sent to GitHub.")
                return
            reason, words = LOCK_REASONS[dialog.GetSelection()]

        def work() -> str:
            self._housekeeping().lock(repo, number, reason)
            why = f" as {words.lower()}" if reason else ""
            return f"Locked #{number}{why}. Only collaborators can comment now."

        self._housekeeping_write(work)

    def _unlock_item(self, model: GitHubItem) -> None:
        repo, number = self._repo, model.number

        def work() -> str:
            self._housekeeping().unlock(repo, number)
            return f"Unlocked #{number}; anyone can comment again."

        self._housekeeping_write(work)

    # -- Transfer and pin ----------------------------------------------------------

    def _transfer_item(self, model: GitHubItem) -> None:
        wx = self._wx
        repo, number = self._repo, model.number
        with wx.TextEntryDialog(
            self.dialog,
            f"Move issue #{number} to which repository (owner/name)? It must have the same "
            "owner, and you need write access to both.",
            "Transfer Issue",
        ) as dialog:
            if self._show_modal(dialog, "Transfer Issue") != wx.ID_OK:
                return
            target = dialog.GetValue().strip()
        if not target:
            return
        if not self._confirm_action(
            f"Transfer issue #{number}, {model.title!r}, from {repo} to {target}? Labels and "
            "milestones that do not exist there are dropped, and assignees who cannot be "
            "assigned there are removed.",
            "Transfer Issue",
        ):
            self._announce("Cancelled; the issue was not moved.")
            return
        self._housekeeping_write(
            lambda: self._housekeeping().transfer(repo, number, target), then_reload=True
        )

    def _pin_item(self, model: GitHubItem, pinned: bool) -> None:
        repo, number = self._repo, model.number

        def work() -> str:
            self._housekeeping().set_pinned(repo, number, pinned)
            if pinned:
                return f"Pinned #{number} to the top of {repo}'s issues."
            return f"Unpinned #{number}."

        self._housekeeping_write(work)

    # -- Issue type ----------------------------------------------------------------

    def _set_item_type(self, model: GitHubItem) -> None:
        repo, number = self._repo, model.number

        def choose(types: Any) -> None:
            wx = self._wx
            if not types:
                self._set_status(
                    f"{repo} has no issue types. An organization sets them up for its repositories."
                )
                return
            labels = ["No type", *[issue_type.label for issue_type in types]]
            with wx.SingleChoiceDialog(
                self.dialog, f"Issue type for #{number}:", "Set Issue Type", labels
            ) as dialog:
                if self._show_modal(dialog, "Set Issue Type") != wx.ID_OK:
                    return
                index = dialog.GetSelection()
            chosen = types[index - 1] if index > 0 else None

            def work() -> str:
                now = self._housekeeping().set_issue_type(repo, number, chosen)
                return f"Issue #{number} is now a {now}." if now else f"#{number} has no type now."

            self._housekeeping_write(work)

        self._housekeeping_run(
            lambda: self._housekeeping().issue_types(repo),
            choose,
            latest_only=True,
            busy="Reading the repository's issue types...",
        )

    # -- Sub-issues ----------------------------------------------------------------

    def _reorder_sub_issues(self, model: GitHubItem) -> None:
        repo, number = self._repo, model.number
        housekeeping = self._housekeeping()

        def open_dialog(order: Any) -> None:
            if not order:
                self._set_status(f"#{number} has no sub-issues to reorder.")
                return
            if len(order) == 1:
                self._set_status(f"#{number} has one sub-issue; there is nothing to reorder.")
                return
            from quill.ui.github_sub_issue_order_dialog import SubIssueOrderDialog

            SubIssueOrderDialog(
                self.dialog,
                housekeeping,
                repo=repo,
                parent_number=number,
                order=list(order),
                announce_cb=self._announce,
            ).show()

        self._housekeeping_run(
            lambda: housekeeping.sub_issues(repo, number),
            open_dialog,
            latest_only=True,
            busy=f"Reading the sub-issues of #{number}...",
        )

    # -- Rate limit ----------------------------------------------------------------

    def _show_api_rate_limit(self) -> None:
        from quill.core.github.rate_limits import GitHubRateLimitError, fetch_rate_limit_report

        token = getattr(self._provider, "token", None)

        def work() -> Any:
            try:
                return fetch_rate_limit_report(token)
            except GitHubRateLimitError as exc:
                raise GitHubItemsError(_words(exc)) from exc

        self._housekeeping_run(
            work,
            lambda report: self._set_status(report.sentence()),
            latest_only=True,
            busy="Reading GitHub's rate limit...",
        )
