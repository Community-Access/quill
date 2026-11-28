"""Explore GitHub's views as Workbench nodes (GitHub PRD section 11, Phase 2).

Every ``explore:<view>`` node in :data:`quill.core.github.workbench_tree.GITHUB_TREE`
loads through :meth:`quill.core.github.explore.GitHubExploreClient.fetch_with_status`,
the call Explore GitHub makes, with the repository, person or search the node
stands for. No new network call: the client and its egress rows already exist.

The four My Work nodes are one fetch narrowed by the reason it names, which
Explore writes as the first line of each row's details ("Review requested").
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.review_requests import REVIEW_SOURCES
from quill.core.workbench.filters import Query, render
from quill.core.workbench.tree import Need, NodeSpec, Scope

__all__ = [
    "EXPLORE_PAGE",
    "EXPLORE_PREFIX",
    "explore_row_type",
    "explore_unavailable",
    "load_explore",
]

EXPLORE_PREFIX = "explore:"

#: ExploreRow.kind -> the action table's row type.
_KINDS = {
    "repo": "repository",
    "person": "person",
    "notification": "notification",
    "invitation": "invitation",
    "runner": "runner",
    "package": "package",
    "codespace": "codespace",
    "environment": "environment",
    "deployment": "deployment",
    "pages": "pages_site",
    "advisory": "advisory",
    "key": "key",
    "webhook": "webhook",
    "deploy_key": "deploy_key",
    "autolink": "autolink",
    "sponsorship": "sponsorship",
    "sponsor_tier": "sponsor_tier",
    "wiki": "wiki",
    "resource": "resource",
    "issue": "issue",
    "pr": "pull_request",
    "label": "label",
    "gist": "gist",
    "discussion": "discussion",
    "discussion_section": "discussion_section",
    "discussion_category": "discussion_category",
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
    "template": "template",
    "watch": "watch",  # Watches (quill/ui/github_workbench_watches.py)
    # Across Repositories (quill/ui/github_workbench_across*.py).
    "across_item": "across_item",
    "across_status": "across_status",
    "repository_set": "repository_set",
    "by_name": "by_name",
    "fleet": "fleet",
}

#: My Work's sources, as Explore labels them, for each reason preset.
#: Review Requests holds both yours and your teams' (GH-R-143).
_REASONS: dict[str, tuple[tuple[str, ...], str]] = {
    "review_requested": (REVIEW_SOURCES, ""),
    "assigned": (("Assigned",), ""),
    "mentioned": (("Mentioned",), ""),
    "authored_pr": (("Authored",), "pr"),
    "authored_issue": (("Authored",), "issue"),
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


#: An Explore view's first page, as Explore always loaded it; Load More adds one.
EXPLORE_PAGE = 50


def _more_note(warning: str) -> str:
    """GitHub's "showing the first 50 items; more may exist", with what to do about it."""
    said = warning.rstrip(".") + "."
    if "more may exist" in warning:
        said += " Load More or Load All reads the rest."
    return said


def _matches_reason(row: ExploreRow, reason: str) -> bool:
    sources, kind = _REASONS.get(reason, ((), ""))
    first = row.detail.split("\n", 1)[0].split("; ")
    return any(source in first for source in sources) and (not kind or row.kind == kind)


_POLL_WAIT = (
    "GitHub asks apps to wait between checks; this is the list from the last check. "
    "Try again in {wait} seconds."
)


def _notification_rows(
    client: Any, include_read: bool, notes: list[str] | None
) -> list[ExploreRow] | None:
    """The last list while GitHub's X-Poll-Interval says not yet; None when a read may go."""
    wait = int(getattr(client, "notification_wait_seconds", lambda _r: 0)(include_read))
    if wait <= 0:
        return None
    if notes is not None:
        notes.append(_POLL_WAIT.format(wait=wait))
    if hasattr(client, "inbox_rules_note"):
        client.inbox_rules_note = ""  # the rules ran on the last read; not said twice
    return list(client.cached_notification_rows(include_read))


def _without_snoozed(
    client: Any, rows: list[ExploreRow], account: str, *, show: bool, notes: list[str] | None
) -> list[ExploreRow]:
    """Snooze for One Day hides a notification here; Include read shows it again, marked."""
    from quill.core.github.attention_queue import GitHubAttentionQueue
    from quill.ui.github_workbench_community import _queue_key

    try:
        state = GitHubAttentionQueue.load(account or client.account_login())
    except Exception:  # noqa: BLE001 - no login, no snoozes: the list as GitHub sent it
        return rows
    kept, hidden = [], 0
    for row in rows:
        key = _queue_key(row)
        if not state.is_snoozed(key):
            kept.append(row)
        elif show:
            until = state.snoozed[key][:16].replace("T", " ")
            detail = f"Snoozed here until {until} UTC.\n{row.detail}"
            kept.append(replace(row, detail=detail))
        else:
            hidden += 1
    if hidden and notes is not None:
        one = hidden == 1
        what = (
            "notification snoozed on this computer is"
            if one
            else "notifications snoozed on this computer are"
        )
        notes.append(
            f"{hidden} {what} hidden; turn on Include read notifications in Workbench "
            f"Options to show {'it' if one else 'them'}."
        )
    return kept


def load_explore(
    client: Any,
    node: NodeSpec,
    *,
    instance: str,
    query: Query,
    account: str = "",
    limit: int = 50,
    notes: list[str] | None = None,
) -> list[ExploreRow]:
    """Fetch an Explore node's rows. Runs off the UI thread.

    *limit* is the Workbench's page (Load More and Load All raise it); a view
    that stopped short, or has more than it loaded, says so into *notes*, so
    the status bar never passes off a first page as the whole list.
    """
    view = node.loader.removeprefix(EXPLORE_PREFIX)
    if view == "my_github":  # the front door: its own assembly (my_github.py)
        from quill.ui.github_workbench_my_github import load_my_github

        return load_my_github(client, account=account, limit=limit, notes=notes)
    repositories: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    if view == "attention":
        from quill.core.github.attention_queue import GitHubAttentionQueue

        state = GitHubAttentionQueue.load(account or client.account_login())
        repositories, categories = tuple(state.repositories), tuple(state.categories)
    include_read = False
    if view == "notifications":
        from quill.core.github.workbench_prefs import load_prefs

        include_read = load_prefs().include_read_notifications
        last = _notification_rows(client, include_read, notes)
        if last is not None:
            return _without_snoozed(client, last, account, show=include_read, notes=notes)
    result = client.fetch_with_status(
        view,
        repo=instance if node.scope in (Scope.REPOSITORY, Scope.ORGANIZATION) else "",
        person=instance if node.scope is Scope.PERSON else "",
        query=(
            instance  # a saved search pinned as a node: its name is its query (GH-R-053)
            if dict(node.preset).get("search") == "instance"
            else render(query)
            if node.scope is Scope.QUERY
            else ""
        ),
        repositories=repositories,
        categories=categories,
        limit=limit,
        include_read=include_read,
    )
    warning = str(getattr(result, "warning", "") or "")
    if notes is not None and warning:
        notes.append(_more_note(warning))
    rows = list(result.items)
    if view == "notifications":
        return _without_snoozed(client, rows, account, show=include_read, notes=notes)
    reason = dict(node.preset).get("reason", "")
    return [row for row in rows if _matches_reason(row, reason)] if reason else rows
