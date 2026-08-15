"""Making a branch of the browse tree fetch itself again.

Two operations that look different and are the same thing: **Refresh**, which
re-reads whatever the listener is standing on, and the reload an action triggers
after it changes what a branch contains -- adding a server, say, where leaving
the old list on screen reads as the add having failed.

Extracted from ``browse_tree_dialog`` under GATE-11 (extract, never rebaseline),
and it earns its own module for a second reason: both operations do the same
delicate three-step dance -- mark the node unloaded, delete its children, put the
placeholder back and expand, which re-enters ``_on_expanding`` and refetches --
and two hand-copied versions of that would drift.
"""

from __future__ import annotations

from typing import Any

#: What a not-yet-loaded branch holds so wx gives it an expander arrow. A
#: deliberate copy of ``browse_tree_dialog._PLACEHOLDER`` (importing it would
#: pull the wx dialog module in just for a dict); the shape must stay in step.
_PLACEHOLDER = {"kind": "placeholder"}


def _refetch(host: Any, node: Any, data: dict) -> None:
    """Empty *node* and let the expand handler fill it in again."""
    tree = host._tree
    data["loaded"] = False
    tree.DeleteChildren(node)
    tree.SetItemData(tree.AppendItem(node, "Loading..."), dict(_PLACEHOLDER))
    tree.Expand(node)  # triggers _on_expanding, which reloads


def refresh_selected(host: Any) -> None:
    """Re-fetch the highlighted node's source, or its nearest parent source.

    Refreshing while standing on a *station* refreshes the folder that station
    is in, which is what somebody pressing Refresh on a stale row means.
    """
    tree = host._tree
    node = tree.GetSelection()
    data = host._node_data(node)
    while data is not None and not host._is_folder_data(data):
        node = tree.GetItemParent(node)
        data = host._node_data(node)
    if data is None:
        return
    if str(data.get("node_id")) == "favorites":
        host._add_favorites(node)  # local rebuild, no network
        return
    _refetch(host, node, data)


def reload_source_branch(host: Any, node_id: str) -> None:
    """Re-fetch one top-level source by id, wherever it sits in the tree.

    By id rather than by position, because the caller is an action that knows
    which source it changed and nothing about where that source is on screen.
    """
    tree = host._tree
    if not tree:
        return
    root = tree.GetRootItem()
    node, cookie = tree.GetFirstChild(root)
    while node is not None and node.IsOk():
        data = host._node_data(node)
        if data is not None and str(data.get("node_id", "")) == node_id:
            _refetch(host, node, data)
            return
        node, cookie = tree.GetNextChild(root, cookie)
