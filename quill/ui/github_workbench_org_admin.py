"""An organization's Roles and Rulesets, from its row in the GitHub Workbench.

The work is in :mod:`quill.core.github.org_admin` and the windows in
:mod:`quill.ui.github_org_admin_dialog`; this mixin reads the list first, in
the background, and opens the window with it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["ORG_ADMIN_REASONS", "ORG_ADMIN_VERBS", "GitHubWorkbenchOrgAdminMixin"]

ORG_ADMIN_VERBS: dict[str, frozenset[str]] = {
    "org_roles": frozenset({"org"}),
    "org_rulesets": frozenset({"org"}),
}

ORG_ADMIN_REASONS: dict[str, str] = {
    verb: "This is for an organization's row, while you are signed in." for verb in ORG_ADMIN_VERBS
}


class GitHubWorkbenchOrgAdminMixin:
    items: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _parent: Callable[[], Any]

    def _org_login(self, row: object) -> str:
        if isinstance(row, ExploreRow) and row.kind == "org" and row.key:
            return str(row.key)
        return ""

    def _fits_org_admin(self, row: object) -> bool:
        return self.signed_in and bool(self._org_login(row))

    _fits_org_roles = _fits_org_admin
    _fits_org_rulesets = _fits_org_admin

    def _org_api(self) -> Any:
        from quill.core.github.org_admin import GitHubOrgAdmin

        return GitHubOrgAdmin(getattr(self.items, "token", None))

    def _do_org_roles(self, _ref: Any, row: object) -> None:
        org = self._org_login(row)
        if not org:
            return
        api = self._org_api()

        def open_window(roles: Any) -> None:
            from quill.ui.github_org_admin_dialog import OrgRolesDialog

            self._say(f"{org} has {len(roles)} organization roles.")
            OrgRolesDialog(self._parent(), api, org=org, roles=roles, announce_cb=self._say).show()

        self._background("read the organization's roles", lambda: api.roles(org), open_window)

    def _do_org_rulesets(self, _ref: Any, row: object) -> None:
        org = self._org_login(row)
        if not org:
            return
        api = self._org_api()

        def open_window(rulesets: Any) -> None:
            from quill.ui.github_org_admin_dialog import OrgRulesetsDialog

            self._say(f"{org} has {len(rulesets)} rulesets.")
            OrgRulesetsDialog(
                self._parent(), api, org=org, rulesets=rulesets, announce_cb=self._say
            ).show()

        self._background("read the organization's rulesets", lambda: api.rulesets(org), open_window)
