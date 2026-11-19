"""Pending invitations on an Access page: Add, Change Role and Remove (GH-R-063).

The Access page's buttons act on the Pending invitations list as they do on
People: Add invites someone, Change Role changes what a repository
invitation offers, and Remove cancels the invitation. Each is previewed and
recorded like every other access change; the work is
:mod:`quill.core.github.access_invitations`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.access import parse_row, plan_add
from quill.core.github.access_invitations import (
    find_invitation,
    invitations_path,
    plan_cancel_invitation,
    plan_invitation_role,
)
from quill.core.github.permissions import REPO_ROLES

__all__ = ["GitHubWorkbenchInvitationsMixin"]


class GitHubWorkbenchInvitationsMixin:
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _run_changes: Callable[[list[Any], str], None]
    github_api: Callable[[], Any]

    def act_on_invitation(
        self, scope: str, ident: dict[str, str], verb: str, row: str, title: str
    ) -> None:
        roles = ["member", "owner"] if scope == "organization" else list(REPO_ROLES)
        if verb == "add":
            who = self._ask_text("Add", "Login or email to invite:")
            if not who:
                return
            index = self._choose("Add", f"Role for {who}:", roles)
            if index >= 0:
                self._run_changes([plan_add(scope, ident, who, "person", roles[index])], title)
            return
        who = parse_row(row).name
        if not who:
            self._say("Select an invitation first.")
            return
        role = ""
        if verb == "change":
            if scope != "repository":
                self._say(
                    "GitHub cannot change an organization invitation's role. Remove it and "
                    "invite them again with the role you want."
                )
                return
            index = self._choose("Change Role", f"Role to offer {who}:", roles)
            if index < 0:
                return
            role = roles[index]
        api = self.github_api()

        def find() -> int | None:
            found = api.rest("GET", invitations_path(scope, ident), query={"per_page": "100"})
            return find_invitation(found.data if isinstance(found.data, list) else [], who)

        def found(number: int | None) -> None:
            if number is None:
                self._say(f"There is no pending invitation for {who} any more.")
                return
            change = (
                plan_invitation_role(ident, number, who, role)
                if role
                else plan_cancel_invitation(scope, ident, number, who)
            )
            self._run_changes([change], title)

        self._background("find the invitation", find, found)
