"""Repositories > My Packages: your GitHub Packages, their versions, and deleting them (PRD 14.2).

GitHub Packages holds what a project publishes besides its code: container
images, npm, Maven, RubyGems and NuGet packages. GitHub lists them only by
type (``GET /user/packages?package_type=...``), so **My Packages** asks once
for each type and reads them as one list: "container quill-engine: private,
from community-access/quill, updated 2026-11-12."

**Delete Package Version...** lists a package's versions, newest first, with
their tags, and deletes the one chosen after asking. **Delete Package...**
deletes the whole package after you type its name. Both need the
``delete:packages`` scope; GitHub keeps a deleted package for 30 days and can
restore it from its own Packages settings.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "PACKAGE_TYPES",
    "PackageError",
    "PackageVersion",
    "delete_package",
    "delete_version",
    "fetch_packages",
    "fetch_versions",
    "package_row",
]

#: GitHub's package types, in the order they are asked for.
PACKAGE_TYPES = ("container", "npm", "maven", "rubygems", "nuget", "docker")


class PackageError(CodedError):
    """Packages could not be read or deleted; the message is said."""

    code = "QUILL-GITHUB-PACKAGES"


@dataclass(frozen=True)
class PackageVersion:
    id: int
    name: str
    tags: tuple[str, ...]
    updated: str

    @property
    def label(self) -> str:
        tags = f", tagged {', '.join(self.tags)}" if self.tags else ", untagged"
        when = f", updated {self.updated}" if self.updated else ""
        return f"{self.name}{tags}{when}"


def _path(kind: str, name: str) -> str:
    return f"/user/packages/{quote(kind, safe='')}/{quote(name, safe='')}"


def _refused(exc: GitHubRestError, doing: str, scope: str) -> PackageError:
    if exc.status in (401, 403):
        return PackageError(
            f"GitHub refused to {doing}: it needs the {scope} permission. Sign in with "
            "GitHub again, from Manage GitHub Accounts, to grant it."
        )
    if exc.status == 404:
        return PackageError(f"GitHub could not find that package to {doing}.")
    return PackageError(f"Could not {doing}: {exc}")


def package_row(raw: Mapping[str, Any]) -> ExploreRow:
    kind = str(raw.get("package_type") or "")
    name = str(raw.get("name") or "")
    visibility = str(raw.get("visibility") or "")
    repository = raw.get("repository")
    repo = str(repository.get("full_name") or "") if isinstance(repository, Mapping) else ""
    updated = str(raw.get("updated_at") or "")[:10]
    count = raw.get("version_count")
    parts = [visibility] if visibility else []
    if isinstance(count, int) and not isinstance(count, bool):
        parts.append(f"{count:,} version{'' if count == 1 else 's'}")
    parts.append(f"from {repo}" if repo else "not linked to a repository")
    if updated:
        parts.append(f"updated {updated}")
    label = f"{kind} {name}: {', '.join(parts)}."
    url = str(raw.get("html_url") or "")
    return ExploreRow(
        label, label + (f"\n{url}" if url else ""), url, repo, "package", f"{kind}/{name}"
    )


def fetch_packages(api: GitHubApi, *, limit: int = 100) -> list[ExploreRow]:
    """Every package of yours, each type asked for in turn."""
    rows: list[ExploreRow] = []
    for kind in PACKAGE_TYPES:
        try:
            data = api.rest(
                "GET",
                "/user/packages",
                query={"package_type": kind, "per_page": str(max(1, min(limit, 100)))},
            ).data
        except GitHubRestError as exc:
            if exc.status in (400, 422):  # a type this account cannot hold
                continue
            raise _refused(exc, "list your packages", "read:packages") from exc
        rows += [package_row(raw) for raw in data or () if isinstance(raw, Mapping)]
    rows.sort(key=lambda row: row.label.lower())
    return rows[:limit]


def fetch_versions(api: GitHubApi, kind: str, name: str) -> list[PackageVersion]:
    try:
        data = api.rest("GET", f"{_path(kind, name)}/versions", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, f"list the versions of {name}", "read:packages") from exc
    versions = []
    for raw in data or ():
        if not isinstance(raw, Mapping):
            continue
        meta = raw.get("metadata")
        container = meta.get("container") if isinstance(meta, Mapping) else None
        tags = container.get("tags") if isinstance(container, Mapping) else None
        versions.append(
            PackageVersion(
                int(raw.get("id") or 0),
                str(raw.get("name") or ""),
                tuple(str(t) for t in tags or ()),
                str(raw.get("updated_at") or "")[:10],
            )
        )
    versions.sort(key=lambda v: v.updated, reverse=True)
    return versions


def delete_version(api: GitHubApi, kind: str, name: str, version: PackageVersion) -> str:
    try:
        api.rest("DELETE", f"{_path(kind, name)}/versions/{version.id}")
    except GitHubRestError as exc:
        if exc.status == 400:
            raise PackageError(
                f"GitHub will not delete the only version of {name}, or a version with more "
                "than 5,000 downloads. Delete the whole package instead."
            ) from exc
        raise _refused(exc, f"delete a version of {name}", "delete:packages") from exc
    return f"Deleted version {version.name} of {name}. GitHub can restore it for 30 days."


def delete_package(api: GitHubApi, kind: str, name: str) -> str:
    try:
        api.rest("DELETE", _path(kind, name))
    except GitHubRestError as exc:
        raise _refused(exc, f"delete {name}", "delete:packages") from exc
    return f"Deleted the {kind} package {name}. GitHub can restore it for 30 days."
