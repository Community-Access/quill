"""Submit one approved QuillVille WinGet manifest set to microsoft/winget-pkgs.

The default operation is a local dry run. A public pull request requires all of
the following: ``--submit``, ``approved_for_submission: true`` in the reviewed
catalogue, and ``WINGET_SUBMIT_TOKEN`` in the process environment. This script
never syncs or force-pushes a fork and never overwrites an existing branch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from scripts.winget.manifests import (
    build_manifest_draft,
    load_catalog,
    validate_templates,
)
from scripts.winget.prepare import fetch_release

API_ROOT = "https://api.github.com"
UPSTREAM = "microsoft/winget-pkgs"
USER_AGENT = "Quill-WinGet-Manifest"


class GitHubAPI:
    """Small GitHub REST client limited to the official API host."""

    def __init__(self, token: str):
        self.token = token

    def request(self, method: str, path: str, payload: dict[str, object] | None = None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("GitHub API paths must be relative to api.github.com.")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            API_ROOT + path,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API host
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise RuntimeError(f"GitHub API {method} {path} returned HTTP {exc.code}.") from None


def _api_path(repository: str, suffix: str) -> str:
    return f"/repos/{repository}/{suffix.lstrip('/')}"


def _branch_name(package_id: str, version: str) -> str:
    return f"quill-{package_id.lower()}-{version}".replace(".", "-")


def _wait_for_fork(api: GitHubAPI, owner: str) -> dict[str, object]:
    repository = _api_path(f"{owner}/{UPSTREAM.split('/', 1)[1]}", "")
    fork = api.request("GET", repository)
    if isinstance(fork, dict):
        return fork
    api.request("POST", _api_path(UPSTREAM, "forks"), {})
    for _attempt in range(15):
        time.sleep(2)
        fork = api.request("GET", repository)
        if isinstance(fork, dict):
            return fork
    raise RuntimeError("GitHub did not make the WinGet fork available in time.")


def _already_published(api: GitHubAPI, package_folder: str, version: str, branch: str) -> bool:
    upstream_version = f"{package_folder}/{version}"
    if (
        api.request(
            "GET",
            _api_path(
                UPSTREAM, f"contents/{quote(upstream_version, safe='/')}?ref={quote(branch)}"
            ),
        )
        is not None
    ):
        print(f"WinGet already contains {upstream_version}; nothing to submit.")
        return True
    return False


def _open_pull_request(
    api: GitHubAPI, owner: str, branch: str, package_id: str, version: str
) -> bool:
    search = urlencode({"q": f'repo:{UPSTREAM} is:pr is:open "{package_id}" "{version}"'})
    results = api.request("GET", f"/search/issues?{search}")
    if isinstance(results, dict) and int(results.get("total_count", 0) or 0) > 0:
        print(f"An open WinGet pull request already covers {package_id} {version}; skipping.")
        return True
    query = urlencode({"state": "open", "head": f"{owner}:{branch}"})
    pulls = api.request("GET", _api_path(UPSTREAM, f"pulls?{query}"))
    if isinstance(pulls, list) and pulls:
        print(f"An open WinGet pull request already uses {branch}; leaving it untouched.")
        return True
    return False


def submit_manifest_set(
    api: GitHubAPI,
    *,
    owner: str,
    package_id: str,
    package_version: str,
    files: dict[str, str],
    asset_name: str,
    asset_sha256: str,
) -> None:
    """Create a fresh fork branch and a single manifest-only upstream PR."""
    upstream = api.request("GET", _api_path(UPSTREAM, ""))
    if not isinstance(upstream, dict):
        raise RuntimeError("Could not read the WinGet upstream repository.")
    default_branch = str(upstream.get("default_branch", "") or "")
    if not default_branch:
        raise RuntimeError("The WinGet upstream repository did not report its default branch.")
    encoded_branch = quote(default_branch, safe="")
    head_record = api.request("GET", _api_path(UPSTREAM, f"branches/{encoded_branch}"))
    if not isinstance(head_record, dict):
        raise RuntimeError("Could not read the current WinGet default-branch commit.")
    head_commit = head_record.get("commit")
    if not isinstance(head_commit, dict):
        raise RuntimeError("The WinGet default branch has no commit record.")
    base_sha = str(head_commit.get("sha", "") or "")
    tree_record = head_commit.get("commit")
    if not isinstance(tree_record, dict) or not base_sha:
        raise RuntimeError("The WinGet default branch has no commit SHA.")
    base_tree = tree_record.get("tree")
    if not isinstance(base_tree, dict) or not base_tree.get("sha"):
        raise RuntimeError("The WinGet default branch has no tree SHA.")

    package_path = next(iter(files)).split("/", 4)
    package_folder = "/".join(package_path[:-1])
    if _already_published(api, package_folder, package_version, default_branch):
        return
    branch = _branch_name(package_id, package_version)
    if _open_pull_request(api, owner, branch, package_id, package_version):
        return

    fork = _wait_for_fork(api, owner)
    fork_repository = str(fork.get("full_name", "") or f"{owner}/winget-pkgs")
    if (
        api.request("GET", _api_path(fork_repository, f"git/ref/heads/{quote(branch, safe='')}"))
        is not None
    ):
        print(f"Branch {branch} already exists in the fork; leaving it untouched.")
        return

    api.request(
        "POST",
        _api_path(fork_repository, "git/refs"),
        {"ref": f"refs/heads/{branch}", "sha": base_sha},
    )
    tree_entries = [
        {
            "path": path,
            "mode": "100644",
            "type": "blob",
            "content": content,
        }
        for path, content in sorted(files.items())
    ]
    tree = api.request(
        "POST",
        _api_path(fork_repository, "git/trees"),
        {"base_tree": base_tree["sha"], "tree": tree_entries},
    )
    if not isinstance(tree, dict) or not tree.get("sha"):
        raise RuntimeError("GitHub did not create the manifest tree.")
    commit = api.request(
        "POST",
        _api_path(fork_repository, "git/commits"),
        {
            "message": f"Add {package_id} {package_version} manifest",
            "tree": tree["sha"],
            "parents": [base_sha],
        },
    )
    if not isinstance(commit, dict) or not commit.get("sha"):
        raise RuntimeError("GitHub did not create the manifest commit.")
    api.request(
        "PATCH",
        _api_path(fork_repository, f"git/refs/heads/{quote(branch, safe='')}"),
        {"sha": commit["sha"], "force": False},
    )

    root = "/".join(package_path[:4])
    existing_package = api.request(
        "GET",
        _api_path(UPSTREAM, f"contents/{quote(root, safe='/')}?ref={quote(default_branch)}"),
    )
    action = "Update" if existing_package is not None else "New package"
    title = f"{action}: {package_id} version {package_version}"
    body = (
        f"Adds the signed Stable installer `{asset_name}`.\n\n"
        f"SHA-256: `{asset_sha256}`\n\n"
        "The manifests match the installed Apps & Features entry and keep the "
        "first-party updater's explicit-upgrade safeguard."
    )
    pull = api.request(
        "POST",
        _api_path(UPSTREAM, "pulls"),
        {
            "title": title,
            "head": f"{owner}:{branch}",
            "base": default_branch,
            "body": body,
        },
    )
    if not isinstance(pull, dict) or not pull.get("html_url"):
        raise RuntimeError("GitHub did not return the created WinGet pull request.")
    print(f"Opened {pull['html_url']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="Exact published Stable release tag.")
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Create a public pull request (requires catalog approval and WINGET_SUBMIT_TOKEN).",
    )
    args = parser.parse_args(argv)

    try:
        validate_templates()
        release = fetch_release(args.tag)
        catalog = load_catalog()
        from quill.core.release_tags import parse_release_tag

        parsed = parse_release_tag(args.tag)
        if parsed is None:
            raise ValueError(f"{args.tag!r} is not a QuillVille release tag.")
        draft = build_manifest_draft(release, parsed.app_key, catalog=catalog)
        print(f"Package: {draft.package_id} {draft.package_version}")
        print(f"Release: {draft.release_url}")
        print(f"Installer: {draft.asset_name}")
        print(f"SHA-256: {draft.asset_sha256}")
        for path, content in sorted(draft.files.items()):
            print(f"\n--- {path} ---\n{content}", end="")
        if not args.submit:
            print("\nDry run only; no public fork, branch, or pull request was created.")
            return 0
        if catalog.get("approved_for_submission") is not True:
            raise ValueError("The package IDs are not approved for public submission in apps.json.")
        token = os.environ.get("WINGET_SUBMIT_TOKEN", "").strip()
        if not token:
            raise ValueError("WINGET_SUBMIT_TOKEN is required for public submission.")
        user = GitHubAPI(token).request("GET", "/user")
        if not isinstance(user, dict) or not user.get("login"):
            raise ValueError("WINGET_SUBMIT_TOKEN did not identify an authenticated GitHub user.")
        submit_manifest_set(
            GitHubAPI(token),
            owner=str(user["login"]),
            package_id=draft.package_id,
            package_version=draft.package_version,
            files=draft.files,
            asset_name=draft.asset_name,
            asset_sha256=draft.asset_sha256,
        )
        return 0
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"Could not prepare or submit the WinGet package: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
