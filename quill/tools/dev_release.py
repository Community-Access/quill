"""Dev builds live in ONE rolling prerelease of the main repository.

``dev-builds.yml`` used to publish every Dev build as its own release in a
separate repository, reached with a personal token. That repository and its
token are gone. A release per Dev build cannot simply move into
``Community-Access/quill``: installed Quill Radio 3.0.4 and QUILL Lite 1.1.2 read
only the first 30 releases (prereleases count, though they are ignored), so a
release for each of eleven apps a day would push their newest Stable build off
the page and those copies would stop seeing updates (``GATE-RELEASE-PAGE``).

So there is **one** release, tagged :data:`DEV_TAG`, that takes a single slot on
that page for good. Every Dev build is a handful of files in it, named with the
build's version, and the release's notes list which commit each build came from.
This module is the one place that knows that shape:

* :func:`split_asset` says which app and version a file belongs to;
* :func:`build_rows` turns the release back into one row per build, in exactly
  the shape the per-build releases had, so the planner and the batch promoter
  keep working unchanged;
* :func:`asset_names` says which files make up one build, for downloading it
  without downloading the whole release.

Nothing here talks to the network except :func:`get_release`, through ``gh``.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from typing import Any

from quill.tools import release_feed as rf

__all__ = [
    "CHECKSUMS_SUFFIX",
    "DEV_TAG",
    "DEV_VERSION_RE",
    "asset_names",
    "build_lines",
    "build_rows",
    "download_command",
    "checksums_name",
    "get_release",
    "release_tag_of",
    "group_assets",
    "source_line",
    "split_asset",
]

DEV_TAG = rf.DEV_TAG
#: A build's checksums file is named for the build: ``<tag>.SHA256SUMS.txt``.
CHECKSUMS_SUFFIX = ".SHA256SUMS.txt"
DEV_VERSION_RE = re.compile(r"\d+\.\d+\.\d+-dev\.\d{8}\.\d+")
#: A file named for its build's tag, such as ``quill-radio-v3.2.0-dev.20261126.1.LICENSE.txt``
#: (a build's checksums and licence files share the release with every other build's).
_TAGGED_RE = re.compile(r"^(?P<tag>.+?-dev\.\d{8}\.\d+)\.(?P<rest>[A-Za-z].*)$")
_BUILD_LINE_RE = re.compile(
    r"^(?P<tag>\S+): Built from Community-Access/quill@(?P<sha>[0-9a-f]{40})\.\s*$", re.M
)


def checksums_name(app_key: str, version: str) -> str:
    """The checksums file of one build, as it is named inside the rolling release."""
    return f"{rf.tag_for(app_key, version)}{CHECKSUMS_SUFFIX}"


def source_line(app_key: str, version: str, sha: str) -> str:
    """The line in the release notes that records which commit a build came from."""
    return f"{rf.tag_for(app_key, version)}: Built from Community-Access/quill@{sha.lower()}."


def build_lines(body: str) -> dict[str, str]:
    """``{build tag: commit sha}`` from the release notes."""
    return {m.group("tag"): m.group("sha").lower() for m in _BUILD_LINE_RE.finditer(body or "")}


def split_asset(name: str) -> tuple[str, str] | None:
    """``(app, version)`` for a file of a Dev build, or ``None`` for anything else.

    Release files start with their app's asset prefix (``Quill-Radio-Setup-...``)
    and carry the Dev version (``3.2.0-dev.20261126.1``). Prefixes overlap
    (``Quill`` begins every other Quill name), so the longest one wins. A
    build's checksums and licence files start with its tag instead.
    """
    found = DEV_VERSION_RE.search(name)
    if found is None:
        return None
    version = found.group(0)
    named_by_tag = _TAGGED_RE.match(name)
    if named_by_tag is not None:
        tagged = rf.app_for_tag(named_by_tag.group("tag"))
        if tagged is not None and tagged[1] == version:
            return tagged
    lower = name.lower()
    best_key, best_len = "", 0
    for key, spec in rf.APPS.items():
        prefix = spec.asset_prefix.lower()
        if lower.startswith(prefix) and len(prefix) > best_len:
            best_key, best_len = key, len(prefix)
    return (best_key, version) if best_key else None


def group_assets(assets: Sequence[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """The release's files, grouped into builds by ``(app, version)``."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for asset in assets:
        key = split_asset(str(asset.get("name") or ""))
        if key is not None:
            groups.setdefault(key, []).append(asset)
    return groups


def asset_names(release: dict[str, Any], app_key: str, version: str) -> list[str]:
    """The names of every file of one build, checksums included."""
    group = group_assets(_assets(release)).get((app_key, version), [])
    return sorted(str(asset["name"]) for asset in group)


def build_rows(release: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per recorded build, shaped like the per-build releases were.

    Only a build the release notes name a commit for is a row: a build whose
    files have arrived but whose note has not yet been written is not ready to
    be promoted, and the planner must not count it as built either.
    """
    lines = build_lines(str(release.get("body") or ""))
    rows: list[dict[str, Any]] = []
    for (app_key, version), group in sorted(group_assets(_assets(release)).items()):
        tag = rf.tag_for(app_key, version)
        sha = lines.get(tag)
        if sha is None:
            continue
        name = rf.app(app_key).name
        stamps = sorted(str(a.get("created_at") or "") for a in group if a.get("created_at"))
        rows.append({
            "tag_name": tag,
            "name": f"{name} {version} (Dev)",
            "draft": False,
            "prerelease": True,
            "published_at": stamps[-1] if stamps else str(release.get("published_at") or ""),
            "body": f"Dev build of {name}, unsigned. Built from Community-Access/quill@{sha}.",
            # The checksums file is presented under the one name the
            # per-build releases gave it.
            "assets": [
                {
                    "name": "SHA256SUMS.txt"
                    if str(a["name"]).endswith(CHECKSUMS_SUFFIX)
                    else a["name"]
                }
                for a in group
            ],
        })
    return rows


def _assets(release: dict[str, Any]) -> list[dict[str, Any]]:
    assets = release.get("assets")
    return [a for a in assets if isinstance(a, dict)] if isinstance(assets, list) else []


def get_release(gh: rf.Gh, repo: str = rf.MAIN_REPO) -> dict[str, Any]:
    """The rolling release with its complete file list, or ``{}`` when there is none yet.

    The file list is read from the paginated assets endpoint: a release object
    does not promise to embed every file once there are hundreds.
    """
    try:
        release = json.loads(gh(["api", f"repos/{repo}/releases/tags/{DEV_TAG}"]) or "{}")
    except (subprocess.CalledProcessError, OSError, ValueError):
        return {}
    if not isinstance(release, dict) or not release.get("id"):
        return {}
    try:
        pages = json.loads(
            gh([
                "api",
                f"repos/{repo}/releases/{release['id']}/assets?per_page=100",
                "--paginate",
                "--slurp",
            ])
            or "[]"
        )
    except (subprocess.CalledProcessError, OSError, ValueError):
        pages = []
    assets: list[dict[str, Any]] = []
    for page in pages if isinstance(pages, list) else []:
        if isinstance(page, list):
            assets.extend(a for a in page if isinstance(a, dict))
        elif isinstance(page, dict):
            assets.append(page)
    release["assets"] = assets
    return release


def release_tag_of(feed: Any, version: str, app_key: str) -> str:
    """The tag of the release a listed build's files are on.

    That is the build's own tag, except for a build made as a Dev build: its
    files are in the one rolling release (:data:`DEV_TAG`), and the feed's file
    addresses say so.
    """
    release = feed.release(version)
    if release is not None:
        for asset in release.assets:
            parts = asset.url.split("/")
            # https://github.com/<owner>/<repo>/releases/download/<tag>/<file>
            if (
                len(parts) > 8
                and parts[2] == "github.com"
                and parts[5] == "releases"
                and parts[6] == "download"
            ):
                return parts[7]
    return rf.tag_for(app_key, version)


def download_command(tag: str, repo: str, folder: str, names: Sequence[str]) -> list[str]:
    """``gh`` arguments that fetch a build's files into *folder*.

    The rolling Dev release holds every app's builds, so only *names* are
    fetched from it; any other release is one build, fetched whole.
    """
    command = ["release", "download", tag, "--repo", repo, "--dir", folder]
    if tag == DEV_TAG:
        for name in names:
            command += ["--pattern", name]
    return command
