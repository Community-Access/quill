"""Is a Workbench list the same as last time? One conditional read says, for free.

The issue and pull request lists come through PyGithub, which cannot send
``If-None-Match``, and reading a pull request row's size makes PyGithub fetch
that pull request on its own, so an F5 on 30 pull requests can cost 31
requests. GH-R-131 asks for a conditional request on every repeated read.

:func:`rows_or_fetch` asks GitHub for the *same window* the list shows (the
same state, the same newest-first order, the same page size) with the ETag of
the last time. A 304 means that window is byte-for-byte the same, so the rows
already made from it are handed back and nothing else is read; a 304 does not
count against the rate limit. Anything else (a change, an error, a window
larger than one page) falls through to the real fetch, so the probe never
shows something stale: a list that changed costs one read more than before,
and one that did not costs none at all.

Rows are kept in memory, per account and list, never on disk. No ``wx``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.navigation_state import account_key_for_token

__all__ = ["PAGE_MAX", "VIEW_PATHS", "forget_lists", "probe_token", "rows_or_fetch", "view_rows"]

PAGE_MAX = 100
"""GitHub's largest page: a longer list cannot be probed in one read."""

_MAX_LISTS = 32

_KEPT: dict[str, tuple[str, tuple[Any, ...]]] = {}
_LOCK = threading.Lock()


def _key(token: str | None, path: str, query: dict[str, str]) -> str:
    return account_key_for_token(token) + " " + path + "?" + repr(sorted(query.items()))


def rows_or_fetch[T](
    token: str | None,
    path: str,
    query: dict[str, str],
    fetch: Callable[[], Sequence[T]],
    *,
    request: Callable[..., Any] | None = None,
) -> tuple[list[T], bool]:
    """The list's rows, and whether they were read again (False: GitHub said unchanged).

    *query* must describe exactly the window *fetch* shows, its ``per_page``
    included. *request* is :func:`~quill.core.github.rest_transport.request_json`
    unless a test passes its own.
    """
    if request is None:
        from quill.core.github.rest_transport import request_json

        send: Callable[..., Any] = request_json
    else:
        send = request
    page = int(query.get("per_page", "30") or 30)
    if not token or page > PAGE_MAX:
        return list(fetch()), True
    key = _key(token, path, query)
    with _LOCK:
        kept = _KEPT.get(key)
    headers = {"If-None-Match": kept[0]} if kept is not None else None
    try:
        probe = send(token, "GET", path, query=dict(query), extra_headers=headers)
    except Exception:  # noqa: BLE001 - the real fetch says what went wrong
        return list(fetch()), True
    if probe.status == 304 and kept is not None:
        return list(kept[1]), False
    rows = list(fetch())
    etag = probe.header("ETag")
    with _LOCK:
        if etag:
            _KEPT[key] = (etag, tuple(rows))
            while len(_KEPT) > _MAX_LISTS:
                del _KEPT[next(iter(_KEPT))]
        else:
            _KEPT.pop(key, None)
    return rows, True


def probe_token(items: object) -> str | None:
    """The token to probe with, from the real provider only.

    A test's fake provider has no GitHub behind it, so it is never probed.
    """
    from quill.core.github.items_provider import GitHubItemsProvider

    if not isinstance(items, GitHubItemsProvider):
        return None
    token = getattr(items, "token", None)
    return token if isinstance(token, str) else None


VIEW_PATHS = {
    "branches": "branches",
    "commits": "commits",
    "tags": "tags",
    "releases": "releases",
    "workflows": "actions/workflows",
    "runs": "actions/runs",
}
"""Each repository list view, and the endpoint whose first page is exactly what it shows."""


def view_rows[T](
    items: object, repo: str, view: str, limit: int, fetch: Callable[[], Sequence[T]]
) -> list[T]:
    """A repository list view's rows, read again only when GitHub says they changed."""
    path = VIEW_PATHS.get(view)
    if path is None:
        return list(fetch())
    window = {"per_page": str(limit)}
    return rows_or_fetch(probe_token(items), f"/repos/{repo}/{path}", window, fetch)[0]


def forget_lists() -> None:
    """Drop every remembered list (sign-out; tests)."""
    with _LOCK:
        _KEPT.clear()
