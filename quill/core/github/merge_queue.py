"""A repository's merge queue, as a list (GH-MR).

Repository > Merge Queue reads the default branch's queue in one GraphQL call
(``repository.mergeQueue``): each entry in order, its pull request, who queued
it, its state and the commit it was queued at. A repository with no merge
queue gives no rows, and the node's note says why. Each row is a pull request
row, so Open, Open on GitHub and the rest work on it as anywhere else.

wx-free and strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.github_graphql import as_dict, graphql_data, split_repo

__all__ = ["QUEUE_STATES", "fetch_merge_queue", "queue_row"]

_QUERY = """
query($o: String!, $n: String!, $first: Int!) {
  repository(owner: $o, name: $n) {
    mergeQueue {
      branch { name }
      entries(first: $first) { nodes {
        position state enqueuedAt
        enqueuer { login }
        headCommit { oid }
        pullRequest { number title url author { login } }
      } }
    }
  }
}
"""

#: GitHub's entry states, in words.
QUEUE_STATES: dict[str, str] = {
    "QUEUED": "waiting",
    "AWAITING_CHECKS": "running its checks",
    "MERGEABLE": "ready to merge",
    "UNMERGEABLE": "cannot merge, and will leave the queue",
    "LOCKED": "being merged",
}


def queue_row(repository: str, branch: str, node: dict[str, Any]) -> ExploreRow:
    pull = as_dict(node.get("pullRequest"))
    number = int(pull.get("number") or 0)
    title = str(pull.get("title") or "")
    state = QUEUE_STATES.get(str(node.get("state") or ""), str(node.get("state") or "").lower())
    who = str(as_dict(node.get("enqueuer")).get("login") or "")
    commit = str(as_dict(node.get("headCommit")).get("oid") or "")[:7]
    position = int(node.get("position") or 0)
    label = f"{position}. #{number} {title}, {state}"
    detail = (
        f"Position {position} in the merge queue for {branch}: #{number} {title}, {state}. "
        + (f"Queued by {who}" if who else "Queued")
        + (f" at commit {commit}, " if commit else ", ")
        + f"{str(node.get('enqueuedAt') or '')[:16].replace('T', ' ')}."
    )
    return ExploreRow(
        label=label,
        detail=detail,
        url=str(pull.get("url") or ""),
        repo=repository,
        kind="pr",
        key=str(number),
        updated_at=str(node.get("enqueuedAt") or ""),
        title=title,
    )


def fetch_merge_queue(token: str | None, repository: str, *, limit: int = 100) -> list[ExploreRow]:
    owner, name = split_repo(repository)
    data = graphql_data(
        token,
        _QUERY,
        {"o": owner, "n": name, "first": max(1, min(int(limit), 100))},
        action="read the merge queue",
    )
    queue = as_dict(as_dict(data.get("repository")).get("mergeQueue"))
    if not queue:
        return []
    branch = str(as_dict(queue.get("branch")).get("name") or "the default branch")
    nodes = as_dict(queue.get("entries")).get("nodes") or []
    rows = [queue_row(repository, branch, as_dict(node)) for node in nodes if node]
    return sorted(rows, key=lambda row: row.label.split(".", 1)[0].zfill(6))
