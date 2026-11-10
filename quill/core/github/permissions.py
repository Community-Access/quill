"""Who may do what in the GitHub Workbench (GitHub PRD section 18, GH-R-060 to GH-R-066).

Four questions, answered here and nowhere else, so menus, context menus,
Shift+F1 and Properties sheets cannot disagree:

1. **Which tier is it?** :class:`WriteTier`: 0 organizing (labels, reactions),
   1 visible to others (comments, close), 2 access and settings (roles, rules),
   3 destructive or hard to reverse (delete, transfer, make public).
2. **Does this account allow that tier here?** :class:`AccessLevel`, chosen per
   account in Workbench Options: Read Only, Organize (tiers 0 and 1) or Full.
   Safe Mode makes every account Read Only for the session.
3. **Does GitHub let you?** A requirement string (``"repo:triage"``,
   ``"org:owner"``, ``"scope:project"``, ``"viewer:viewerCanUpdate"``, joined
   with ``+`` when it needs several) checked against a :class:`ViewerContext`
   built from what GitHub said about you and the object (``permissions`` on a
   repository, ``viewerCan*`` fields, the token's scopes).
4. **What do you have, and how do you get the rest?** :data:`SCOPES`, every
   scope any Workbench feature can use, with what it unlocks, and the three
   ways to add the missing ones (the device flow again, a classic token's
   page, ``gh auth refresh``).

Each refusal is one sentence naming what it needs, what you have and who can
change it. wx-free and strict-typed; the access choice is one JSON file,
written atomically.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "ACCESS_FILENAME",
    "REPO_ROLES",
    "SCOPES",
    "AccessLevel",
    "AccessStore",
    "Scope",
    "ViewerContext",
    "WriteTier",
    "check",
    "classic_token_url",
    "effective_level",
    "expand_scopes",
    "fine_grained_steps",
    "gh_refresh_command",
    "level_allows",
    "missing_scopes",
    "repo_role",
    "requirement_words",
    "safe_mode_on",
    "scope_rows",
]


class WriteTier(IntEnum):
    """How much a write changes (section 18.4), which decides how it is confirmed."""

    ORGANIZING = 0
    VISIBLE = 1
    ACCESS = 2
    DESTRUCTIVE = 3

    @property
    def words(self) -> str:
        return _TIER_WORDS[self]


_TIER_WORDS = {
    WriteTier.ORGANIZING: "organizing: saves at once and can be undone",
    WriteTier.VISIBLE: "visible to others: saves at once unless Workbench Options asks first",
    WriteTier.ACCESS: "access and settings: a preview in words first",
    WriteTier.DESTRUCTIVE: (
        "destructive or hard to reverse: a preview, then the name typed to confirm"
    ),
}


class AccessLevel(StrEnum):
    """What one account may do in the Workbench, whatever GitHub would allow."""

    READ_ONLY = "read_only"
    ORGANIZE = "organize"
    FULL = "full"

    @property
    def label(self) -> str:
        return {"read_only": "Read Only", "organize": "Organize", "full": "Full"}[self.value]


def level_allows(level: AccessLevel, tier: WriteTier) -> bool:
    """Read Only allows no write; Organize tiers 0 and 1; Full everything."""
    if level is AccessLevel.READ_ONLY:
        return False
    if level is AccessLevel.ORGANIZE:
        return tier <= WriteTier.VISIBLE
    return True


def safe_mode_on() -> bool:
    return os.environ.get("QUILL_SAFE_MODE", "").strip() in {"1", "true", "yes"}


ACCESS_FILENAME = "github_workbench_access.json"


@dataclass
class AccessStore:
    """Each account's Workbench access level, kept on this device."""

    path: Path | None = None
    levels: dict[str, AccessLevel] = field(default_factory=dict)

    def _file(self) -> Path:
        return self.path or (app_data_dir() / ACCESS_FILENAME)

    @classmethod
    def load(cls, path: Path | None = None) -> AccessStore:
        store = cls(path)
        raw = read_json(store._file(), default={})
        levels = raw.get("levels", {}) if isinstance(raw, dict) else {}
        for account, value in levels.items() if isinstance(levels, dict) else ():
            if isinstance(account, str) and value in {level.value for level in AccessLevel}:
                store.levels[account] = AccessLevel(value)
        return store

    def level(self, account: str) -> AccessLevel:
        return self.levels.get(account, AccessLevel.FULL)

    def set(self, account: str, level: AccessLevel) -> None:
        self.levels[account] = level
        write_json_atomic(
            self._file(),
            {"schema_version": 1, "levels": {k: v.value for k, v in sorted(self.levels.items())}},
        )


def effective_level(stored: AccessLevel, *, safe_mode: bool | None = None) -> AccessLevel:
    """The level in force: Safe Mode makes every account Read Only (GH-R-066)."""
    on = safe_mode_on() if safe_mode is None else safe_mode
    return AccessLevel.READ_ONLY if on else stored


# ---------------------------------------------------------------------------
# Scopes (section 18.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scope:
    name: str
    unlocks: str
    group: str
    risky: bool = False
    why: str = ""


SCOPES: tuple[Scope, ...] = (
    Scope(
        "repo",
        "private repositories and every write to issues, pull requests, "
        "labels, milestones, releases, Actions, secrets and settings",
        "Repositories",
    ),
    Scope("public_repo", "writes to public repositories only", "Repositories"),
    Scope("workflow", "saving files under .github/workflows", "Repositories"),
    Scope(
        "delete_repo",
        "deleting a repository",
        "Repositories",
        True,
        "Only if you delete repositories from the Workbench; the command still "
        "asks you to type the name.",
    ),
    Scope("admin:repo_hook", "creating, editing and deleting repository webhooks", "Repositories"),
    Scope("read:org", "listing your organizations, teams and members", "Organizations"),
    Scope("write:org", "managing organization membership and teams", "Organizations"),
    Scope(
        "admin:org",
        "organization settings, roles, member privileges and Actions permissions",
        "Organizations",
        True,
        "Only for organization owners who manage settings here.",
    ),
    Scope("admin:org_hook", "organization webhooks", "Organizations"),
    Scope("read:audit_log", "reading an organization's audit log", "Organizations"),
    Scope("project", "set an item's projects and edit project fields, views and items", "Projects"),
    Scope("read:project", "reading Projects only", "Projects"),
    Scope("notifications", "the notifications inbox without full repo access", "You"),
    Scope("user", "editing your profile, emails and follows", "You"),
    Scope("user:follow", "following and unfollowing people", "You"),
    Scope("user:email", "reading your email addresses", "You"),
    Scope("gist", "creating, editing, starring and deleting gists", "Gists"),
    Scope("write:packages", "publishing packages and changing their access", "Packages"),
    Scope("read:packages", "reading private packages", "Packages"),
    Scope(
        "delete:packages",
        "deleting and restoring packages",
        "Packages",
        True,
        "Only if you delete packages from the Workbench.",
    ),
    Scope("admin:public_key", "your SSH keys", "Keys"),
    Scope("admin:gpg_key", "your GPG keys", "Keys"),
    Scope("admin:ssh_signing_key", "your SSH signing keys", "Keys"),
    Scope(
        "security_events", "code scanning and Dependabot alerts: list, dismiss, reopen", "Security"
    ),
    Scope("codespace", "creating, starting, stopping and deleting Codespaces", "Codespaces"),
    Scope("copilot", "Copilot settings for an organization", "Copilot"),
)

#: What a classic scope also grants (GitHub's documented scope hierarchy).
_IMPLIES: dict[str, tuple[str, ...]] = {
    "repo": ("public_repo", "repo:status", "repo_deployment", "repo:invite", "security_events"),
    "admin:org": ("write:org", "read:org", "manage_runners:org"),
    "write:org": ("read:org",),
    "project": ("read:project",),
    "user": ("read:user", "user:email", "user:follow"),
    "write:packages": ("read:packages",),
    "admin:repo_hook": ("write:repo_hook", "read:repo_hook"),
    "admin:org_hook": (),
    "admin:public_key": ("write:public_key", "read:public_key"),
    "admin:gpg_key": ("write:gpg_key", "read:gpg_key"),
}


def expand_scopes(scopes: Iterable[str]) -> frozenset[str]:
    """*scopes* and everything each one implies."""
    found: set[str] = set()
    pending = [scope.strip() for scope in scopes if scope.strip()]
    while pending:
        scope = pending.pop()
        if scope in found:
            continue
        found.add(scope)
        pending.extend(_IMPLIES.get(scope, ()))
    return frozenset(found)


def missing_scopes(have: Iterable[str] | None, wanted: Iterable[str]) -> tuple[str, ...]:
    """The scopes in *wanted* that *have* (and what it implies) does not cover."""
    if have is None:
        return ()
    granted = expand_scopes(have)
    return tuple(scope for scope in wanted if scope not in granted)


def scope_rows(have: Iterable[str] | None) -> list[tuple[Scope, str]]:
    """Each scope with its sentence: "project: set an item's projects... You have it."

    *have* is ``None`` for a fine-grained token or a GitHub App, whose
    permissions GitHub does not list in a header: the sentence says so rather
    than guessing.
    """
    granted = expand_scopes(have) if have is not None else None
    rows: list[tuple[Scope, str]] = []
    for scope in SCOPES:
        if granted is None:
            state = "This token's permissions are set on GitHub."
        elif scope.name in granted:
            state = "You have it."
        else:
            state = "You do not have it."
        risky = " Optional and risky: " + scope.why if scope.risky and scope.why else ""
        rows.append((scope, f"{scope.name}: {scope.unlocks}. {state}{risky}"))
    return rows


def gh_refresh_command(scopes: Iterable[str]) -> str:
    """The ``gh`` command that adds *scopes* to its sign-in."""
    names = ",".join(scopes)
    return f"gh auth refresh -h github.com -s {names}" if names else ""


def classic_token_url(scopes: Iterable[str]) -> str:
    """GitHub's new classic token page with *scopes* ticked and a description filled."""
    from urllib.parse import urlencode

    return "https://github.com/settings/tokens/new?" + urlencode({
        "scopes": ",".join(scopes),
        "description": "QUILL GitHub Workbench",
    })


#: A fine-grained token's permission, by GitHub's own name, for each scope.
_FINE_GRAINED: dict[str, str] = {
    "repo": "Repository permissions: Contents, Issues, Pull requests, Metadata: Read and write",
    "public_repo": "Repository access: Public repositories",
    "workflow": "Repository permissions: Workflows: Read and write",
    "delete_repo": "Repository permissions: Administration: Read and write",
    "admin:repo_hook": "Repository permissions: Webhooks: Read and write",
    "read:org": "Organization permissions: Members: Read-only",
    "write:org": "Organization permissions: Members: Read and write",
    "admin:org": "Organization permissions: Administration: Read and write",
    "admin:org_hook": "Organization permissions: Webhooks: Read and write",
    "read:audit_log": "Organization permissions: Administration: Read-only",
    "project": "Organization permissions: Projects: Read and write",
    "read:project": "Organization permissions: Projects: Read-only",
    "notifications": "Not available to fine-grained tokens: use a classic token or sign in",
    "user": "Account permissions: Profile: Read and write",
    "user:follow": "Account permissions: Followers: Read and write",
    "user:email": "Account permissions: Email addresses: Read-only",
    "gist": "Account permissions: Gists: Read and write",
    "write:packages": "Not available to fine-grained tokens yet: use a classic token",
    "read:packages": "Not available to fine-grained tokens yet: use a classic token",
    "delete:packages": "Not available to fine-grained tokens yet: use a classic token",
    "admin:public_key": "Account permissions: Git SSH keys: Read and write",
    "admin:gpg_key": "Account permissions: GPG keys: Read and write",
    "admin:ssh_signing_key": "Account permissions: SSH signing keys: Read and write",
    "security_events": "Repository permissions: Code scanning alerts, Dependabot alerts: "
    "Read and write",
    "codespace": "Account permissions: Codespaces: Read and write",
    "copilot": "Organization permissions: Copilot Business: Read and write",
}


def fine_grained_steps(scopes: Iterable[str]) -> list[str]:
    """What to set on a fine-grained token, by GitHub's names, for *scopes*."""
    return [f"{scope}: {_FINE_GRAINED.get(scope, 'see GitHub docs')}" for scope in scopes]


# ---------------------------------------------------------------------------
# Roles and requirements (section 18.2)
# ---------------------------------------------------------------------------

REPO_ROLES: tuple[str, ...] = ("read", "triage", "write", "maintain", "admin")
_REPO_RANK = {role: index for index, role in enumerate(REPO_ROLES)}
_PERMISSION_KEYS = (
    ("admin", "admin"),
    ("maintain", "maintain"),
    ("push", "write"),
    ("triage", "triage"),
    ("pull", "read"),
)


def repo_role(permissions: object) -> str:
    """The role GitHub reported: a REST ``permissions`` map or GraphQL ``viewerPermission``."""
    if isinstance(permissions, str):
        word = permissions.strip().lower()
        return {"write": "write", "push": "write", "pull": "read"}.get(word, word)
    if isinstance(permissions, Mapping):
        for key, role in _PERMISSION_KEYS:
            if permissions.get(key):
                return role
    return ""


@dataclass(frozen=True)
class ViewerContext:
    """What GitHub said about you and one object, for :func:`check`."""

    signed_in: bool = True
    login: str = ""
    where: str = ""
    repo_role: str = ""
    org_role: str = ""
    team_role: str = ""
    scopes: tuple[str, ...] | None = None
    viewer: Mapping[str, bool] = field(default_factory=dict)
    is_self: bool = False
    level: AccessLevel = AccessLevel.FULL


_ROLE_WORDS = {
    "read": "read",
    "triage": "triage",
    "write": "write",
    "maintain": "maintain",
    "admin": "admin",
}


def requirement_words(requirement: str) -> str:
    """A requirement in words: "triage access to the repository and the project scope"."""
    parts: list[str] = []
    for token in (t for t in requirement.split("+") if t):
        kind, _, value = token.partition(":")
        if kind == "repo":
            parts.append(f"{value} access to the repository")
        elif kind == "org":
            parts.append(f"the organization {value} role")
        elif kind == "team":
            parts.append(f"team {value}")
        elif kind == "scope":
            parts.append(f"the {value} permission")
        elif kind == "viewer":
            parts.append(f"GitHub's permission ({value})")
        elif kind == "self":
            parts.append("being your own")
        elif kind == "sign_in":
            parts.append("a signed-in account")
        else:
            parts.append(token)
    return " and ".join(parts) or "nothing"


def _check_one(token: str, ctx: ViewerContext) -> str:
    kind, _, value = token.partition(":")
    where = ctx.where or "this repository"
    if kind == "sign_in" or not ctx.signed_in:
        return "" if ctx.signed_in else "Sign in to GitHub first: Account, Manage GitHub Accounts."
    if kind == "repo":
        have = ctx.repo_role
        if have and _REPO_RANK.get(have, -1) >= _REPO_RANK.get(value, 99):
            return ""
        you = f"You have {have} access." if have else "GitHub did not say what access you have."
        return (
            f"Changing this needs {value} access to {where}. {you} An owner or admin "
            "of the repository can give it to you."
        )
    if kind == "org":
        if value == "member" and ctx.org_role in {"member", "owner"}:
            return ""
        if value == "owner" and ctx.org_role == "owner":
            return ""
        you = f"You are a {ctx.org_role}." if ctx.org_role else "You are not a member."
        return f"This needs the {value} role in the organization. {you} An owner can change that."
    if kind == "team":
        if ctx.team_role == "maintainer" or ctx.org_role == "owner":
            return ""
        return (
            "This needs a maintainer of the team or an owner of the organization. "
            "A team maintainer can make you one."
        )
    if kind == "scope":
        if ctx.scopes is None or not missing_scopes(ctx.scopes, (value,)):
            return ""
        return (
            f"Your sign-in does not have the {value} permission. Account, GitHub "
            "Permissions adds it."
        )
    if kind == "viewer":
        if ctx.viewer.get(value, True):
            return ""
        return f"GitHub says you may not do this here ({value} is false)."
    if kind == "self":
        return "" if ctx.is_self else "Only the account's own person can change this."
    return ""


def check(requirement: str, ctx: ViewerContext, tier: WriteTier | None = None) -> str:
    """ "" when *ctx* may do something needing *requirement*; else why not, in sentences."""
    if tier is not None and not level_allows(ctx.level, tier):
        if ctx.level is AccessLevel.READ_ONLY:
            return (
                "This account is read only in the Workbench. Workbench Options, "
                "Accounts changes it."
            )
        return (
            "This account is set to Organize in the Workbench, which allows organizing and "
            "comments, not access, settings or deleting."
        )
    for token in (t for t in requirement.split("+") if t):
        reason = _check_one(token, ctx)
        if reason:
            return reason
    return ""
