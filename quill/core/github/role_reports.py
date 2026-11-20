"""Roles and Access, answered from GitHub's own replies (GitHub PRD 18.2, 18.3.2, 22.10).

Each function here reads through a :class:`~quill.core.github.workbench_api.GitHubApi`
and returns the words a Roles and Access command shows, built from
:mod:`quill.core.github.role_evidence`: what GitHub said, with the request
that said it, and what GitHub would not say, said as unknown.

* :func:`my_access` -- My Access Here;
* :func:`why_cant_they` -- Why Can't They?, from the person's real role and
  the rules GitHub says apply to the branch;
* :func:`role_report` and :func:`compare_report` -- View As Role and Compare
  Roles: GitHub's documented defaults, said to be that, then who on this
  repository GitHub says has each role;
* :func:`review_by_repository` -- the Access Review's effective access per person,
  team and repository, with where it comes from;
* :func:`bulk_preview` -- a Bulk Access Change previewed per person, from each
  target's current role, with no request for a change that changes nothing;
* :func:`account_access` and :func:`compare_accounts` -- Compare Accounts.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from quill.core.github.access import AccessChange, AccessRow, compare_roles, view_as_role
from quill.core.github.permissions import REPO_ROLES, repo_role
from quill.core.github.role_evidence import (
    DOCUMENTED,
    Fact,
    blocking,
    branch_rules,
    documented_need,
    fetch,
    person_role,
    team_role,
    token_facts,
)
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "AccountAccess",
    "account_access",
    "bulk_preview",
    "compare_accounts",
    "compare_report",
    "my_access",
    "review_by_repository",
    "role_holders",
    "role_report",
    "why_cant_they",
]

_VIEWER = """query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) { viewerPermission }
}"""


def _lines(facts: Sequence[Fact]) -> str:
    return "\n".join(fact.line() for fact in facts)


def _owner(repo: str) -> str:
    return repo.split("/", 1)[0]


def _viewer_permission(api: GitHubApi, repo: str) -> Fact:
    owner, _, name = repo.partition("/")
    try:
        data = api.graphql(_VIEWER, {"owner": owner, "name": name})
    except Exception as exc:  # noqa: BLE001 - GraphQL refused: said, not guessed
        return Fact(f"GitHub's viewerPermission could not be read: {exc}.")
    repository = data.get("repository") if isinstance(data, Mapping) else None
    value = repository.get("viewerPermission") if isinstance(repository, Mapping) else None
    if not value:
        return Fact("GitHub returned no viewerPermission for this repository.")
    return Fact(f"viewerPermission is {value}.", "GraphQL repository.viewerPermission")


def _org_facts(api: GitHubApi, org: str, login: str, *, me: bool) -> list[Fact]:
    facts: list[Fact] = []
    path = f"/user/memberships/orgs/{org}" if me else f"/orgs/{org}/memberships/{login}"
    member = fetch(api, path)
    who = "You are" if me else f"{login} is"
    if member.ok and isinstance(member.data, Mapping):
        role = str(member.data.get("role") or "")
        state = str(member.data.get("state") or "")
        word = "an owner" if role == "admin" else "a member"
        pending = " (invited, not yet joined)" if state == "pending" else ""
        facts.append(Fact(f"{who} {word} of {org}{pending}.", path))
    else:
        whose = "your" if me else f"{login}'s"
        facts.append(Fact(member.why_not(f"{whose} place in {org}")))
    base = fetch(api, f"/orgs/{org}")
    value = (
        base.data.get("default_repository_permission") if isinstance(base.data, Mapping) else None
    )
    if base.ok and value:
        facts.append(
            Fact(
                f"{org}'s base permission for members is {value}; the higher of it, a "
                "team's and a direct role counts.",
                f"/orgs/{org}",
            )
        )
    return facts


def _team_facts(api: GitHubApi, repo: str, login: str, *, me: bool) -> list[Fact]:
    path = f"/repos/{repo}/teams"
    teams = fetch(api, path, {"per_page": "100"})
    if not teams.ok or not isinstance(teams.data, list):
        return [Fact(teams.why_not(f"the teams with access to {repo}"))]
    if not teams.data:
        return [Fact(f"GitHub lists no team with access to {repo}.", path)]
    org = _owner(repo)
    mine: set[str] = set()
    if me:
        own = fetch(api, "/user/teams", {"per_page": "100"})
        rows = own.data if own.ok and isinstance(own.data, list) else []
        mine = {
            str(t.get("slug", ""))
            for t in rows
            if isinstance(t, Mapping)
            and str((t.get("organization") or {}).get("login", "")).casefold() == org.casefold()
        }
    found: list[Fact] = []
    for team in teams.data[:30]:
        if not isinstance(team, Mapping):
            continue
        slug = str(team.get("slug", ""))
        role = team_role(team.get("permission"))
        if me:
            on = slug in mine
        else:
            membership = fetch(api, f"/orgs/{org}/teams/{slug}/memberships/{login}")
            if membership.status not in (200, 404):
                found.append(Fact(membership.why_not(f"whether {login} is on the team {slug}")))
                continue
            on = membership.ok and (membership.data or {}).get("state") == "active"
        if on:
            found.append(Fact(f"Through the team {slug}: {role}.", path))
    return found or [
        Fact(f"No team that has access to {repo} has {'you' if me else login} on it.", path)
    ]


# -- My Access Here --------------------------------------------------------------------


def my_access(
    api: GitHubApi, repo: str, login: str, *, token: str | None, scopes_header: str | None
) -> str:
    """Your effective role on *repo*, and where each part comes from, as GitHub says."""
    facts: list[Fact] = []
    read = fetch(api, f"/repos/{repo}")
    data = read.data if read.ok and isinstance(read.data, Mapping) else {}
    if read.ok:
        role = repo_role(data.get("permissions"))
        facts.append(
            Fact(f"You have {role or 'no'} access to {repo}.", f"/repos/{repo} permissions")
        )
    else:
        facts.append(Fact(read.why_not(repo)))
    facts.append(_viewer_permission(api, repo))
    if login:
        facts.extend(person_role(api, repo, login)[2])
    owner = data.get("owner") if isinstance(data.get("owner"), Mapping) else {}
    if isinstance(owner, Mapping) and owner.get("type") == "Organization":
        facts.extend(_org_facts(api, str(owner.get("login")), login, me=True))
        facts.extend(_team_facts(api, repo, login, me=True))
    branch = str(data.get("default_branch") or "")
    if branch:
        facts.extend(branch_rules(api, repo, branch)[1])
    facts.extend(token_facts(token, scopes_header))
    return _lines(facts)


# -- Why Can't They? -------------------------------------------------------------------


def why_cant_they(api: GitHubApi, repo: str, login: str, ability: str, branch: str = "") -> str:
    """Why *login* cannot do *ability* on *repo*: their real role, then the rules that apply."""
    role, permission, facts = person_role(api, repo, login)
    needed = documented_need(ability)
    lines = [fact.line() for fact in facts]
    if not needed:
        lines.append(f"QUILL does not know what {ability} needs on {repo}.")
        return "\n".join(lines)
    need = f"{ability} needs {needed}. {DOCUMENTED}"
    if not role and permission != "none":
        lines.append(f"So whether {login} may do it cannot be known here. {need}")
        return "\n".join(lines)
    if role and role not in REPO_ROLES:
        lines.append(
            f"Whether the custom role {role} includes {ability} cannot be known from GitHub's "
            f"API. Built-in: {need}"
        )
        return "\n".join(lines)
    if not role or REPO_ROLES.index(role) < REPO_ROLES.index(needed):
        lines.append(
            f"{need} An admin of {repo} can change {login}'s role on its Access page, or give "
            f"a team they are on {needed}."
        )
        return "\n".join(lines)
    lines.append(f"{login}'s role allows {ability}. {DOCUMENTED}")
    if branch:
        rules, rule_facts = branch_rules(api, repo, branch)
        stops = blocking(rules, ability)
        if stops:
            lines.append(
                f"What GitHub says can still stop it on {branch}: "
                + "; ".join(rule.words() for rule in stops)
                + "."
            )
        else:
            lines.extend(fact.line() for fact in rule_facts)
            lines.append(
                f"GitHub reports nothing on {branch} that stops it. If it still fails, "
                "GitHub's own refusal says why: Explain That (Shift+F9) after the attempt."
            )
    return "\n".join(lines)


# -- View As Role and Compare Roles -----------------------------------------------------


def role_holders(api: GitHubApi, repo: str) -> tuple[dict[str, list[str]], str]:
    """Who GitHub says has each role on *repo* (``role_name``), or why it would not say."""
    path = f"/repos/{repo}/collaborators"
    read = fetch(api, path, {"per_page": "100"})
    if not read.ok or not isinstance(read.data, list):
        return {}, read.why_not(f"who has which role on {repo}")
    found: dict[str, list[str]] = {}
    for row in read.data:
        if isinstance(row, Mapping):
            role = str(row.get("role_name") or repo_role(row.get("permissions")) or "")
            found.setdefault(role, []).append(str(row.get("login", "")))
    return found, ""


def _holders_line(holders: Mapping[str, list[str]], role: str, repo: str) -> str:
    people = holders.get(role, [])
    if not people:
        return f"GitHub says nobody has {role} on {repo} directly."
    shown = ", ".join(people[:10]) + (f" and {len(people) - 10} more" if len(people) > 10 else "")
    return f"GitHub says {shown} {'has' if len(people) == 1 else 'have'} {role} on {repo}."


def role_report(api: GitHubApi | None, role: str, repo: str) -> str:
    """View As Role: the documented defaults, said as such, then who has it here."""
    lines = [DOCUMENTED, "", *view_as_role(role)]
    if api is not None and repo:
        holders, why = role_holders(api, repo)
        lines += ["", why or _holders_line(holders, role, repo)]
        custom = sorted(r for r in holders if r and r not in REPO_ROLES)
        if custom:
            lines.append(
                f"{repo} also has the custom role{'s' if len(custom) > 1 else ''} "
                f"{', '.join(custom)}; GitHub's API does not list what a custom role adds."
            )
    return "\n".join(lines)


def compare_report(api: GitHubApi | None, low: str, high: str, repo: str) -> str:
    """Compare Roles: the documented difference, said as such, then the holders of each."""
    more = compare_roles(low, high) or compare_roles(high, low)
    lines = [DOCUMENTED, "", *(more or ["By those defaults, they may do the same."])]
    if api is not None and repo:
        holders, why = role_holders(api, repo)
        lines += ["", why] if why else ["", *(_holders_line(holders, r, repo) for r in (low, high))]
    return "\n".join(lines)


# -- the Access Review --------------------------------------------------------------------


def review_by_repository(
    api: GitHubApi, org: str, *, pause: Callable[[], None] = lambda: None
) -> dict[str, list[AccessRow]]:
    """``{repository: rows}``: who GitHub says has access, how much, and from where."""
    repos = fetch(api, f"/orgs/{org}/repos", {"per_page": "100"})
    if not repos.ok or not isinstance(repos.data, list):
        return {org: [AccessRow("(unknown)", "person", "", repos.why_not(f"{org}'s repositories"))]}
    access: dict[str, list[AccessRow]] = {}
    for repo in repos.data:
        if not isinstance(repo, Mapping):
            continue
        name = str(repo.get("full_name", ""))
        pause()
        access[name] = _repository_rows(api, name)
    return access


def _logins(api: GitHubApi, path: str, affiliation: str) -> set[str] | None:
    read = fetch(api, path, {"per_page": "100", "affiliation": affiliation})
    if not read.ok or not isinstance(read.data, list):
        return None
    return {str(r.get("login", "")) for r in read.data if isinstance(r, Mapping)}


def _repository_rows(api: GitHubApi, repo: str) -> list[AccessRow]:
    path = f"/repos/{repo}/collaborators"
    every = fetch(api, path, {"per_page": "100", "affiliation": "all"})
    if not every.ok or not isinstance(every.data, list):
        return [AccessRow("(unknown)", "person", "", every.why_not(f"who has access to {repo}"))]
    direct = _logins(api, path, "direct")
    outside = _logins(api, path, "outside")
    rows: list[AccessRow] = []
    for row in every.data:
        if not isinstance(row, Mapping):
            continue
        login = str(row.get("login", ""))
        role = str(row.get("role_name") or repo_role(row.get("permissions")) or "")
        if outside is not None and login in outside:
            source = "outside collaborator"
        elif direct is not None and login in direct:
            source = "direct"
        elif direct is None:
            source = "direct or through the organization (GitHub would not say which)"
        else:
            source = "through the organization or a team"
        rows.append(AccessRow(login, "person", role, source))
    teams = fetch(api, f"/repos/{repo}/teams", {"per_page": "100"})
    for team in teams.data if teams.ok and isinstance(teams.data, list) else []:
        if isinstance(team, Mapping):
            rows.append(
                AccessRow(
                    str(team.get("slug", "")), "team", team_role(team.get("permission")), "team"
                )
            )
    return rows


# -- Bulk Access Changes, previewed per person -------------------------------------------


def _current_role(api: GitHubApi, change: AccessChange, who: str, kind: str, repo: str) -> str:
    """The role *who* has on *repo* now, as GitHub says; "none" or "unknown"."""
    if kind == "team":
        org = repo.split("/", 1)[0]
        read = fetch(api, f"/orgs/{org}/teams/{who}/repos/{repo}")
        if read.status == 404:
            return "none"
        if not read.ok or not isinstance(read.data, Mapping):
            return "unknown"
        return str(read.data.get("role_name") or repo_role(read.data.get("permissions")) or "")
    role, permission, facts = person_role(api, repo, who)
    if role:
        return role
    return (
        "none" if permission == "none" or any("no access" in f.text for f in facts) else "unknown"
    )


def bulk_preview(
    api: GitHubApi,
    changes: Sequence[AccessChange],
    who: str,
    kind: str,
    role: str,
    targets: Sequence[Mapping[str, str]],
) -> tuple[list[AccessChange], list[str]]:
    """``(changes to send, preview lines)``: one line per repository, from its current role.

    A target that already has *role* sends nothing and its line says so, so the
    preview and the requests are always the same list.
    """
    sending: list[AccessChange] = []
    lines: list[str] = []
    for change, target in zip(changes, targets, strict=True):
        repo = target.get("repo", "")
        now = _current_role(api, change, who, kind, repo)
        if now == role:
            lines.append(f"{who} on {repo}: already {role}; nothing is sent.")
            continue
        was = (
            "no access"
            if now == "none"
            else ("a role GitHub would not say" if now == "unknown" else now)
        )
        words = f"{who} on {repo}: {was} now, {role} after."
        lines.append(words)
        sending.append(replace(change, words=words))
    return sending, lines


# -- Compare Accounts -----------------------------------------------------------------------


@dataclass(frozen=True)
class AccountAccess:
    """One signed-in account's access to one repository, as GitHub told that account."""

    label: str
    role: str
    facts: tuple[Fact, ...]
    identity_problem: str = ""


def account_access(
    api: GitHubApi, label: str, login: str, repo: str, *, token: str | None
) -> AccountAccess:
    """What GitHub tells *login*'s own token about *repo*, after checking the token is theirs.

    The token is asked who it belongs to first (``GET /user``); if GitHub names
    somebody else, nothing is shown under *label*, so one account's access can
    never appear under another's name.
    """
    me = fetch(api, "/user")
    who = str(me.data.get("login", "")) if me.ok and isinstance(me.data, Mapping) else ""
    if not who:
        return AccountAccess(label, "", (Fact(me.why_not(f"who {label} is")),), "unknown")
    if who.casefold() != login.casefold():
        problem = (
            f"The token saved for {label} now belongs to {who}, so nothing is shown for "
            f"{label}. Sign in again as {login} from Manage GitHub Accounts."
        )
        return AccountAccess(label, "", (Fact(problem),), problem)
    scopes = me.headers.get("x-oauth-scopes") if "x-oauth-scopes" in me.headers else None
    read = fetch(api, f"/repos/{repo}")
    facts: list[Fact] = []
    role = ""
    if read.ok and isinstance(read.data, Mapping):
        role = repo_role(read.data.get("permissions"))
        facts.append(Fact(f"{role or 'no'} access to {repo}.", f"/repos/{repo} permissions"))
    else:
        facts.append(Fact(read.why_not(repo)))
    facts.append(_viewer_permission(api, repo))
    named, _permission, own = person_role(api, repo, login)
    if named and named != role:
        role = named
    facts.extend(own)
    facts.extend(token_facts(token, scopes))
    return AccountAccess(label, role, tuple(facts))


def compare_accounts(repo: str, first: AccountAccess, second: AccountAccess) -> str:
    """Two accounts side by side on *repo*: each one's evidence, then what differs."""
    lines = [f"{repo}, as GitHub answered each account's own sign-in."]
    for side in (first, second):
        lines += ["", f"{side.label}: {side.role or 'role not known'}."]
        lines += [f"  {fact.line()}" for fact in side.facts]
    lines.append("")
    if first.identity_problem or second.identity_problem or not (first.role and second.role):
        lines.append("What each may do cannot be compared until both roles are known.")
        return "\n".join(lines)
    if first.role == second.role:
        lines.append(
            f"Both have {first.role}: by GitHub's documented defaults they may do the same."
        )
        return "\n".join(lines)
    if first.role in REPO_ROLES and second.role in REPO_ROLES:
        low, high = sorted((first, second), key=lambda s: REPO_ROLES.index(s.role))
        more = compare_roles(low.role, high.role)
        lines.append(f"What {high.label} may do that {low.label} may not. {DOCUMENTED}")
        lines += [f"  {ability}" for ability in more]
    else:
        lines.append("One of them has a custom role; GitHub's API does not list what it adds.")
    return "\n".join(lines)
