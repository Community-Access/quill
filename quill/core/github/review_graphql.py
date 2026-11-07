"""Small authenticated GraphQL bridge for review-thread state and mutations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.error_codes import CodedError
from quill.core.github.merge_policy import GitHubPullQueueState
from quill.core.net import verified_ssl_context


class ReviewGraphQLError(CodedError):
    """GitHub could not read or change review-thread resolution state."""

    code = "QUILL-GITHUB-REVIEW-GRAPHQL-ERROR"


@dataclass(frozen=True, slots=True)
class ReviewThreadState:
    node_id: str
    resolved: bool
    can_resolve: bool
    can_unresolve: bool
    outdated: bool
    line: int
    original_line: int


_THREADS_QUERY = """
query($owner:String!, $repo:String!, $number:Int!, $after:String) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$number) {
      reviewThreads(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated viewerCanResolve viewerCanUnresolve
          line originalLine
          comments(first:1) { nodes { databaseId } }
        }
      }
    }
  }
}
"""

_THREAD_PAGE_SIZE = 100
_MAX_THREAD_PAGES = 100
_PULL_QUEUE_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$number) {
      headRefOid isMergeQueueEnabled isInMergeQueue
      autoMergeRequest { enabledAt mergeMethod }
    }
  }
}
"""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def _request(token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "QUILL-GitHub-Workbench",
        },
        method="POST",
    )
    try:
        opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
        with opener.open(request, timeout=20) as response:
            result = json.load(response)
    except HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise ReviewGraphQLError(
                "GitHub redirected the GraphQL request; credentials were not forwarded."
            ) from exc
        raise ReviewGraphQLError(
            f"GitHub returned HTTP {exc.code} for the review-thread request."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - retain a usable REST review on failure
        raise ReviewGraphQLError(f"GitHub review-thread request failed: {exc}") from exc
    if not isinstance(result, dict):
        raise ReviewGraphQLError("GitHub returned an invalid review-thread response.")
    errors = result.get("errors")
    if errors:
        message = "; ".join(
            str(row.get("message", "error")) for row in errors if isinstance(row, dict)
        )
        raise ReviewGraphQLError(message or "GitHub rejected the review-thread request.")
    data = result.get("data")
    if not isinstance(data, dict):
        raise ReviewGraphQLError("GitHub returned no review-thread data.")
    return data


def fetch_thread_states(token: str, full_name: str, number: int) -> dict[int, ReviewThreadState]:
    """Page through GraphQL threads, keyed by the root REST comment ID."""
    parts = full_name.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ReviewGraphQLError("Enter a valid owner/repo before loading review threads.")
    owner, repo = parts
    if number <= 0:
        raise ReviewGraphQLError(
            "A positive pull request number is required to load review threads."
        )
    states: dict[int, ReviewThreadState] = {}
    after: str | None = None
    page_count = 0
    while True:
        page_count += 1
        if page_count > _MAX_THREAD_PAGES:
            raise ReviewGraphQLError(
                f"GitHub returned more than {_THREAD_PAGE_SIZE * _MAX_THREAD_PAGES} review threads."
            )
        data = _request(
            token,
            _THREADS_QUERY,
            {"owner": owner, "repo": repo, "number": number, "after": after},
        )
        try:
            connection = data["repository"]["pullRequest"]["reviewThreads"]
            nodes = connection["nodes"]
            page = connection["pageInfo"]
        except (KeyError, TypeError) as exc:
            raise ReviewGraphQLError("GitHub returned incomplete review-thread data.") from exc
        if (
            not isinstance(connection, dict)
            or not isinstance(nodes, list)
            or not isinstance(page, dict)
        ):
            raise ReviewGraphQLError("GitHub returned malformed review-thread pagination data.")
        for node in nodes or ():
            if not isinstance(node, dict):
                raise ReviewGraphQLError("GitHub returned a malformed review thread.")
            comments_connection = node.get("comments")
            comments = (
                comments_connection.get("nodes") if isinstance(comments_connection, dict) else None
            )
            if not isinstance(comments, list) or not comments or not isinstance(comments[0], dict):
                raise ReviewGraphQLError(
                    "GitHub returned a review thread without its root comment."
                )
            root_id = comments[0].get("databaseId")
            if isinstance(root_id, bool) or not isinstance(root_id, int) or root_id <= 0:
                raise ReviewGraphQLError(
                    "GitHub returned a review thread without a valid root comment ID."
                )
            thread_id = node.get("id")
            resolved = node.get("isResolved")
            can_resolve = node.get("viewerCanResolve")
            can_unresolve = node.get("viewerCanUnresolve")
            outdated = node.get("isOutdated")
            if (
                not isinstance(thread_id, str)
                or not thread_id
                or not isinstance(resolved, bool)
                or not isinstance(can_resolve, bool)
                or not isinstance(can_unresolve, bool)
                or not isinstance(outdated, bool)
            ):
                raise ReviewGraphQLError("GitHub returned incomplete review-thread state.")
            line = node.get("line")
            original_line = node.get("originalLine")
            if any(
                value is not None and (isinstance(value, bool) or not isinstance(value, int))
                for value in (line, original_line)
            ):
                raise ReviewGraphQLError("GitHub returned invalid review-thread line numbers.")
            states[root_id] = ReviewThreadState(
                node_id=thread_id,
                resolved=resolved,
                can_resolve=can_resolve,
                can_unresolve=can_unresolve,
                outdated=outdated,
                line=line or 0,
                original_line=original_line or 0,
            )
        has_next_page = page.get("hasNextPage")
        if not isinstance(has_next_page, bool):
            raise ReviewGraphQLError("GitHub returned invalid review-thread page state.")
        if not has_next_page:
            return states
        cursor = page.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor == after:
            raise ReviewGraphQLError("GitHub returned an invalid review-thread page cursor.")
        after = cursor


def fetch_pull_queue_state(token: str, full_name: str, number: int) -> GitHubPullQueueState:
    """Read the queue/auto-merge status and HEAD revision for one pull request."""
    parts = full_name.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ReviewGraphQLError("Enter a valid owner/repo before loading merge-queue status.")
    if number <= 0:
        raise ReviewGraphQLError(
            "A positive pull request number is required to load merge-queue status."
        )
    data = _request(
        token,
        _PULL_QUEUE_QUERY,
        {"owner": parts[0], "repo": parts[1], "number": number},
    )
    try:
        pull = data["repository"]["pullRequest"]
    except (KeyError, TypeError) as exc:
        raise ReviewGraphQLError("GitHub returned incomplete merge-queue data.") from exc
    if not isinstance(pull, dict):
        raise ReviewGraphQLError("GitHub returned no pull request for merge-queue status.")
    enabled = pull.get("isMergeQueueEnabled")
    in_queue = pull.get("isInMergeQueue")
    head_sha = pull.get("headRefOid")
    auto_merge = pull.get("autoMergeRequest")
    if (
        not isinstance(enabled, bool)
        or not isinstance(in_queue, bool)
        or not isinstance(head_sha, str)
        or (auto_merge is not None and not isinstance(auto_merge, dict))
    ):
        raise ReviewGraphQLError("GitHub returned incomplete merge-queue state.")
    return GitHubPullQueueState(
        merge_queue_enabled=enabled,
        in_merge_queue=in_queue,
        auto_merge_enabled=auto_merge is not None,
        head_sha=head_sha,
    )


def set_thread_resolved(token: str, node_id: str, resolved: bool) -> None:
    """Resolve or reopen one thread using its GraphQL node ID."""
    if not node_id:
        raise ReviewGraphQLError("This review thread has no GitHub thread ID.")
    mutation = "resolveReviewThread" if resolved else "unresolveReviewThread"
    data = _request(
        token,
        "mutation($threadId:ID!) { "
        f"{mutation}(input:{{threadId:$threadId}}) {{ thread {{ id isResolved }} }} }}",
        {"threadId": node_id},
    )
    result = data.get(mutation)
    returned = result.get("thread") if isinstance(result, dict) else None
    if (
        not isinstance(returned, dict)
        or returned.get("id") != node_id
        or returned.get("isResolved") is not resolved
    ):
        raise ReviewGraphQLError("GitHub did not confirm the thread state change.")
