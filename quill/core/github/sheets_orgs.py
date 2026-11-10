"""Sheets for organizations and teams (GitHub PRD Appendix C, 18.3, 18.3.3, GH-R-140, 141).

The Organization sheet: profile, your membership (public or private), members,
teams, outside collaborators, invitations, roles, member privileges and the
base repository permission, Actions permissions, webhooks, secrets, issue
types, custom properties and token requests. Member privileges and the base
permission are tier 2: a preview in words, owners only.

The Team sheet (18.3.3): name, description, visibility, parent, notifications
and your role on it; members and maintainers; repositories and the team's
role on each; projects; child teams; code review assignment (on or off, round
robin or load balance, how many reviewers, notify the whole team: GH-R-141);
identity provider groups; and the Danger Zone note. Lists are changed from the
Access buttons (:mod:`quill.core.github.access`), each previewed.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, page, patch, ro, toggle, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["ORGANIZATION", "TEAM", "TEAM_REVIEW_QUERY"]

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


def _invitation_row(row: Mapping[str, Any]) -> str:
    who = row.get("login") or row.get("email") or ""
    return f"{who}, {row.get('role', '')}"


def _membership(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "your_org_role": "owner" if data.get("role") == "admin" else str(data.get("role") or "")
    }


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
                ro("your_org_role", "Your role"),
                ed("public_member", "Show my membership publicly", _K.CHECK),
            ),
            page(
                "members",
                "Members",
                ro(
                    "members",
                    "Members",
                    _K.TABLE,
                    "Each member and "
                    "their role. Add invites; Change Role and Remove "
                    "act on the selected row, each previewed.",
                ),
            ),
            page("teams", "Teams", ro("teams", "Teams", _K.TABLE)),
            page(
                "outside", "Outside Collaborators", ro("outside", "Outside collaborators", _K.TABLE)
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
                    help="The audit log API "
                    "is for GitHub Enterprise Cloud; Open on GitHub "
                    "reads it otherwise.",
                ),
            ),
        ),
    ),
    (
        Read(_ORG, _organization),
        Read("/user/memberships/orgs/{org}", _membership, optional=True),
        Read(
            _ORG + "/public_members/{me}", _public, optional=True, fallback={"public_member": False}
        ),
        Read(
            _ORG + "/members", _items("members", lambda r: str(r.get("login", ""))), optional=True
        ),
        Read(
            _ORG + "/teams",
            _items("teams", lambda r: f"{r.get('name', '')}, {r.get('privacy', '')}"),
            optional=True,
        ),
        Read(
            _ORG + "/outside_collaborators",
            _items("outside", lambda r: str(r.get("login", ""))),
            optional=True,
        ),
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
        "public_member": toggle(_ORG + "/public_members/{me}", "org:member", _O),
        "actions_repositories": patch(
            _ORG + "/actions/permissions", _OWNER, _A, "enabled_repositories", method="PUT"
        ),
        "allowed_actions": patch(_ORG + "/actions/permissions", _OWNER, _A, method="PUT"),
    },
    title=lambda ident: ident["org"],
    url=lambda ident: f"https://github.com/{ident['org']}",
)


# ---------------------------------------------------------------------------
# Teams (18.3.3)
# ---------------------------------------------------------------------------

_TEAM = "/orgs/{org}/teams/{team}"

TEAM_REVIEW_QUERY = (
    "query($org:String!,$team:String!){organization(login:$org){team(slug:$team){id "
    "viewerCanAdminister reviewRequestDelegationEnabled reviewRequestDelegationAlgorithm "
    "reviewRequestDelegationMemberCount reviewRequestDelegationNotifyTeam "
    "projectsV2(first:50){nodes{title}}}}}"
)
_REVIEW_MUTATION = (
    "mutation($id:ID!,$enabled:Boolean!,$algorithm:TeamReviewAssignmentAlgorithm,"
    "$count:Int,$notify:Boolean){updateTeamReviewAssignment(input:{id:$id,enabled:$enabled,"
    "algorithm:$algorithm,teamMemberCount:$count,notifyTeam:$notify}){team{id}}}"
)
_ALGORITHMS = {"round robin": "ROUND_ROBIN", "load balance": "LOAD_BALANCE"}


def _team(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "slug": str(data.get("slug") or ""),
        "description": str(data.get("description") or ""),
        "privacy": "visible" if data.get("privacy") == "closed" else "secret",
        "parent": str(dig(data, "parent", "slug") or ""),
        "notifications": data.get("notification_setting") != "notifications_disabled",
        "members_count": int(data.get("members_count") or 0),
        "repos_count": int(data.get("repos_count") or 0),
        "created": when(data.get("created_at")),
        "url": str(data.get("html_url") or ""),
    }


def _team_role(data: Mapping[str, Any]) -> dict[str, Value]:
    role = str(data.get("role") or "")
    return {
        "your_team_role": role,
        "you_maintain": "You are a maintainer of this team."
        if role == "maintainer"
        else "You are a member of this team.",
    }


def _review(data: Mapping[str, Any]) -> dict[str, Value]:
    team = dig(data, "organization", "team") or {}
    algorithm = str(team.get("reviewRequestDelegationAlgorithm") or "ROUND_ROBIN")
    return {
        "node_id": str(team.get("id") or ""),
        "viewerCanAdminister": bool(team.get("viewerCanAdminister")),
        "review_enabled": bool(team.get("reviewRequestDelegationEnabled")),
        "review_algorithm": "load balance" if algorithm == "LOAD_BALANCE" else "round robin",
        "review_count": int(team.get("reviewRequestDelegationMemberCount") or 1),
        "review_notify": bool(team.get("reviewRequestDelegationNotifyTeam")),
        "projects": tuple(
            str(node.get("title", ""))
            for node in dig(team, "projectsV2", "nodes") or ()
            if isinstance(node, Mapping)
        ),
    }


def _compose_review(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    """Code review assignment is one mutation: every setting goes together (GH-R-141)."""
    current = {
        "review_enabled": ident.get("review_enabled") == "True",
        "review_algorithm": ident.get("review_algorithm") or "round robin",
        "review_count": ident.get("review_count") or "1",
        "review_notify": ident.get("review_notify") == "True",
    }
    merged = {**current, **edits}
    rest = {k: v for k, v in edits.items() if not k.startswith("review_")}
    found: list[tuple[str, str, dict[str, object]]] = []
    if rest:
        body: dict[str, object] = {}
        for key, value in rest.items():
            if key == "privacy":
                body["privacy"] = "closed" if value == "visible" else "secret"
            elif key == "notifications":
                body["notification_setting"] = (
                    "notifications_enabled" if value else "notifications_disabled"
                )
            else:
                body[key] = value
        found.append(("PATCH", f"/orgs/{ident['org']}/teams/{ident['team']}", body))
    if any(key.startswith("review_") for key in edits):
        found.append((
            "GRAPHQL",
            _REVIEW_MUTATION,
            {
                "id": ident.get("node_id", ""),
                "enabled": bool(merged["review_enabled"]),
                "algorithm": _ALGORITHMS.get(str(merged["review_algorithm"]), "ROUND_ROBIN"),
                "count": int(str(merged["review_count"] or 1)),
                "notify": bool(merged["review_notify"]),
            },
        ))
    return found


def _role_rows(role: str) -> Any:
    return _items(f"{role}s", lambda r: f"{r.get('login', '')}, {role}")


TEAM = SheetDef(
    "team",
    SheetSpec(
        "team",
        "Team",
        (
            page(
                "general",
                "General",
                ed("name", "Name"),
                ro("slug", "Slug"),
                ed("description", "Description"),
                ed(
                    "privacy",
                    "Visibility",
                    _K.CHOICE,
                    "Visible to every member, or secret to its members and owners.",
                    choices=("visible", "secret"),
                ),
                ro("parent", "Parent team", help="Child Teams on the parent's sheet moves it."),
                ed(
                    "notifications",
                    "Notifications",
                    _K.CHECK,
                    "Notify the team when it is mentioned.",
                ),
                ro("created", "Created", _K.DATE),
                ro("you_maintain", "You"),
            ),
            page(
                "members",
                "Members",
                ro("maintainers", "Maintainers", _K.TABLE),
                ro(
                    "members",
                    "Members",
                    _K.TABLE,
                    "Insert adds people, F2 changes a role, "
                    "Delete removes; each is previewed first.",
                ),
            ),
            page(
                "repositories",
                "Repositories",
                ro("team_repos", "Repositories", _K.TABLE, "Each repository and the team's role."),
            ),
            page("projects", "Projects", ro("projects", "Projects", _K.TABLE)),
            page("child_teams", "Child Teams", ro("children", "Child teams", _K.TABLE)),
            page(
                "review",
                "Code Review",
                ed("review_enabled", "Assign reviews automatically", _K.CHECK),
                ed(
                    "review_algorithm",
                    "How",
                    _K.CHOICE,
                    "Round robin takes turns; load "
                    "balance picks whoever has the fewest open reviews.",
                    choices=("round robin", "load balance"),
                ),
                ed("review_count", "How many reviewers", _K.NUMBER),
                ed("review_notify", "Notify the whole team as well", _K.CHECK),
            ),
            page("idp", "Identity Provider", ro("idp_groups", "Linked groups", _K.TABLE)),
            page(
                "danger",
                "Danger Zone",
                ro(
                    "danger_note",
                    "Delete",
                    help="Delete Team on "
                    "the context menu deletes it, after a preview "
                    "naming every repository that loses its access "
                    "and the name typed. Its child teams move up.",
                ),
            ),
        ),
    ),
    (
        Read(_TEAM, _team),
        Read(
            _TEAM + "/memberships/{me}",
            _team_role,
            optional=True,
            fallback={"you_maintain": "You are not on this team."},
        ),
        Read(
            _TEAM + "/members",
            _role_rows("maintainer"),
            optional=True,
            query=lambda _i: {"role": "maintainer"},
        ),
        Read(
            _TEAM + "/members",
            _role_rows("member"),
            optional=True,
            query=lambda _i: {"role": "member"},
        ),
        Read(
            _TEAM + "/repos",
            _items("team_repos", lambda r: f"{r.get('full_name', '')}, {r.get('role_name', '')}"),
            optional=True,
        ),
        Read(_TEAM + "/teams", _items("children", lambda r: str(r.get("name", ""))), optional=True),
        Read(
            _TEAM + "/team-sync/group-mappings",
            _items("groups", lambda r: str(r.get("group_name", ""))),
            optional=True,
        ),
        Read(
            graphql=TEAM_REVIEW_QUERY,
            variables=lambda i: {"org": i["org"], "team": i["team"]},
            extract=_review,
            optional=True,
        ),
    ),
    {
        key: Write(_TEAM, "team:maintainer", _A, "PATCH", "patch")
        for key in (
            "name",
            "description",
            "privacy",
            "notifications",
            "review_enabled",
            "review_algorithm",
            "review_count",
            "review_notify",
        )
    },
    title=lambda ident: f"Team {ident['team']}",
    url=lambda ident: f"https://github.com/orgs/{ident['org']}/teams/{ident['team']}",
    compose=_compose_review,
    adopt=("node_id", "review_enabled", "review_algorithm", "review_count", "review_notify"),
    renames=("name", "team"),
)
