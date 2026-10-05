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

**Prefetch must never crowd out the listener (2026-10-03).** Arrowing down
Apple's Top Podcasts used to start a background fetch on every row the cursor
crossed -- and a show's fetch is its whole RSS feed, downloaded and parsed. A
screen-reader user arrowing through a hundred shows queued dozens of them on
the four shared workers; the folder they actually opened waited behind the
queue, and the parsing competed with the window for the interpreter, which is
the "hangs a bit with the screen reader" that was reported. So: highlight-ahead
waits until the cursor rests (:data:`HIGHLIGHT_REST_MS`), at most
:data:`MAX_INFLIGHT` prefetches run at once, and read-ahead skips podcast shows,
whose children are a feed download each.

Host-taking functions like ``browse_find`` and ``browse_refresh`` (GATE-11).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import browse_sources

#: How many just-arrived child folders to read ahead, and the cache cap.
READ_AHEAD_FOLDERS = 6
CACHE_CAP = 64

#: At most this many prefetches in flight. The task manager has four workers
#: shared with everything else in the app; the folder the listener actually
#: opens must always find one free.
MAX_INFLIGHT = 2

#: How long the cursor must rest on a folder before highlight-ahead fetches
#: it. Long enough that arrowing past a row costs nothing; short enough that a
#: listener who stops to listen has the answer before pressing Right.
HIGHLIGHT_REST_MS = 400


def _expensive(node_id: str) -> bool:
    """A podcast show: opening it downloads and parses its whole feed."""
    from quill.core.radio.browse_nodes import split_id
    from quill.core.radio.row_actions import PODCAST_SHOW_KINDS

    return split_id(node_id)[0] in PODCAST_SHOW_KINDS


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
    if len(inflight) >= MAX_INFLIGHT:
        return False  # the expand will fetch it itself, at the front of the queue
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
    """The cursor landed on a folder: fetch it once the cursor rests there."""
    pending = getattr(host, "_prefetch_rest", None)
    if pending is not None:
        try:
            pending.Stop()
        except Exception:  # noqa: BLE001 - a timer from a torn-down window
            pass
        host._prefetch_rest = None
    if data is None or not host._is_folder_data(data) or data.get("loaded"):
        return
    node_id = str(data.get("node_id") or "")
    if not _should_fetch(host, node_id):
        return
    wx = getattr(host, "_wx", None)
    if wx is None:
        _submit(host, node_id)  # no event loop to wait on (tests, headless)
        return
    host._prefetch_rest = wx.CallLater(HIGHLIGHT_REST_MS, _rested, host, node_id)


def _rested(host: Any, node_id: str) -> None:
    """The cursor stayed: fetch, if it is still on that folder and still unloaded."""
    host._prefetch_rest = None
    try:
        data = host._selected_data()
    except Exception:  # noqa: BLE001 - the window closed while we waited
        return
    if not data or str(data.get("node_id") or "") != node_id or data.get("loaded"):
        return
    if _should_fetch(host, node_id):
        _submit(host, node_id)


def read_ahead(host: Any, node_id_labels: list[str]) -> None:
    """Children just arrived: fetch the first few child folders too."""
    for child_id in node_id_labels[:READ_AHEAD_FOLDERS]:
        if _expensive(child_id):
            continue
        if _should_fetch(host, child_id):
            _submit(host, child_id)


def take(host: Any, node_id: str) -> list | None:
    """The prefetched children for *node_id*, consumed -- or ``None``."""
    cache, _inflight = _state(host)
    return cache.pop(node_id, None)
