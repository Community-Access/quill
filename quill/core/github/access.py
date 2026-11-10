"""Managing access: the Access pages, the access matrix, bulk changes and roles (PRD 18.3, 22.10).

Every object with an access list has an Access page of the same shape: who
has access (people, teams), each row "kellylford, person, maintain, direct",
and Add..., Change Role... and Remove. This module is that page's arithmetic,
wx-free:

- :func:`parse_row` reads a row back; :func:`plan_add`, :func:`plan_change`
  and :func:`plan_remove` turn an action into :class:`AccessChange` requests
  with a preview in words and a tier (section 18.4), for repositories,
  organizations and teams;
- :func:`lockout_problem` refuses removing your own admin role, the last
  owner of an organization or the only admin of a repository, saying who
  else could do it (18.4: no self-lockout);
- :func:`matrix_rows` is the access matrix (18.3.2): one row per person and
  repository, with role and source, filterable and exportable as CSV;
- :func:`bulk_plan` is a bulk change in any direction, previewed in full;
- :data:`ROLE_ABILITIES`, :func:`view_as_role`, :func:`compare_roles` and
  :func:`why_cant_they` answer "what can a role do here?" read-only (22.10).

wx-free and strict-typed.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from quill.core.github.permissions import REPO_ROLES, WriteTier

__all__ = [
    "ROLE_ABILITIES",
    "AccessChange",
    "AccessRow",
    "bulk_plan",
    "compare_roles",
    "lockout_problem",
    "matrix_csv",
    "matrix_rows",
    "parse_row",
    "plan_add",
    "plan_change",
    "plan_remove",
    "view_as_role",
    "why_cant_they",
]


@dataclass(frozen=True)
class AccessRow:
    """One row of an Access page: who, what kind, which role, from where."""

    name: str
    kind: str = "person"
    role: str = ""
    source: str = "direct"

    def text(self) -> str:
        return f"{self.name}, {self.kind}, {self.role}, {self.source}"


def parse_row(text: str) -> AccessRow:
    """A row as the sheet shows it, read back: "docs, team, write, through organization"."""
    parts = [part.strip() for part in text.split(",")]
    name = parts[0] if parts else ""
    kind = parts[1] if len(parts) > 1 else "person"
    role = parts[2] if len(parts) > 2 else ""
    source = ", ".join(parts[3:]) if len(parts) > 3 else "direct"
    if kind not in ("person", "team", "invited"):
        # A two-part row ("kelly, maintainer") is a team member and their role.
        return AccessRow(name, "person", kind, "team")
    return AccessRow(name, kind, role, source)


@dataclass(frozen=True)
class AccessChange:
    """One request an access action sends, and how it is previewed."""

    method: str
    path: str
    body: Mapping[str, object] | None
    words: str
    tier: WriteTier
    undo: tuple[str, str, Mapping[str, object] | None] | None = None


def _api_role(role: str) -> str:
    return {"read": "pull", "write": "push"}.get(role, role)


def plan_add(scope: str, ident: Mapping[str, str], who: str, kind: str, role: str) -> AccessChange:
    """Add a person or team with a role, to a repository, organization or team."""
    name = who.strip().lstrip("@")
    if scope == "repository":
        repo = ident["repo"]
        if kind == "team":
            org = repo.split("/", 1)[0]
            return AccessChange(
                "PUT",
                f"/orgs/{org}/teams/{name}/repos/{repo}",
                {"permission": _api_role(role)},
                f"Give the team {name} {role} access to {repo}.",
                WriteTier.ACCESS,
                ("DELETE", f"/orgs/{org}/teams/{name}/repos/{repo}", None),
            )
        return AccessChange(
            "PUT",
            f"/repos/{repo}/collaborators/{name}",
            {"permission": _api_role(role)},
            f"Invite {name} to {repo} with {role} access. GitHub sends them an invitation.",
            WriteTier.ACCESS,
            ("DELETE", f"/repos/{repo}/collaborators/{name}", None),
        )
    if scope == "team":
        org, team = ident["org"], ident["team"]
        return AccessChange(
            "PUT",
            f"/orgs/{org}/teams/{team}/memberships/{name}",
            {"role": "maintainer" if role == "maintainer" else "member"},
            f"Add {name} to the team {team} as a {role or 'member'}.",
            WriteTier.ACCESS,
            ("DELETE", f"/orgs/{org}/teams/{team}/memberships/{name}", None),
        )
    org = ident["org"]
    return AccessChange(
        "PUT",
        f"/orgs/{org}/memberships/{name}",
        {"role": "admin" if role == "owner" else "member"},
        f"Invite {name} to {org} as {'an owner' if role == 'owner' else 'a member'}.",
        WriteTier.ACCESS,
        ("DELETE", f"/orgs/{org}/memberships/{name}", None),
    )


def plan_change(scope: str, ident: Mapping[str, str], row: AccessRow, role: str) -> AccessChange:
    """Change a row's role: the same request as adding, previewed as a change."""
    found = plan_add(scope, ident, row.name, row.kind, role)
    where = ident.get("repo") or ident.get("team") or ident.get("org", "")
    back = plan_add(scope, ident, row.name, row.kind, row.role) if row.role else None
    return AccessChange(
        found.method,
        found.path,
        found.body,
        f"Change {row.name} from {row.role or 'their role'} to {role} on {where}.",
        WriteTier.ACCESS,
        (back.method, back.path, back.body) if back else None,
    )


def plan_remove(scope: str, ident: Mapping[str, str], row: AccessRow) -> AccessChange:
    """Remove a row: tier 3 when it is an admin or owner (18.4)."""
    added = plan_add(scope, ident, row.name, row.kind, row.role or "read")
    where = ident.get("repo") or ident.get("team") or ident.get("org", "")
    method, path, _body = added.undo or ("DELETE", added.path, None)
    heavy = row.role in ("admin", "owner", "maintainer")
    return AccessChange(
        method,
        path,
        None,
        f"Remove {row.name} ({row.role or 'their access'}) from {where}."
        + (" They lose access at once." if row.kind != "invited" else ""),
        WriteTier.DESTRUCTIVE if heavy else WriteTier.ACCESS,
        (added.method, added.path, added.body),
    )


def lockout_problem(
    rows: Sequence[AccessRow], target: AccessRow, me: str, *, new_role: str = ""
) -> str:
    """Why removing or lowering *target* is refused, or "" when it is safe (18.4)."""
    top = {"admin", "owner"}
    if target.role not in top or new_role in top:
        return ""
    others = [r.name for r in rows if r.role in top and r.name != target.name]
    if target.name.casefold() == me.casefold() and not others:
        return (
            "That would leave nobody who can manage it, you included. Make someone else an "
            "admin or owner first."
        )
    if target.name.casefold() == me.casefold():
        return (
            "That removes your own admin access. Ask "
            + " or ".join(others[:3])
            + " to do it if it is what you want."
        )
    if not others:
        return (
            f"{target.name} is the only admin or owner. Make someone else one first, or "
            "nobody can manage it."
        )
    return ""


# ---------------------------------------------------------------------------
# The access matrix and bulk changes (18.3.2)
# ---------------------------------------------------------------------------


def matrix_rows(
    access: Mapping[str, Sequence[AccessRow]],
) -> list[tuple[str, str, str, str]]:
    """(person, repository, role, source) for every pair, sorted by person then repository."""
    found = [
        (row.name, repo, row.role, row.source) for repo, rows in access.items() for row in rows
    ]
    return sorted(found, key=lambda r: (r[0].casefold(), r[1].casefold()))


def matrix_csv(rows: Sequence[tuple[str, str, str, str]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["person", "repository", "role", "source"])
    writer.writerows(rows)
    return out.getvalue()


def bulk_plan(
    scope: str,
    who: str,
    kind: str,
    role: str,
    targets: Sequence[Mapping[str, str]],
    *,
    remove: bool = False,
) -> list[AccessChange]:
    """One change per target: give a team Write on twelve repositories, or take it away."""
    if remove:
        return [plan_remove(scope, ident, AccessRow(who, kind, role)) for ident in targets]
    return [plan_add(scope, ident, who, kind, role) for ident in targets]


# ---------------------------------------------------------------------------
# Roles, read-only (22.10)
# ---------------------------------------------------------------------------

#: What each repository role may do, lowest first; each role has every ability above it.
ROLE_ABILITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("read", ("read code and issues", "open issues", "comment", "fork", "star and watch")),
    (
        "triage",
        (
            "apply labels",
            "assign people",
            "set milestones",
            "close and reopen issues",
            "mark duplicates",
            "request reviews",
        ),
    ),
    (
        "write",
        (
            "push to branches",
            "merge pull requests",
            "manage labels and milestones",
            "lock conversations",
            "create releases",
            "re-run workflows",
            "delete branches",
        ),
    ),
    (
        "maintain",
        (
            "manage topics and settings that do not touch access",
            "manage Pages",
            "push to protected branches where rules allow",
        ),
    ),
    (
        "admin",
        (
            "manage collaborators and teams",
            "change branch protection and rulesets",
            "change visibility",
            "manage webhooks, keys and secrets",
            "rename, transfer, archive or delete the repository",
        ),
    ),
)


def view_as_role(role: str) -> list[str]:
    """Everything *role* may do, in order: View As Role, read-only."""
    found: list[str] = []
    for name, abilities in ROLE_ABILITIES:
        found.extend(abilities)
        if name == role:
            break
    return found


def compare_roles(low: str, high: str) -> list[str]:
    """What *high* may do that *low* may not."""
    lower = set(view_as_role(low))
    return [ability for ability in view_as_role(high) if ability not in lower]


def why_cant_they(person: str, role: str, ability: str, where: str) -> str:
    """Why *person*, with *role*, cannot do *ability* here, and what would change it."""
    for name, abilities in ROLE_ABILITIES:
        if ability in abilities:
            needed = name
            break
    else:
        return f"QUILL does not know what {ability} needs on {where}."
    if REPO_ROLES.index(role) >= REPO_ROLES.index(needed) if role in REPO_ROLES else False:
        return (
            f"{person} has {role}, which allows {ability} on {where}. If it still fails, a "
            "ruleset or branch protection may block it: the repository's Branches and Rules "
            "page says which."
        )
    return (
        f"{person} has {role or 'no'} access to {where}; {ability} needs {needed}. An admin of "
        f"{where} can change their role on its Access page, or give a team they are on "
        f"{needed}."
    )
