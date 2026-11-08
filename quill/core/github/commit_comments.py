"""Comments on a commit: list them and add one, on the whole commit or a file line.

``GET /repos/{owner}/{repo}/commits/{sha}/comments`` lists a commit's comments
and ``POST`` to the same path adds one. A comment on a line carries ``path``
and ``line`` (GitHub's ``position`` is a diff offset and is deprecated, so it is
never sent). Both go through
:func:`~quill.core.github.rest_transport.request_json` (api.github.com only, no
redirects followed), and a new comment is reported only when GitHub's reply
carries its id.

A comment reads as author, date and text: "octocat, 2026-11-07: Looks good".

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message
from quill.core.github.run_actions import repo_path

_MAX_PAGES = 10
_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class CommitComment:
    """One comment on a commit, as GitHub returned it."""

    id: int
    author: str
    created_at: str
    body: str
    path: str = ""
    line: int | None = None
    url: str = ""

    @property
    def date(self) -> str:
        return self.created_at[:10] or "an unknown date"

    @property
    def where(self) -> str:
        """ "the whole commit", or "README.md line 12"."""
        if not self.path:
            return "the whole commit"
        return f"{self.path} line {self.line}" if self.line else self.path

    def label(self) -> str:
        """The list row: author, date and the first line of the text."""
        first = next((line.strip() for line in self.body.splitlines() if line.strip()), "")
        place = f" on {self.where}" if self.path else ""
        return f"{self.author or 'unknown'}, {self.date}{place}: {first or '(no text)'}"

    def detail(self) -> str:
        """Author, date, where it is and the whole text, for the detail box."""
        lines = [
            f"Author: {self.author or 'unknown'}",
            f"Date: {self.created_at or 'unknown'}",
            f"On: {self.where}",
            "",
            self.body,
        ]
        if self.url:
            lines.extend(["", self.url])
        return "\n".join(lines)


def _sha(sha: str) -> str:
    value = sha.strip()
    if not 7 <= len(value) <= 40 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise GitHubItemsError("Choose a commit first.")
    return value


def parse_commit_comment(row: object) -> CommitComment | None:
    """One REST comment object, or None when it is not one."""
    if not isinstance(row, Mapping):
        return None
    identifier = row.get("id")
    if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
        return None
    user = row.get("user")
    line = row.get("line")
    return CommitComment(
        id=identifier,
        author=str(user.get("login") or "") if isinstance(user, Mapping) else "",
        created_at=str(row.get("created_at") or ""),
        body=str(row.get("body") or ""),
        path=str(row.get("path") or ""),
        line=line if isinstance(line, int) and not isinstance(line, bool) and line > 0 else None,
        url=str(row.get("html_url") or ""),
    )


class _CommentAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


class GitHubCommitCommentsMixin:
    """List and add commit comments."""

    def fetch_commit_comments(
        self: _CommentAccess, full_name: str, sha: str
    ) -> GitHubFetchResult[CommitComment]:
        """Every comment on *sha*, oldest first, up to a thousand."""
        path = f"{repo_path(full_name)}/commits/{_sha(sha)}/comments"
        found: list[CommitComment] = []
        for page in range(1, _MAX_PAGES + 1):
            try:
                response = request_json(
                    self._token,
                    "GET",
                    path,
                    query={"per_page": str(_PAGE_SIZE), "page": str(page)},
                )
            except GitHubRestError as exc:
                raise GitHubItemsError(
                    rest_failure_message("read the commit's comments", exc)
                ) from exc
            rows: list[Any] = response.data if isinstance(response.data, list) else []
            found.extend(comment for row in rows if (comment := parse_commit_comment(row)))
            if len(rows) < _PAGE_SIZE:
                return GitHubFetchResult(tuple(found))
        return GitHubFetchResult(
            tuple(found),
            complete=False,
            truncated=True,
            warning=f"Showing the first {len(found)} comments; the commit has more.",
        )

    def add_commit_comment(
        self: _CommentAccess,
        full_name: str,
        sha: str,
        body: str,
        *,
        path: str = "",
        line: int | None = None,
    ) -> CommitComment:
        """Comment on the whole commit, or on *line* of *path* when both are given."""
        if not body.strip():
            raise GitHubItemsError("A comment needs some text.")
        file_path = path.strip().strip("/")
        if line is not None and (isinstance(line, bool) or line <= 0):
            raise GitHubItemsError("A line number is a whole number from 1 up.")
        if line is not None and not file_path:
            raise GitHubItemsError("Name the file the line is in, or clear the line number.")
        self._require_write_access("comment on a commit")
        payload: dict[str, object] = {"body": body}
        if file_path:
            payload["path"] = file_path
            if line is not None:
                payload["line"] = line
        target = f"{repo_path(full_name)}/commits/{_sha(sha)}/comments"
        action = f"comment on {file_path or 'the commit'}"
        try:
            response = request_json(self._token, "POST", target, body=payload)
        except GitHubRestError as exc:
            raise GitHubItemsError(rest_failure_message(action, exc)) from exc
        comment = parse_commit_comment(response.data) if response.status == 201 else None
        if comment is None:
            raise GitHubItemsError("GitHub did not confirm the new comment.")
        return comment


__all__ = ["CommitComment", "GitHubCommitCommentsMixin", "parse_commit_comment"]
