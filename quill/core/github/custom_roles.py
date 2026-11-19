"""Custom repository roles, custom organization roles and the audit log (GitHub PRD 18.3, 18.6).

All three are GitHub Enterprise Cloud features. QUILL does not guess whether
an organization has it: it asks, and when GitHub refuses, it says so in
GitHub's own words with the status, then what that usually means:

    GitHub refused to read the audit log of acme: Not Found (HTTP 404). The
    audit log API is for organizations on GitHub Enterprise Cloud; Open on
    GitHub reads this organization's audit log on any plan.

* **Custom repository roles** (``/orgs/{org}/custom-repository-roles``):
  list, create (a name, a description, a base role and the permissions it
  adds), change and delete; :func:`repository_permissions` lists the
  permissions a role may add, in GitHub's words.
* **Organization roles** (``/orgs/{org}/organization-roles``): create,
  change and delete a custom one; giving and taking roles is
  :mod:`quill.core.github.org_admin`.
* **Audit log** (``/orgs/{org}/audit-log``): newest first, optionally
  searched with GitHub's phrase syntax ("action:repo.create actor:kim").

wx-free and strict-typed.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from quill.core.github.org_people import describe_refusal
from quill.core.github.quick_actions import QuickError, bulleted, fill
from quill.core.github.rest_transport import GitHubRestError

__all__ = [
    "BASE_ROLES",
    "audit_lines",
    "audit_log",
    "custom_role_lines",
    "custom_role_picks",
    "custom_roles",
    "delete_custom_role",
    "delete_org_role",
    "org_permissions",
    "org_role_picks",
    "permission_lines",
    "repository_permissions",
    "save_custom_role",
    "save_org_role",
]

#: The roles a custom repository role builds on.
BASE_ROLES: tuple[str, ...] = ("read", "triage", "write", "maintain")

_ENTERPRISE = {
    "audit": "The audit log API is for organizations on GitHub Enterprise Cloud; Open on "
    "GitHub reads this organization's audit log on any plan.",
    "custom": "Custom repository roles are a GitHub Enterprise Cloud feature; an "
    "organization on another plan has only the five built-in roles.",
    "org": "Custom organization roles are a GitHub Enterprise Cloud feature; an organization "
    "on another plan can give its built-in roles only.",
}


def _call(api: Any, method: str, path: str, ctx: Mapping[str, str], what: str, kind: str,
          body: Any = None, query: dict[str, str] | None = None) -> Any:  # fmt: skip
    """One call; a refusal said in GitHub's words, then what it usually means."""
    try:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["body"] = body
        if query:
            kwargs["query"] = query
        return api.rest(method, fill(path, ctx), **kwargs).data
    except GitHubRestError as exc:
        said = f"GitHub refused to {what}: {describe_refusal(exc)}."
        if exc.status in (403, 404, 410, 422):
            said += " " + _ENTERPRISE[kind]
        raise QuickError(said) from exc


# -- custom repository roles ---------------------------------------------------------------


def custom_roles(api: Any, ctx: dict[str, str]) -> list[Mapping[str, Any]]:
    data = _call(
        api,
        "GET",
        "/orgs/{org}/custom-repository-roles",
        ctx,
        f"list the custom repository roles of {ctx.get('org')}",
        "custom",
    )
    rows = data.get("custom_roles") if isinstance(data, Mapping) else data
    return [row for row in rows or () if isinstance(row, Mapping)]


def _role_line(role: Mapping[str, Any]) -> str:
    adds = ", ".join(str(p).replace("_", " ") for p in role.get("permissions") or ())
    about = f": {role['description']}" if role.get("description") else ""
    base = f", based on {role.get('base_role')}" if role.get("base_role") else ""
    return f"{role.get('name')}{base}{about}. Adds: {adds or 'nothing'}."


def custom_role_lines(data: Any, _ctx: dict[str, str]) -> str:
    rows = [_role_line(r) for r in data or () if isinstance(r, Mapping)]
    return bulleted(rows, "This organization has no custom repository roles.")


def custom_role_picks(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [(str(r.get("name")), str(r.get("id"))) for r in custom_roles(api, ctx)]


def _permissions(text: str) -> list[str]:
    return [p.strip().replace(" ", "_") for p in text.split(",") if p.strip()]


def save_custom_role(api: Any, ctx: dict[str, str]) -> Any:
    """Create a custom repository role, or change the picked one (only the answers given)."""
    body: dict[str, object] = {}
    for key in ("name", "description", "base_role"):
        if ctx.get(key):
            body[key] = ctx[key]
    if ctx.get("permissions"):
        body["permissions"] = _permissions(ctx["permissions"])
    if ctx.get("role"):
        return _call(api, "PATCH", "/orgs/{org}/custom-repository-roles/{role}", ctx,
                     f"change the role {ctx.get('role_label', '')}", "custom", body)  # fmt: skip
    if not body.get("permissions"):
        raise QuickError("A custom role adds at least one permission to its base role.")
    return _call(api, "POST", "/orgs/{org}/custom-repository-roles", ctx,
                 f"make the role {ctx.get('name', '')}", "custom", body)  # fmt: skip


def delete_custom_role(api: Any, ctx: dict[str, str]) -> Any:
    return _call(api, "DELETE", "/orgs/{org}/custom-repository-roles/{role}", ctx,
                 f"delete the role {ctx.get('role_label', '')}", "custom")  # fmt: skip


def repository_permissions(api: Any, ctx: dict[str, str]) -> Any:
    return _call(api, "GET", "/orgs/{org}/repository-fine-grained-permissions", ctx,
                 "list the permissions a custom role may add", "custom")  # fmt: skip


def permission_lines(data: Any, _ctx: dict[str, str]) -> str:
    rows = [
        f"{p.get('name')}: {p.get('description') or 'no description'}"
        for p in data or ()
        if isinstance(p, Mapping)
    ]
    return bulleted(rows, "GitHub listed no permissions.")


# -- organization roles ------------------------------------------------------------------


def org_role_picks(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = _call(api, "GET", "/orgs/{org}/organization-roles", ctx,
                 "list the organization's roles", "org")  # fmt: skip
    rows = data.get("roles") if isinstance(data, Mapping) else data
    return [
        (str(r.get("name")), str(r.get("id")))
        for r in rows or ()
        if isinstance(r, Mapping) and str(r.get("source") or "Organization") == "Organization"
    ]


def save_org_role(api: Any, ctx: dict[str, str]) -> Any:
    body: dict[str, object] = {}
    for key in ("name", "description", "base_role"):
        if ctx.get(key):
            body[key] = ctx[key]
    if ctx.get("permissions"):
        body["permissions"] = _permissions(ctx["permissions"])
    if ctx.get("role"):
        return _call(api, "PATCH", "/orgs/{org}/organization-roles/{role}", ctx,
                     f"change the role {ctx.get('role_label', '')}", "org", body)  # fmt: skip
    return _call(api, "POST", "/orgs/{org}/organization-roles", ctx,
                 f"make the role {ctx.get('name', '')}", "org", body)  # fmt: skip


def delete_org_role(api: Any, ctx: dict[str, str]) -> Any:
    return _call(api, "DELETE", "/orgs/{org}/organization-roles/{role}", ctx,
                 f"delete the role {ctx.get('role_label', '')}", "org")  # fmt: skip


def org_permissions(api: Any, ctx: dict[str, str]) -> Any:
    return _call(api, "GET", "/orgs/{org}/organization-fine-grained-permissions", ctx,
                 "list the permissions an organization role may hold", "org")  # fmt: skip


# -- the audit log ---------------------------------------------------------------------


def audit_log(api: Any, ctx: dict[str, str]) -> Any:
    query = {"per_page": "100", "order": "desc"}
    if ctx.get("phrase"):
        query["phrase"] = ctx["phrase"]
    return _call(api, "GET", "/orgs/{org}/audit-log", ctx,
                 f"read the audit log of {ctx.get('org')}", "audit", query=query)  # fmt: skip


def _when(event: Mapping[str, Any]) -> str:
    stamp = event.get("@timestamp") or event.get("created_at")
    if isinstance(stamp, (int, float)):
        moment = dt.datetime.fromtimestamp(stamp / 1000, tz=dt.UTC)
        return moment.strftime("%Y-%m-%d %H:%M UTC")
    return str(stamp or "")[:16].replace("T", " ")


def audit_lines(data: Any, ctx: dict[str, str]) -> str:
    """Each event as a sentence: "2026-11-19 10:02 UTC: kim did repo.create on acme/site"."""
    rows = []
    for event in data or ():
        if not isinstance(event, Mapping):
            continue
        said = f"{_when(event)}: {event.get('actor') or 'someone'} did {event.get('action')}"
        where = event.get("repo") or event.get("team") or event.get("user")
        rows.append(said + (f" on {where}" if where else ""))
    found = "searching for " + ctx["phrase"] if ctx.get("phrase") else ""
    return bulleted(rows, f"The audit log has nothing {found or 'yet'}.".replace("  ", " "))
