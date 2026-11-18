"""An issue's field values, and deleting an issue, from its row (GitHub PRD 14 and 22.11).

The work is in :mod:`quill.core.github.issue_admin`. **Issue Fields...** lists
every field the owner defines with this issue's value (or why it has none);
choosing one asks for its new value the way its kind needs: a choice for a
single select, a date as year-month-day, a number, or text, with Clear to take
the value away. **Delete Issue...** asks for the issue's number typed out,
because GitHub cannot bring a deleted issue back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["ISSUE_ADMIN_REASONS", "ISSUE_ADMIN_VERBS", "GitHubWorkbenchIssueAdminMixin"]

ISSUE_ADMIN_VERBS: dict[str, frozenset[str]] = {
    "issue_fields": frozenset({"item"}),
    "delete_issue": frozenset({"item"}),
}

ISSUE_ADMIN_REASONS: dict[str, str] = {
    "issue_fields": "Issue fields belong to an issue, while you are signed in.",
    "delete_issue": "Delete Issue is for an issue, while you are signed in as an admin.",
}

_KIND = {"single_select": "a choice", "date": "a date", "number": "a number", "text": "text"}


class GitHubWorkbenchIssueAdminMixin:
    frame: Any
    items: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]
    _repo_for: Callable[[Any], str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_issue_admin(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubItem) and not row.is_pr

    _fits_issue_fields = _fits_issue_admin
    _fits_delete_issue = _fits_issue_admin

    def _do_issue_fields(self, ref: Any, row: object) -> None:
        from quill.core.github.issue_admin import read_issue_fields

        assert isinstance(row, GitHubItem)
        repo, number, api = self._repo_for(ref), row.number, self.github_api()

        def chosen(found: Any) -> None:
            if not found.values:
                self._say(f"{repo.split('/', 1)[0]} defines no issue fields.")
                return
            picked = self._choose(
                f"Issue Fields of #{number}",
                f"#{number}'s fields. Choose one to set or clear it:",
                [value.words() for value in found.values],
            )
            if picked >= 0:
                self._change_field(api, repo, number, found.values[picked], found.choices)

        self._background(
            "read the issue fields", lambda: read_issue_fields(api, repo, number), chosen
        )

    def _change_field(
        self, api: Any, repo: str, number: int, field: Any, choices: dict[str, tuple[str, ...]]
    ) -> None:
        from quill.core.github.issue_admin import set_field_value

        if field.state in ("hidden", "unsupported", "unavailable"):
            self._say(f"{field.name} cannot be changed here: {field.words()}.")
            return
        offered = choices.get(field.field_id, ())
        title = f"{field.name} on #{number}"
        if field.data_type == "single_select" and offered:
            options = [*offered, "Clear it"]
            picked = self._choose(title, f"{field.name}:", options)
            if picked < 0:
                return
            if picked == len(offered):
                self._clear(api, repo, number, field)
                return
            answer = offered[picked]
        else:
            if field.state == "value":
                act = self._choose(title, field.words(), ["Change it...", "Clear it"])
                if act < 0:
                    return
                if act == 1:
                    self._clear(api, repo, number, field)
                    return
            answer = self._ask_text(
                title,
                f"{field.name}, {_KIND.get(field.data_type, 'text')}:",
                value=", ".join(field.values),
            )
            if not answer:
                return
        self._background(
            f"set {field.name}",
            lambda: set_field_value(api, repo, number, field, answer, offered),
            lambda said: self._say(str(said)),
        )

    def _clear(self, api: Any, repo: str, number: int, field: Any) -> None:
        from quill.core.github.issue_admin import clear_field_value

        self._background(
            f"clear {field.name}",
            lambda: clear_field_value(api, repo, number, field),
            lambda said: self._say(str(said)),
        )

    def _do_delete_issue(self, ref: Any, row: object) -> None:
        from quill.core.github.issue_admin import delete_issue

        assert isinstance(row, GitHubItem)
        repo, number = self._repo_for(ref), row.number
        typed = self._ask_text(
            "Delete Issue",
            f"Deleting #{number} {row.title!r} removes it, its comments and its history for "
            "good; GitHub cannot bring it back. Closing it keeps everything. Type its number "
            "to delete it:",
        )
        if not typed:
            return
        if typed.strip().lstrip("#") != str(number):
            self._say("That is not the issue's number, so nothing was deleted.")
            return
        api = self.github_api()

        def done(said: Any) -> None:
            self._say(str(said))
            self.frame.reload()

        self._background(f"delete #{number}", lambda: delete_issue(api, repo, number), done)
