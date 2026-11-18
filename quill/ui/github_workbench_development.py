"""Close an issue for its reason, make a branch for it, and work its task list (GH-D).

Close or Reopen on an open issue asks why, as GitHub does: completed, not
planned, or a duplicate of another issue, which it asks for by number. A pull
request has no reason, so it keeps the plain question. Create Branch for This
Issue makes a branch from the default branch, named as GitHub suggests
(``42-fix-the-parser``) in a box you can change, and links it to the issue,
so it is the issue's Development on GitHub and on the issue's sheet. Check or
Uncheck a Task turns over one ``- [ ]`` item of the issue's body, and Convert
Tasks to Sub-issues makes each plain item an issue, a sub-issue of this one,
and links its line to it. Both read the body again before writing and save
nothing if somebody changed it meanwhile. The work is
:mod:`quill.core.github.issue_development`. A pull request's patch, revert and
conflicts come in through :class:`GitHubWorkbenchPullToolsMixin`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_dry_run import (
    DRY_RUN_REASONS,
    DRY_RUN_VERBS,
    GitHubWorkbenchDryRunMixin,
    failure_sentence,
)
from quill.ui.github_workbench_inbox_rules import (
    INBOX_RULE_REASONS,
    INBOX_RULE_VERBS,
    GitHubWorkbenchInboxRulesMixin,
)
from quill.ui.github_workbench_merge import (
    MERGE_REASONS,
    MERGE_VERBS,
    GitHubWorkbenchMergeMixin,
)
from quill.ui.github_workbench_practice import (
    PRACTICE_REASONS,
    PRACTICE_VERBS,
    GitHubWorkbenchPracticeMixin,
)
from quill.ui.github_workbench_pull_tools import (
    PULL_TOOL_REASONS,
    PULL_TOOL_VERBS,
    GitHubWorkbenchPullToolsMixin,
)
from quill.ui.github_workbench_tier2 import (
    TIER2_REASONS,
    TIER2_VERBS,
    GitHubWorkbenchTier2Mixin,
)

__all__ = [
    "DEVELOPMENT_REASONS",
    "DEVELOPMENT_VERBS",
    "GitHubWorkbenchDevelopmentMixin",
    "failure_sentence",
]

DEVELOPMENT_VERBS: dict[str, frozenset[str]] = {
    "create_branch": frozenset({"item"}),
    "edit_tasks": frozenset({"item"}),
    "convert_tasks": frozenset({"item"}),
    **PULL_TOOL_VERBS,
    **MERGE_VERBS,
    **INBOX_RULE_VERBS,
    **DRY_RUN_VERBS,
    **PRACTICE_VERBS,
    **TIER2_VERBS,
}

DEVELOPMENT_REASONS: dict[str, str] = {
    "create_branch": "Create Branch is for an issue, while you are signed in.",
    "edit_tasks": "Task lists are for an issue, while you are signed in.",
    "convert_tasks": "Task lists are for an issue, while you are signed in.",
    **PULL_TOOL_REASONS,
    **MERGE_REASONS,
    **INBOX_RULE_REASONS,
    **DRY_RUN_REASONS,
    **PRACTICE_REASONS,
    **TIER2_REASONS,
}


class GitHubWorkbenchDevelopmentMixin(
    GitHubWorkbenchPullToolsMixin,
    GitHubWorkbenchMergeMixin,
    GitHubWorkbenchInboxRulesMixin,
    GitHubWorkbenchDryRunMixin,
    GitHubWorkbenchPracticeMixin,
    GitHubWorkbenchTier2Mixin,
):
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

    # -- task lists ------------------------------------------------------------

    _fits_edit_tasks = _fits_create_branch
    _fits_convert_tasks = _fits_create_branch

    def _issue_body(self, repository: str, number: int) -> str:
        data = self.github_api().rest("GET", f"/repos/{repository}/issues/{number}").data
        return str((data or {}).get("body") or "")

    def _save_body(self, repository: str, number: int, before: str, after: str) -> None:
        """Write *after* only when the issue still says *before*; nobody's edit is lost."""
        from quill.core.github.issue_development import IssueDevelopmentError

        if self._issue_body(repository, number) != before:
            raise IssueDevelopmentError(
                f"#{number} was changed on GitHub while you chose; nothing was saved. Try again."
            )
        self.github_api().rest(
            "PATCH", f"/repos/{repository}/issues/{number}", body={"body": after}
        )

    def _do_edit_tasks(self, ref: Any, row: object) -> None:
        """Check or Uncheck a Task: pick one task of the issue's list, and turn it over."""
        from quill.core.github.issue_development import task_items, toggle_task

        assert isinstance(row, GitHubItem)
        repository, number = ref.instance, row.number

        def chosen(body: str) -> None:
            items = task_items(body)
            if not items:
                self._say(f"#{number} has no task list.")
                return
            picked = self._choose(
                f"Tasks in #{number}",
                f"{len(items)} tasks. Enter checks or unchecks the one you choose:",
                [item.sentence for item in items],
            )
            if picked < 0:
                return
            item = items[picked]
            after = toggle_task(body, item)
            word = "Unchecked" if item.checked else "Checked"
            self._background(
                "save the task list",
                lambda: self._save_body(repository, number, body, after),
                lambda _done: (self._say(f"{word}: {item.text}."), self.frame.reload()),
            )

        self._background("read the task list", lambda: self._issue_body(repository, number), chosen)

    def _do_convert_tasks(self, ref: Any, row: object) -> None:
        """Convert Tasks to Sub-issues: each plain task becomes an issue, linked in place."""
        from quill.core.github.issue_development import convertible

        assert isinstance(row, GitHubItem)
        repository, number = ref.instance, row.number

        def confirm(body: str) -> None:
            items = convertible(body)
            if not items:
                self._say(f"#{number} has no tasks that are not issues already.")
                return
            names = "; ".join(item.text for item in items[:10])
            more = f", and {len(items) - 10} more" if len(items) > 10 else ""
            if not self._confirm(
                "Convert Tasks to Sub-issues",
                f"Make {len(items)} sub-issues of #{number}: {names}{more}? Each task line "
                "becomes a link to its issue, checked or not as it was.",
            ):
                return
            self._background(
                "make the sub-issues",
                lambda: self._convert(repository, number, body, items),
                lambda said: (self._say(str(said)), self.frame.reload()),
            )

        self._background(
            "read the task list", lambda: self._issue_body(repository, number), confirm
        )

    def _convert(self, repository: str, number: int, body: str, items: list[Any]) -> str:
        """Make each issue and add it as a sub-issue; link the ones made, say any refused."""
        from quill.core.github.issue_development import linked_body

        api = self.github_api()
        made: dict[int, int] = {}
        refused: list[str] = []
        for item in items:
            try:
                issue = api.rest(
                    "POST", f"/repos/{repository}/issues", body={"title": item.text[:256]}
                ).data
                api.rest(
                    "POST",
                    f"/repos/{repository}/issues/{number}/sub_issues",
                    body={"sub_issue_id": int(issue["id"])},
                )
                made[item.line] = int(issue["number"])
            except Exception as exc:  # noqa: BLE001 - one refusal never stops the rest
                refused.append(f"{item.text}: {exc}")
        if made:
            self._save_body(repository, number, body, linked_body(body, made))
        said = f"Made {len(made)} sub-issues of #{number}: " + ", ".join(
            f"#{n}" for n in made.values()
        )
        if refused:
            said += f". GitHub refused {len(refused)}: " + "; ".join(refused)
        return said + "."
