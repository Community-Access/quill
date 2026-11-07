"""Wave 4's Explore views, and the conditional read behind Explore's REST views.

Code, commit and repository search; Insights; the community profile;
Actions caches; and secret and variable names. :func:`fetch_extra_view`
answers ``None`` for any other view, so the client's existing routing is
untouched. Kept apart from ``explore.py`` (GATE-11).

:func:`explore_api_get` is the Pages view's read, now conditional: it sends
the last ETag and a 304 hands back the stored body. :func:`explore_failure`
turns any failure into one sentence -- a secondary rate limit becomes "GitHub
asked QUILL to wait 60 seconds." rather than a stack of per-call errors.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.auth_diagnostics import github_exception_hint
from quill.core.github.conditional_requests import conditional_get
from quill.core.github.explore_models import ExploreRow, GitHubExploreError
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rate_limits import is_wait_message
from quill.core.github.repo_actions import GitHubRepoActions
from quill.core.github.repo_insights import fetch_community_profile, fetch_insights
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.search_views import SEARCH_VIEWS, run_search

EXTRA_REPO_VIEWS = frozenset({"insights", "community", "actions_caches", "secrets"})
EXTRA_VIEWS = SEARCH_VIEWS | EXTRA_REPO_VIEWS
_REDIRECTS = (301, 302, 303, 307, 308)


def fetch_extra_view(
    provider: Any,
    view: str,
    *,
    repo: str,
    query: str,
    limit: int,
    warnings: list[str],
) -> list[ExploreRow] | None:
    """Rows for a Wave 4 view, or ``None`` when *view* is not one of them."""
    if view not in EXTRA_VIEWS:
        return None
    token = getattr(provider, "token", None)
    if view in SEARCH_VIEWS:
        return run_search(token, view, query, limit=limit, warnings=warnings)
    if not repo or "/" not in repo:
        raise GitHubExploreError("Enter a repository as owner/repo for this view.")
    try:
        if view == "insights":
            return fetch_insights(token, repo, limit=limit, warnings=warnings)
        if view == "community":
            return fetch_community_profile(token, repo)
        actions = GitHubRepoActions(token)
        if view == "actions_caches":
            return actions.list_caches(repo, limit=limit, warnings=warnings)
        return actions.list_secret_names(repo, limit=limit, warnings=warnings)
    except GitHubItemsError as exc:
        raise GitHubExploreError(str(exc.args[0]) if exc.args else str(exc)) from exc


def collapse_waits(warnings: list[str]) -> list[str]:
    """One secondary-limit sentence in place of every warning it caused."""
    waits = [warning for warning in warnings if is_wait_message(warning.split(": ")[-1])]
    if not waits:
        return warnings
    return [waits[0].split(": ")[-1]] + [w for w in warnings if w not in waits]


def explore_failure(view: str, exc: Exception) -> str:
    """The sentence for a view that could not load."""
    text = str(exc.args[0]) if exc.args else str(exc)
    if is_wait_message(text):
        return text
    hint = github_exception_hint(exc)
    if hint and is_wait_message(hint):
        return hint
    return f"Could not load {view.replace('_', ' ')}: {exc}"


def _api_failure(path: str, exc: GitHubRestError) -> str:
    text = str(exc.args[0]) if exc.args else ""
    if is_wait_message(text):
        return text
    status = exc.status
    pages = path.endswith("/pages") or "/pages/" in path
    if status == 404 and path.endswith("/pages"):
        return "This repository has no GitHub Pages site."
    if status in _REDIRECTS:
        return (
            "GitHub redirected the Pages request; the authenticated request was not followed."
            if pages
            else "GitHub redirected the request; the authenticated request was not followed."
        )
    if status == 401:
        return "The GitHub token is invalid or expired. Sign in again."
    headers = exc.headers or {}
    if status == 429 or (status == 403 and headers.get("x-ratelimit-remaining") == "0"):
        retry_after = headers.get("retry-after")
        detail = f" Retry after {retry_after} seconds." if retry_after else ""
        return f"GitHub API rate limit reached.{detail}"
    if status == 403:
        return "GitHub denied this request. Check account and repository permissions."
    if status is None:
        return text or "Could not reach GitHub."
    what = "GitHub Pages request" if pages else "GitHub request"
    return f"{what} failed (HTTP {status})."


def explore_api_get(token: str | None, path: str, *, opener: Any = None) -> Any:
    """GET *path* with the last ETag; raise :class:`GitHubExploreError` in plain words."""
    try:
        return conditional_get(token, path, opener=opener).data
    except GitHubRestError as exc:
        raise GitHubExploreError(_api_failure(path, exc)) from exc


__all__ = [
    "EXTRA_REPO_VIEWS",
    "EXTRA_VIEWS",
    "collapse_waits",
    "explore_api_get",
    "explore_failure",
    "fetch_extra_view",
]
