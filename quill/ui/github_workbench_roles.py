"""Account > Roles and Access, answered from GitHub's own replies (GitHub PRD 18.2, 18.3, 22.10).

- **My Access Here**: your role here, and where each part comes from:
  the repository's permissions, ``viewerPermission``, your organization
  membership and base permission, the teams you are on, the rules on the
  default branch, and this sign-in's scopes (or that a fine-grained token's
  permissions cannot be known).
- **View As Role** and **Compare Roles**: GitHub's documented defaults, said
  to be that, then who on this repository GitHub says has each role.
- **Why Can't They?**: the person's real role (GitHub's ``role_name``, a
  custom role too), what the ability needs, and the rules GitHub says apply.
- **Access Review**: effective access per person and team, with its source.
- **Bulk Access Changes**: previewed per person from each repository's
  current role; nothing is sent for a change that changes nothing.
- **Compare Accounts**: two signed-in accounts on this repository, each asked
  with its own sign-in, side by side.
- **Act As Another Account**: one action, sent as another signed-in account,
  held to that account's level and named in the question and the outcome.

The words come from :mod:`quill.core.github.role_reports`; this mixin only
asks, runs the reads off the UI thread and shows the answer.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.github.access import bulk_plan, matrix_csv, matrix_rows, view_as_role
from quill.core.github.permissions import REPO_ROLES

__all__ = ["ROLE_TOOLS", "GitHubWorkbenchRolesMixin"]

#: The Roles and Access verbs this mixin answers (``_tool_<verb>``).
ROLE_TOOLS = frozenset({
    "my_access",
    "view_as_role",
    "compare_roles",
    "why_cant_they",
    "access_matrix",
    "bulk_access",
    "compare_accounts",
    "act_as",
})

_P = "github.workbench."


class GitHubWorkbenchRolesMixin:
    """Roles and Access for the GitHub provider."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    def _repository(self) -> str:
        return str(self.current_repository_name())  # type: ignore[attr-defined]

    def _show_text(self, title: str, text: str) -> None:
        from quill.ui.github_workbench_results import show_results

        show_results(self.frame.frame, title, text, copy_text=self.frame.copy_text)

    def _token(self) -> str | None:
        token = getattr(self.items, "token", None)
        return token if isinstance(token, str) else None

    def _pick_role(self, title: str) -> str:
        index = self._choose(title, "Role:", list(REPO_ROLES))
        return REPO_ROLES[index] if index >= 0 else ""

    # -- My Access Here ---------------------------------------------------------------

    def _tool_my_access(self) -> None:
        repository = self._repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        api = self.github_api()  # type: ignore[attr-defined]
        login = self.account_name()  # type: ignore[attr-defined]
        token = self._token()
        scopes = getattr(self.items, "last_scopes_header", None)

        def read() -> str:
            from quill.core.github.role_reports import my_access

            return my_access(
                api,
                repository,
                login,
                token=token,
                scopes_header=scopes if isinstance(scopes, str) else None,
            )

        self._background(
            "read your access", read, lambda text: self._show_text("My Access Here", text)
        )

    # -- View As Role, Compare Roles, Why Can't They? ------------------------------------

    def _tool_view_as_role(self) -> None:
        role = self._pick_role("View As Role")
        if not role:
            return
        repository = self._repository()
        api = self.github_api() if repository else None  # type: ignore[attr-defined]

        def read() -> str:
            from quill.core.github.role_reports import role_report

            return role_report(api, role, repository)

        self._background("read who has the role", read, lambda t: self._show_text(role, t))

    def _tool_compare_roles(self) -> None:
        low = self._pick_role("Compare Roles: the first role")
        high = self._pick_role("Compare Roles: the second role") if low else ""
        if not (low and high):
            return
        repository = self._repository()
        api = self.github_api() if repository else None  # type: ignore[attr-defined]

        def read() -> str:
            from quill.core.github.role_reports import compare_report

            return compare_report(api, low, high, repository)

        self._background(
            "compare the roles", read, lambda t: self._show_text(f"{low} and {high}", t)
        )

    def _tool_why_cant_they(self) -> None:
        repository = self._repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        person = self._ask_text("Why Can't They?", "Their login:").lstrip("@")
        abilities = view_as_role("admin")
        index = self._choose("Why Can't They?", "What they cannot do:", abilities) if person else -1
        if index < 0:
            return
        ability = abilities[index]
        api = self.github_api()  # type: ignore[attr-defined]

        def read() -> str:
            from quill.core.github.role_evidence import BLOCKING, fetch
            from quill.core.github.role_reports import why_cant_they

            branch = ""
            if ability in BLOCKING:
                found = fetch(api, f"/repos/{repository}")
                data = found.data if isinstance(found.data, dict) else {}
                branch = str(data.get("default_branch") or "")
            return why_cant_they(api, repository, person, ability, branch)

        self._background(
            "read their access",
            read,
            lambda text: self._show_text(f"Why can't {person} {ability}?", text),
        )

    # -- the Access Review and bulk changes (18.3.2) ---------------------------------------

    def _tool_access_matrix(self) -> None:
        org = self._ask_text("Access Review", "Organization:")
        if not org:
            return
        api = self.github_api()  # type: ignore[attr-defined]

        def read() -> list[tuple[str, str, str, str]]:
            from quill.core.github.role_reports import review_by_repository

            return matrix_rows(review_by_repository(api, org, pause=lambda: time.sleep(0)))

        def done(rows: list[tuple[str, str, str, str]]) -> None:
            self._say(f"{len(rows)} person, team and repository rows.")
            self._show_text(
                f"Access Review: {org}",
                "\n".join(", ".join(r) for r in rows) or "GitHub lists nobody with access yet.",
            )
            self.frame.copy_text(matrix_csv(rows))

        self._background("read the access review", read, done)

    def _tool_bulk_access(self) -> None:
        who = self._ask_text("Bulk Access Changes", "Team slug or person's login:").lstrip("@")
        if not who:
            return
        kinds = ["team", "person"]
        kind_index = self._choose("Bulk Access Changes", f"{who} is a:", kinds)
        role = self._pick_role("The role to give") if kind_index >= 0 else ""
        repos_text = (
            self._ask_text("Bulk Access Changes", "Repositories, comma-separated (owner/name):")
            if role
            else ""
        )
        targets = [{"repo": r.strip()} for r in repos_text.split(",") if "/" in r]
        if not targets:
            return
        kind = kinds[kind_index]
        changes = bulk_plan("repository", who, kind, role, targets)
        api = self.github_api()  # type: ignore[attr-defined]

        def read() -> tuple[list[Any], list[str]]:
            from quill.core.github.role_reports import bulk_preview

            return bulk_preview(api, changes, who, kind, role, targets)

        def done(found: tuple[list[Any], list[str]]) -> None:
            sending, lines = found
            if not sending:
                self._show_text("Bulk Access Changes", "\n".join(lines))
                self._say(f"Nothing to change: {who} already has {role} on every one.")
                return
            skipped = [line for line in lines if "nothing is sent" in line]
            if skipped:
                self._show_text("Bulk Access Changes: already so", "\n".join(skipped))
            self._run_changes(sending, "Bulk Access Changes")  # type: ignore[attr-defined]

        self._background("read the current access", read, done)

    # -- Compare Accounts and Act As (18.3) ------------------------------------------------

    def _account_api(self, account: Any) -> Any:
        """A connection of *account*'s own: its token, its host, its own remembered reads."""
        from quill.core.github.accounts import load_github_account_token
        from quill.core.github.workbench_api import TokenApi

        return TokenApi(load_github_account_token(account.id))

    def _accounts(self) -> tuple[list[Any], str | None]:
        from quill.core.github.accounts import active_github_account_id, list_github_accounts

        return list_github_accounts(), active_github_account_id()

    def _tool_compare_accounts(self) -> None:
        repository = self._repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        accounts, active = self._accounts()
        if len(accounts) < 2:
            self._say(
                "Compare Accounts needs two signed-in accounts: Account, Manage GitHub "
                "Accounts adds another."
            )
            return
        labels = [account.display_name for account in accounts]
        first = next((i for i, a in enumerate(accounts) if a.id == active), 0)
        index = self._choose(
            "Compare Accounts", f"Compare {labels[first]} with which account?", labels
        )
        if index < 0:
            return
        if index == first:
            self._say("Choose a different account from the one to compare it with.")
            return
        pair = (accounts[first], accounts[index])
        if pair[0].host != pair[1].host:
            self._say(
                "Cannot compare these: they are on different servers, and a repository lives "
                "on one."
            )
            return
        apis = [self._account_api(account) for account in pair]

        def read() -> str:
            from quill.core.github.accounts import load_github_account_token
            from quill.core.github.role_reports import account_access, compare_accounts

            found = [
                account_access(
                    api,
                    account.display_name,
                    account.login,
                    repository,
                    token=load_github_account_token(account.id),
                )
                for api, account in zip(apis, pair, strict=True)
            ]
            return compare_accounts(repository, found[0], found[1])

        self._background(
            "compare the accounts",
            read,
            lambda text: self._show_text(f"Compare Accounts: {repository}", text),
        )

    def _tool_act_as(self) -> None:
        from quill.core.github.act_as import actions_for, confirmation, plan
        from quill.core.github.items_provider import GitHubItem

        repository = self._repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        accounts, active = self._accounts()
        others = [account for account in accounts if account.id != active]
        if not others:
            self._say(
                "Act As needs a second signed-in account: Account, Manage GitHub Accounts adds one."
            )
            return
        index = self._choose(
            "Act As Another Account",
            "Which account does it?",
            [account.display_name for account in others],
        )
        if index < 0:
            return
        account = others[index]
        row = self.frame.selected_row() if self.frame is not None else None
        item = row if isinstance(row, GitHubItem) else None
        kind = ("pull_request" if item.is_pr else "issue") if item is not None else "repository"
        actions = actions_for(kind)
        which = self._choose(
            f"Act As {account.login}",
            f"What should {account.login} do?",
            [action.title for action in actions],
        )
        if which < 0:
            return
        action = actions[which]
        text = ""
        if action.needs_text:
            text = self._ask_text(f"Comment as {account.login}", "Comment:", multiline=True)
            if not text:
                return
        request = plan(
            action,
            repository,
            number=item.number if item is not None else 0,
            is_open=(item.state == "open") if item is not None else True,
            text=text,
        )
        if self._refused_for(account, request):
            return
        if not self._confirm(
            f"Act As {account.login}", confirmation(account.login, account.host, request)
        ):
            return
        self._send_as(account, request)

    def _refused_for(self, account: Any, request: Any) -> bool:
        """The other account's own Workbench level, checked as the gate checks any write."""
        from quill.core.github.permissions import AccessStore, effective_level
        from quill.core.github.write_gate import refusal

        level = effective_level(AccessStore.load().level(account.level_key))
        said = refusal(f"{request.words} as {account.login}", request.tier, level)
        if said:
            self._say(said)
        return bool(said)

    def _send_as(self, account: Any, request: Any) -> None:
        from quill.core.github.act_as import identity_problem, outcome
        from quill.core.github.rest_transport import GitHubRestError, rest_failure_message
        from quill.core.github.role_evidence import fetch

        api = self._account_api(account)

        def work() -> tuple[str, bool]:
            me = fetch(api, "/user")
            problem = identity_problem(account.login, account.host, me.data if me.ok else None)
            if problem:
                return problem, False
            try:
                api.rest(request.method, request.path, body=request.body)
            except GitHubRestError as exc:
                why = rest_failure_message(request.words, exc).removeprefix(
                    f"Could not {request.words}. "
                )
                return outcome(account.login, request, why), False
            return outcome(account.login, request), True

        def done(result: tuple[str, bool]) -> None:
            sentence, sent = result
            self._say(sentence)
            if sent:
                self._record_act_as(account, request)

        self._background(f"act as {account.login}", work, done)

    def _record_act_as(self, account: Any, request: Any) -> None:
        try:
            self.change_log().record(  # type: ignore[attr-defined]
                account=account.login,
                kind="act_as",
                ident={"path": request.path},
                target=request.path,
                summary=f"As {account.login} on {account.host}: {request.words}",
                changes=[],
                tier=int(request.tier),
                confirmed=True,
                can_undo=False,
            )
        except OSError:
            pass
