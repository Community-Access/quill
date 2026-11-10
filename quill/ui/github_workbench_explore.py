"""Explore GitHub's views as Workbench nodes (GitHub PRD section 11, Phase 2).

Every ``explore:<view>`` node in :data:`quill.core.github.workbench_tree.GITHUB_TREE`
loads through :meth:`quill.core.github.explore.GitHubExploreClient.fetch_with_status`,
the call Explore GitHub makes, with the repository, person or search the node
stands for. No new network call: the client and its egress rows already exist.

The four My Work nodes are one fetch narrowed by the reason it names, which
Explore writes as the first line of each row's details ("Review requested").
"""

from __future__ import annotations

from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.workbench.filters import Query, render
from quill.core.workbench.tree import Need, NodeSpec, Scope

__all__ = ["EXPLORE_PREFIX", "explore_row_type", "explore_unavailable", "load_explore"]

EXPLORE_PREFIX = "explore:"

#: ExploreRow.kind -> the action table's row type.
_KINDS = {
    "repo": "repository",
    "person": "person",
    "notification": "notification",
    "issue": "issue",
    "pr": "pull_request",
    "label": "label",
    "gist": "gist",
    "discussion": "discussion",
    "security": "security_alert",
    "cache": "cache",
    # The Phase 3 loaders' rows (quill/ui/github_workbench_loaders.py).
    "saved_search": "saved_search",
    "file": "file",
    "folder": "folder",
    "milestone": "milestone",
    "project": "project",
    "org": "organization",
    "team": "team",
    "favorite": "favorite",
    "admin_action": "admin_action",
    "help_topic": "help_topic",
}

#: My Work's sources, as Explore labels them, for each reason preset.
_REASONS = {
    "review_requested": ("Review requested", ""),
    "assigned": ("Assigned", ""),
    "mentioned": ("Mentioned", ""),
    "authored_pr": ("Authored", "pr"),
    "authored_issue": ("Authored", "issue"),
}


def explore_row_type(row: ExploreRow) -> str:
    return _KINDS.get(row.kind, "result")


def explore_unavailable(node: NodeSpec, *, instance: str, signed_in: bool, query: Query) -> str:
    """Why an Explore node cannot load right now ("" when it can)."""
    if Need.SIGN_IN in node.needs and not signed_in:
        return "Sign in to GitHub to see this: GitHub menu > Manage GitHub Accounts."
    if node.scope is Scope.REPOSITORY and not instance:
        return "Open a repository first: Ctrl+L, or File > Open GitHub Address."
    if node.scope is Scope.QUERY and query.is_empty:
        return "Type what to search for in the filter box, then press Enter."
    return ""


def _matches_reason(row: ExploreRow, reason: str) -> bool:
    source, kind = _REASONS.get(reason, ("", ""))
    first = row.detail.split("\n", 1)[0]
    return source in first.split("; ") and (not kind or row.kind == kind)


def load_explore(
    client: Any, node: NodeSpec, *, instance: str, query: Query, account: str = ""
) -> list[ExploreRow]:
    """Fetch an Explore node's rows. Runs off the UI thread."""
    view = node.loader.removeprefix(EXPLORE_PREFIX)
    repositories: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    if view == "attention":
        from quill.core.github.attention_queue import GitHubAttentionQueue

        state = GitHubAttentionQueue.load(account or client.account_login())
        repositories, categories = tuple(state.repositories), tuple(state.categories)
    result = client.fetch_with_status(
        view,
        repo=instance if node.scope is Scope.REPOSITORY else "",
        person=instance if node.scope is Scope.PERSON else "",
        query=render(query) if node.scope is Scope.QUERY else "",
        repositories=repositories,
        categories=categories,
    )
    rows = list(result.items)
    reason = dict(node.preset).get("reason", "")
    return [row for row in rows if _matches_reason(row, reason)] if reason else rows
