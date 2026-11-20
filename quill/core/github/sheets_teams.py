"""The Team sheet (GitHub PRD Appendix C, 18.3.3, GH-R-140, 141).

Name, description, visibility, parent (a picker of the organization's teams;
empty makes it a top-level team), notifications and your role on it; members
and maintainers; repositories and the team's role on each; projects; child
teams; code review assignment (on or off, round robin or load balance, how
many reviewers, notify the whole team: GH-R-141); identity provider groups;
and the Danger Zone note. Lists are changed from the Access buttons
(:mod:`quill.core.github.access`), each previewed, and none of them may take
away the last maintainer's own place.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import (
    Ident,
    Options,
    Read,
    SheetDef,
    SheetSaveError,
    Write,
)
from quill.core.github.sheet_fields import dig, ed, lst, page, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["TEAM", "TEAM_REVIEW_QUERY"]

_A = WriteTier.ACCESS
_K = FieldKind


def _items(key: str, render: Any) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        rows = data.get("items") if isinstance(data.get("items"), list) else lst(data, key)
        return {key: tuple(render(row) for row in rows or () if isinstance(row, Mapping))}

    return extract


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
            if key == "parent":
                body.pop("parent")
                if value not in ("", None) and not isinstance(value, int):
                    raise SheetSaveError(f"There is no team called {value} here to move it under.")
                body["parent_team_id"] = value or None
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
                ed(
                    "parent",
                    "Parent team",
                    _K.CHOICE,
                    "The team it sits under, and whose repositories its members also reach. "
                    "Empty makes it a top-level team.",
                ),
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
                ro(
                    "team_repos",
                    "Repositories",
                    _K.TABLE,
                    "Each repository and the team's role. Add gives the team a repository, "
                    "Change Role changes its role, Remove takes the repository away; each is "
                    "previewed first.",
                ),
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
            _items(
                "team_repos",
                lambda r: f"{r.get('full_name', '')}, repository, {r.get('role_name', '')}, team",
            ),
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
            "parent",
            "review_enabled",
            "review_algorithm",
            "review_count",
            "review_notify",
        )
    },
    title=lambda ident: f"Team {ident['team']}",
    url=lambda ident: f"https://github.com/orgs/{ident['org']}/teams/{ident['team']}",
    options={
        "parent": Options(
            "/orgs/{org}/teams", lambda r: str(r.get("slug", "")), lambda r: r.get("id")
        )
    },
    compose=_compose_review,
    adopt=("node_id", "review_enabled", "review_algorithm", "review_count", "review_notify"),
    renames=("name", "team"),
)
