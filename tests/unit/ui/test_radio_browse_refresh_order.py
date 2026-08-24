"""A reloaded branch must not answer from before the change.

The browse tree prefetches: landing on a folder starts its fetch so the expand
that usually follows is instant, and the answer waits in a per-window cache
until an expand consumes it. That cache is why "delete the last row and it is
still there", and "add a row and it is missing", both ended with the listener
pressing Refresh by hand -- the reload expanded the branch, the expand took the
prefetched answer, and the prefetched answer predated the edit.

The fix is one line of *ordering*: the cache is dropped before the expand,
because wx fires EVT_TREE_ITEM_EXPANDING inside ``Expand`` and the handler
consumes the entry on its way through.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import browse_refresh


class _Tree:
    """Records the order of the operations a refetch performs."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self.calls: list[str] = []

    def DeleteChildren(self, _node: Any) -> None:  # noqa: N802
        self.calls.append("delete")

    def AppendItem(self, _node: Any, _text: str) -> object:  # noqa: N802
        self.calls.append("placeholder")
        return object()

    def SetItemData(self, _node: Any, _data: dict) -> None:  # noqa: N802
        return None

    def Collapse(self, _node: Any) -> None:  # noqa: N802
        self.calls.append("collapse")

    def Expand(self, _node: Any) -> None:  # noqa: N802
        # wx fires the expanding event from inside Expand, and the handler
        # takes the prefetched answer. Modelled exactly, because the bug was
        # that the cache was cleared one instruction later than this.
        self.calls.append("expand")
        self._host.consumed = dict(self._host._prefetch_cache)


class _Host:
    def __init__(self) -> None:
        self._tree = _Tree(self)
        self._prefetch_cache = {"youtube": ["a stale row"]}
        self.consumed: dict = {}


def test_the_prefetched_answer_is_dropped_before_the_branch_reopens() -> None:
    host = _Host()

    browse_refresh._refetch(host, object(), {"node_id": "youtube", "loaded": True})

    # What the expand saw: nothing. Otherwise the branch reloads straight back
    # to the list it had before the row was added or deleted.
    assert host.consumed == {}
    assert host._prefetch_cache == {}


def test_the_branch_is_collapsed_first_so_the_expand_event_actually_fires() -> None:
    """``Expand`` on a node wx already considers expanded fires nothing at all."""
    host = _Host()

    browse_refresh._refetch(host, object(), {"node_id": "youtube", "loaded": True})

    assert host._tree.calls == ["delete", "placeholder", "collapse", "expand"]


def test_the_branch_is_marked_unloaded_so_the_handler_refetches() -> None:
    host = _Host()
    data = {"node_id": "youtube", "loaded": True}

    browse_refresh._refetch(host, object(), data)

    assert data["loaded"] is False


def test_forgetting_a_prefetch_survives_a_host_that_never_had_one() -> None:
    class _Bare:
        pass

    browse_refresh.forget_prefetch(_Bare(), "youtube")  # must not raise
