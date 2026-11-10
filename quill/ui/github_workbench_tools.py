"""The GitHub Workbench's filter and permission tools (GitHub PRD 17.2, 18; Phases 9 and 10).

- **Filter Builder** (Ctrl+Alt+F): values from the repository (labels,
  milestones, assignable people, teams, branches), the query into the filter
  box, and Save as Search.
- **Account > GitHub Permissions** (Ctrl+Shift+P): every scope, what it
  unlocks and whether you have it; Add Permissions (the next sign-in asks for
  the missing ones too, one approval on GitHub), Copy Command for ``gh``,
  Classic Token Page, Fine-grained Steps, and Check Again.
- **Account > Change History** (Ctrl+Shift+H): every write, before and after;
  Undo on any row GitHub allows, Copy, Save as CSV, Clear.
- **Roles and Access:** My Access Here, View As Role, Compare Roles, Why Can't
  They?, Access Review (the access matrix, as CSV too), Bulk Access Changes
  (previewed, a result per change) and this account's Workbench level.
- **Access pages:** Add..., Change Role... and Remove on a sheet's list, each
  previewed in words, refused when it would lock you out (18.4), and recorded.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.github.access import (
    AccessRow,
    bulk_plan,
    compare_roles,
    lockout_problem,
    matrix_csv,
    parse_row,
    plan_add,
    plan_change,
    plan_remove,
    view_as_role,
    why_cant_they,
)
from quill.core.github.permissions import (
    REPO_ROLES,
    SCOPES,
    AccessLevel,
    WriteTier,
    classic_token_url,
    fine_grained_steps,
    gh_refresh_command,
    missing_scopes,
    scope_rows,
)

__all__ = ["GitHubWorkbenchToolsMixin"]

_P = "github.workbench."
_TOOLS = frozenset({
    "filter_builder",
    "permissions",
    "change_history",
    "my_access",
    "view_as_role",
    "compare_roles",
    "why_cant_they",
    "access_matrix",
    "bulk_access",
    "account_level",
})
_TABLE_SCOPES = {
    "repository": "repository",
    "team": "team",
    "organization": "organization",
}


class GitHubWorkbenchToolsMixin:
    """Filter Builder, permissions, history and access, for the GitHub provider."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    def supports_tool(self, command_id: str) -> bool:
        return command_id.removeprefix(_P) in _TOOLS

    def run_tool(self, command_id: str) -> bool:
        verb = command_id.removeprefix(_P)
        if verb not in _TOOLS or self.frame is None:
            return False
        getattr(self, f"_tool_{verb}")()
        return True

    def _repository(self) -> str:
        return str(self.current_repository_name())  # type: ignore[attr-defined]

    # -- Teams in the tree (18.3.3, GH-R-143) -------------------------------------

    def load_teams(self, loader: str, organization: str) -> list[Any]:
        """Organizations > org > Teams, or People > My Teams. Runs off the UI thread."""
        from quill.core.github.explore_models import ExploreRow

        api = self.github_api()  # type: ignore[attr-defined]
        path = "/user/teams" if loader == "teams:mine" else f"/orgs/{organization}/teams"
        answer = api.rest("GET", path, query={"per_page": "100"})
        rows = answer.data if isinstance(answer.data, list) else []
        found = []
        for team in rows:
            if not isinstance(team, dict):
                continue
            org = str((team.get("organization") or {}).get("login") or organization)
            parent = (team.get("parent") or {}).get("name") if team.get("parent") else ""
            where = f", child of {parent}" if parent else ""
            mine = f" ({org})" if loader == "teams:mine" else ""
            label = f"{team.get('name', '')}{mine}{where}, {team.get('privacy', '')}"
            detail = f"{team.get('description') or 'No description.'}\n{team.get('html_url', '')}"
            found.append(
                ExploreRow(
                    label,
                    detail,
                    str(team.get("html_url") or ""),
                    org,
                    "team",
                    str(team.get("slug") or ""),
                )
            )
        return found

    # -- Filter Builder (17.2) ---------------------------------------------------

    def _tool_filter_builder(self) -> None:
        repository = self._repository()
        api = self.github_api()  # type: ignore[attr-defined]

        def values() -> dict[str, list[str]]:
            found: dict[str, list[str]] = {}
            if not repository:
                return found
            sources = {
                "labels": (f"/repos/{repository}/labels", "name"),
                "milestones": (f"/repos/{repository}/milestones", "title"),
                "people": (f"/repos/{repository}/assignees", "login"),
                "branches": (f"/repos/{repository}/branches", "name"),
                "teams": (f"/repos/{repository}/teams", "slug"),
            }
            for key, (path, field) in sources.items():
                try:
                    answer = api.rest("GET", path, query={"per_page": "100"})
                except Exception:  # noqa: BLE001 - a picker that cannot load is typed into
                    continue
                rows = answer.data if isinstance(answer.data, list) else []
                found[key] = [str(r.get(field, "")) for r in rows if isinstance(r, dict)]
            return found

        self._background("load the filter values", values, self._show_builder)

    def _show_builder(self, values: dict[str, list[str]]) -> None:
        from quill.ui.github_filter_builder_dialog import FilterBuilderDialog

        frame = self.frame
        dialog = FilterBuilderDialog(frame.frame, values=values, initial=frame.filter.GetValue())
        if not dialog.show():
            return
        frame.filter.ChangeValue(dialog.query)
        frame.apply_filter()
        if dialog.save and dialog.query:
            from quill.ui.github_workbench_loaders import saved_items_for

            saved = saved_items_for(self.items)
            saved.save_search(dialog.query)
            saved.save()
            self._say(f"Saved the search {dialog.query}.")

    # -- GitHub Permissions (18.1) --------------------------------------------------

    def _scopes_now(self) -> tuple[str, ...] | None:
        return self.token_scopes()  # type: ignore[attr-defined, no-any-return]

    def _tool_permissions(self) -> None:
        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        have = self._scopes_now()
        rows = scope_rows(have)
        holder: dict[str, Any] = {}

        def missing() -> list[str]:
            return list(missing_scopes(self._scopes_now(), [s.name for s in SCOPES if not s.risky]))

        def add(_index: int) -> None:
            from quill.core.github.oauth_sign_in import request_extra_scopes

            wanted = missing()
            if have is None or not wanted:
                self._say(
                    "Nothing to add: this sign-in has every permission the Workbench uses."
                    if have is not None
                    else "This token's permissions are set on GitHub; Fine-grained Steps "
                    "lists what to set there."
                )
                return
            request_extra_scopes(wanted)
            self._run_editor("file.github_manage_accounts")  # type: ignore[attr-defined]
            self._say(f"Sign in again and approve on GitHub to add {', '.join(wanted)}.")

        def copy_command(_index: int) -> None:
            command = gh_refresh_command(missing() or [s.name for s in SCOPES if not s.risky])
            self.frame.copy_text(command)

        def token_page(_index: int) -> None:
            import webbrowser

            if not webbrowser.open(classic_token_url(missing() or ["repo"]), new=2):
                self._say("Could not open your browser.")

        def fine_grained(_index: int) -> None:
            self.frame.copy_text("\n".join(fine_grained_steps(missing() or ["repo"])))

        def check_again(_index: int) -> None:
            def read() -> tuple[str, ...] | None:
                answer = self.github_api().rest("GET", "/user")  # type: ignore[attr-defined]
                header = answer.header("x-oauth-scopes")
                return tuple(s.strip() for s in header.split(",") if s.strip()) if header else None

            def done(found: tuple[str, ...] | None) -> None:
                before = set(have or ())
                after = set(found or ())
                gained = sorted(after - before)
                self.items.last_scopes_header = ", ".join(found) if found is not None else None
                holder["dialog"].set_rows([said for _s, said in scope_rows(found)])
                self._say(f"Added {', '.join(gained)}." if gained else "No change.")

            self._background("check the permissions", read, done)

        dialog = WorkbenchListDialog(
            self.frame.frame,
            "GitHub Permissions",
            [said for _scope, said in rows],
            list_name="Permissions",
            list_help="Every permission the Workbench can use: what it unlocks, and whether "
            "you have it.",
            detail=lambda i: rows[i][1] + (f"\n\nGroup: {rows[i][0].group}." if i >= 0 else ""),
            actions=[
                (
                    "&Add Permissions...",
                    "Sign in again asking for every missing permission: "
                    "one approval on GitHub adds them all.",
                    add,
                ),
                (
                    "Copy &Command",
                    "Copy the gh command that adds the missing permissions.",
                    copy_command,
                ),
                (
                    "Classic &Token Page",
                    "Open GitHub's new-token page with the missing scopes listed.",
                    token_page,
                ),
                (
                    "&Fine-grained Steps",
                    "Copy what to set on a fine-grained token, by GitHub's names.",
                    fine_grained,
                ),
                ("Check A&gain", "Read the permissions again and say what changed.", check_again),
            ],
            copy_text=self.frame.copy_text,
        )
        holder["dialog"] = dialog
        dialog.show()

    # -- Change History (18.5) --------------------------------------------------------

    def _tool_change_history(self) -> None:
        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        log = self.change_log()  # type: ignore[attr-defined]
        entries = list(reversed(log.entries))
        holder: dict[str, Any] = {}

        def refresh() -> None:
            entries[:] = list(reversed(log.entries))
            holder["dialog"].set_rows([e.row_text() for e in entries])

        def undo(index: int) -> None:
            if index < 0:
                return
            real = len(log.entries) - 1 - index
            self.undo_entry(real)  # type: ignore[attr-defined]
            refresh()

        def save_csv(_index: int) -> None:
            from pathlib import Path

            wx = self.frame._wx
            with wx.FileDialog(
                self.frame.frame,
                "Save Change History",
                wildcard="CSV files (*.csv)|*.csv",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as dialog:
                from quill.ui.dialog_contract import show_modal_dialog

                if show_modal_dialog(dialog, "Save Change History") != wx.ID_OK:
                    return
                Path(dialog.GetPath()).write_text(log.as_csv(), encoding="utf-8")
            self._say("Saved.")

        def clear(_index: int) -> None:
            if self._confirm(
                "Clear Change History",
                "Forget every change in the history? "  # type: ignore[attr-defined]
                "Nothing on GitHub changes.",
            ):
                log.clear()
                refresh()
                self._say("Change History cleared.")

        dialog = WorkbenchListDialog(
            self.frame.frame,
            "Change History",
            [e.row_text() for e in entries],
            list_name="Changes",
            list_help="Every change the Workbench made on GitHub, newest first, kept on this "
            "device for 90 days. Secret values are never recorded.",
            detail=lambda i: entries[i].detail_text() if 0 <= i < len(entries) else "",
            actions=[
                ("&Undo This Change", "Reverse the selected change, where GitHub allows it.", undo),
                ("&Save as CSV...", "Save the whole history as a CSV file.", save_csv),
                ("C&lear History...", "Forget every change in the history, after asking.", clear),
            ],
            copy_text=self.frame.copy_text,
        )
        holder["dialog"] = dialog
        dialog.show()

    # -- Roles (18.2, 22.10) ------------------------------------------------------------

    def _tool_my_access(self) -> None:
        repository = self._repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        api = self.github_api()  # type: ignore[attr-defined]

        def read() -> str:
            from quill.core.github.permissions import repo_role

            data = api.rest("GET", f"/repos/{repository}").data
            role = repo_role(data.get("permissions") if isinstance(data, dict) else None)
            owner = (data or {}).get("owner", {}) if isinstance(data, dict) else {}
            parts = [f"You have {role or 'no'} access to {repository}."]
            if isinstance(owner, dict) and owner.get("type") == "Organization":
                try:
                    org = api.rest("GET", f"/orgs/{owner.get('login')}").data
                    base = str((org or {}).get("default_repository_permission") or "")
                    if base:
                        parts.append(f"The organization's base permission is {base}.")
                except Exception:  # noqa: BLE001 - members may not read it
                    pass
                parts.append("The higher one counts; a team you are on can raise it.")
            return " ".join(parts)

        self._background("read your access", read, self._say)

    def _pick_role(self, title: str) -> str:
        index = self._choose(title, "Role:", list(REPO_ROLES))
        return REPO_ROLES[index] if index >= 0 else ""

    def _tool_view_as_role(self) -> None:
        role = self._pick_role("View As Role")
        if role:
            self._show_text(f"What {role} may do", "\n".join(view_as_role(role)))

    def _tool_compare_roles(self) -> None:
        low = self._pick_role("Compare Roles: the first role")
        high = self._pick_role("Compare Roles: the second role") if low else ""
        if low and high:
            more = compare_roles(low, high) or compare_roles(high, low)
            self._show_text(f"{low} and {high}", "\n".join(more) or "They may do the same.")

    def _tool_why_cant_they(self) -> None:
        person = self._ask_text("Why Can't They?", "Their login:")
        role = self._pick_role("Their role here") if person else ""
        abilities = view_as_role("admin")
        index = self._choose("Why Can't They?", "What they cannot do:", abilities) if role else -1
        if index >= 0:
            where = self._repository() or "this repository"
            self._say(why_cant_they(person, role, abilities[index], where))

    def _show_text(self, title: str, text: str) -> None:
        from quill.ui.github_workbench_results import show_results

        show_results(self.frame.frame, title, text, copy_text=self.frame.copy_text)

    def _tool_access_matrix(self) -> None:
        org = self._ask_text("Access Review", "Organization:")
        if not org:
            return
        api = self.github_api()  # type: ignore[attr-defined]

        def read() -> list[tuple[str, str, str, str]]:
            from quill.core.github.access import matrix_rows
            from quill.core.github.sheet_rows import collaborator_row

            repos = api.rest("GET", f"/orgs/{org}/repos", query={"per_page": "100"}).data or []
            access: dict[str, list[AccessRow]] = {}
            for repo in repos if isinstance(repos, list) else []:
                name = str(repo.get("full_name", ""))
                rows = (
                    api.rest("GET", f"/repos/{name}/collaborators", query={"per_page": "100"}).data
                    or []
                )
                access[name] = [parse_row(collaborator_row(r)) for r in rows if isinstance(r, dict)]
                time.sleep(0)
            return matrix_rows(access)

        def done(rows: list[tuple[str, str, str, str]]) -> None:
            text = matrix_csv(rows)
            self._say(f"{len(rows)} person and repository pairs.")
            self._show_text(
                f"Access Review: {org}",
                "\n".join(", ".join(r) for r in rows) or "Nobody has direct access yet.",
            )
            self.frame.copy_text(text)

        self._background("read the access matrix", read, done)

    def _tool_bulk_access(self) -> None:
        who = self._ask_text("Bulk Access Changes", "Team slug or person's login:")
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
        changes = bulk_plan("repository", who, kinds[kind_index], role, targets)
        self._run_changes(changes, "Bulk Access Changes")

    def _tool_account_level(self) -> None:
        from quill.core.github.permissions import AccessStore

        levels = list(AccessLevel)
        index = self._choose(
            "Workbench Level",
            "What the Workbench may change with this account, whatever GitHub allows:",
            [level.label for level in levels],
        )
        if index < 0:
            return
        account = self.account_name()  # type: ignore[attr-defined]
        AccessStore.load().set(account, levels[index])
        self._say(f"{account or 'This account'} is now {levels[index].label} in the Workbench.")

    # -- Access pages: Add, Change Role, Remove (18.3) --------------------------------------

    def table_action(self, target: Any, state: dict[str, Any]) -> Callable[[Any, str, str], None]:
        """The Access buttons on a sheet's list (people, teams, members)."""

        def act(spec: Any, verb: str, row: str) -> None:
            scope = _TABLE_SCOPES.get(target.kind)
            if scope is None or spec.key not in (
                "collaborators",
                "teams",
                "members",
                "maintainers",
            ):
                self._say("This list is changed on GitHub's page; Open on GitHub goes there.")
                return
            ident = state["ident"]
            rows = [parse_row(r) for r in state["loaded"].values.get(spec.key) or ()]
            roles = (
                ["member", "maintainer"]
                if scope == "team"
                else (["member", "owner"] if scope == "organization" else list(REPO_ROLES))
            )
            if verb == "add":
                who = self._ask_text("Add", "Login, or team slug for a team:")
                if not who:
                    return
                index = self._choose("Add", f"Role for {who}:", roles)
                if index < 0:
                    return
                kind = "team" if spec.key == "teams" else "person"
                change = plan_add(scope, ident, who, kind, roles[index])
            else:
                found = parse_row(row)
                if verb == "change":
                    index = self._choose("Change Role", f"New role for {found.name}:", roles)
                    if index < 0:
                        return
                    problem = lockout_problem(
                        rows,
                        found,
                        self.account_name(),  # type: ignore[attr-defined]
                        new_role=roles[index],
                    )
                    change = plan_change(scope, ident, found, roles[index])
                else:
                    problem = lockout_problem(rows, found, self.account_name())  # type: ignore[attr-defined]
                    change = plan_remove(scope, ident, found)
                if problem:
                    self._say(problem)
                    return
            self._run_changes([change], target.title())

        return act

    def _run_changes(self, changes: list[Any], title: str) -> None:
        """Preview every change in words, then send them, a result per change (18.4)."""
        if not changes:
            return
        tier = max(change.tier for change in changes)
        words = "\n".join(change.words for change in changes)
        if not self.confirm_tier(max(tier, WriteTier.ACCESS), words, str(len(changes))):  # type: ignore[attr-defined]
            return
        api = self.github_api()  # type: ignore[attr-defined]

        def work() -> list[str]:
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
            return results

        def done(results: list[str]) -> None:
            failed = sum(1 for r in results if "Failed:" in r)
            self._say(f"{len(results) - failed} done, {failed} failed.")
            self._record_access(changes, results)
            if len(results) > 1 or failed:
                self._show_text(title, "\n".join(results))

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
