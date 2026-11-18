"""Close an issue for its reason, and make a branch for it (GH-D, GitHub PRD 16).

Close or Reopen on an open issue asks why, as GitHub does: completed, not
planned, or a duplicate of another issue, which it asks for by number. A pull
request has no reason, so it keeps the plain question. Create Branch for This
Issue makes a branch from the default branch, named as GitHub suggests
(``42-fix-the-parser``) in a box you can change, and links it to the issue,
so it is the issue's Development on GitHub and on the issue's sheet. The
work is :mod:`quill.core.github.issue_development`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["DEVELOPMENT_REASONS", "DEVELOPMENT_VERBS", "GitHubWorkbenchDevelopmentMixin"]

DEVELOPMENT_VERBS: dict[str, frozenset[str]] = {"create_branch": frozenset({"item"})}

DEVELOPMENT_REASONS: dict[str, str] = {
    "create_branch": "Create Branch is for an issue, while you are signed in.",
}


class GitHubWorkbenchDevelopmentMixin:
    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_create_branch(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubItem) and not row.is_pr

    def _close_issue_with_reason(self, ref: Any, row: GitHubItem) -> None:
        """Ask why, then close: completed, not planned, or a duplicate of an issue named."""
        from quill.core.github.issue_development import CLOSE_REASONS, close_issue

        labels = [reason.label for reason in CLOSE_REASONS]
        picked = self._choose(
            f"Close #{row.number}", f"Close #{row.number}, {row.title}, as:", labels
        )
        if picked < 0:
            return
        reason = CLOSE_REASONS[picked]
        duplicate_of = 0
        if reason.rest == "duplicate":
            typed = self._ask_text(
                "Duplicate Of", f"#{row.number} is a duplicate of issue number:"
            ).lstrip("#")
            if not typed:
                return
            if not typed.isdigit():
                self._say(f"{typed} is not an issue number.")
                return
            duplicate_of = int(typed)
        api, repository = self.github_api(), ref.instance
        self._background(
            f"close #{row.number}",
            lambda: close_issue(api, repository, row.number, reason, duplicate_of=duplicate_of),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_create_branch(self, ref: Any, row: object) -> None:
        from quill.core.github.issue_development import (
            branch_name_for,
            create_linked_branch,
            valid_branch_name,
        )

        assert isinstance(row, GitHubItem)
        name = self._ask_text(
            "Create Branch for This Issue",
            f"Branch name for #{row.number}, made from the default branch and linked to it:",
            value=branch_name_for(row.number, row.title),
        )
        if not name:
            return
        why = valid_branch_name(name)
        if why:
            self._say(why)
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "make the branch",
            lambda: create_linked_branch(api, repository, row.number, name),
            lambda said: self._say(f"{said} To work on it: git fetch, then git switch {name}."),
        )
