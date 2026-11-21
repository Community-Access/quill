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
- **Roles and Access:** this account's Workbench level here, and Access
  Templates and Apply Access Template (GH-R-068,
  :mod:`quill.ui.github_workbench_access_templates`); the rest (My Access
  Here, View As Role, Compare Roles, Why Can't They?, Access Review, Bulk
  Access Changes, Compare Accounts, Act As) is
  :mod:`quill.ui.github_workbench_roles`, answered from GitHub's replies.
- **Access pages:** Add..., Change Role... and Remove on a sheet's list, each
  previewed in words, refused when it would lock you out (18.4), and recorded:
  :mod:`quill.ui.github_workbench_access_pages`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.permissions import (
    SCOPES,
    AccessLevel,
    classic_token_url,
    fine_grained_steps,
    gh_refresh_command,
    missing_scopes,
    scope_rows,
)
from quill.ui.github_workbench_access_pages import GitHubWorkbenchAccessPagesMixin
from quill.ui.github_workbench_access_templates import GitHubWorkbenchAccessTemplatesMixin
from quill.ui.github_workbench_least_privilege import GitHubWorkbenchLeastPrivilegeMixin
from quill.ui.github_workbench_roles import ROLE_TOOLS, GitHubWorkbenchRolesMixin

__all__ = ["GitHubWorkbenchToolsMixin"]

_P = "github.workbench."
_TOOLS = frozenset({
    "filter_builder",
    "permissions",
    "change_history",
    "access_templates",  # GH-R-068: github_workbench_access_templates.py
    "apply_access_template",
    "account_level",
    "least_privilege",
    *ROLE_TOOLS,
})


class GitHubWorkbenchToolsMixin(
    GitHubWorkbenchAccessPagesMixin,
    GitHubWorkbenchAccessTemplatesMixin,
    GitHubWorkbenchLeastPrivilegeMixin,
    GitHubWorkbenchRolesMixin,
):
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

    # -- Teams in the tree (18.3.3, GH-R-143) -------------------------------------

    def load_teams(self, loader: str, organization: str) -> list[Any]:
        """Organizations > org > Teams, or People > My Teams. Runs off the UI thread."""
        from quill.core.github.explore_models import ExploreRow
        from quill.core.github.sheets_teams import team_privacy

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
            label = f"{team.get('name', '')}{mine}{where}, {team_privacy(team)}"
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

    # -- Roles (18.2): the rest is quill.ui.github_workbench_roles --------------------------

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
        AccessStore.load().set(self.level_key(), levels[index])  # type: ignore[attr-defined]
        self._say(f"{account or 'This account'} is now {levels[index].label} in the Workbench.")
