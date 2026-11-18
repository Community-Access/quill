"""Single commands on rows the Workbench already lists (GitHub PRD sections 16 to 19).

Each one does one thing GitHub offers for that kind of row, and says what
happened in a sentence:

* a release: **Delete Release...** (its tag can go too, if asked);
* a milestone: **Delete Milestone...** (its issues stay, without it);
* a deployment: **Delete Deployment...** (GitHub deletes only an inactive one);
* a webhook: **Send Test Push** and **Turn On or Off**;
* a branch: **Merge Into...** another branch, as GitHub's merge button would;
* a repository: **Send Repository Dispatch...**, which starts workflows that
  listen for ``repository_dispatch``;
* a branch or tag: **Download Source...** as a zip or tar.gz.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.items_provider import GitHubArtifact
from quill.core.github.repo_settings_lists import hooks_path
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "RowAdminError",
    "delete_deployment",
    "delete_milestone",
    "delete_release",
    "merge_branch",
    "repository_dispatch",
    "set_webhook_active",
    "source_download",
    "test_push",
]


class RowAdminError(CodedError):
    """A row command GitHub refused; the message says why and what to do."""

    code = "QUILL-GITHUB-ROWADMIN-FAILED"


def _repo(repo: str) -> str:
    return f"/repos/{quote(repo, safe='/')}"


def _why(exc: GitHubRestError, doing: str) -> RowAdminError:
    if exc.status in (401, 403):
        return RowAdminError(f"GitHub refused to {doing}; it needs more access to the repository.")
    if exc.status == 404:
        return RowAdminError(f"GitHub found nothing to {doing}; it may already be gone.")
    return RowAdminError(f"Could not {doing}: {exc}")


def delete_release(api: GitHubApi, repo: str, tag: str, *, delete_tag: bool = False) -> str:
    """Delete the release for *tag*; with *delete_tag*, the tag itself as well."""
    try:
        data = api.rest("GET", f"{_repo(repo)}/releases/tags/{quote(tag, safe='')}").data
    except GitHubRestError as exc:
        raise _why(exc, f"find the release {tag}") from exc
    release_id = data.get("id") if isinstance(data, Mapping) else None
    if release_id is None:
        raise RowAdminError(f"GitHub sent no release for {tag}, so nothing was deleted.")
    try:
        api.rest("DELETE", f"{_repo(repo)}/releases/{int(release_id)}")
    except GitHubRestError as exc:
        raise _why(exc, f"delete the release {tag}") from exc
    if not delete_tag:
        return f"Deleted the release {tag}. The tag {tag} stays."
    try:
        api.rest("DELETE", f"{_repo(repo)}/git/refs/tags/{quote(tag, safe='')}")
    except GitHubRestError as exc:
        return f"Deleted the release {tag}, but not its tag: {_why(exc, 'delete the tag')}"
    return f"Deleted the release {tag} and its tag."


def delete_milestone(api: GitHubApi, repo: str, title: str) -> str:
    """Delete the milestone called *title*; its issues stay, with no milestone."""
    try:
        listed = api.rest(
            "GET", f"{_repo(repo)}/milestones", query={"state": "all", "per_page": "100"}
        ).data
    except GitHubRestError as exc:
        raise _why(exc, "read the milestones") from exc
    found = next(
        (m for m in listed or () if isinstance(m, Mapping) and m.get("title") == title), None
    )
    if found is None:
        raise RowAdminError(f"GitHub has no milestone called {title!r} now.")
    try:
        api.rest("DELETE", f"{_repo(repo)}/milestones/{int(found['number'])}")
    except GitHubRestError as exc:
        raise _why(exc, f"delete the milestone {title}") from exc
    count = int(found.get("open_issues") or 0) + int(found.get("closed_issues") or 0)
    kept = f" Its {count} issues stay, with no milestone." if count else ""
    return f"Deleted the milestone {title}.{kept}"


def delete_deployment(api: GitHubApi, repo: str, deployment_id: str) -> str:
    try:
        api.rest("DELETE", f"{_repo(repo)}/deployments/{int(deployment_id)}")
    except GitHubRestError as exc:
        if exc.status == 422:
            raise RowAdminError(
                "GitHub deletes only an inactive deployment. A newer deployment to the same "
                "environment makes this one inactive; then delete it."
            ) from exc
        raise _why(exc, "delete the deployment") from exc
    return f"Deleted deployment {deployment_id}."


def test_push(api: GitHubApi, repo: str, hook: str) -> str:
    """Ask GitHub to send the webhook a push event for the latest push, as a test."""
    try:
        api.rest("POST", f"{hooks_path(repo)}/{quote(hook, safe='')}/tests")
    except GitHubRestError as exc:
        raise _why(exc, "send a test push") from exc
    return (
        "Asked GitHub to send a test push. It goes only if the webhook listens for pushes; "
        "its result is the newest of Recent Deliveries."
    )


def set_webhook_active(api: GitHubApi, owner: str, hook: str, active: bool) -> str:
    """Turn a repository's or an organization's webhook on or off."""
    try:
        api.rest("PATCH", f"{hooks_path(owner)}/{quote(hook, safe='')}", body={"active": active})
    except GitHubRestError as exc:
        raise _why(exc, "change the webhook") from exc
    if active:
        return "The webhook is on; GitHub sends it events again."
    return "The webhook is off; GitHub sends it nothing until it is on."


def merge_branch(api: GitHubApi, repo: str, base: str, head: str, message: str = "") -> str:
    """Merge *head* into *base* on GitHub, as a merge commit."""
    body: dict[str, object] = {"base": base, "head": head}
    if message.strip():
        body["commit_message"] = message.strip()
    try:
        reply = api.rest("POST", f"{_repo(repo)}/merges", body=body)
    except GitHubRestError as exc:
        if exc.status == 409:
            raise RowAdminError(
                f"{head} and {base} conflict, so nothing was merged. Merge them on your "
                "computer, or open a pull request to resolve it."
            ) from exc
        raise _why(exc, f"merge {head} into {base}") from exc
    if reply.status == 204:
        return f"{base} already has everything in {head}; nothing to merge."
    sha = str((reply.data or {}).get("sha") or "")[:7] if isinstance(reply.data, Mapping) else ""
    return f"Merged {head} into {base}" + (f" as {sha}." if sha else ".")


def repository_dispatch(api: GitHubApi, repo: str, event_type: str, payload: str = "") -> str:
    """Send a ``repository_dispatch`` event; *payload* is optional JSON for workflows."""
    name = event_type.strip()
    if not name or len(name) > 100:
        raise RowAdminError("Name the event, up to 100 characters, such as deploy.")
    body: dict[str, Any] = {"event_type": name}
    if payload.strip():
        try:
            parsed = json.loads(payload)
        except ValueError as exc:
            raise RowAdminError(f"The payload is not JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RowAdminError('The payload must be a JSON object, such as {"env": "test"}.')
        body["client_payload"] = parsed
    try:
        api.rest("POST", f"{_repo(repo)}/dispatches", body=body)
    except GitHubRestError as exc:
        raise _why(exc, "send the event") from exc
    return f"Sent {name}. Workflows that listen for repository_dispatch of that type start now."


def source_download(repo: str, ref: str, archive: str = "zip") -> GitHubArtifact:
    """The repository's files at *ref*, as a download the artifact downloader can stream."""
    kind = "zipball" if archive == "zip" else "tarball"
    url = f"https://api.github.com{_repo(repo)}/{kind}/{quote(ref, safe='')}"
    name = f"{repo.rsplit('/', 1)[-1]}-{ref.replace('/', '-')}"
    return GitHubArtifact(id=0, name=name, size_bytes=0, expired=False, archive_download_url=url)
