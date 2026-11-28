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
from quill.ui.github_workbench_account_keys import (
    ACCOUNT_KEY_REASONS,
    ACCOUNT_KEY_VERBS,
    GitHubWorkbenchAccountKeysMixin,
)
from quill.ui.github_workbench_accounts import (
    ACCOUNT_REASONS,
    ACCOUNT_VERBS,
    GitHubWorkbenchAccountsMixin,
)
from quill.ui.github_workbench_advisories import (
    ADVISORY_REASONS,
    ADVISORY_VERBS,
    GitHubWorkbenchAdvisoriesMixin,
)
from quill.ui.github_workbench_ask_how import (
    ASK_HOW_REASONS,
    ASK_HOW_VERBS,
    GitHubWorkbenchAskHowMixin,
)
from quill.ui.github_workbench_authoring import (
    AUTHORING_REASONS,
    AUTHORING_VERBS,
    GitHubWorkbenchAuthoringMixin,
)
from quill.ui.github_workbench_batch_merge import (
    BATCH_MERGE_REASONS,
    BATCH_MERGE_VERBS,
    GitHubWorkbenchBatchMergeMixin,
)
from quill.ui.github_workbench_code_scanning import (
    CODE_SCANNING_REASONS,
    CODE_SCANNING_VERBS,
    GitHubWorkbenchCodeScanningMixin,
)
from quill.ui.github_workbench_codespaces import (
    CODESPACE_REASONS,
    CODESPACE_VERBS,
    GitHubWorkbenchCodespacesMixin,
)
from quill.ui.github_workbench_collab import (
    COLLAB_REASONS,
    COLLAB_VERBS,
    GitHubWorkbenchCollabMixin,
)
from quill.ui.github_workbench_discussions import (
    DISCUSSION_REASONS,
    DISCUSSION_VERBS,
    GitHubWorkbenchDiscussionsMixin,
)
from quill.ui.github_workbench_drafts import (
    DRAFT_REASONS,
    DRAFT_VERBS,
    GitHubWorkbenchDraftsMixin,
)
from quill.ui.github_workbench_dry_run import (
    DRY_RUN_REASONS,
    DRY_RUN_VERBS,
    GitHubWorkbenchDryRunMixin,
    failure_sentence,
)
from quill.ui.github_workbench_environments import (
    ENVIRONMENT_REASONS,
    ENVIRONMENT_VERBS,
    GitHubWorkbenchEnvironmentsMixin,
)
from quill.ui.github_workbench_evidence import (
    EVIDENCE_REASONS,
    EVIDENCE_VERBS,
    GitHubWorkbenchEvidenceMixin,
)
from quill.ui.github_workbench_inbox_rules import (
    INBOX_RULE_REASONS,
    INBOX_RULE_VERBS,
    GitHubWorkbenchInboxRulesMixin,
)
from quill.ui.github_workbench_issue_admin import (
    ISSUE_ADMIN_REASONS,
    ISSUE_ADMIN_VERBS,
    GitHubWorkbenchIssueAdminMixin,
)
from quill.ui.github_workbench_merge import (
    MERGE_REASONS,
    MERGE_VERBS,
    GitHubWorkbenchMergeMixin,
)
from quill.ui.github_workbench_my_github import (
    MY_GITHUB_REASONS,
    MY_GITHUB_VERBS,
    GitHubWorkbenchMyGitHubMixin,
)
from quill.ui.github_workbench_new_ruleset import (
    NEW_RULESET_REASONS,
    NEW_RULESET_VERBS,
    GitHubWorkbenchNewRulesetMixin,
)
from quill.ui.github_workbench_org_admin import (
    ORG_ADMIN_REASONS,
    ORG_ADMIN_VERBS,
    GitHubWorkbenchOrgAdminMixin,
)
from quill.ui.github_workbench_packages import (
    PACKAGE_REASONS,
    PACKAGE_VERBS,
    GitHubWorkbenchPackagesMixin,
)
from quill.ui.github_workbench_pages import (
    PAGES_REASONS,
    PAGES_VERBS,
    GitHubWorkbenchPagesMixin,
)
from quill.ui.github_workbench_plain_batch import (
    PLAIN_BATCH_REASONS,
    PLAIN_BATCH_VERBS,
    GitHubWorkbenchPlainBatchMixin,
)
from quill.ui.github_workbench_practice import (
    PRACTICE_REASONS,
    PRACTICE_VERBS,
    GitHubWorkbenchPracticeMixin,
)
from quill.ui.github_workbench_project_admin import (
    PROJECT_ADMIN_REASONS,
    PROJECT_ADMIN_VERBS,
    GitHubWorkbenchProjectAdminMixin,
)
from quill.ui.github_workbench_pull_reviews import (
    PULL_REVIEW_REASONS,
    PULL_REVIEW_VERBS,
    GitHubWorkbenchPullReviewsMixin,
)
from quill.ui.github_workbench_pull_tools import (
    PULL_TOOL_REASONS,
    PULL_TOOL_VERBS,
    GitHubWorkbenchPullToolsMixin,
)
from quill.ui.github_workbench_quick import (
    QUICK_REASONS,
    QUICK_VERBS,
    GitHubWorkbenchQuickMixin,
)
from quill.ui.github_workbench_resources import (
    RESOURCE_REASONS,
    RESOURCE_VERBS,
    GitHubWorkbenchResourcesMixin,
)
from quill.ui.github_workbench_row_admin import (
    ROW_ADMIN_REASONS,
    ROW_ADMIN_VERBS,
    GitHubWorkbenchRowAdminMixin,
)
from quill.ui.github_workbench_run_more import (
    RUN_MORE_REASONS,
    RUN_MORE_VERBS,
    GitHubWorkbenchRunMoreMixin,
)
from quill.ui.github_workbench_runner_admin import (
    RUNNER_ADMIN_REASONS,
    RUNNER_ADMIN_VERBS,
    GitHubWorkbenchRunnerAdminMixin,
)
from quill.ui.github_workbench_scoped import (
    SCOPED_REASONS,
    SCOPED_VERBS,
    GitHubWorkbenchScopedListsMixin,
)
from quill.ui.github_workbench_service_status import (
    SERVICE_STATUS_REASONS,
    SERVICE_STATUS_VERBS,
    GitHubWorkbenchServiceStatusMixin,
)
from quill.ui.github_workbench_settings_lists import (
    SETTINGS_LIST_REASONS,
    SETTINGS_LIST_VERBS,
    GitHubWorkbenchSettingsListsMixin,
)
from quill.ui.github_workbench_sponsors import (
    SPONSOR_REASONS,
    SPONSOR_VERBS,
    GitHubWorkbenchSponsorsMixin,
)
from quill.ui.github_workbench_star_lists import (
    STAR_LIST_REASONS,
    STAR_LIST_VERBS,
    GitHubWorkbenchStarListsMixin,
)
from quill.ui.github_workbench_tier2 import (
    TIER2_REASONS,
    TIER2_VERBS,
    GitHubWorkbenchTier2Mixin,
)
from quill.ui.github_workbench_tour import (
    TOUR_REASONS,
    TOUR_VERBS,
    GitHubWorkbenchTourMixin,
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
    **BATCH_MERGE_VERBS,
    **EVIDENCE_VERBS,
    **COLLAB_VERBS,
    **DRAFT_VERBS,
    **INBOX_RULE_VERBS,
    **MY_GITHUB_VERBS,
    **DRY_RUN_VERBS,
    **PLAIN_BATCH_VERBS,
    **PRACTICE_VERBS,
    **SERVICE_STATUS_VERBS,
    **ASK_HOW_VERBS,
    **TOUR_VERBS,
    **TIER2_VERBS,
    **PACKAGE_VERBS,
    **STAR_LIST_VERBS,
    **ACCOUNT_VERBS,
    **ADVISORY_VERBS,
    **ACCOUNT_KEY_VERBS,
    **SETTINGS_LIST_VERBS,
    **SPONSOR_VERBS,
    **RUNNER_ADMIN_VERBS,
    **RESOURCE_VERBS,
    **CODE_SCANNING_VERBS,
    **CODESPACE_VERBS,
    **RUN_MORE_VERBS,
    **ENVIRONMENT_VERBS,
    **NEW_RULESET_VERBS,
    **PULL_REVIEW_VERBS,
    **PAGES_VERBS,
    **PROJECT_ADMIN_VERBS,
    **ORG_ADMIN_VERBS,
    **ISSUE_ADMIN_VERBS,
    **ROW_ADMIN_VERBS,
    **SCOPED_VERBS,
    **QUICK_VERBS,
    **DISCUSSION_VERBS,
    **AUTHORING_VERBS,
}

DEVELOPMENT_REASONS: dict[str, str] = {
    "create_branch": "Create Branch is for an issue, while you are signed in.",
    "edit_tasks": "Task lists are for an issue, while you are signed in.",
    "convert_tasks": "Task lists are for an issue, while you are signed in.",
    **PULL_TOOL_REASONS,
    **MERGE_REASONS,
    **BATCH_MERGE_REASONS,
    **EVIDENCE_REASONS,
    **COLLAB_REASONS,
    **DRAFT_REASONS,
    **INBOX_RULE_REASONS,
    **MY_GITHUB_REASONS,
    **DRY_RUN_REASONS,
    **PLAIN_BATCH_REASONS,
    **PRACTICE_REASONS,
    **SERVICE_STATUS_REASONS,
    **ASK_HOW_REASONS,
    **TOUR_REASONS,
    **TIER2_REASONS,
    **PACKAGE_REASONS,
    **STAR_LIST_REASONS,
    **ACCOUNT_REASONS,
    **ADVISORY_REASONS,
    **ACCOUNT_KEY_REASONS,
    **SETTINGS_LIST_REASONS,
    **SPONSOR_REASONS,
    **RUNNER_ADMIN_REASONS,
    **RESOURCE_REASONS,
    **CODE_SCANNING_REASONS,
    **CODESPACE_REASONS,
    **RUN_MORE_REASONS,
    **ENVIRONMENT_REASONS,
    **NEW_RULESET_REASONS,
    **PULL_REVIEW_REASONS,
    **PAGES_REASONS,
    **PROJECT_ADMIN_REASONS,
    **ORG_ADMIN_REASONS,
    **ISSUE_ADMIN_REASONS,
    **ROW_ADMIN_REASONS,
    **SCOPED_REASONS,
    **QUICK_REASONS,
    **DISCUSSION_REASONS,
    **AUTHORING_REASONS,
}


class GitHubWorkbenchDevelopmentMixin(
    GitHubWorkbenchPullToolsMixin,
    GitHubWorkbenchMergeMixin,
    GitHubWorkbenchBatchMergeMixin,
    GitHubWorkbenchEvidenceMixin,
    GitHubWorkbenchCollabMixin,
    GitHubWorkbenchDraftsMixin,
    GitHubWorkbenchInboxRulesMixin,
    GitHubWorkbenchMyGitHubMixin,
    GitHubWorkbenchDryRunMixin,
    GitHubWorkbenchPlainBatchMixin,
    GitHubWorkbenchPracticeMixin,
    GitHubWorkbenchServiceStatusMixin,
    GitHubWorkbenchAskHowMixin,
    GitHubWorkbenchTourMixin,
    GitHubWorkbenchTier2Mixin,
    GitHubWorkbenchPackagesMixin,
    GitHubWorkbenchStarListsMixin,
    GitHubWorkbenchAccountsMixin,
    GitHubWorkbenchAdvisoriesMixin,
    GitHubWorkbenchAccountKeysMixin,
    GitHubWorkbenchSettingsListsMixin,
    GitHubWorkbenchSponsorsMixin,
    GitHubWorkbenchRunnerAdminMixin,
    GitHubWorkbenchResourcesMixin,
    GitHubWorkbenchCodeScanningMixin,
    GitHubWorkbenchCodespacesMixin,
    GitHubWorkbenchRunMoreMixin,
    GitHubWorkbenchEnvironmentsMixin,
    GitHubWorkbenchNewRulesetMixin,
    GitHubWorkbenchPullReviewsMixin,
    GitHubWorkbenchPagesMixin,
    GitHubWorkbenchProjectAdminMixin,
    GitHubWorkbenchOrgAdminMixin,
    GitHubWorkbenchIssueAdminMixin,
    GitHubWorkbenchRowAdminMixin,
    GitHubWorkbenchScopedListsMixin,
    GitHubWorkbenchQuickMixin,
    GitHubWorkbenchDiscussionsMixin,
    GitHubWorkbenchAuthoringMixin,
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
        assert isinstance(row, GitHubItem)
        self._create_branch_for(ref.instance, row.number, row.title)

    def _create_branch_for(
        self,
        repository: str,
        number: int,
        title: str,
        after: Callable[[str], None] | None = None,
    ) -> None:
        """Ask the name, then make it linked to #*number*; *after* gets the name once made.

        The issue's sheet (its Linked branches list) passes *after* to show the
        new branch at once.
        """
        from quill.core.github.issue_development import (
            branch_name_for,
            create_linked_branch,
            valid_branch_name,
        )

        name = self._ask_text(
            "Create Branch for This Issue",
            f"Branch name for #{number}, made from the default branch and linked to it:",
            value=branch_name_for(number, title),
        )
        if not name:
            return
        why = valid_branch_name(name)
        if why:
            self._say(why)
            return
        api = self.github_api()

        def done(said: Any) -> None:
            self._say(f"{said} To work on it: git fetch, then git switch {name}.")
            if after is not None:
                after(name)

        self._background(
            "make the branch",
            lambda: create_linked_branch(api, repository, number, name),
            done,
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
