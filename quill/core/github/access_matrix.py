"""Access and setting matrices, each a list a screen reader walks (GitHub PRD 18.3.2).

A grid of people against repositories is unreadable by ear, so each matrix
is a list with one row per pair, and each row says the effective permission
and **where it comes from**:

    jeff on quill: Admin, from team Maintainers; also Write directly.
    kim on site: Write, directly, as an outside collaborator.
    ana on docs: Read, from the organization's base permission.

* :func:`people_rows`: people x repositories. Every source GitHub has for a
  repository role is read and named: being an owner of the organization, the
  organization's base permission, each team (with its role there), and
  direct access (an outside collaborator's is said so). The highest is the
  effective role; the others follow as "also".
* :func:`team_rows`: teams x repositories, each team's role on each.
* :func:`property_rows`: custom properties x repositories, unset ones said
  as "not set" rather than left out.

Each row is a ``resource`` row of the organization's nodes, so the Workbench
list filters it (Show Only, the filter box) and File > Export List saves it.
A list GitHub will not show to you (a repository's direct collaborators, to
anyone but its admins) is named in the node's note, never shown as nobody.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.permissions import REPO_ROLES, repo_role
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Cell",
    "Grant",
    "OrgAccess",
    "cells",
    "people_rows",
    "property_rows",
    "read_access",
    "role_of",
    "team_rows",
]

_PAGE = {"per_page": "100"}
_BASE = "the organization's base permission"
_OWNER = "being an owner of the organization"


@dataclass(frozen=True)
class Grant:
    """One way a person has a role on a repository."""

    role: str  # read, triage, write, maintain, admin, or a custom role's name
    rank: int  # its place in REPO_ROLES (a custom role ranks as its base role)
    source: str  # "team Maintainers", "directly", _BASE, _OWNER

    def how(self) -> str:
        return self.source if self.source.startswith("directly") else f"from {self.source}"

    def title(self) -> str:
        return self.role[:1].upper() + self.role[1:]


@dataclass
class Cell:
    """A person and a repository: every grant, the highest first."""

    person: str
    repo: str
    grants: list[Grant] = field(default_factory=list)

    def best(self) -> Grant:
        return max(self.grants, key=lambda g: g.rank)

    def sentence(self) -> str:
        """ "jeff on quill: Admin, from team Maintainers; also Write directly." """
        ordered = sorted(self.grants, key=lambda g: -g.rank)
        top, rest = ordered[0], ordered[1:]
        said = f"{self.person} on {self.repo.rsplit('/', 1)[-1]}: {top.title()}, {top.how()}"
        if rest:
            said += "; also " + "; also ".join(f"{g.title()} {g.how()}" for g in rest)
        return said + "."


@dataclass
class OrgAccess:
    """What one organization's access was read as, and what could not be read."""

    org: str
    base: str = ""
    owners: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    repos: list[str] = field(default_factory=list)
    teams: dict[str, str] = field(default_factory=dict)  # slug: name
    parents: dict[str, str] = field(default_factory=dict)  # slug: parent's name
    team_members: dict[str, list[str]] = field(default_factory=dict)
    team_repos: dict[str, list[tuple[str, str, int]]] = field(default_factory=dict)
    direct: dict[str, list[tuple[str, str, int]]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _rank(role: str, permissions: object = None) -> int:
    base = role if role in REPO_ROLES else (repo_role(permissions) or "read")
    return REPO_ROLES.index(base) if base in REPO_ROLES else 0


def _list(api: GitHubApi, path: str, **query: str) -> list[Mapping[str, Any]]:
    data = api.rest("GET", path, query={**_PAGE, **query}).data
    return [row for row in data or () if isinstance(row, Mapping)]


def _role_of(row: Mapping[str, Any]) -> tuple[str, int]:
    permissions = row.get("permissions")
    role = str(row.get("role_name") or repo_role(permissions) or "read")
    role = {"pull": "read", "push": "write"}.get(role, role)
    return role, _rank(role, permissions)


def role_of(row: Mapping[str, Any]) -> tuple[str, int]:
    """A collaborator row's role and its rank, as the access matrix reads it."""
    return _role_of(row)


def read_access(api: GitHubApi, org: str, *, teams_too: bool = True) -> OrgAccess:
    """Read every source of repository access in *org*: one call per repository and team."""
    found = OrgAccess(org)
    data = api.rest("GET", f"/orgs/{org}").data
    found.base = str((data or {}).get("default_repository_permission") or "none")
    found.repos = [str(r.get("full_name") or "") for r in _list(api, f"/orgs/{org}/repos")]
    if len(found.repos) == 100:
        found.notes.append("Read the first 100 repositories; the rest are not in this list.")
    found.members = [str(r.get("login") or "") for r in _list(api, f"/orgs/{org}/members")]
    found.owners = [
        str(r.get("login") or "") for r in _list(api, f"/orgs/{org}/members", role="admin")
    ]
    try:
        found.outside = [
            str(r.get("login") or "") for r in _list(api, f"/orgs/{org}/outside_collaborators")
        ]
    except GitHubRestError:
        found.notes.append("Outside collaborators are shown only to the organization's owners.")
    for team in _list(api, f"/orgs/{org}/teams") if teams_too else ():
        slug = str(team.get("slug") or "")
        found.teams[slug] = str(team.get("name") or slug)
        parent = team.get("parent")
        if isinstance(parent, Mapping):
            found.parents[slug] = str(parent.get("name") or parent.get("slug") or "")
        try:
            found.team_members[slug] = [
                str(r.get("login") or "") for r in _list(api, f"/orgs/{org}/teams/{slug}/members")
            ]
            found.team_repos[slug] = [
                (str(r.get("full_name") or ""), *_role_of(r))
                for r in _list(api, f"/orgs/{org}/teams/{slug}/repos")
            ]
        except GitHubRestError:
            found.notes.append(f"The team {found.teams[slug]} is not shown to you in full.")
    hidden = 0
    for repo in found.repos:
        try:
            rows = _list(api, f"/repos/{repo}/collaborators", affiliation="direct")
        except GitHubRestError:
            hidden += 1
            continue
        found.direct[repo] = [(str(r.get("login") or ""), *_role_of(r)) for r in rows]
    if hidden:
        found.notes.append(
            f"Direct access to {hidden} repositor{'y is' if hidden == 1 else 'ies are'} shown "
            f"only to {'its' if hidden == 1 else 'their'} admins, so those rows leave direct "
            "access out."
        )
    return found


def cells(access: OrgAccess) -> list[Cell]:
    """Every person and repository pair with any access, each grant named."""
    table: dict[tuple[str, str], Cell] = {}

    def give(person: str, repo: str, grant: Grant) -> None:
        if person and repo:
            table.setdefault((person.casefold(), repo), Cell(person, repo)).grants.append(grant)

    outside = {o.casefold() for o in access.outside}
    base = access.base if access.base in REPO_ROLES else ""
    for repo in access.repos:
        for owner in access.owners:
            give(owner, repo, Grant("admin", _rank("admin"), _OWNER))
        if base:
            for member in access.members:
                give(member, repo, Grant(base, _rank(base), _BASE))
    for slug, repos in access.team_repos.items():
        name = access.teams.get(slug, slug)
        for repo, role, rank in repos:
            for member in access.team_members.get(slug, ()):
                give(member, repo, Grant(role, rank, f"team {name}"))
    for repo, rows in access.direct.items():
        for login, role, rank in rows:
            how = (
                "directly, as an outside collaborator"
                if login.casefold() in outside
                else "directly"
            )
            give(login, repo, Grant(role, rank, how))
    return sorted(table.values(), key=lambda c: (c.person.casefold(), c.repo.casefold()))


def _row(org: str, label: str, key: str, page: str) -> ExploreRow:
    return ExploreRow(label, f"{label}\n{page}", page, org, "resource", key)


def people_rows(api: GitHubApi, org: str, warnings: list[str]) -> list[ExploreRow]:
    """People x repositories: who has what on each, and where it comes from."""
    access = read_access(api, org)
    warnings.extend(access.notes)
    page = f"https://github.com/orgs/{org}/people"
    return [
        _row(org, cell.sentence(), f"access_people:{cell.person}:{cell.repo}", page)
        for cell in cells(access)
    ]


def team_rows(api: GitHubApi, org: str, warnings: list[str]) -> list[ExploreRow]:
    """Teams x repositories: each team's role on each repository it reaches."""
    access = read_access(api, org)
    warnings.extend(note for note in access.notes if "team" in note or "first 100" in note)
    rows = []
    for slug, repos in sorted(access.team_repos.items(), key=lambda kv: kv[0].casefold()):
        name = access.teams.get(slug, slug)
        parent = access.parents.get(slug, "")
        under = f", a child team of {parent}" if parent else ""
        count = len(access.team_members.get(slug, ()))
        for repo, role, _ in sorted(repos):
            label = (
                f"{name} on {repo.rsplit('/', 1)[-1]}: {role[:1].upper()}{role[1:]}, "
                f"for {count} member{'' if count == 1 else 's'}{under}."
            )
            page = f"https://github.com/orgs/{org}/teams/{slug}/repositories"
            rows.append(_row(org, label, f"access_teams:{slug}:{repo}", page))
    if not rows:
        warnings.append("No team has a repository here yet.")
    return rows


def property_rows(api: GitHubApi, org: str, warnings: list[str]) -> list[ExploreRow]:
    """Custom properties x repositories: every property on every repository, unset ones too."""
    names = [
        str(p.get("property_name") or "") for p in _list(api, f"/orgs/{org}/properties/schema")
    ]
    if not names:
        warnings.append("The organization has no custom properties. Define a Custom Property...")
    page = f"https://github.com/organizations/{org}/settings/custom-properties"
    rows = []
    for repo in _list(api, f"/orgs/{org}/properties/values"):
        values = {
            str(p.get("property_name")): p.get("value")
            for p in repo.get("properties") or ()
            if isinstance(p, Mapping)
        }
        said = "; ".join(f"{name} is {_value(values.get(name))}" for name in names)
        full = str(repo.get("repository_full_name") or repo.get("repository_name") or "")
        label = f"{full.rsplit('/', 1)[-1]}: {said or 'no properties'}."
        rows.append(_row(org, label, f"org_property_values:{full}", page))
    return rows


def _value(value: object) -> str:
    if value in (None, "", [], ()):
        return "not set"
    if isinstance(value, Sequence) and not isinstance(value, str):
        return " and ".join(str(v) for v in value)
    return str(value)
