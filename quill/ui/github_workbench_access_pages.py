"""The Access buttons on a Properties sheet's lists: Add, Change Role and Remove (PRD 18.3, 18.4).

Every list of who has access works the same way: a repository's people and
teams, an organization's members and outside collaborators, a team's members
and maintainers, and a team's repositories. Each change is previewed in
words; a tier 3 change (removing an admin, owner or maintainer, an outside
collaborator, or making a member an outside collaborator) asks for the name
typed; and each is refused, before anything is sent, when it would lock you
or the organization out (:func:`quill.core.github.access.lockout_problem`
on the loaded list, and for a team's admin role on a repository,
:func:`quill.core.github.org_people.team_repo_problem`, asked of GitHub just
before the change). A result per change is said and recorded in Change
History.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.github.access import (
    OUTSIDE,
    AccessRow,
    lockout_problem,
    parse_row,
    plan_add,
    plan_change,
    plan_remove,
)
from quill.core.github.permissions import REPO_ROLES, WriteTier
from quill.ui.github_workbench_invitations import GitHubWorkbenchInvitationsMixin

__all__ = ["GitHubWorkbenchAccessPagesMixin", "table_command"]

_P = "github.workbench."
_TABLE_SCOPES = {"repository": "repository", "team": "team", "organization": "organization"}
_ACCESS_LISTS = frozenset({
    "collaborators",
    "teams",
    "members",
    "maintainers",
    "invitations",
    "outside",
    "team_repos",
})
_CHANGEABLE = frozenset({
    "collaborators",
    "teams",
    "members",
    "maintainers",
    "outside",
    "team_repos",
})
#: The lists read together for a lockout check: a team's members are on two lists.
_TOGETHER = {
    ("team", "members"): ("members", "maintainers"),
    ("team", "maintainers"): ("members", "maintainers"),
    ("organization", "outside"): ("members", "outside"),
}
_MANAGERS = {"team": frozenset({"maintainer"})}


def table_command(key: str, verb: str) -> str:
    """The declared command a sheet list's Add, Change Role or Remove is ("" for none)."""
    if key == "branches":
        return {"add": f"{_P}create_branch", "remove": f"{_P}unlink_branch"}.get(verb, "")
    if key == "poll":  # a discussion's poll: Add and Change vote; Remove only explains
        return f"{_P}poll_vote" if verb in ("add", "change") else ""
    return f"{_P}access_{verb}" if key in _ACCESS_LISTS else ""


def _roles(scope: str, key: str) -> list[str]:
    if scope == "team":
        return list(REPO_ROLES) if key == "team_repos" else ["member", "maintainer"]
    if scope == "organization":
        return ["member", "owner"] if key == "outside" else ["member", "owner", OUTSIDE]
    return list(REPO_ROLES)


class GitHubWorkbenchAccessPagesMixin(GitHubWorkbenchInvitationsMixin):
    """Add, Change Role and Remove on a sheet's access lists."""

    frame: Any

    def table_action(self, target: Any, state: dict[str, Any]) -> Callable[[Any, str, str], None]:
        """The Access buttons on a sheet's list (people, teams, members, repositories)."""

        def act(spec: Any, verb: str, row: str) -> None:
            if self.refused(table_command(spec.key, verb)):  # type: ignore[attr-defined]
                return  # the level check, as the dispatcher makes it for a command
            if spec.key == "branches" and target.kind == "issue":
                self.act_on_linked_branch(state, verb, row)  # type: ignore[attr-defined]
                return
            scope = _TABLE_SCOPES.get(target.kind)
            if spec.key == "invitations" and scope in ("repository", "organization"):
                self.act_on_invitation(scope, state["ident"], verb, row, target.title())
                return
            if target.kind == "discussion" and spec.key == "poll":
                self.vote_from_sheet(dict(state["ident"]), verb)  # type: ignore[attr-defined]
                return
            if scope is None or spec.key not in _CHANGEABLE:
                self._say("This list is changed on GitHub's page; Open on GitHub goes there.")
                return
            self._act_on_access(scope, spec.key, verb, row, target.title(), state)

        return act

    def _act_on_access(
        self, scope: str, key: str, verb: str, row: str, title: str, state: dict[str, Any]
    ) -> None:
        ident = state["ident"]
        values = state["loaded"].values
        lists = _TOGETHER.get((scope, key), (key,))
        rows = [parse_row(r) for one in lists for r in values.get(one) or ()]
        roles = _roles(scope, key)
        me = self.account_name()  # type: ignore[attr-defined]
        top = _MANAGERS.get(scope, frozenset({"admin", "owner"}))
        guard: Callable[[Any], str] | None = None
        if verb == "add":
            change = self._planned_add(scope, key, ident, rows, me)
            if change is None:
                return
            name = change.path.rsplit("/", 1)[-1]
        else:
            found = parse_row(row)
            name = found.name
            new_role = ""
            if verb == "change":
                index = self._choose("Change Role", f"New role for {found.name}:", roles)
                if index < 0:
                    return
                new_role = roles[index]
                change = plan_change(scope, ident, found, new_role)
            else:
                change = plan_remove(scope, ident, found)
            problem = lockout_problem(rows, found, me, new_role=new_role, top=top)
            if problem:
                self._say(problem)
                return
            if key == "team_repos" and found.role == "admin" and new_role != "admin":
                guard = self._team_repo_guard(ident, found.name)
        self._run_changes([change], title, name=name, guard=guard)

    def _planned_add(self, scope: str, key: str, ident: Any, rows: list[AccessRow], me: str) -> Any:
        if key == "outside":
            who = self._ask_text("Make Outside Collaborator", "Login of the member:")
            if not who:
                return None
            target = next((r for r in rows if r.name.casefold() == who.casefold()), None)
            problem = lockout_problem(
                rows, target or AccessRow(who, "person", "member"), me, new_role=OUTSIDE
            )
            if problem:
                self._say(problem)
                return None
            return plan_add(scope, ident, who, "person", OUTSIDE)
        prompt = "Login, or team slug for a team:"
        if key == "team_repos":
            prompt = "Repository, as owner/name:"
        who = self._ask_text("Add", prompt)
        if not who:
            return None
        roles = [r for r in _roles(scope, key) if r != OUTSIDE]
        index = self._choose("Add", f"Role for {who}:", roles)
        if index < 0:
            return None
        kind = {"teams": "team", "team_repos": "repository"}.get(key, "person")
        return plan_add(scope, ident, who, kind, roles[index])

    def _team_repo_guard(self, ident: Any, repo: str) -> Callable[[Any], str]:
        from quill.core.github.org_people import team_repo_problem

        org, team = ident["org"], ident["team"]
        return lambda api: team_repo_problem(api, org, team, repo)

    def _run_changes(
        self,
        changes: list[Any],
        title: str,
        *,
        name: str = "",
        guard: Callable[[Any], str] | None = None,
    ) -> None:
        """Preview every change in words, then send them, a result per change (18.4).

        A tier 3 change asks for *name* typed (the count, for a batch). *guard*
        runs just before anything is sent; a sentence from it refuses the lot.
        """
        if not changes:
            return
        tier = max(change.tier for change in changes)
        words = "\n".join(change.words for change in changes)
        typed = name if len(changes) == 1 and name else str(len(changes))
        if not self.confirm_tier(max(tier, WriteTier.ACCESS), words, typed):  # type: ignore[attr-defined]
            return
        api = self.github_api()  # type: ignore[attr-defined]

        def work() -> tuple[str, list[str]]:
            if guard is not None:
                problem = guard(api)
                if problem:
                    return problem, []
            results: list[str] = []
            for index, change in enumerate(changes):
                if index:
                    time.sleep(getattr(self, "batch_pace", 1.0))
                try:
                    api.rest(change.method, change.path, body=change.body)
                except Exception as exc:  # noqa: BLE001 - a result per change
                    results.append(f"{change.words} Failed: {exc}")
                else:
                    results.append(f"{change.words} Done.")
            return "", results

        def done(answer: tuple[str, list[str]]) -> None:
            refused, results = answer
            if refused:
                self._say(refused)  # nothing was sent
                return
            failed = sum(1 for r in results if "Failed:" in r)
            self._say(f"{len(results) - failed} done, {failed} failed.")
            self._record_access(changes, results)
            if len(results) > 1 or failed:
                self._show_text(title, "\n".join(results))  # type: ignore[attr-defined]

        self._background("change access", work, done)

    def _record_access(self, changes: list[Any], results: list[str]) -> None:
        try:
            log = self.change_log()  # type: ignore[attr-defined]
            for change, result in zip(changes, results, strict=True):
                log.record(
                    account=self.account_name(),  # type: ignore[attr-defined]
                    kind="access",
                    ident={"path": change.path},
                    target=change.path,
                    summary=change.words,
                    changes=[],
                    tier=int(change.tier),
                    confirmed="Done." in result,
                    can_undo=False,
                )
        except OSError:
            pass
