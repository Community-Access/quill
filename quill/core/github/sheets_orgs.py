"""The Organization sheet (GitHub PRD Appendix C, 18.3).

Profile, your membership (public or private), members (each an owner or a
member, with two-factor on or off where you may see it), teams, outside
collaborators, invitations, roles, member privileges and the
base repository permission, Actions permissions, webhooks, secrets, issue
types, custom properties and token requests. Member privileges and the base
permission are tier 2: a preview in words, owners only.

The Team sheet (18.3.3) is in :mod:`quill.core.github.sheets_teams`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Read, SheetDef
from quill.core.github.sheet_fields import dig, ed, lst, page, patch, ro, toggle, when
from quill.core.github.sheets_you import FOLLOW_ORGANIZATION, ORG_YOU_READ, sponsoring_field
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["ORGANIZATION"]

_O, _V, _A = WriteTier.ORGANIZING, WriteTier.VISIBLE, WriteTier.ACCESS
_K = FieldKind
_ORG = "/orgs/{org}"
_OWNER = "org:owner"


def _items(key: str, render: Any) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        rows = data.get("items") if isinstance(data.get("items"), list) else lst(data, key)
        return {key: tuple(render(row) for row in rows or () if isinstance(row, Mapping))}

    return extract


_PRIVILEGES = (
    ("members_can_create_public_repositories", "Members may create public repositories"),
    ("members_can_create_private_repositories", "Members may create private repositories"),
    ("members_can_create_internal_repositories", "Members may create internal repositories"),
    ("members_can_fork_private_repositories", "Members may fork private repositories"),
    ("members_can_create_pages", "Members may create Pages sites"),
    ("web_commit_signoff_required", "Require sign-off on web commits"),
)


def _organization(data: Mapping[str, Any]) -> dict[str, Value]:
    found: dict[str, Value] = {
        "login": str(data.get("login") or ""),
        "name": str(data.get("name") or ""),
        "description": str(data.get("description") or ""),
        "email": str(data.get("email") or ""),
        "location": str(data.get("location") or ""),
        "blog": str(data.get("blog") or ""),
        "base_permission": str(data.get("default_repository_permission") or ""),
        "two_factor": bool(data.get("two_factor_requirement_enabled")),
        "repositories": int(data.get("public_repos") or 0)
        + int(data.get("total_private_repos") or 0),
        "created": when(data.get("created_at")),
        "url": str(data.get("html_url") or ""),
    }
    for key, _label in _PRIVILEGES:
        found[key] = bool(data.get(key))
    return found


def _login(row: Mapping[str, Any]) -> str:
    return str(row.get("login", ""))


def _invitation_row(row: Mapping[str, Any]) -> str:
    who = row.get("login") or row.get("email") or ""
    return f"{who}, {row.get('role', '')}"


def _membership(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "your_org_role": "owner" if data.get("role") == "admin" else str(data.get("role") or "")
    }


def _names(values: Mapping[str, Value], key: str) -> tuple[str, ...]:
    found = values.get(key)
    return tuple(str(name) for name in found) if isinstance(found, tuple) else ()


def _people(values: Mapping[str, Value]) -> dict[str, Value]:
    """Members with their role and two-factor, outside collaborators by name (Access rows)."""
    owners = {o.casefold() for o in _names(values, "owner_logins")}
    hidden = bool(values.get("two_factor_hidden"))
    off = {o.casefold() for o in _names(values, "no_two_factor")}

    def member(login: str) -> str:
        role = "owner" if login.casefold() in owners else "member"
        factor = "not shown to you" if hidden else ("off" if login.casefold() in off else "on")
        return f"{login}, person, {role}, direct, two-factor {factor}"

    members = tuple(member(m) for m in _names(values, "member_logins"))
    outside = tuple(
        f"{o}, person, outside collaborator, repositories only"
        for o in _names(values, "outside_logins")
    )
    return {"members": members, "outside": outside}


def _public(_data: Mapping[str, Any]) -> dict[str, Value]:
    return {"public_member": True}


def _actions(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "actions_repositories": str(data.get("enabled_repositories") or "all"),
        "allowed_actions": str(data.get("allowed_actions") or "all"),
    }


ORGANIZATION = SheetDef(
    "organization",
    SheetSpec(
        "organization",
        "Organization",
        (
            page(
                "general",
                "General",
                ro("login", "Login"),
                ed("name", "Name"),
                ed("description", "Description"),
                ed("email", "Public email"),
                ed("location", "Location"),
                ed("blog", "Website"),
                ro("created", "Created", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "you",
                "You",
                ed(
                    "following",
                    "Following",
                    _K.CHECK,
                    "Follow it to see its public activity in your feed.",
                ),
                ed("public_member", "Show my membership publicly", _K.CHECK),
                ro("your_org_role", "Your role"),
                sponsoring_field(),
            ),
            page(
                "members",
                "Members",
                ro(
                    "members",
                    "Members",
                    _K.TABLE,
                    "Each member, owner or member, and whether two-factor sign-in is on "
                    "(owners see that). Add invites; Change Role and Remove act on the "
                    "selected row, each previewed; Change Role to outside collaborator "
                    "converts them, after their name is typed. You cannot remove or lower "
                    "yourself when that would leave nobody to manage the organization.",
                ),
            ),
            page("teams", "Teams", ro("teams", "Teams", _K.TABLE)),
            page(
                "outside",
                "Outside Collaborators",
                ro(
                    "outside",
                    "Outside collaborators",
                    _K.TABLE,
                    "People with access to some repositories who are not members. Add makes "
                    "a member an outside collaborator; Change Role invites one to be a "
                    "member; Remove takes away every repository they have here.",
                ),
            ),
            page("invitations", "Invitations", ro("invitations", "Pending invitations", _K.TABLE)),
            page("roles", "Roles", ro("roles", "Organization roles", _K.TABLE)),
            page(
                "privileges",
                "Member Privileges",
                ed(
                    "base_permission",
                    "Base repository permission",
                    _K.CHOICE,
                    "What every member may do in every repository, before teams and direct access.",
                    choices=("none", "read", "write", "admin"),
                ),
                *(ed(key, label, _K.CHECK) for key, label in _PRIVILEGES),
                ro("two_factor", "Two-factor authentication required", _K.CHECK),
            ),
            page("repositories", "Repositories", ro("repositories", "Repositories", _K.NUMBER)),
            page(
                "actions",
                "Actions",
                ed(
                    "actions_repositories",
                    "Repositories that may use Actions",
                    _K.CHOICE,
                    choices=("all", "none", "selected"),
                ),
                ed(
                    "allowed_actions",
                    "Allowed actions",
                    _K.CHOICE,
                    choices=("all", "local_only", "selected"),
                ),
            ),
            page("webhooks", "Webhooks", ro("hooks", "Webhooks", _K.TABLE)),
            page(
                "secrets",
                "Secrets and Variables",
                ro("secrets", "Secrets", _K.TABLE, "Names only."),
                ro("variables", "Variables", _K.TABLE),
            ),
            page("issue_types", "Issue Types", ro("issue_types", "Issue types", _K.TABLE)),
            page(
                "properties",
                "Custom Properties",
                ro("custom_properties", "Custom properties", _K.TABLE),
            ),
            page(
                "tokens",
                "Token Requests",
                ro("token_requests", "Fine-grained token requests", _K.TABLE),
            ),
            page(
                "audit",
                "Audit Log",
                ro(
                    "audit_note",
                    "Audit log",
                    help="Audit Log... on the organization's row reads it, newest first, "
                    "and searches it. GitHub offers it only to organizations on GitHub "
                    "Enterprise Cloud; elsewhere it says why in GitHub's own words, and "
                    "Open on GitHub reads it.",
                ),
            ),
        ),
    ),
    (
        Read(_ORG, _organization),
        Read("/user/memberships/orgs/{org}", _membership, optional=True),
        ORG_YOU_READ,
        Read(
            _ORG + "/public_members/{me}", _public, optional=True, fallback={"public_member": False}
        ),
        Read(
            _ORG + "/members",
            _items("member_logins", _login),
            optional=True,
            query=lambda _i: {"per_page": "100"},
        ),
        Read(
            _ORG + "/members",
            _items("owner_logins", _login),
            optional=True,
            query=lambda _i: {"role": "admin", "per_page": "100"},
        ),
        Read(
            _ORG + "/members",
            _items("no_two_factor", _login),
            optional=True,
            fallback={"two_factor_hidden": True},
            query=lambda _i: {"filter": "2fa_disabled", "per_page": "100"},
        ),
        Read(
            _ORG + "/teams",
            _items("teams", lambda r: f"{r.get('name', '')}, {r.get('privacy', '')}"),
            optional=True,
        ),
        Read(_ORG + "/outside_collaborators", _items("outside_logins", _login), optional=True),
        Read(_ORG + "/invitations", _items("invitations", _invitation_row), optional=True),
        Read(
            _ORG + "/organization-roles",
            _items("roles", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(_ORG + "/actions/permissions", _actions, optional=True),
        Read(
            _ORG + "/hooks",
            _items("hooks", lambda r: str(dig(r, "config", "url") or "")),
            optional=True,
        ),
        Read(
            _ORG + "/actions/secrets",
            _items("secrets", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(
            _ORG + "/actions/variables",
            _items("variables", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(
            _ORG + "/issue-types",
            _items(
                "issue_types",
                lambda r: f"{r.get('name', '')}, {'on' if r.get('is_enabled') else 'off'}",
            ),
            optional=True,
        ),
        Read(
            _ORG + "/properties/schema",
            _items("custom_properties", lambda r: str(r.get("property_name", ""))),
            optional=True,
        ),
        Read(
            _ORG + "/personal-access-token-requests",
            _items("token_requests", lambda r: str(dig(r, "owner", "login") or "")),
            optional=True,
        ),
    ),
    {
        "name": patch(_ORG, _OWNER, _V),
        "description": patch(_ORG, _OWNER, _V),
        "email": patch(_ORG, _OWNER, _V),
        "location": patch(_ORG, _OWNER, _V),
        "blog": patch(_ORG, _OWNER, _V),
        "base_permission": patch(_ORG, _OWNER, _A, "default_repository_permission"),
        **{key: patch(_ORG, _OWNER, _A) for key, _label in _PRIVILEGES},
        "following": FOLLOW_ORGANIZATION,
        "public_member": toggle(_ORG + "/public_members/{me}", "org:member", _O),
        "actions_repositories": patch(
            _ORG + "/actions/permissions", _OWNER, _A, "enabled_repositories", method="PUT"
        ),
        "allowed_actions": patch(_ORG + "/actions/permissions", _OWNER, _A, method="PUT"),
    },
    title=lambda ident: ident["org"],
    url=lambda ident: f"https://github.com/{ident['org']}",
    derive=_people,
)
