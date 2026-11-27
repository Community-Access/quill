"""Find a Person or Organization, Tracked Accounts and Account Actions in the Workbench.

* **Go > Find a Person or Organization...** (``Ctrl+Alt+E``) opens the type-ahead
  window (:mod:`quill.ui.github_find_account_dialog`).
* **People > Tracked Accounts** lists the accounts you kept, favorites first,
  then your favorite repositories (:mod:`quill.core.github.tracked_accounts`).
* **Account Actions...** on a person or organization row opens the same
  actions for that account: repositories, track, favorite, follow.

The work is :class:`quill.core.github.account_desk.AccountDesk`; this mixin only
builds it for the signed-in account and hands the window its host callbacks.
A write to GitHub (follow, star) is held to the account's Workbench level at
the moment it is sent, so a Read Only account can still search and look.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["ACCOUNT_REASONS", "ACCOUNT_VERBS", "GitHubWorkbenchAccountsMixin"]

ACCOUNT_VERBS: dict[str, frozenset[str]] = {
    "find_account": frozenset({"view"}),
    "account_actions": frozenset({"person", "organization"}),
}

ACCOUNT_REASONS: dict[str, str] = {
    "find_account": "Find a Person or Organization is for the Workbench, while you are signed in.",
    "account_actions": "Account Actions is for a person or an organization row.",
}


class GitHubWorkbenchAccountsMixin:
    frame: Any
    items: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    github_api: Callable[[], Any]
    access_level: Callable[[], Any]

    def _fits_find_account(self, _row: object) -> bool:
        return self.signed_in

    def _fits_account_actions(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and bool(row.key or row.label)

    def account_desk(self) -> Any:
        from quill.core.github.account_desk import AccountDesk
        from quill.core.github.navigation_state import account_key_for_token
        from quill.core.github.permissions import WriteTier
        from quill.core.github.tracked_accounts import TrackedAccounts
        from quill.core.github.write_gate import refusal

        store = TrackedAccounts.load(account_key_for_token(getattr(self.items, "token", None)))

        def refuse(what: str) -> str:
            return refusal(what, WriteTier.ORGANIZING, self.access_level())

        return AccountDesk(self.github_api(), store, refuse=refuse)

    @staticmethod
    def _open_url(url: str) -> None:
        import webbrowser

        webbrowser.open(url, new=2)

    def _add_repo_to_list(self, repo: str) -> None:
        from quill.core.github.explore_models import ExploreRow as Row

        # Through the checked dispatcher, so the account's level is held to like any command.
        self.run(  # type: ignore[attr-defined]
            "github.workbench.star_lists",
            None,
            Row(repo, "", f"https://github.com/{repo}", repo, "repo", repo),
        )

    def _do_find_account(self, _ref: Any, _row: object, start: str = "") -> None:
        from quill.ui.github_find_account_dialog import FindAccountDialog

        FindAccountDialog(
            self.frame.frame,
            self.account_desk(),
            say=self._say,
            background=self._background,
            open_url=self._open_url,
            add_to_list=self._add_repo_to_list,
        ).show(start)

    def _do_account_actions(self, ref: Any, row: object) -> None:
        """The row's account, looked up by its login so the same window acts on it."""
        if not isinstance(row, ExploreRow):
            return
        login = (row.key or row.label).split(" ", 1)[0].rstrip(":,")
        self._do_find_account(ref, row, login)
