"""Repository files for the shared file browser: folders, file text, READMEs,
file history and blame (Wave 3).

Every call goes through :func:`~quill.core.github.rest_transport.request_json`
(REST) or :func:`~quill.core.github.github_graphql.graphql_data` (blame), so the
token stays on ``api.github.com``. Folders and file text work anonymously on a
public repository; blame needs a signed-in account, because GitHub's GraphQL API
does not answer anonymous requests.

Blame comes back from GitHub as ranges of lines, and neighbouring ranges are
often the same commit. :func:`group_blame_runs` joins those, so each run reads as
one sentence: "Lines 10 to 14: Jeff Bishop, 3 November 2026, 1a2b3c4, Fix the
diff". No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import base64
import binascii
import datetime as _dt
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

from quill.core.github.github_graphql import as_dict, graphql_data, split_repo
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.milestones import spoken_date
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

__all__ = [
    "BlameRun",
    "FileCommit",
    "GitHubRepoFilesMixin",
    "RepoEntry",
    "blob_url",
    "clean_repo_path",
    "group_blame_runs",
    "parse_blame",
    "parse_file_history",
    "parse_folder",
]

_KIND_WORDS = {"dir": "folder", "file": "file", "symlink": "link", "submodule": "submodule"}
_MAX_TEXT_BYTES = 1_000_000

_BLAME_QUERY = """
query($owner:String!, $repo:String!, $ref:String!, $path:String!) {
  repository(owner:$owner, name:$repo) {
    object(expression:$ref) {
      ... on Commit {
        blame(path:$path) {
          ranges {
            startingLine endingLine
            commit { oid abbreviatedOid messageHeadline url
                     author { name date user { login } } }
          }
        }
      }
    }
  }
}
"""


def clean_repo_path(path: str) -> str:
    """A repository path without leading or trailing slashes, or a clear error."""
    cleaned = path.strip().strip("/")
    parts = cleaned.split("/") if cleaned else []
    if "\\" in cleaned or any(part in ("", ".", "..") for part in parts):
        raise GitHubItemsError(f"{path!r} is not a path inside the repository.")
    return cleaned


def _clean_ref(ref: str) -> str:
    value = ref.strip()
    if not value or len(value) > 256 or any(ord(char) < 33 for char in value):
        raise GitHubItemsError("Enter a branch, tag or commit first.")
    return value


def blob_url(full_name: str, ref: str, path: str) -> str:
    """The github.com address of *path* at *ref*, as the open-file path expects."""
    return (
        f"https://github.com/{full_name}/blob/{quote(ref, safe='/')}/"
        f"{quote(clean_repo_path(path), safe='/')}"
    )


@dataclass(frozen=True, slots=True)
class RepoEntry:
    """One file or folder in a repository folder."""

    name: str
    path: str
    kind: str  # "dir", "file", "symlink" or "submodule"
    size: int = 0
    sha: str = ""
    url: str = ""

    @property
    def is_folder(self) -> bool:
        return self.kind == "dir"

    @property
    def label(self) -> str:
        if self.is_folder:
            return f"{self.name}, folder"
        word = _KIND_WORDS.get(self.kind, "file")
        if self.kind == "file":
            return f"{self.name}, {_size_words(self.size)}"
        return f"{self.name}, {word}"


def _size_words(size: int) -> str:
    if size < 1024:
        return f"{size} byte" + ("" if size == 1 else "s")
    if size < 1024 * 1024:
        return f"{size // 1024} kilobytes"
    return f"{size / (1024 * 1024):.1f} megabytes"


def parse_folder(data: object) -> list[RepoEntry]:
    """``GET /contents/{path}`` for a folder, folders first, then by name."""
    rows = data if isinstance(data, list) else []
    entries: list[RepoEntry] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        try:
            size = int(row.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        entries.append(
            RepoEntry(
                name=str(row.get("name") or row["path"]),
                path=str(row["path"]),
                kind=str(row.get("type") or "file"),
                size=size,
                sha=str(row.get("sha") or ""),
                url=str(row.get("html_url") or ""),
            )
        )
    return sorted(entries, key=lambda entry: (not entry.is_folder, entry.name.casefold()))


def _decode_content(data: object, path: str) -> str:
    if not isinstance(data, dict):
        raise GitHubItemsError(f"{path} is a folder, not a file.")
    if data.get("type") not in (None, "file"):
        raise GitHubItemsError(f"{path} is a {data.get('type')}, not a file QUILL can show.")
    if data.get("encoding") != "base64" or not isinstance(data.get("content"), str):
        raise GitHubItemsError(
            f"{path} is larger than the 1 MB GitHub sends this way. Open it on GitHub instead."
        )
    try:
        raw = base64.b64decode(str(data["content"]), validate=False)
    except (binascii.Error, ValueError) as exc:
        raise GitHubItemsError(f"GitHub sent {path} in a form QUILL could not read.") from exc
    if len(raw) > _MAX_TEXT_BYTES or b"\x00" in raw[:8192]:
        raise GitHubItemsError(f"{path} is a binary file, so there is no text to show.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubItemsError(f"{path} is not UTF-8 text, so there is no text to show.") from exc
    return text.removeprefix("﻿")


@dataclass(frozen=True, slots=True)
class FileCommit:
    """One commit that changed a path."""

    sha: str
    title: str
    author: str
    date: str
    url: str = ""

    def label(self, today: _dt.date | None = None) -> str:
        when = spoken_date(self.date, today=today) or "no date"
        title = self.title or "No commit message"
        return f"{title}: {self.author or 'unknown'}, {when}, {self.sha[:7]}"


def parse_file_history(data: object) -> list[FileCommit]:
    rows = data if isinstance(data, list) else []
    commits: list[FileCommit] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("sha"):
            continue
        info = as_dict(row.get("commit"))
        author = as_dict(info.get("author"))
        login = as_dict(row.get("author"))
        message = str(info.get("message") or "")
        commits.append(
            FileCommit(
                sha=str(row["sha"]),
                title=message.splitlines()[0] if message else "",
                author=str(author.get("name") or login.get("login") or ""),
                date=str(author.get("date") or ""),
                url=str(row.get("html_url") or ""),
            )
        )
    return commits


@dataclass(frozen=True, slots=True)
class BlameRun:
    """A run of consecutive lines last changed by one commit."""

    start: int
    end: int
    sha: str
    title: str
    author: str
    date: str
    url: str = ""

    def label(self, today: _dt.date | None = None) -> str:
        lines = (
            f"Line {self.start}"
            if self.start == self.end
            else (f"Lines {self.start} to {self.end}")
        )
        when = spoken_date(self.date, today=today) or "no date"
        return (
            f"{lines}: {self.author or 'unknown'}, {when}, {self.sha[:7]}, "
            f"{self.title or 'no commit message'}"
        )


def parse_blame(data: object) -> list[BlameRun]:
    """GitHub's blame ranges, first line first, before grouping."""
    repository = data.get("repository") if isinstance(data, dict) else None
    target = repository.get("object") if isinstance(repository, dict) else None
    if not isinstance(target, dict):
        raise GitHubItemsError("That branch, tag or commit is not in this repository.")
    blame = target.get("blame")
    if not isinstance(blame, dict):
        raise GitHubItemsError("GitHub has no blame for this file at that commit.")
    runs: list[BlameRun] = []
    for row in blame.get("ranges") or ():
        if not isinstance(row, dict):
            continue
        commit = as_dict(row.get("commit"))
        author = as_dict(commit.get("author"))
        user = as_dict(author.get("user"))
        try:
            start, end = int(row.get("startingLine") or 0), int(row.get("endingLine") or 0)
        except (TypeError, ValueError):
            continue
        if start <= 0 or end < start:
            continue
        runs.append(
            BlameRun(
                start=start,
                end=end,
                sha=str(commit.get("oid") or ""),
                title=str(commit.get("messageHeadline") or ""),
                author=str(author.get("name") or user.get("login") or ""),
                date=str(author.get("date") or ""),
                url=str(commit.get("url") or ""),
            )
        )
    return sorted(runs, key=lambda run: run.start)


def group_blame_runs(ranges: Iterable[BlameRun]) -> list[BlameRun]:
    """Join neighbouring ranges from the same commit into one run."""
    grouped: list[BlameRun] = []
    for run in sorted(ranges, key=lambda item: item.start):
        last = grouped[-1] if grouped else None
        if last is not None and last.sha == run.sha and run.start <= last.end + 1:
            grouped[-1] = BlameRun(
                last.start,
                max(last.end, run.end),
                last.sha,
                last.title,
                last.author,
                last.date,
                last.url,
            )
        else:
            grouped.append(run)
    return grouped


class _FilesAccess(Protocol):
    _token: str | None


def _get(
    provider: _FilesAccess, action: str, path: str, query: dict[str, str] | None = None
) -> RestResponse:
    try:
        return request_json(provider._token, "GET", path, query=query)
    except GitHubRestError as exc:
        if exc.status == 404:
            raise GitHubItemsError(
                f"Could not {action}. GitHub could not find it at that branch, tag or "
                "commit, or this account cannot see the repository."
            ) from exc
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc


class GitHubRepoFilesMixin:
    """Folder, file, README, history and blame reads for ``GitHubItemsProvider``."""

    def fetch_default_branch(self: _FilesAccess, full_name: str) -> str:
        data = _get(self, "read the repository", repo_path(full_name)).data
        branch = data.get("default_branch") if isinstance(data, dict) else ""
        return str(branch or "main")

    def fetch_ref_names(self: _FilesAccess, full_name: str, *, limit: int = 100) -> list[str]:
        """Branch names, then tag names, for the browser's branch-or-tag box."""
        names: list[str] = []
        for kind in ("branches", "tags"):
            rows = _get(
                self,
                f"list the {kind}",
                f"{repo_path(full_name)}/{kind}",
                {"per_page": str(max(1, min(limit, 100)))},
            ).data
            for row in rows if isinstance(rows, list) else ():
                if isinstance(row, dict) and row.get("name"):
                    names.append(str(row["name"]))
        return list(dict.fromkeys(names))

    def fetch_repo_folder(
        self: _FilesAccess, full_name: str, ref: str, path: str = ""
    ) -> list[RepoEntry]:
        folder = clean_repo_path(path)
        url = f"{repo_path(full_name)}/contents" + (f"/{quote(folder, safe='/')}" if folder else "")
        data = _get(self, "open the folder", url, {"ref": _clean_ref(ref)}).data
        if isinstance(data, dict):
            raise GitHubItemsError(f"{folder or 'That path'} is a file, not a folder.")
        return parse_folder(data)

    def fetch_repo_file_text(self: _FilesAccess, full_name: str, path: str, ref: str) -> str:
        file_path = clean_repo_path(path)
        if not file_path:
            raise GitHubItemsError("Choose a file first.")
        data = _get(
            self,
            f"open {file_path}",
            f"{repo_path(full_name)}/contents/{quote(file_path, safe='/')}",
            {"ref": _clean_ref(ref)},
        ).data
        return _decode_content(data, file_path)

    def fetch_readme(
        self: _FilesAccess, full_name: str, ref: str, folder: str = ""
    ) -> tuple[str, str]:
        """``(path, text)`` of the README GitHub shows for *folder* (``""`` for the top)."""
        where = clean_repo_path(folder)
        url = f"{repo_path(full_name)}/readme" + (f"/{quote(where, safe='/')}" if where else "")
        try:
            response = request_json(self._token, "GET", url, query={"ref": _clean_ref(ref)})
        except GitHubRestError as exc:
            if exc.status == 404:
                place = f"the {where} folder" if where else "this repository"
                raise GitHubItemsError(f"{place[0].upper()}{place[1:]} has no README.") from exc
            raise GitHubItemsError(rest_failure_message("read the README", exc)) from exc
        data: Any = response.data
        readme_path = str(data.get("path") or "README") if isinstance(data, dict) else "README"
        return readme_path, _decode_content(data, readme_path)

    def fetch_file_history(
        self: _FilesAccess, full_name: str, path: str, ref: str, *, limit: int = 50
    ) -> list[FileCommit]:
        file_path = clean_repo_path(path)
        query = {"sha": _clean_ref(ref), "per_page": str(max(1, min(limit, 100)))}
        if file_path:
            query["path"] = file_path
        data = _get(self, "read the file history", f"{repo_path(full_name)}/commits", query).data
        return parse_file_history(data)

    def fetch_blame(self: _FilesAccess, full_name: str, ref: str, path: str) -> list[BlameRun]:
        owner, name = split_repo(full_name)
        file_path = clean_repo_path(path)
        if not file_path:
            raise GitHubItemsError("Choose a file first.")
        data = graphql_data(
            self._token,
            _BLAME_QUERY,
            {"owner": owner, "repo": name, "ref": _clean_ref(ref), "path": file_path},
            action=f"read the blame for {file_path}",
        )
        return group_blame_runs(parse_blame(data))
