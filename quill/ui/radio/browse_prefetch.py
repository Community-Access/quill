"""Predictive prefetch: the browse tree loads what you are about to open.

Expansion has always been async, so the window never froze -- but every cold
expand still cost a network round trip *while you waited on the folder*. The
fix is to spend that round trip before you ask:

- **Highlight-ahead**: landing on a collapsed, unloaded folder starts its
  fetch immediately, in the background. By the time Right-arrow or Enter
  lands, the answer is usually already here and the folder opens instantly.
- **Read-ahead**: when a folder's children arrive, the first few child
  folders are fetched too -- walking downward stays ahead of you.

Both are driven by where the listener actually is, never by a startup sweep:
a hidden source is still never contacted, Safe Mode still fetches nothing,
and sources the listener never visits are never touched. Results live in a
small per-dialog cache (newest 64 folders), consumed once on expand; the
sources' own caches (and the station catalog) do the durable caching.

Host-taking functions like ``browse_find`` and ``browse_refresh`` (GATE-11).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import browse_sources

#: How many just-arrived child folders to read ahead, and the cache cap.
READ_AHEAD_FOLDERS = 6
CACHE_CAP = 64


def _state(host: Any) -> tuple[dict[str, list], set[str]]:
    cache = getattr(host, "_prefetch_cache", None)
    if cache is None:
        cache = host._prefetch_cache = {}
        host._prefetch_inflight = set()
    return cache, host._prefetch_inflight


def _should_fetch(host: Any, node_id: str) -> bool:
    if getattr(host, "_task_manager", None) is None:
        return False  # partially built host (tests construct via __new__)
    if not node_id or node_id == "favorites":
        return False  # favorites are local and instant already
    if getattr(host, "_safe_mode", False) and browse_sources.needs_network(node_id):
        return False
    cache, inflight = _state(host)
    return node_id not in cache and node_id not in inflight


def _submit(host: Any, node_id: str) -> None:
    cache, inflight = _state(host)
    inflight.add(node_id)

    def _work(**_kwargs: Any) -> list:
        return host._fetch_children(node_id)

    def _done(_op: str, children: object) -> None:
        inflight.discard(node_id)
        if not isinstance(children, list) or not children:
            return  # a miss just means the expand fetches normally
        cache[node_id] = children
        while len(cache) > CACHE_CAP:
            cache.pop(next(iter(cache)))

    def _failed(_op: str, _error: BaseException) -> None:
        inflight.discard(node_id)

    host._task_manager.submit("radio-browse-prefetch", _work, on_success=_done, on_failure=_failed)


def note_selected(host: Any, data: dict | None) -> None:
    """The cursor landed on a folder: start its fetch now, quietly."""
    if data is None or not host._is_folder_data(data) or data.get("loaded"):
        return
    node_id = str(data.get("node_id") or "")
    if _should_fetch(host, node_id):
        _submit(host, node_id)


def read_ahead(host: Any, node_id_labels: list[str]) -> None:
    """Children just arrived: fetch the first few child folders too."""
    for child_id in node_id_labels[:READ_AHEAD_FOLDERS]:
        if _should_fetch(host, child_id):
            _submit(host, child_id)


def take(host: Any, node_id: str) -> list | None:
    """The prefetched children for *node_id*, consumed -- or ``None``."""
    cache, _inflight = _state(host)
    return cache.pop(node_id, None)
