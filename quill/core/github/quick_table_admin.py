"""Quick commands for an organization's administration (GitHub PRD 18.3, 18.4, 18.6).

On an organization's row:

* **Custom Repository Roles**, **New Custom Repository Role...**, **Change
  Custom Repository Role...**, **Delete Custom Repository Role...** and
  **Permissions for Custom Roles**;
* **New Organization Role...**, **Change Organization Role...**, **Delete
  Organization Role...** and **Permissions for Organization Roles** (giving
  and taking roles is Organization Roles..., :mod:`quill.core.github.org_admin`);
* **Audit Log...**, newest first, searched with GitHub's phrase syntax;
* **Members Without Two-Factor**.

The roles and the audit log are GitHub Enterprise Cloud features; when GitHub
refuses, the refusal is said in GitHub's words (:mod:`quill.core.github.custom_roles`).
Deleting a role is tier 3: its name is typed first.

wx-free and strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.github import custom_roles as roles
from quill.core.github.quick_actions import Ask, Quick, bulleted, call

__all__ = ["ADMIN_QUICK"]

_ORG = frozenset({"org"})
_MENU = ("organization",)
_ENTERPRISE = "needs Jeff: an organization on GitHub Enterprise Cloud"
_KEEP = "Keep it as it is"


def _role_asks(base: tuple[str, ...], *, change: bool) -> tuple[Ask, ...]:
    """Name, description, base role and permissions; a change keeps whatever is left empty."""
    keep = (_KEEP,) if change else ()
    return (
        Ask("name", "Its new name (empty keeps it):" if change else "The role's name:",
            optional=change),
        Ask("description", "What it is for (optional):", optional=True),
        Ask("base_role", "The role it builds on:", "choice", (*keep, *base),
            (*(("",) if change else ()), *base)),
        Ask("permissions", "The permissions it adds, separated by commas (Permissions for "
            "Custom Roles lists them):", optional=True),
    )  # fmt: skip


def _two_factor(data: Any, _ctx: dict[str, str]) -> str:
    rows = [str(r.get("login")) for r in data or () if isinstance(r, dict)]
    return bulleted(rows, "Every member has two-factor sign-in on.")


ADMIN_QUICK: tuple[Quick, ...] = (
    Quick("custom_repo_roles", "Custom Repository Roles", _MENU, _ORG,
          "The organization's own repository roles: each one's base role and what it adds.",
          ("GET /orgs/{org}/custom-repository-roles",),
          roles.custom_roles, roles.custom_role_lines, report=True, needs=("org",)),
    Quick("new_custom_repo_role", "New Custom Repository Role...", _MENU, _ORG,
          "Make a repository role: a base role and the permissions it adds.",
          ("POST /orgs/{org}/custom-repository-roles",),
          roles.save_custom_role, lambda _d, ctx: f"Made the role {ctx['name']}.", tier="A",
          need="org:owner", asks=_role_asks(roles.BASE_ROLES, change=False), needs=("org",),
          live=_ENTERPRISE),
    Quick("change_custom_repo_role", "Change Custom Repository Role...", _MENU, _ORG,
          "Change a custom repository role's name, description, base role or permissions.",
          ("PATCH /orgs/{org}/custom-repository-roles/{role_id}",),
          roles.save_custom_role, lambda _d, ctx: f"Changed the role {ctx['role_label']}.",
          tier="A", need="org:owner", pick=roles.custom_role_picks, pick_key="role",
          pick_question="Which role?", asks=_role_asks(roles.BASE_ROLES, change=True),
          needs=("org",), live=_ENTERPRISE),
    Quick("delete_custom_repo_role", "Delete Custom Repository Role...", _MENU, _ORG,
          "Delete a custom repository role; whoever has it keeps its base role.",
          ("DELETE /orgs/{org}/custom-repository-roles/{role_id}",),
          roles.delete_custom_role, lambda _d, ctx: f"Deleted the role {ctx['role_label']}.",
          tier="D", need="org:owner", pick=roles.custom_role_picks, pick_key="role",
          pick_question="Which role?",
          confirm="Delete the role {role_label}? People and teams given it keep its base role "
          "and lose what it adds.", typed="role_label", needs=("org",), live=_ENTERPRISE),
    Quick("custom_role_permissions", "Permissions for Custom Roles", _MENU, _ORG,
          "Every permission a custom repository role can add, in GitHub's words.",
          ("GET /orgs/{org}/repository-fine-grained-permissions",),
          roles.repository_permissions, roles.permission_lines, report=True, needs=("org",)),
    Quick("new_org_role", "New Organization Role...", _MENU, _ORG,
          "Make an organization role: the organization permissions it holds.",
          ("POST /orgs/{org}/organization-roles",),
          roles.save_org_role, lambda _d, ctx: f"Made the role {ctx['name']}.", tier="A",
          need="org:owner",
          asks=_role_asks(("read", "triage", "write", "maintain", "admin"), change=False),
          needs=("org",), live=_ENTERPRISE),
    Quick("change_org_role", "Change Organization Role...", _MENU, _ORG,
          "Change a custom organization role's name, description or permissions.",
          ("PATCH /orgs/{org}/organization-roles/{role_id}",),
          roles.save_org_role, lambda _d, ctx: f"Changed the role {ctx['role_label']}.",
          tier="A", need="org:owner", pick=roles.org_role_picks, pick_key="role",
          pick_question="Which role?",
          asks=_role_asks(("read", "triage", "write", "maintain", "admin"), change=True),
          needs=("org",), live=_ENTERPRISE),
    Quick("delete_org_role", "Delete Organization Role...", _MENU, _ORG,
          "Delete a custom organization role; whoever holds it loses it.",
          ("DELETE /orgs/{org}/organization-roles/{role_id}",),
          roles.delete_org_role, lambda _d, ctx: f"Deleted the role {ctx['role_label']}.",
          tier="D", need="org:owner", pick=roles.org_role_picks, pick_key="role",
          pick_question="Which role?",
          confirm="Delete the role {role_label}? Every person and team holding it loses it.",
          typed="role_label", needs=("org",), live=_ENTERPRISE),
    Quick("org_role_permissions", "Permissions for Organization Roles", _MENU, _ORG,
          "Every permission an organization role can hold, in GitHub's words.",
          ("GET /orgs/{org}/organization-fine-grained-permissions",),
          roles.org_permissions, roles.permission_lines, report=True, needs=("org",)),
    Quick("audit_log", "Audit Log...", _MENU, _ORG,
          "What people did in the organization, newest first; search with GitHub's words, "
          "such as action:repo.create or actor:kim.",
          ("GET /orgs/{org}/audit-log",),
          roles.audit_log, roles.audit_lines, report=True,
          asks=(Ask("phrase", "Search for (empty lists everything recent):", optional=True),),
          needs=("org",)),
    Quick("two_factor_off", "Members Without Two-Factor", _MENU, _ORG,
          "Members who have not turned on two-factor sign-in. GitHub shows this to owners.",
          ("GET /orgs/{org}/members",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/members?filter=2fa_disabled"
                                "&per_page=100", ctx),
          _two_factor, report=True, needs=("org",)),
)  # fmt: skip
