"""Bounded, source-aware fetches for the GitHub personal attention queue."""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.core.github.attention_queue import QUEUE_CATEGORIES
from quill.core.github.explore_models import (
    ExploreRow,
    GitHubExploreError,
    _issue_row,
    _rows,
    _text,
)
from quill.core.github.fetch_results import GitHubFetchResult

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider


def account_login(provider: GitHubItemsProvider) -> str:
    """Return the signed-in login for account-scoped local queue state."""
    if not provider.is_authenticated:
        raise GitHubExploreError("Sign in to GitHub for this account view.")
    user = provider._gh.get_user()  # noqa: SLF001
    login = _text(getattr(user, "login", "")).strip()
    if not login:
        raise GitHubExploreError("Could not determine the signed-in GitHub user.")
    return login


def fetch_attention_queue(
    provider: GitHubItemsProvider,
    *,
    repositories: tuple[str, ...] | list[str] = (),
    categories: tuple[str, ...] | list[str] = (),
    limit: int = 50,
) -> GitHubFetchResult[ExploreRow]:
    """Combine assignments, requested reviews, mentions, and failed-check PRs."""
    if not provider.is_authenticated:
        raise GitHubExploreError("Sign in to GitHub to load your attention queue.")
    limit = max(1, min(limit, 100))
    login = account_login(provider)
    selected_categories = [key for key, _label in QUEUE_CATEGORIES if key in categories]
    if not selected_categories:
        selected_categories = [key for key, _label in QUEUE_CATEGORIES]
    selected_repositories = list(
        dict.fromkeys(repo.strip() for repo in repositories if repo.strip())
    )
    if any("/" not in repository for repository in selected_repositories):
        raise GitHubExploreError("Queue repositories must use owner/repo format.")
    queries = {
        "assigned": ("Assigned", f"is:open assignee:{login}"),
        "review_requested": ("Review requested", f"is:open is:pr review-requested:{login}"),
        "mentioned": ("Mentioned", f"is:open mentions:{login}"),
        "failed_checks": ("Failed checks", "is:open is:pr status:failure"),
    }
    scopes: tuple[str | None, ...] = tuple(selected_repositories) or (None,)
    warnings: list[str] = []
    found: dict[str, ExploreRow] = {}
    for repository in scopes:
        for category in selected_categories:
            label, query = queries[category]
            scope = f" in {repository}" if repository else " across repositories"
            source = f"{label}{scope}"
            scoped_query = f"{query} repo:{repository}" if repository else query
            try:
                matches = provider._gh.search_issues(scoped_query)  # noqa: SLF001
            except Exception as exc:  # noqa: BLE001 - keep other queue sources available
                warnings.append(f"{source}: could not load results: {exc}")
                continue
            for raw in _rows(matches, limit, source=source, warnings=warnings):
                row = _issue_row(raw, label)
                key = (row.url or f"{row.repo}/{row.kind}/{row.key}").casefold()
                if key in found:
                    previous = found[key]
                    sources = list(dict.fromkeys((previous.detail.splitlines()[0], label)))
                    updated = max(previous.updated_at, row.updated_at)
                    found[key] = ExploreRow(
                        previous.label,
                        f"Also: {', '.join(sources)}\n{previous.label}\n"
                        f"Updated: {updated}\n{row.url}",
                        previous.url or row.url,
                        previous.repo or row.repo,
                        previous.kind or row.kind,
                        previous.key or row.key,
                        updated,
                        previous.title or row.title,
                    )
                else:
                    found[key] = row
    rows = sorted(
        found.values(),
        key=lambda row: (row.updated_at, row.repo.casefold(), row.key),
        reverse=True,
    )
    if len(rows) > limit:
        warnings.append(f"Attention queue: showing the first {limit} items; more may exist")
    return GitHubFetchResult(
        tuple(rows[:limit]), complete=not warnings, warning="; ".join(warnings)
    )


__all__ = ["account_login", "fetch_attention_queue"]
