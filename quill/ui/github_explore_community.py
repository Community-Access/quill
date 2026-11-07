"""Security alert triage and Discussion actions in Explore GitHub (QUILL and QUILL Lite).

In the security views, Dismiss Alert asks for one of GitHub's own reasons for
that kind of alert and an optional comment, then asks to confirm; Reopen Alert
asks to confirm. In the Discussions view, Open Discussion Thread shows the
comments and replies, where you can reply and mark the answer, and New
Discussion starts one in a category. Each change is reported only when GitHub
confirms it.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.github.alert_triage import DISMISS_REASONS, parse_alert_key
from quill.core.github.explore import GitHubExploreError
from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from quill.core.github.explore import ExploreRow

__all__ = ["GitHubExploreCommunityMixin"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


def _explore_error(work: Callable[[], object]) -> Callable[[], None]:
    """Run *work*, turning a provider error into the one Explore reports."""

    def run() -> None:
        try:
            work()
        except GitHubItemsError as exc:
            raise GitHubExploreError(_message(exc)) from exc

    return run


class GitHubExploreCommunityMixin:
    """Alert triage and Discussions actions for ``GitHubExploreDialog``."""

    def _add_community_actions(self, add: Callable[[str, Callable[[], None]], None]) -> None:
        """Context-menu rows for the selected row and the current view."""
        row = self._selected()
        signed_in = self._client._provider.is_authenticated
        if row is not None and row.kind == "security" and signed_in and parse_alert_key(row.key):
            if self._view_key() == "security":
                add("Dismiss Alert...", lambda: self._dismiss_alert(row))
            else:
                add("Reopen Alert...", lambda: self._reopen_alert(row))
        if row is not None and row.kind == "discussion" and row.key.isdecimal():
            add("Open Discussion Thread...", lambda: self._open_discussion_thread(row))
        if self._view_key() == "discussions" and signed_in:
            add("New Discussion...", self._new_discussion)

    # -- security alerts --------------------------------------------------------

    def _dismiss_alert(self, row: ExploreRow) -> None:
        parsed = parse_alert_key(row.key)
        if parsed is None:
            return
        kind, number = parsed
        wx = self._wx
        reasons = DISMISS_REASONS[kind.key]
        from quill.ui.dialog_contract import show_modal_dialog

        with wx.SingleChoiceDialog(
            self.dialog,
            f"Why are you dismissing {kind.label} alert #{number}?",
            "Dismiss Alert",
            [words for _value, words in reasons],
        ) as picker:
            if show_modal_dialog(picker, "Dismiss Alert", announce=self._announce) != wx.ID_OK:
                self._announce("Cancelled; nothing was sent to GitHub.")
                return
            reason, words = reasons[max(0, picker.GetSelection())]
        comment = self._prompt("Comment for the dismissal (optional):", "Dismiss Alert")
        if comment is None:
            self._announce("Cancelled; nothing was sent to GitHub.")
            return
        if not self._confirm(
            f"Dismiss {kind.label} alert #{number} in {row.repo} as {words.lower()}? "
            "Everyone with access sees it as dismissed.",
            "Dismiss Alert",
        ):
            self._announce("Cancelled; nothing was sent to GitHub.")
            return
        provider = self._client._provider
        self._run_write(
            _explore_error(
                lambda: provider.set_security_alert_state(
                    row.repo, kind.key, number, dismiss=True, reason=reason, comment=comment
                )
            ),
            f"Dismissed {kind.label} alert #{number}.",
        )

    def _reopen_alert(self, row: ExploreRow) -> None:
        parsed = parse_alert_key(row.key)
        if parsed is None:
            return
        kind, number = parsed
        if not self._confirm(f"Reopen {kind.label} alert #{number} in {row.repo}?", "Reopen Alert"):
            self._announce("Cancelled; nothing was sent to GitHub.")
            return
        provider = self._client._provider
        self._run_write(
            _explore_error(
                lambda: provider.set_security_alert_state(row.repo, kind.key, number, dismiss=False)
            ),
            f"Reopened {kind.label} alert #{number}.",
        )

    # -- discussions ------------------------------------------------------------

    def _open_discussion_thread(self, row: ExploreRow) -> None:
        from quill.ui.github_discussion_dialog import GitHubDiscussionDialog

        GitHubDiscussionDialog(
            self.dialog,
            self._client._provider,
            repo=row.repo,
            number=int(row.key),
            announce_cb=self._announce,
        ).show()
        self._load(None)

    def _new_discussion(self) -> None:
        repo = self._repo.GetValue().strip()
        if "/" not in repo:
            self._announce("Enter a repository as owner/repo first.")
            return
        provider = self._client._provider
        self._status.SetLabel("Loading discussion categories...")

        def worker() -> None:
            try:
                repo_id, categories = provider.fetch_discussion_categories(repo)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._categories_failed, _message(exc))
                return
            self._wx.CallAfter(self._categories_loaded, repo, repo_id, categories)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: category read.

    def _categories_failed(self, error: str) -> None:
        if dialog_alive(self.dialog):
            self._status.SetLabel(error)
            self._announce(error)

    def _categories_loaded(self, repo: str, repo_id: str, categories: list[object]) -> None:
        if not dialog_alive(self.dialog):
            return
        self._status.SetLabel("")
        from quill.ui.github_discussion_dialog import NewDiscussionDialog

        values = NewDiscussionDialog(self.dialog, categories, announce_cb=self._announce).show()
        if values is None:
            self._announce("Cancelled; nothing was sent to GitHub.")
            return
        category, title, body = values
        provider = self._client._provider
        self._run_write(
            _explore_error(lambda: provider.create_discussion(repo_id, category.id, title, body)),
            f"Started the discussion {title} in {category.name}.",
        )
