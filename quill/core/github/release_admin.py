"""Release management for the shared GitHub Items viewer (Wave 4).

Edit a release (name, notes, draft, prerelease, and publishing a draft),
upload a file as a release asset, and delete an asset. The Releases list shows
releases by tag; :func:`find_release` looks the tag up again so the edit works
on what GitHub holds now, with the IDs the write endpoints need.

Uploads go to ``uploads.github.com`` -- the one GitHub host besides
``api.github.com`` that takes the token, and only for this call. The opener
refuses redirects, so the token never follows a reply to a third host. The
file is sent in chunks so :class:`UploadProgress` can say how far it got at
quarter steps (25, 50, 75 percent) rather than on every block; the final
result is what GitHub's reply says the asset is.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import json
import mimetypes
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rate_limits import RATE_LIMITS, secondary_wait_seconds, wait_message
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path
from quill.core.net import verified_ssl_context

UPLOAD_ROOT = "https://uploads.github.com"
MAX_ASSET_BYTES = 2 * 1024 * 1024 * 1024
_UPLOAD_TIMEOUT_SECONDS = 120
_CHUNK = 256 * 1024


@dataclass(frozen=True, slots=True)
class ReleaseAssetRecord:
    id: int
    name: str
    size: int = 0
    download_count: int = 0


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    """A release as GitHub holds it now, with the IDs its write endpoints need."""

    id: int
    tag: str
    name: str = ""
    body: str = ""
    draft: bool = False
    prerelease: bool = False
    html_url: str = ""
    assets: tuple[ReleaseAssetRecord, ...] = ()

    def asset_named(self, name: str) -> ReleaseAssetRecord | None:
        return next((asset for asset in self.assets if asset.name == name), None)


def parse_release(data: object) -> ReleaseRecord:
    if not isinstance(data, dict) or not isinstance(data.get("id"), int):
        raise GitHubItemsError("GitHub sent a release without an ID.")
    assets = tuple(
        ReleaseAssetRecord(
            int(row["id"]),
            str(row.get("name") or ""),
            int(row.get("size") or 0),
            int(row.get("download_count") or 0),
        )
        for row in data.get("assets") or ()
        if isinstance(row, dict) and isinstance(row.get("id"), int)
    )
    return ReleaseRecord(
        id=int(data["id"]),
        tag=str(data.get("tag_name") or ""),
        name=str(data.get("name") or ""),
        body=str(data.get("body") or ""),
        draft=bool(data.get("draft")),
        prerelease=bool(data.get("prerelease")),
        html_url=str(data.get("html_url") or ""),
        assets=assets,
    )


def _call(action: str, call: Callable[[], RestResponse], expect: tuple[int, ...]) -> RestResponse:
    try:
        response = call()
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def release_change_sentence(before: ReleaseRecord, after: ReleaseRecord) -> str:
    """What changed, said from GitHub's reply rather than from what was asked."""
    changes: list[str] = []
    if before.draft and not after.draft:
        changes.append("published")
    elif not before.draft and after.draft:
        changes.append("made a draft")
    if before.prerelease != after.prerelease:
        changes.append("marked a prerelease" if after.prerelease else "marked a full release")
    if before.name != after.name:
        changes.append(f"renamed {after.name!r}" if after.name else "name cleared")
    if before.body != after.body:
        changes.append("notes updated")
    label = after.name or after.tag
    if not changes:
        return f"Release {label}: GitHub confirmed it with no changes."
    return f"Release {label}: " + ", ".join(changes) + "."


class UploadProgress:
    """Call *report* with 25, 50 and 75 percent as bytes go out (never twice for one step)."""

    def __init__(self, total: int, report: Callable[[int], None] | None) -> None:
        self._total = max(1, total)
        self._report = report
        self._sent = 0
        self._said = 0

    def advance(self, count: int) -> None:
        self._sent += count
        step = (self._sent * 100 // self._total) // 25 * 25
        if self._report is not None and 0 < step < 100 and step > self._said:
            self._said = step
            self._report(step)


class _ProgressReader:
    """A file object urllib reads in blocks; each block advances the progress."""

    def __init__(self, handle: BinaryIO, progress: UploadProgress) -> None:
        self._handle = handle
        self._progress = progress

    def read(self, size: int = -1) -> bytes:
        block = self._handle.read(_CHUNK if size is None or size < 0 else min(size, _CHUNK))
        if block:
            self._progress.advance(len(block))
        return block


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


class GitHubReleaseAdmin:
    """Edit a release, upload an asset and delete one, for one signed-in session."""

    def __init__(self, token: str | None) -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    def find_release(self, repo: str, tag: str) -> ReleaseRecord:
        """The release with *tag*, drafts included (they have no tag URL yet)."""
        base = repo_path(repo)
        for page in range(1, 6):

            def read(page: int = page) -> RestResponse:
                return request_json(
                    self._token,
                    "GET",
                    f"{base}/releases",
                    query={"per_page": "100", "page": str(page)},
                )

            data = _call("read the releases", read, (200,)).data
            rows = data if isinstance(data, list) else []
            for row in rows:
                if isinstance(row, dict) and str(row.get("tag_name") or "") == tag:
                    return parse_release(row)
            if len(rows) < 100:
                break
        raise GitHubItemsError(
            f"GitHub has no release tagged {tag} in {repo} that this account can see. "
            "Refresh the list; it may have been deleted."
        )

    def edit_release(
        self,
        repo: str,
        release: ReleaseRecord,
        *,
        name: str,
        body: str,
        draft: bool,
        prerelease: bool,
    ) -> tuple[ReleaseRecord, str]:
        """PATCH the release; return GitHub's copy and a sentence of what changed."""
        self._require_write_access("edit a release")
        payload: dict[str, object] = {
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }
        data = _call(
            f"edit release {release.tag}",
            lambda: request_json(
                self._token,
                "PATCH",
                f"{repo_path(repo)}/releases/{release.id}",
                body=payload,
            ),
            (200,),
        ).data
        after = parse_release(data)
        if after.draft != draft:
            raise GitHubItemsError(
                f"GitHub saved release {release.tag}, but it is still "
                f"{'a draft' if after.draft else 'published'}."
            )
        return after, release_change_sentence(release, after)

    def delete_asset(self, repo: str, asset: ReleaseAssetRecord) -> None:
        self._require_write_access("delete a release asset")
        _call(
            f"delete {asset.name}",
            lambda: request_json(
                self._token, "DELETE", f"{repo_path(repo)}/releases/assets/{asset.id}"
            ),
            (204,),
        )

    def upload_release_asset(
        self,
        repo: str,
        release: ReleaseRecord,
        path: str | os.PathLike[str],
        *,
        progress: Callable[[int], None] | None = None,
        opener: Any = None,
    ) -> ReleaseAssetRecord:
        """Send *path* as a new asset; return the asset GitHub says it stored."""
        self._require_write_access("upload a release asset")
        source = Path(path)
        try:
            size = source.stat().st_size
        except OSError as exc:
            raise GitHubItemsError(f"Could not read {source.name}: {exc.strerror}.") from exc
        if size <= 0:
            raise GitHubItemsError(f"{source.name} is empty; GitHub will not take an empty asset.")
        if size > MAX_ASSET_BYTES:
            raise GitHubItemsError(f"{source.name} is over GitHub's 2 GB limit for one asset.")
        if release.asset_named(source.name) is not None:
            raise GitHubItemsError(
                f"Release {release.tag} already has an asset named {source.name}. "
                "Delete that one first, or rename the file."
            )
        if wait := RATE_LIMITS.wait_seconds():
            raise GitHubItemsError(wait_message(wait))
        url = (
            f"{UPLOAD_ROOT}{repo_path(repo)}/releases/{release.id}/assets"
            f"?name={quote(source.name, safe='')}"
        )
        content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        tracker = UploadProgress(size, progress)
        if opener is None:
            opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
        try:
            with source.open("rb") as handle:
                request = Request(
                    url,
                    data=_ProgressReader(handle, tracker),  # type: ignore[arg-type]
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                        "User-Agent": "QUILL-GitHub-Workbench",
                        "Content-Type": content_type,
                        "Content-Length": str(size),
                    },
                    method="POST",
                )
                with opener.open(request, timeout=_UPLOAD_TIMEOUT_SECONDS) as response:
                    status = int(getattr(response, "status", 201) or 201)
                    raw = response.read(1_000_000)
        except HTTPError as exc:
            raise GitHubItemsError(_upload_failure(source.name, exc)) from exc
        except OSError as exc:
            raise GitHubItemsError(f"Could not upload {source.name}: {exc}") from exc
        if status != 201:
            raise GitHubItemsError(
                f"Could not upload {source.name}. GitHub answered HTTP {status} "
                "without confirming the asset."
            )
        try:
            data = json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
        except ValueError:
            data = {}
        if not isinstance(data, dict) or not isinstance(data.get("id"), int):
            raise GitHubItemsError(
                f"GitHub took {source.name} but did not describe the asset; refresh to check it."
            )
        return ReleaseAssetRecord(
            int(data["id"]), str(data.get("name") or source.name), int(data.get("size") or size)
        )


def _upload_failure(name: str, exc: HTTPError) -> str:
    try:
        body = json.loads(exc.read(100_000).decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 - the body is optional on errors
        body = {}
    message = str(body.get("message", "")) if isinstance(body, dict) else ""
    headers: Any = exc.headers or {}
    seconds = secondary_wait_seconds(exc.code, headers, message)
    if seconds is not None:
        RATE_LIMITS.observe_secondary(seconds)
        return wait_message(seconds)
    if exc.code in (301, 302, 303, 307, 308):
        return (
            f"Could not upload {name}. GitHub redirected the upload; QUILL did not follow it, "
            "so your token stayed with GitHub."
        )
    if exc.code == 422:
        return (
            f"Could not upload {name}. GitHub refused it: "
            f"{message or 'an asset with that name may already exist'}."
        )
    plain = {str(k): str(v) for k, v in headers.items()} if hasattr(headers, "items") else {}
    return rest_failure_message(
        f"upload {name}", GitHubRestError(message, status=exc.code, headers=plain, data=body)
    )


__all__ = [
    "MAX_ASSET_BYTES",
    "UPLOAD_ROOT",
    "GitHubReleaseAdmin",
    "ReleaseAssetRecord",
    "ReleaseRecord",
    "UploadProgress",
    "parse_release",
    "release_change_sentence",
]
