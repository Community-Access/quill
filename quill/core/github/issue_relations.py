"""An issue's relationships: its parent, its sub-issues, and what blocks it.

GitHub links issues three ways this module reads and changes over REST:

* **parent and sub-issues**: ``GET .../issues/{n}/parent``,
  ``POST .../issues/{n}/sub_issues`` (``sub_issue_id``, and ``replace_parent``
  to move one from another parent), ``DELETE .../issues/{n}/sub_issue``;
* **blocked by**: ``GET``/``POST .../dependencies/blocked_by`` (``issue_id``)
  and ``DELETE .../dependencies/blocked_by/{issue_id}``;
* **blocking**: ``GET .../dependencies/blocking``, read only, because it is the
  other side of someone else's "blocked by".

GitHub names the issue to link by its database **id**, not its number, so an
issue typed as ``#12`` or ``owner/repo#12`` is looked up first
(:meth:`GitHubIssueRelations.issue_ref`). Every write is confirmed by GitHub's
reply before it is reported. No ``wx``; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

__all__ = ["GitHubIssueRelations", "IssueRef", "Relations", "parse_issue_ref"]

_REF = re.compile(r"^\s*(?:(?P<repo>[\w.-]+/[\w.-]+))?#?(?P<number>\d+)\s*$")
_URL = re.compile(r"github\.com/(?P<repo>[\w.-]+/[\w.-]+)/(?:issues|pull)/(?P<number>\d+)")


@dataclass(frozen=True, slots=True)
class IssueRef:
    """An issue as GitHub's relationship routes need it: its id, and how it reads."""

    id: int
    number: int
    title: str
    repo: str
    state: str = "open"

    def label(self, here: str = "") -> str:
        where = "" if self.repo == here else f"{self.repo}"
        return f"{where}#{self.number} {self.title} ({self.state})"


@dataclass(frozen=True, slots=True)
class Relations:
    """Everything one issue is linked to."""

    parent: IssueRef | None = None
    sub_issues: tuple[IssueRef, ...] = ()
    blocked_by: tuple[IssueRef, ...] = ()
    blocking: tuple[IssueRef, ...] = ()
    unread: tuple[str, ...] = field(default_factory=tuple)

    def lines(self, here: str) -> list[str]:
        """The relationships as rows to read, each starting with what it is."""
        rows: list[str] = []
        if self.parent is not None:
            rows.append(f"Parent: {self.parent.label(here)}")
        rows += [f"Sub-issue: {i.label(here)}" for i in self.sub_issues]
        rows += [f"Blocked by: {i.label(here)}" for i in self.blocked_by]
        rows += [f"Blocking: {i.label(here)}" for i in self.blocking]
        rows += [f"Not read: {what}" for what in self.unread]
        return rows

    def summary(self) -> str:
        parts = []
        if self.parent is not None:
            parts.append(f"a parent, #{self.parent.number}")
        for count, one, many in (
            (len(self.sub_issues), "sub-issue", "sub-issues"),
            (len(self.blocked_by), "issue blocking it", "issues blocking it"),
            (len(self.blocking), "issue it blocks", "issues it blocks"),
        ):
            if count:
                parts.append(f"{count} {one if count == 1 else many}")
        return ", ".join(parts) if parts else "no relationships"


def parse_issue_ref(text: str, here: str) -> tuple[str, int]:
    """``(repo, number)`` from "#12", "12", "owner/repo#12" or an issue's address."""
    found = _URL.search(text or "")
    if found:
        return found["repo"], int(found["number"])
    match = _REF.match(text or "")
    if not match:
        raise GitHubItemsError(
            "Type an issue as #12, owner/repo#12, or paste its address from GitHub."
        )
    return (match["repo"] or here), int(match["number"])


def _ref(raw: Any, fallback_repo: str) -> IssueRef | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    repo = fallback_repo
    url = str(raw.get("repository_url", "") or "")
    if "/repos/" in url:
        repo = url.split("/repos/", 1)[1]
    return IssueRef(
        id=int(raw["id"]),
        number=int(raw.get("number", 0) or 0),
        title=str(raw.get("title", "") or ""),
        repo=repo,
        state=str(raw.get("state", "open") or "open"),
    )


class GitHubIssueRelations:
    """Read and change one issue's relationships, for one signed-in session."""

    def __init__(
        self, token: str | None, request: Callable[..., RestResponse] = request_json
    ) -> None:
        self._token = token
        self._request = request

    def _call(self, action: str, method: str, path: str, expect: tuple[int, ...], **kw: Any) -> Any:
        try:
            response = self._request(self._token, method, path, **kw)
        except GitHubRestError as exc:
            raise GitHubItemsError(rest_failure_message(action, exc)) from exc
        if response.status not in expect:
            raise GitHubItemsError(
                f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
            )
        return response.data

    def _write(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    def issue_ref(self, text: str, here: str) -> IssueRef:
        """The issue *text* names (``#12``, ``owner/repo#12`` or its address), with its id."""
        repo, number = parse_issue_ref(text, here)
        data = self._call("find that issue", "GET", f"{repo_path(repo)}/issues/{number}", (200,))
        found = _ref(data, repo)
        if found is None:
            raise GitHubItemsError(f"GitHub has no issue #{number} in {repo}.")
        return found

    def _list(self, action: str, path: str, repo: str) -> list[IssueRef]:
        data = self._call(action, "GET", path, (200,), query={"per_page": "100"})
        rows = data if isinstance(data, list) else []
        return [r for r in (_ref(raw, repo) for raw in rows) if r is not None]

    def relations(self, repo: str, number: int) -> Relations:
        """Parent, sub-issues, blocked by and blocking; a part GitHub refuses is named."""
        base = f"{repo_path(repo)}/issues/{number}"
        unread: list[str] = []
        parent: IssueRef | None = None
        try:  # 404 is GitHub's answer for "no parent", not a failure
            reply = self._request(self._token, "GET", f"{base}/parent")
            if reply.status == 200:
                parent = _ref(reply.data, repo)
        except GitHubRestError as exc:
            if exc.status != 404:
                unread.append(f"the parent ({rest_failure_message('read the parent', exc)})")

        def listed(what: str, path: str) -> tuple[IssueRef, ...]:
            try:
                return tuple(self._list(f"read {what}", path, repo))
            except GitHubItemsError as exc:
                unread.append(f"{what} ({exc})")
                return ()

        return Relations(
            parent=parent,
            sub_issues=listed("the sub-issues", f"{base}/sub_issues"),
            blocked_by=listed("what blocks it", f"{base}/dependencies/blocked_by"),
            blocking=listed("what it blocks", f"{base}/dependencies/blocking"),
            unread=tuple(unread),
        )

    def add_sub_issue(self, repo: str, number: int, child: IssueRef, *, move: bool = False) -> None:
        """Make *child* a sub-issue; *move* takes it from the parent it has now."""
        action = f"add #{child.number} as a sub-issue"
        self._write(action)
        body: dict[str, Any] = {"sub_issue_id": child.id}
        if move:
            body["replace_parent"] = True
        self._call(
            action, "POST", f"{repo_path(repo)}/issues/{number}/sub_issues", (200, 201), body=body
        )

    def remove_sub_issue(self, repo: str, number: int, child: IssueRef) -> None:
        action = f"remove #{child.number} from the sub-issues"
        self._write(action)
        self._call(
            action,
            "DELETE",
            f"{repo_path(repo)}/issues/{number}/sub_issue",
            (200, 204),
            body={"sub_issue_id": child.id},
        )

    def add_blocked_by(self, repo: str, number: int, blocker: IssueRef) -> None:
        action = f"mark #{number} as blocked by #{blocker.number}"
        self._write(action)
        self._call(
            action,
            "POST",
            f"{repo_path(repo)}/issues/{number}/dependencies/blocked_by",
            (200, 201),
            body={"issue_id": blocker.id},
        )

    def remove_blocked_by(self, repo: str, number: int, blocker: IssueRef) -> None:
        action = f"stop #{number} being blocked by #{blocker.number}"
        self._write(action)
        self._call(
            action,
            "DELETE",
            f"{repo_path(repo)}/issues/{number}/dependencies/blocked_by/{blocker.id}",
            (200, 204),
        )
