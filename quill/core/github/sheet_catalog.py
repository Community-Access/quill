"""Which sheet each Workbench row or node opens, and with what ident (GitHub PRD 15.1).

Alt+Enter on anything: a list row, a tree node, a search result, a
notification. :func:`target_for` names the object a row stands for, as a
sheet kind and the ident its reads and writes are filled with;
:func:`target_for_node` does the same for a tree node (the repository on
``owner/name``, the person on a person). :data:`SHEETS` is every sheet the
Workbench has, by kind, and :func:`context_for` turns what a load learned
into the :class:`~quill.core.github.permissions.ViewerContext` that decides
which fields are editable.

Rows are read by duck typing (``getattr``), so this module needs neither the
Items models nor any window, and stays wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.sheet_engine import SheetDef
from quill.core.github.sheets_items import ISSUE
from quill.core.github.sheets_labels import LABEL, MILESTONE
from quill.core.github.sheets_pulls import PULL_REQUEST
from quill.core.github.sheets_repo import REPOSITORY
from quill.core.workbench.properties import Value

__all__ = [
    "LAST_PAGE",
    "SHEETS",
    "Target",
    "add_finder",
    "context_for",
    "register",
    "target_for",
    "target_for_node",
]

SHEETS: dict[str, SheetDef] = {
    sheet.kind: sheet for sheet in (ISSUE, PULL_REQUEST, REPOSITORY, LABEL, MILESTONE)
}


def _phase_8_sheets() -> tuple[SheetDef, ...]:
    """Every other object's sheet (Appendix C), loaded with the catalogue."""
    from quill.core.github.sheets_actions import ARTIFACT, CACHE, JOB, RUN, WORKFLOW
    from quill.core.github.sheets_code import BRANCH, BRANCH_PROTECTION, COMMIT, FILE, RULESET, TAG
    from quill.core.github.sheets_deploy import DEPLOYMENT, ENVIRONMENT, RUNNER, SECRET, VARIABLE
    from quill.core.github.sheets_misc import (
        CODESPACE,
        DEPLOY_KEY,
        GIST,
        NOTIFICATION,
        WEBHOOK,
    )
    from quill.core.github.sheets_orgs import ORGANIZATION, TEAM
    from quill.core.github.sheets_people import COLLABORATOR, INVITATION, PERSON
    from quill.core.github.sheets_projects import PROJECT
    from quill.core.github.sheets_releases import PACKAGE, RELEASE, RELEASE_ASSET
    from quill.core.github.sheets_security import SECURITY_ALERT
    from quill.core.github.sheets_talk import COMMENT, DISCUSSION, ISSUE_TYPE

    return (
        BRANCH,
        BRANCH_PROTECTION,
        COMMIT,
        FILE,
        RULESET,
        TAG,
        WORKFLOW,
        RUN,
        JOB,
        ARTIFACT,
        CACHE,
        ENVIRONMENT,
        DEPLOYMENT,
        RUNNER,
        SECRET,
        VARIABLE,
        RELEASE,
        RELEASE_ASSET,
        PACKAGE,
        PERSON,
        COLLABORATOR,
        INVITATION,
        ORGANIZATION,
        TEAM,
        GIST,
        CODESPACE,
        NOTIFICATION,
        WEBHOOK,
        DEPLOY_KEY,
        SECURITY_ALERT,
        DISCUSSION,
        COMMENT,
        ISSUE_TYPE,
        PROJECT,
    )


SHEETS.update({sheet.kind: sheet for sheet in _phase_8_sheets()})

#: The last page used per kind of object (section 16.3), for this session.
LAST_PAGE: dict[str, str] = {}


def register(*sheets: SheetDef) -> None:
    """Add sheets to :data:`SHEETS` (each Phase 8 catalogue module calls this once)."""
    for sheet in sheets:
        SHEETS[sheet.kind] = sheet


@dataclass(frozen=True)
class Target:
    """One object: its sheet kind and the values that name it."""

    kind: str
    ident: Mapping[str, str]

    @property
    def sheet(self) -> SheetDef:
        return SHEETS[self.kind]

    def title(self) -> str:
        """ "Issue #42 Properties - owner/name"."""
        name = self.sheet.title(self.ident) or self.sheet.sheet.title
        where = self.ident.get("repo", "") if self.kind != "repository" else ""
        return self.sheet.sheet.heading(name, where)


Finder = Callable[[object, str], "Target | None"]


def _number_at_end(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return tail if tail.isdigit() else ""


def _repo_of_url(url: str) -> str:
    parts = url.split("github.com/", 1)[-1].split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 and url.startswith("https://") else ""


def target_for(row: object, instance: str = "") -> Target | None:
    """The object *row* stands for, or ``None`` when it has no sheet yet."""
    cls = type(row).__name__
    url = str(getattr(row, "url", "") or "")
    repo = str(getattr(row, "repo", "") or "") or instance or _repo_of_url(url)
    if cls == "GitHubItem":
        kind = "pull_request" if getattr(row, "is_pr", False) else "issue"
        return Target(kind, {"repo": repo, "number": str(getattr(row, "number", ""))})
    finder = _BY_CLASS.get(cls)
    if finder is not None:
        return finder(row, repo)
    if cls != "ExploreRow":
        return None
    kind = str(getattr(row, "kind", ""))
    key = str(getattr(row, "key", "") or "")
    title = str(getattr(row, "title", "") or "")
    if kind in ("issue", "pr") and _number_at_end(url):
        return Target(
            "pull_request" if kind == "pr" else "issue",
            {"repo": repo, "number": _number_at_end(url)},
        )
    if kind == "repo" and repo:
        return Target("repository", {"repo": repo})
    if kind == "label" and repo:
        return Target("label", {"repo": repo, "name": title or key or str(row)})
    if kind == "milestone" and repo and _number_at_end(url):
        return Target("milestone", {"repo": repo, "number": _number_at_end(url), "title": key})
    extra = _BY_KIND.get(kind)
    if extra is not None:
        return extra(row, repo)
    return None


#: Phase 8 adds finders here: class name, or Explore row kind, to a Target maker.
_BY_CLASS: dict[str, Finder] = {}
_BY_KIND: dict[str, Finder] = {}


def add_finder(*, cls: str = "", kind: str = "", finder: Finder) -> None:
    if cls:
        _BY_CLASS[cls] = finder
    if kind:
        _BY_KIND[kind] = finder


def _from_url_tail(url: str, marker: str) -> str:
    """The path segment after *marker* in a GitHub address (a tag in .../download/v1/x)."""
    part = url.split(marker, 1)[1] if marker in url else ""
    return part.split("/", 1)[0]


def _install_finders() -> None:
    def attr(row: object, name: str) -> str:
        return str(getattr(row, name, "") or "")

    add_finder(
        cls="GitHubBranch",
        finder=lambda r, repo: Target("branch", {"repo": repo, "branch": attr(r, "name")}),
    )
    add_finder(
        cls="GitHubTag",
        finder=lambda r, repo: Target("tag", {"repo": repo, "tag": attr(r, "name")}),
    )
    add_finder(
        cls="GitHubCommit",
        finder=lambda r, repo: Target("commit", {"repo": repo, "sha": attr(r, "sha")}),
    )
    add_finder(
        cls="GitHubRelease",
        finder=lambda r, repo: Target("release", {"repo": repo, "tag": attr(r, "tag")}),
    )
    add_finder(
        cls="GitHubReleaseAsset",
        finder=lambda r, repo: (
            Target(
                "release_asset",
                {
                    "repo": repo,
                    "name": attr(r, "name"),
                    "tag": _from_url_tail(attr(r, "browser_download_url"), "/releases/download/"),
                },
            )
            if repo
            else None
        ),
    )
    add_finder(
        cls="GitHubWorkflow",
        finder=lambda r, repo: Target(
            "workflow", {"repo": repo, "id": attr(r, "id"), "name": attr(r, "name")}
        ),
    )
    add_finder(
        cls="GitHubWorkflowRun",
        finder=lambda r, repo: Target(
            "run", {"repo": repo, "id": attr(r, "id"), "number": attr(r, "run_number")}
        ),
    )
    add_finder(
        kind="person",
        finder=lambda r, _repo: Target("person", {"login": attr(r, "key") or attr(r, "label")}),
    )
    add_finder(
        kind="org",
        finder=lambda r, _repo: Target("organization", {"org": attr(r, "key") or attr(r, "label")}),
    )
    add_finder(kind="gist", finder=lambda r, _repo: Target("gist", {"id": attr(r, "key")}))
    add_finder(
        kind="team",
        finder=lambda r, repo: (
            Target("team", {"org": repo, "team": attr(r, "key")}) if repo else None
        ),
    )
    add_finder(
        kind="notification", finder=lambda r, _repo: Target("notification", {"id": attr(r, "key")})
    )
    add_finder(
        kind="cache", finder=lambda r, repo: Target("cache", {"repo": repo, "id": attr(r, "key")})
    )
    add_finder(
        kind="project",
        finder=lambda r, _repo: Target(
            "project", {"node_id": attr(r, "key"), "title": attr(r, "title")}
        ),
    )
    add_finder(
        kind="file",
        finder=lambda r, repo: (
            Target("file", {"repo": repo, "path": attr(r, "key")}) if attr(r, "key") else None
        ),
    )

    def alert(row: object, repo: str) -> Target | None:
        kind, _, number = attr(row, "key").partition(":")
        if not kind or not number:
            return None
        return Target(
            "security_alert", {"repo": repo, "number": number, "alert_path": f"{kind}/alerts"}
        )

    def discussion(row: object, repo: str) -> Target | None:
        number = _number_at_end(attr(row, "url"))
        return Target("discussion", {"repo": repo, "number": number}) if number else None

    add_finder(kind="security", finder=alert)
    add_finder(kind="discussion", finder=discussion)


def target_for_node(template: str, key: str, instance: str) -> Target | None:
    """The object a tree node is: a repository, person or organization (else ``None``)."""
    if not instance:
        return None
    if template == "repository" and key == "repository":
        return Target("repository", {"repo": instance})
    if template == "person" and key == "person" and "person" in SHEETS:
        return Target("person", {"login": instance})
    if template == "organization" and key == "organization" and "organization" in SHEETS:
        return Target("organization", {"org": instance})
    return None


def context_for(
    values: Mapping[str, Value],
    viewer: Mapping[str, bool],
    *,
    signed_in: bool,
    login: str = "",
    scopes: tuple[str, ...] | None = None,
    level: AccessLevel = AccessLevel.FULL,
    where: str = "",
) -> ViewerContext:
    """What GitHub said about you and this object, for greying with reasons."""
    owner = str(values.get("login", "") or values.get("owner", ""))
    return ViewerContext(
        signed_in=signed_in,
        login=login,
        where=where,
        repo_role=str(values.get("your_access", "") or ""),
        org_role=str(values.get("your_org_role", "") or ""),
        team_role=str(values.get("your_team_role", "") or ""),
        scopes=scopes,
        viewer=dict(viewer),
        is_self=bool(login) and owner.casefold() == login.casefold(),
        level=level,
    )


_install_finders()
