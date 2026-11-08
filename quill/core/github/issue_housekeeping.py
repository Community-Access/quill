"""Issue housekeeping for the GitHub Items viewer (Wave 4).

Lock and unlock a conversation with a reason, transfer an issue to another
repository, pin and unpin it, set its issue type where the repository has
types, and reorder a parent issue's sub-issues. Lock, unlock and the
sub-issue order are REST; transfer, pin and issue types exist only in GraphQL,
so those go to ``/graphql`` through the same
:func:`~quill.core.github.rest_transport.request_json` (one host, one token,
one rate-limit tracker).

Each write is confirmed by GitHub's reply before it is reported: a transfer
says the issue's new address, a pin says it is pinned. No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

LOCK_REASONS: tuple[tuple[str, str], ...] = (
    ("", "No reason given"),
    ("off-topic", "Off-topic"),
    ("too heated", "Too heated"),
    ("resolved", "Resolved"),
    ("spam", "Spam"),
)


@dataclass(frozen=True, slots=True)
class IssueType:
    id: str
    name: str
    description: str = ""

    @property
    def label(self) -> str:
        return f"{self.name}: {self.description}" if self.description else self.name


@dataclass(frozen=True, slots=True)
class SubIssue:
    id: int
    number: int
    title: str
    state: str = "open"
    url: str = ""

    @property
    def label(self) -> str:
        return f"#{self.number} {self.title} ({self.state})"


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


def _number(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitHubItemsError("Select an issue with a number first.")
    return value


def _split(repo: str) -> tuple[str, str]:
    repo_path(repo)  # validates owner/name
    owner, name = repo.split("/")
    return owner, name


def move_plan(
    order: list[SubIssue], index: int, delta: int
) -> tuple[dict[str, int], list[SubIssue]]:
    """The body that moves ``order[index]`` by *delta*, and the order that results.

    Moving up one places the item before its upper neighbour; moving down one
    places it after its lower neighbour. Raises when the move leaves the list.
    """
    target = index + delta
    if not 0 <= index < len(order) or not 0 <= target < len(order) or delta == 0:
        raise GitHubItemsError(
            "That sub-issue is already first." if delta < 0 else "That sub-issue is already last."
        )
    moving = order[index]
    neighbour = order[target]
    body = {"sub_issue_id": moving.id}
    body["before_id" if delta < 0 else "after_id"] = neighbour.id
    rest = order[:index] + order[index + 1 :]
    rest.insert(target, moving)
    return body, rest


class GitHubIssueHousekeeping:
    """Lock, transfer, pin, issue type and sub-issue order for one signed-in session."""

    def __init__(self, token: str | None) -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    def _graphql(self, action: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
        reply = _call(
            action,
            lambda: request_json(
                self._token, "POST", "/graphql", body={"query": query, "variables": variables}
            ),
            (200,),
        ).data
        payload = reply if isinstance(reply, dict) else {}
        errors = payload.get("errors")
        if errors:
            words = "; ".join(
                str(row.get("message", "error")) for row in errors if isinstance(row, dict)
            )
            raise GitHubItemsError(f"Could not {action}. GitHub said: {words or 'error'}.")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise GitHubItemsError(f"Could not {action}. GitHub sent no data.")
        return data

    def _issue_id(self, repo: str, number: int) -> str:
        owner, name = _split(repo)
        data = self._graphql(
            f"find issue #{number}",
            "query($owner:String!,$name:String!,$number:Int!){"
            "repository(owner:$owner,name:$name){issue(number:$number){id}}}",
            {"owner": owner, "name": name, "number": _number(number)},
        )
        issue = (data.get("repository") or {}).get("issue") if isinstance(data, dict) else None
        if not isinstance(issue, dict) or not issue.get("id"):
            raise GitHubItemsError(
                f"GitHub has no issue #{number} in {repo} "
                "(pull requests cannot be pinned or transferred)."
            )
        return str(issue["id"])

    # -- Lock -----------------------------------------------------------------

    def lock(self, repo: str, number: int, reason: str = "") -> None:
        self._require_write_access("lock a conversation")
        if reason not in dict(LOCK_REASONS):
            raise GitHubItemsError(f"GitHub does not accept {reason!r} as a lock reason.")
        body: dict[str, object] = {"lock_reason": reason} if reason else {}
        _call(
            f"lock #{number}",
            lambda: request_json(
                self._token,
                "PUT",
                f"{repo_path(repo)}/issues/{_number(number)}/lock",
                body=body,
            ),
            (204,),
        )

    def unlock(self, repo: str, number: int) -> None:
        self._require_write_access("unlock a conversation")
        _call(
            f"unlock #{number}",
            lambda: request_json(
                self._token, "DELETE", f"{repo_path(repo)}/issues/{_number(number)}/lock"
            ),
            (204,),
        )

    # -- Transfer -------------------------------------------------------------

    def transfer(self, repo: str, number: int, target: str) -> str:
        """Move the issue to *target*; return the new address GitHub reports."""
        self._require_write_access("transfer an issue")
        if target.strip().casefold() == repo.casefold():
            raise GitHubItemsError("Choose a different repository to transfer the issue to.")
        owner, name = _split(target.strip())
        issue_id = self._issue_id(repo, number)
        found = self._graphql(
            f"find {target}",
            "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){id}}",
            {"owner": owner, "name": name},
        )
        target_id = (found.get("repository") or {}).get("id")
        if not target_id:
            raise GitHubItemsError(f"GitHub has no repository {target} that this account can see.")
        data = self._graphql(
            f"transfer #{number} to {target}",
            "mutation($issue:ID!,$repo:ID!){transferIssue(input:{issueId:$issue,"
            "repositoryId:$repo}){issue{number url repository{nameWithOwner}}}}",
            {"issue": issue_id, "repo": str(target_id)},
        )
        moved = (data.get("transferIssue") or {}).get("issue")
        if not isinstance(moved, dict) or not moved.get("url"):
            raise GitHubItemsError(
                "GitHub answered without the moved issue; check both repositories on github.com."
            )
        where = (moved.get("repository") or {}).get("nameWithOwner") or target
        return f"Moved to {where} as #{moved.get('number')}: {moved['url']}"

    # -- Pin ------------------------------------------------------------------

    def set_pinned(self, repo: str, number: int, pinned: bool) -> None:
        verb = "pin" if pinned else "unpin"
        self._require_write_access(f"{verb} an issue")
        issue_id = self._issue_id(repo, number)
        mutation = "pinIssue" if pinned else "unpinIssue"
        data = self._graphql(
            f"{verb} #{number}",
            f"mutation($issue:ID!){{{mutation}(input:{{issueId:$issue}}){{issue{{isPinned}}}}}}",
            {"issue": issue_id},
        )
        issue = (data.get(mutation) or {}).get("issue")
        if isinstance(issue, dict) and "isPinned" in issue and bool(issue["isPinned"]) != pinned:
            raise GitHubItemsError(
                f"GitHub answered, but #{number} is still {'not ' if pinned else ''}pinned."
            )

    # -- Issue types ----------------------------------------------------------

    def issue_types(self, repo: str) -> tuple[IssueType, ...]:
        """The repository's issue types; empty when it has none (an organization feature)."""
        owner, name = _split(repo)
        data = self._graphql(
            "read the issue types",
            "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
            "issueTypes(first:50){nodes{id name description isEnabled}}}}",
            {"owner": owner, "name": name},
        )
        nodes = (((data.get("repository") or {}).get("issueTypes")) or {}).get("nodes") or ()
        return tuple(
            IssueType(
                str(node["id"]), str(node.get("name") or ""), str(node.get("description") or "")
            )
            for node in nodes
            if isinstance(node, dict) and node.get("id") and node.get("isEnabled", True)
        )

    def set_issue_type(self, repo: str, number: int, issue_type: IssueType | None) -> str:
        """Set (or clear, with ``None``) the type; return the type GitHub now reports."""
        self._require_write_access("set an issue type")
        issue_id = self._issue_id(repo, number)
        data = self._graphql(
            f"set the type of #{number}",
            "mutation($issue:ID!,$type:ID){updateIssueIssueType(input:{issueId:$issue,"
            "issueTypeId:$type}){issue{issueType{name}}}}",
            {"issue": issue_id, "type": issue_type.id if issue_type else None},
        )
        issue = (data.get("updateIssueIssueType") or {}).get("issue") or {}
        now = (issue.get("issueType") or {}).get("name") if isinstance(issue, dict) else None
        expected = issue_type.name if issue_type else None
        if (now or None) != expected:
            raise GitHubItemsError(f"GitHub answered, but #{number}'s type is {now or 'not set'}.")
        return str(now or "")

    # -- Sub-issues -----------------------------------------------------------

    def sub_issues(self, repo: str, number: int) -> list[SubIssue]:
        data = _call(
            f"list the sub-issues of #{number}",
            lambda: request_json(
                self._token,
                "GET",
                f"{repo_path(repo)}/issues/{_number(number)}/sub_issues",
                query={"per_page": "100"},
            ),
            (200,),
        ).data
        return [
            SubIssue(
                int(row["id"]),
                int(row.get("number") or 0),
                str(row.get("title") or ""),
                str(row.get("state") or "open"),
                str(row.get("html_url") or ""),
            )
            for row in (data if isinstance(data, list) else ())
            if isinstance(row, dict) and isinstance(row.get("id"), int)
        ]

    def move_sub_issue(
        self, repo: str, parent: int, order: list[SubIssue], index: int, delta: int
    ) -> list[SubIssue]:
        """Move one sub-issue up or down by one; return the order GitHub confirmed."""
        self._require_write_access("reorder sub-issues")
        body, _expected = move_plan(order, index, delta)
        _call(
            f"move #{order[index].number}",
            lambda: request_json(
                self._token,
                "PATCH",
                f"{repo_path(repo)}/issues/{_number(parent)}/sub_issues/priority",
                body=dict(body),
            ),
            (200,),
        )
        return self.sub_issues(repo, parent)


__all__ = [
    "LOCK_REASONS",
    "GitHubIssueHousekeeping",
    "IssueType",
    "SubIssue",
    "move_plan",
]
