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


# --- never crowding out the listener (2026-10-03) ----------------------------------


class _Later:
    """wx.CallLater, held instead of run, so a test decides when time passes."""

    made: list[_Later] = []

    def __init__(self, _ms: int, fn: Any, *args: Any) -> None:
        self.fn, self.args, self.stopped = fn, args, False
        _Later.made.append(self)

    def Stop(self) -> None:  # noqa: N802
        self.stopped = True

    def fire(self) -> None:
        if not self.stopped:
            self.fn(*self.args)


class _WxHost(_Host):
    def __init__(self) -> None:
        super().__init__()
        self._wx = type("wx", (), {"CallLater": _Later})
        self.selected: dict | None = None

    def _selected_data(self) -> dict | None:
        return self.selected


def test_arrowing_past_folders_fetches_nothing_until_the_cursor_rests() -> None:
    """Arrowing down Top Podcasts used to fetch every show's feed it crossed."""
    _Later.made.clear()
    host = _WxHost()
    for n in range(5):
        host.selected = {"node_id": f"appleshow:{n}", "loaded": False}
        browse_prefetch.note_selected(host, host.selected)
    assert host.fetched == []
    assert [t.stopped for t in _Later.made] == [True, True, True, True, False]
    for timer in _Later.made:
        timer.fire()
    assert host.fetched == ["appleshow:4"], "only where the cursor stopped"


def test_a_rest_on_a_folder_the_cursor_has_left_fetches_nothing() -> None:
    _Later.made.clear()
    host = _WxHost()
    host.selected = {"node_id": "appleshow:1", "loaded": False}
    browse_prefetch.note_selected(host, host.selected)
    host.selected = {"node_id": "x", "station": object()}  # moved onto a station
    browse_prefetch.note_selected(host, host.selected)
    _Later.made[0].fn(*_Later.made[0].args)  # the stale timer fires anyway
    assert host.fetched == []


def test_no_more_than_two_prefetches_run_at_once() -> None:
    host = _Host()
    host._task_manager = type("Held", (), {"submit": lambda *a, **k: None})()
    browse_prefetch.read_ahead(host, [f"xiph:{n}" for n in range(6)])
    assert len(host._prefetch_inflight) == browse_prefetch.MAX_INFLIGHT


def test_read_ahead_skips_podcast_shows() -> None:
    """Each show's children are a whole feed download; read-ahead is for folders."""
    host = _Host()
    browse_prefetch.read_ahead(host, ["appleshow:1", "pishow:https://f", "applegenre:us\t1487"])
    assert host.fetched == ["applegenre:us\t1487"]
