"""Predictive prefetch for the browse tree: fetch what the cursor is near.

Pinned: highlighting an unloaded folder fetches it in the background and the
expand consumes the cached answer; Safe Mode prefetches nothing that needs
the network; the cache is consumed once and bounded.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import folder
from quill.ui.radio import browse_prefetch


class _SyncTasks:
    def submit(self, _name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure("op", error)
        else:
            on_success("op", result)


class _Host:
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._safe_mode = safe_mode
        self._task_manager = _SyncTasks()
        self.fetched: list[str] = []

    def _is_folder_data(self, data: dict | None) -> bool:
        return bool(data) and "station" not in (data or {})

    def _fetch_children(self, node_id: str) -> list:
        self.fetched.append(node_id)
        return [folder(f"{node_id}-child", "Child")]


def test_highlighting_a_folder_prefetches_and_expand_consumes_it() -> None:
    host = _Host()
    browse_prefetch.note_selected(host, {"node_id": "tunein", "loaded": False})
    assert host.fetched == ["tunein"]
    ready = browse_prefetch.take(host, "tunein")
    assert ready is not None and ready[0].label == "Child"
    assert browse_prefetch.take(host, "tunein") is None  # consumed once
    # Re-selecting an already-consumed folder fetches it again next time.
    browse_prefetch.note_selected(host, {"node_id": "tunein", "loaded": False})
    assert host.fetched == ["tunein", "tunein"]


def test_a_loaded_folder_and_favorites_are_never_prefetched() -> None:
    host = _Host()
    browse_prefetch.note_selected(host, {"node_id": "tunein", "loaded": True})
    browse_prefetch.note_selected(host, {"node_id": "favorites", "loaded": False})
    browse_prefetch.note_selected(host, {"node_id": "x", "station": object()})
    assert host.fetched == []


def test_safe_mode_prefetches_nothing_that_needs_the_network() -> None:
    host = _Host(safe_mode=True)
    browse_prefetch.note_selected(host, {"node_id": "tunein", "loaded": False})
    assert host.fetched == []


def test_read_ahead_is_bounded() -> None:
    host = _Host()
    browse_prefetch.read_ahead(host, [f"n{i}" for i in range(20)])
    assert len(host.fetched) == browse_prefetch.READ_AHEAD_FOLDERS
