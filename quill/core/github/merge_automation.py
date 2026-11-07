"""Auto-merge and the merge queue for one pull request, through GitHub GraphQL.

Four mutations -- ``enablePullRequestAutoMerge``, ``disablePullRequestAutoMerge``,
``enqueuePullRequest`` and ``dequeuePullRequest`` -- all keyed by the pull
request's node ID, which is read first. Each function returns the sentence the
reviewer hears, built only from what GitHub's reply confirmed; a reply that
does not show the change raises instead of claiming it.

The transport is :func:`quill.core.github.review_graphql._request`, the same
reviewed call the review outline already uses (one egress entry, one place
that refuses redirects).
"""

from __future__ import annotations

from typing import Any

from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_graphql import ReviewGraphQLError, _request

#: The merge methods GitHub accepts, keyed by the words the chooser shows.
MERGE_METHODS: dict[str, str] = {
    "Create a merge commit": "MERGE",
    "Squash and merge": "SQUASH",
    "Rebase and merge": "REBASE",
}

_PULL_ID_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) { pullRequest(number:$number) { id headRefOid } }
}
"""

_ENABLE = """
mutation($id:ID!, $method:PullRequestMergeMethod!) {
  enablePullRequestAutoMerge(input:{pullRequestId:$id, mergeMethod:$method}) {
    pullRequest { autoMergeRequest { enabledAt mergeMethod } }
  }
}
"""

_DISABLE = """
mutation($id:ID!) {
  disablePullRequestAutoMerge(input:{pullRequestId:$id}) {
    pullRequest { autoMergeRequest { enabledAt } }
  }
}
"""

_ENQUEUE = """
mutation($id:ID!, $head:GitObjectID) {
  enqueuePullRequest(input:{pullRequestId:$id, expectedHeadOid:$head}) {
    mergeQueueEntry { id position state }
  }
}
"""

_DEQUEUE = """
mutation($id:ID!) {
  dequeuePullRequest(input:{id:$id}) { mergeQueueEntry { id state } }
}
"""

#: GitHub's GraphQL refusals, rephrased as what to do about them.
_KNOWN_REFUSALS: tuple[tuple[str, str], ...] = (
    (
        "auto merge is not allowed",
        "Auto-merge is turned off for this repository. A repository admin can turn it "
        "on in the repository's Settings, General, Pull Requests.",
    ),
    (
        "clean status",
        "GitHub can merge this pull request now, so auto-merge has nothing to wait for. "
        "Merge it instead.",
    ),
    (
        "merge queue is not enabled",
        "The base branch has no merge queue. Use auto-merge or merge it directly.",
    ),
    (
        "not enabled for this repository",
        "That merge method is turned off for this repository; choose another one.",
    ),
    (
        "must have admin rights",
        "Your account needs write access to this repository for that.",
    ),
)


def _explain(action: str, exc: ReviewGraphQLError) -> GitHubReviewError:
    text = str(exc.args[0]) if exc.args else str(exc)
    for needle, advice in _KNOWN_REFUSALS:
        if needle in text.casefold():
            return GitHubReviewError(f"Could not {action}. {advice}")
    return GitHubReviewError(f"Could not {action}. GitHub said: {text}")


def _token(provider: Any, action: str) -> str:
    token = getattr(provider, "token", None)
    if not getattr(provider, "is_authenticated", False) or not token:
        raise GitHubReviewError(
            f"Sign in to GitHub to {action}; the anonymous viewer is read-only."
        )
    return str(token)


def _pull_ids(token: str, full_name: str, number: int, action: str) -> tuple[str, str]:
    parts = full_name.split("/", 1)
    if len(parts) != 2 or not all(parts) or number <= 0:
        raise GitHubReviewError("Choose a pull request in an owner/repo repository first.")
    try:
        data = _request(
            token, _PULL_ID_QUERY, {"owner": parts[0], "repo": parts[1], "number": number}
        )
    except ReviewGraphQLError as exc:
        raise _explain(action, exc) from exc
    repository = data.get("repository")
    pull = repository.get("pullRequest") if isinstance(repository, dict) else None
    node_id = pull.get("id") if isinstance(pull, dict) else None
    if not isinstance(node_id, str) or not node_id:
        raise GitHubReviewError(
            f"Could not {action}. GitHub did not return pull request #{number}."
        )
    head = pull.get("headRefOid") if isinstance(pull, dict) else ""
    return node_id, head if isinstance(head, str) else ""


def _mutate(token: str, action: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    try:
        return _request(token, query, variables)
    except ReviewGraphQLError as exc:
        raise _explain(action, exc) from exc


def enable_auto_merge(provider: Any, full_name: str, number: int, method_label: str) -> str:
    action = "turn on auto-merge"
    method = MERGE_METHODS.get(method_label)
    if method is None:
        raise GitHubReviewError("Choose a merge method for auto-merge.")
    token = _token(provider, action)
    node_id, _head = _pull_ids(token, full_name, number, action)
    data = _mutate(token, action, _ENABLE, {"id": node_id, "method": method})
    result = data.get("enablePullRequestAutoMerge")
    pull = result.get("pullRequest") if isinstance(result, dict) else None
    request = pull.get("autoMergeRequest") if isinstance(pull, dict) else None
    if not isinstance(request, dict) or not request.get("enabledAt"):
        raise GitHubReviewError(f"GitHub did not confirm auto-merge for pull request #{number}.")
    confirmed = str(request.get("mergeMethod") or method).casefold()
    return (
        f"Auto-merge is on for pull request #{number}; GitHub will {confirmed} it "
        "when the required reviews and checks pass."
    )


def disable_auto_merge(provider: Any, full_name: str, number: int) -> str:
    action = "turn off auto-merge"
    token = _token(provider, action)
    node_id, _head = _pull_ids(token, full_name, number, action)
    data = _mutate(token, action, _DISABLE, {"id": node_id})
    result = data.get("disablePullRequestAutoMerge")
    pull = result.get("pullRequest") if isinstance(result, dict) else None
    if not isinstance(pull, dict) or pull.get("autoMergeRequest") is not None:
        raise GitHubReviewError(f"GitHub did not confirm auto-merge is off for #{number}.")
    return f"Auto-merge is off for pull request #{number}."


def enqueue_pull_request(provider: Any, full_name: str, number: int) -> str:
    action = "add the pull request to the merge queue"
    token = _token(provider, action)
    node_id, head = _pull_ids(token, full_name, number, action)
    variables: dict[str, object] = {"id": node_id, "head": head or None}
    data = _mutate(token, action, _ENQUEUE, variables)
    result = data.get("enqueuePullRequest")
    entry = result.get("mergeQueueEntry") if isinstance(result, dict) else None
    if not isinstance(entry, dict) or not entry.get("id"):
        raise GitHubReviewError(f"GitHub did not confirm #{number} joined the merge queue.")
    position = entry.get("position")
    where = f" at position {position}" if isinstance(position, int) and position > 0 else ""
    return f"Pull request #{number} is in the merge queue{where}."


def dequeue_pull_request(provider: Any, full_name: str, number: int) -> str:
    action = "remove the pull request from the merge queue"
    token = _token(provider, action)
    node_id, _head = _pull_ids(token, full_name, number, action)
    data = _mutate(token, action, _DEQUEUE, {"id": node_id})
    result = data.get("dequeuePullRequest")
    if not isinstance(result, dict) or "mergeQueueEntry" not in result:
        raise GitHubReviewError(f"GitHub did not confirm #{number} left the merge queue.")
    return f"Pull request #{number} is out of the merge queue."


__all__ = [
    "MERGE_METHODS",
    "dequeue_pull_request",
    "disable_auto_merge",
    "enable_auto_merge",
    "enqueue_pull_request",
]
