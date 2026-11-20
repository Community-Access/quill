"""Least-privilege advice from what QUILL saw, with what it cannot know said plainly.

Account > Roles and Access > Least Privilege Advice reads four things and
changes nothing:

* :mod:`quill.core.github.observed_use`: the kinds of request this account
  sent through QUILL on this computer, the commands that passed the write
  gate with their tiers, and every 403 with what GitHub said it wanted
  (``X-Accepted-GitHub-Permissions`` for a fine-grained token);
* Change History (:mod:`quill.core.github.change_log`): each write's kind and tier;
* ``X-OAuth-Scopes``: a classic token's scopes, or no header at all for a
  fine-grained token or a GitHub App, whose permissions GitHub does not list;
* the account's Workbench level (:mod:`quill.core.github.permissions`).

From those it suggests the smallest classic scopes, the fine-grained
permissions by GitHub's own names, and the smallest Workbench level that
cover what was seen -- and then says what it cannot know. A suggestion that
depends on something QUILL cannot see (whether a repository is private) says
so beside it instead of guessing.

wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from quill.core.github.observed_use import AccountUse
from quill.core.github.permissions import AccessLevel, WriteTier, expand_scopes

__all__ = [
    "Advice",
    "advise",
    "classic_needs",
    "fine_grained_needs",
    "parse_accepted",
    "report",
]

# -- what an area of GitHub needs -----------------------------------------------------------

#: Classic scope for a *change* in an area ("" when none is needed beyond signing in).
_CLASSIC_WRITE: dict[str, str] = {
    "repos/hooks": "admin:repo_hook",
    "repos/contents:workflows": "workflow",
    "repos/code-scanning": "security_events",
    "repos/dependabot": "security_events",
    "repos/secret-scanning": "security_events",
    "orgs": "admin:org",
    "orgs/hooks": "admin:org_hook",
    "orgs/members": "write:org",
    "orgs/memberships": "write:org",
    "orgs/teams": "write:org",
    "orgs/invitations": "write:org",
    "orgs/outside_collaborators": "admin:org",
    "orgs/packages": "write:packages",
    "orgs/copilot": "copilot",
    "teams/members": "write:org",
    "teams/memberships": "write:org",
    "teams/repos": "write:org",
    "user": "user",
    "user/emails": "user",
    "user/following": "user:follow",
    "user/keys": "admin:public_key",
    "user/gpg_keys": "admin:gpg_key",
    "user/ssh_signing_keys": "admin:ssh_signing_key",
    "user/packages": "write:packages",
    "user/codespaces": "codespace",
    "user/repos": "repo",
    "gists": "gist",
    "notifications": "notifications",
    "projects": "project",
}
#: Classic scope for a *read* in an area, where reading needs one.
_CLASSIC_READ: dict[str, str] = {
    "repos/hooks": "admin:repo_hook",
    "repos/code-scanning": "security_events",
    "repos/dependabot": "security_events",
    "repos/secret-scanning": "security_events",
    "orgs/members": "read:org",
    "orgs/teams": "read:org",
    "orgs/hooks": "admin:org_hook",
    "orgs/audit-log": "read:audit_log",
    "orgs/code-scanning": "security_events",
    "orgs/dependabot": "security_events",
    "orgs/secret-scanning": "security_events",
    "orgs/packages": "read:packages",
    "orgs/copilot": "copilot",
    "user/orgs": "read:org",
    "user/teams": "read:org",
    "user/memberships": "read:org",
    "user/emails": "user:email",
    "user/keys": "admin:public_key",
    "user/gpg_keys": "admin:gpg_key",
    "user/ssh_signing_keys": "admin:ssh_signing_key",
    "user/packages": "read:packages",
    "user/codespaces": "codespace",
    "notifications": "notifications",
    "projects": "read:project",
}
#: GitHub's fine-grained permission for an area, by the name on GitHub's token page.
_FINE: dict[str, str] = {
    "repos": "Administration",
    "repos/issues": "Issues",
    "repos/labels": "Issues",
    "repos/milestones": "Issues",
    "repos/assignees": "Issues",
    "repos/pulls": "Pull requests",
    "repos/contents": "Contents",
    "repos/contents:workflows": "Workflows",
    "repos/commits": "Contents",
    "repos/branches": "Contents",
    "repos/git": "Contents",
    "repos/compare": "Contents",
    "repos/releases": "Contents",
    "repos/tags": "Contents",
    "repos/readme": "Contents",
    "repos/merges": "Contents",
    "repos/actions": "Actions",
    "repos/hooks": "Webhooks",
    "repos/deployments": "Deployments",
    "repos/environments": "Environments",
    "repos/pages": "Pages",
    "repos/collaborators": "Administration",
    "repos/invitations": "Administration",
    "repos/rulesets": "Administration",
    "repos/topics": "Administration",
    "repos/keys": "Administration",
    "repos/autolinks": "Administration",
    "repos/code-scanning": "Code scanning alerts",
    "repos/dependabot": "Dependabot alerts",
    "repos/secret-scanning": "Secret scanning alerts",
    "repos/security-advisories": "Repository security advisories",
    "repos/discussions": "Discussions",
    "repos/statuses": "Commit statuses",
    "repos/check-runs": "Checks",
    "repos/check-suites": "Checks",
    "repos/codespaces": "Codespaces",
    "repos/dependency-graph": "Contents",
    "orgs": "Organization Administration",
    "orgs/members": "Members",
    "orgs/memberships": "Members",
    "orgs/teams": "Members",
    "orgs/invitations": "Members",
    "orgs/hooks": "Organization webhooks",
    "orgs/audit-log": "Organization Administration",
    "orgs/actions": "Organization Administration",
    "orgs/copilot": "Copilot Business",
    "teams/members": "Members",
    "user": "Profile",
    "user/emails": "Email addresses",
    "user/following": "Followers",
    "user/keys": "Git SSH keys",
    "user/gpg_keys": "GPG keys",
    "user/ssh_signing_keys": "SSH signing keys",
    "user/codespaces": "Codespaces",
    "user/starred": "Starring",
    "gists": "Gists",
}
#: Areas a fine-grained token cannot reach at all.
_NOT_FINE: dict[str, str] = {
    "notifications": "the notifications inbox",
    "orgs/packages": "packages",
    "user/packages": "packages",
}
#: Change History kinds whose writes need more than repository access.
_KIND_SCOPE: dict[str, str] = {
    "gist": "gist",
    "organization": "admin:org",
    "team": "write:org",
    "person": "user",
    "project": "project",
    "package": "write:packages",
    "codespace": "codespace",
    "webhook": "admin:repo_hook",
    "security_alert": "security_events",
}


def _split(request: str) -> tuple[str, str]:
    method, _, area = request.partition(" ")
    return method.upper(), area


def classic_needs(use: AccountUse, kinds: Iterable[str] = ()) -> tuple[set[str], set[str]]:
    """``(needed, needed_if_private)``: the classic scopes what was seen needs.

    A change to a repository needs ``repo``, unless every repository changed is
    public, when ``public_repo`` does; QUILL cannot see which, so a plain
    repository change lands in *needed_if_private* as ``repo`` and in *needed*
    as ``public_repo``. A read of a repository needs ``repo`` only if it is
    private.
    """
    needed: set[str] = set()
    private: set[str] = set()
    for request in use.requests:
        method, area = _split(request)
        if method == "GET":
            scope = _CLASSIC_READ.get(area, "")
            if scope:
                needed.add(scope)
            elif area.startswith("repos"):
                private.add("repo")
            continue
        scope = _CLASSIC_WRITE.get(area, "")
        if method == "DELETE" and area == "repos":
            scope = "delete_repo"
        if scope == "repo" or area.startswith("repos"):
            needed.add("public_repo")
            private.add("repo")
        if scope and scope != "repo":
            needed.add(scope)
    for command in use.commands:
        needed.update(_command_scopes(command))
    for kind in kinds:
        scope = _KIND_SCOPE.get(kind, "")
        if scope:
            needed.add(scope)
        elif kind not in ("access", "api_console"):
            needed.add("public_repo")
            private.add("repo")
    needed.discard("")
    if "repo" in needed:
        needed.discard("public_repo")
    return needed, private - needed


def _command_scopes(command_id: str) -> set[str]:
    from quill.core.github.write_requirements import COMMAND_REQUIREMENTS, EDITOR_REQUIREMENTS

    declared = COMMAND_REQUIREMENTS.get(command_id) or EDITOR_REQUIREMENTS.get(command_id)
    if declared is None:
        return set()
    found: set[str] = set()
    for token in declared[0].split("+"):
        kind, _, value = token.partition(":")
        if kind == "scope" and value:
            found.add(value)
        elif kind == "org":
            found.add("admin:org" if value == "owner" else "read:org")
        elif kind == "team":
            found.add("write:org")
    return found


def parse_accepted(value: str) -> list[str]:
    """``"issues=write; pull_requests=write"`` as ``["Issues: write", ...]`` (any one set)."""
    words: list[str] = []
    for option in value.replace(";", ",").split(","):
        name, _, access = option.strip().partition("=")
        if name:
            label = name.replace("_", " ").strip().capitalize()
            words.append(f"{label}: {access.strip() or 'some access'}")
    return words


def fine_grained_needs(use: AccountUse) -> tuple[dict[str, str], set[str], list[str]]:
    """``(permissions, unreachable, unnamed)`` for a fine-grained token.

    *permissions* maps GitHub's permission name to ``"Read-only"`` or
    ``"Read and write"``; *unreachable* names what no fine-grained token can
    reach; *unnamed* is each area QUILL has no permission name for.
    """
    found: dict[str, str] = {}
    unreachable: set[str] = set()
    unnamed: list[str] = []
    for request in sorted(use.requests):
        method, area = _split(request)
        if area in _NOT_FINE:
            unreachable.add(_NOT_FINE[area])
            continue
        name = _FINE.get(area)
        if name is None:
            if area.startswith("repos"):
                name = "Metadata"
            else:
                if area not in unnamed and not area.startswith(("search", "users", "rate_limit")):
                    unnamed.append(area)
                continue
        level = "Read-only" if method == "GET" else "Read and write"
        if found.get(name) != "Read and write":
            found[name] = level
    if any(_split(r)[1].startswith("repos") for r in use.requests):
        found.setdefault("Metadata", "Read-only")  # every repository token has it
    return found, unreachable, unnamed


# -- the advice --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Advice:
    """What the report says, as parts a test can check."""

    login: str
    classic: bool  # GitHub sent X-OAuth-Scopes
    has: tuple[str, ...]
    needed: tuple[str, ...]
    needed_if_private: tuple[str, ...]
    unused: tuple[str, ...]
    narrower: Mapping[str, tuple[str, ...]]
    fine: Mapping[str, str]
    unreachable: tuple[str, ...]
    unnamed: tuple[str, ...]
    refused: Mapping[str, str]
    highest_tier: int | None
    smallest_level: AccessLevel
    level: AccessLevel
    seen_requests: int
    seen_commands: int
    seen_changes: int
    since: float
    notes: tuple[str, ...] = field(default=())


def _smallest_level(tier: int | None) -> AccessLevel:
    if tier is None:
        return AccessLevel.READ_ONLY
    return AccessLevel.ORGANIZE if tier <= WriteTier.VISIBLE else AccessLevel.FULL


def advise(
    *,
    login: str,
    use: AccountUse,
    scopes: Sequence[str] | None,
    history: Iterable[object] = (),
    level: AccessLevel = AccessLevel.FULL,
) -> Advice:
    """The advice for one account. *history* is its Change History entries.

    *scopes* is the token's ``X-OAuth-Scopes`` (``None`` when GitHub sent no
    such header: a fine-grained token or a GitHub App).
    """
    entries = [e for e in history if not login or getattr(e, "account", "") in ("", login)]
    kinds = [str(getattr(e, "kind", "")) for e in entries]
    needed, private = classic_needs(use, kinds)
    tiers = [int(t) for t in use.commands.values()]
    tiers += [int(getattr(e, "tier", 0)) for e in entries]
    highest = max(tiers) if tiers else None
    has = tuple(scopes) if scopes is not None else ()
    covered = expand_scopes((*needed, *private))
    unused = tuple(s for s in has if s not in covered and not expand_scopes((s,)) & covered)
    narrower = {
        s: tuple(sorted(expand_scopes((s,)) & covered))
        for s in has
        if s not in covered and expand_scopes((s,)) & covered
    }
    fine, unreachable, unnamed = fine_grained_needs(use)
    return Advice(
        login=login,
        classic=scopes is not None,
        has=has,
        needed=tuple(sorted(needed)),
        needed_if_private=tuple(sorted(private)),
        unused=unused,
        narrower=narrower,
        fine=dict(sorted(fine.items())),
        unreachable=tuple(sorted(unreachable)),
        unnamed=tuple(unnamed),
        refused=dict(sorted(use.refused.items())),
        highest_tier=highest,
        smallest_level=_smallest_level(highest),
        level=level,
        seen_requests=len(use.requests),
        seen_commands=len(use.commands),
        seen_changes=len(entries),
        since=use.since,
    )


def _names(items: Iterable[str]) -> str:
    listed = list(items)
    return ", ".join(listed) if listed else "none"


def _day(moment: float) -> str:
    return time.strftime("%d %b %Y", time.localtime(moment)) if moment else "this session"


def report(advice: Advice) -> str:
    """The whole report, in plain sentences, for a window to read."""
    from quill.core.github.permissions import classic_token_url

    who = advice.login or "this account"
    lines = [
        f"Least privilege advice for {who}, from what QUILL saw on this computer. "
        "It changes nothing.",
        "",
        "What QUILL saw",
        f"Since {_day(advice.since)}: {advice.seen_requests} kinds of request to GitHub, "
        f"{advice.seen_commands} commands that change GitHub, and {advice.seen_changes} "
        "changes in Change History.",
    ]
    if advice.refused:
        lines.append(f"GitHub refused {len(advice.refused)} kinds of request:")
        for request, wanted in advice.refused.items():
            asked = "; ".join(parse_accepted(wanted)) if wanted else "GitHub did not say what"
            lines.append(f"{request}: it wanted {asked}.")
    lines += ["", "Workbench level"]
    if advice.highest_tier is None:
        lines.append("Read Only covers it: nothing QUILL saw changed GitHub.")
    else:
        tier = WriteTier(min(max(advice.highest_tier, 0), WriteTier.DESTRUCTIVE))
        lines.append(
            f"{advice.smallest_level.label} covers it: the most a change needed was tier "
            f"{int(tier)}, {tier.words.split(':', 1)[0]}."
        )
    if advice.level is not advice.smallest_level:
        lines.append(
            f"This account is set to {advice.level.label}. Roles and Access, Workbench Level "
            "for This Account changes it."
        )
    lines += ["", "Classic token scopes"]
    if advice.classic:
        lines.append(f"This token has: {_names(advice.has)}.")
    else:
        lines.append("This token sends no scopes, so it is a fine-grained token or an app's.")
    smallest = list(advice.needed)
    lines.append(f"Enough for what QUILL saw: {_names(smallest)}.")
    if advice.needed_if_private:
        lines.append(
            f"Add {_names(advice.needed_if_private)} only if a repository you use is private: "
            "public_repo covers changes to public ones, and reading a public one needs no scope."
        )
    if advice.classic and advice.unused:
        lines.append(f"Never used here: {_names(advice.unused)}.")
    for broad, enough in advice.narrower.items():
        lines.append(f"{broad} is more than was used: {_names(enough)} would do.")
    if advice.classic and (advice.unused or advice.narrower):
        lines.append("GitHub's page for a new token with only the scopes above:")
        lines.append(classic_token_url(sorted({*smallest, *advice.needed_if_private}) or ["repo"]))
    if advice.classic and not advice.unused and not advice.narrower:
        lines.append("Every scope this token has was used here.")
    lines += ["", "Fine-grained token"]
    if advice.fine:
        lines.append("Repository and account permissions that cover what QUILL saw:")
        lines += [f"{name}: {access}." for name, access in advice.fine.items()]
    else:
        lines.append("QUILL saw no request a fine-grained permission is named for.")
    if advice.unreachable:
        lines.append(
            f"No fine-grained token reaches {_names(advice.unreachable)}: keep a classic token "
            "or Sign In with GitHub for those."
        )
    if advice.unnamed:
        lines.append(f"QUILL has no permission name for: {_names(advice.unnamed)}.")
    lines += [
        "",
        "What QUILL cannot know",
        "It saw only this computer's use of this account. Another computer, the gh command, "
        "scripts and GitHub's website are not counted, and something you do rarely may not "
        "have happened yet.",
        "GitHub does not list a fine-grained token's exact permissions, so QUILL cannot say "
        "which ones this token has: only what worked, and what GitHub refused.",
        "It counts requests sent through its own REST path. GraphQL (Projects, Discussions) "
        "and some lists read another way are counted only through the commands you ran and "
        "Change History.",
        "It cannot see whether a repository is private, so repo is suggested only where that "
        "would matter.",
        "",
        "To change a token, use GitHub: Settings, Developer settings, Personal access tokens.",
    ]
    return "\n".join(lines)
