"""An organization's people: roles, two-factor, and the checks that stop a lockout (PRD 18.4).

Every command that removes someone from an organization, makes a member an
outside collaborator, or takes a team's admin role away from a repository
asks here first, just before it sends anything, so it is refused when it
would leave you, or the organization, with nobody to manage it:

* :func:`member_problem`: removing a member who is the last owner, or
  yourself while you are an owner;
* :func:`convert_problem`: making yourself an outside collaborator (GitHub
  converts only members, so an owner is explained, not attempted);
* :func:`team_repo_problem`: taking admin from a team you are on, when that
  team is how you administer the repository.

:func:`member_rows` is the Members list with each person's role and
two-factor state, for the organization's Members node. wx-free and
strict-typed.
"""

from __future__ import annotations

from quill.core.github.access import AccessRow, lockout_problem
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "convert_problem",
    "member_problem",
    "member_rows",
    "owner_logins",
    "team_repo_problem",
    "two_factor_off",
    "viewer_login",
]


def viewer_login(api: GitHubApi) -> str:
    """The signed-in account's login."""
    data = api.rest("GET", "/user").data
    return str(data.get("login") or "") if isinstance(data, dict) else ""


def _logins(api: GitHubApi, path: str, **query: str) -> list[str]:
    data = api.rest("GET", path, query={"per_page": "100", **query}).data
    return [str(r.get("login") or "") for r in data or () if isinstance(r, dict)]


def owner_logins(api: GitHubApi, org: str) -> list[str]:
    """Every owner of *org*."""
    return _logins(api, f"/orgs/{org}/members", role="admin")


def two_factor_off(api: GitHubApi, org: str) -> list[str] | None:
    """Members without two-factor sign-in, or ``None`` when GitHub shows that only to owners."""
    try:
        return _logins(api, f"/orgs/{org}/members", filter="2fa_disabled")
    except GitHubRestError as exc:
        if exc.status in (403, 404, 422):
            return None
        raise


def _same(a: str, b: str) -> bool:
    return a.strip().lstrip("@").casefold() == b.strip().lstrip("@").casefold()


def member_problem(api: GitHubApi, org: str, login: str) -> str:
    """Why removing *login* from *org* is refused, or "" when it is safe."""
    me = viewer_login(api)
    owners = owner_logins(api, org)
    rows = [AccessRow(name, "person", "owner") for name in owners]
    role = "owner" if any(_same(login, o) for o in owners) else "member"
    target = AccessRow(next((o for o in owners if _same(o, login)), login), "person", role)
    return lockout_problem(rows, target, me)


def convert_problem(api: GitHubApi, org: str, login: str) -> str:
    """Why making *login* an outside collaborator of *org* is refused, or ""."""
    if _same(login, viewer_login(api)):
        return (
            "That takes you out of the organization and its teams. Another owner can do it "
            "if it is what you want."
        )
    if any(_same(login, owner) for owner in owner_logins(api, org)):
        return (
            f"{login} is an owner of {org}; GitHub makes only members outside collaborators. "
            "Change them to a member first."
        )
    return ""


def team_repo_problem(api: GitHubApi, org: str, team: str, repo: str) -> str:
    """Why taking admin on *repo* from *team* is refused: it is how you administer it."""
    me = viewer_login(api)
    if any(_same(me, owner) for owner in owner_logins(api, org)):
        return ""  # an owner administers every repository whatever the teams say
    try:
        api.rest("GET", f"/orgs/{org}/teams/{team}/memberships/{me}")
    except GitHubRestError as exc:
        if exc.status == 404:
            return ""  # you are not on the team
        raise
    direct = api.rest(
        "GET", f"/repos/{repo}/collaborators", query={"affiliation": "direct", "per_page": "100"}
    ).data
    for row in direct or ():
        if isinstance(row, dict) and _same(str(row.get("login") or ""), me):
            if (row.get("permissions") or {}).get("admin"):
                return ""  # you are an admin of it directly too
    return (
        f"That takes away your own admin access to {repo}: you have it through the team "
        f"{team}. Ask another admin of {repo}, or an owner of {org}, to do it if it is what "
        "you want."
    )


def member_rows(api: GitHubApi, org: str, warnings: list[str]) -> list[ExploreRow]:
    """The organization's members, each with their role and two-factor state, as sentences."""
    members = _logins(api, f"/orgs/{org}/members")
    owners = {o.casefold() for o in owner_logins(api, org)}
    off = two_factor_off(api, org)
    if off is None:
        warnings.append("Two-factor sign-in is shown only to the organization's owners.")
    page = f"https://github.com/orgs/{org}/people"
    rows = []
    for login in members:
        role = "owner" if login.casefold() in owners else "member"
        factor = "" if off is None else (", two-factor off" if login in off else ", two-factor on")
        label = f"{login}, {role}{factor}."
        rows.append(
            ExploreRow(label, f"{label}\n{page}", page, org, "resource", f"org_members:{login}")
        )
    if len(members) == 100:
        warnings.append("Showing the first 100 members; GitHub's people page lists the rest.")
    return rows
