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
    # Collapse first, always. ``Expand`` on a node wx already considers
    # expanded fires no EVT_TREE_ITEM_EXPANDING at all -- and that event is
    # what reloads -- so the branch could be left holding nothing but the
    # "Loading..." row, or its old rows, depending on what wx did with the
    # expanded state when its children were deleted. Collapsing costs nothing
    # when it is already collapsed and makes the reload deterministic either
    # way.
    # BEFORE the expand, not after: wx fires EVT_TREE_ITEM_EXPANDING inside
    # ``Expand``, and the handler consumes the prefetched answer on its way
    # through -- an answer computed *before* the change. Forgetting it
    # afterwards is forgetting it one instruction too late, which is why a
    # branch could reload straight back to the list it had (a deleted row
    # still on screen, an added row still missing, reported 2026-08-23).
    forget_prefetch(host, str(data.get("node_id") or ""))
    tree.Collapse(node)
    tree.Expand(node)  # triggers _on_expanding, which reloads


def forget_prefetch(host: Any, node_id: str) -> None:
    """Drop any prefetched answer for *node_id*. Never raises."""
    cache = getattr(host, "_prefetch_cache", None)
    if isinstance(cache, dict):
        cache.pop(node_id, None)


def forget_load(host: Any, node: Any) -> None:
    """Let a branch be fetched again next time it is opened.

    ``loaded`` is set *before* the fetch, so without this a branch that
    failed could never be retried by closing and reopening it -- the one
    gesture anybody would try. (Moved here from the dialog: this module owns
    the loaded-flag dance.)
    """
    data = host._node_data(node)
    if data is not None:
        data["loaded"] = False


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


def reload_source_branch(host: Any, node_id: str, *, select: str = "") -> None:
    """Re-fetch one top-level source by id, wherever it sits in the tree.

    By id rather than by position, because the caller is an action that knows
    which source it changed and nothing about where that source is on screen.

    *select* is the node id of a row to put the cursor on once the branch has
    reloaded -- the row that was just added. The reload is asynchronous, so it
    is remembered and applied by :func:`apply_pending_select` when the rows
    arrive. "Added it, now where is it?" should not be a question.
    """
    if select:
        host._pending_select = select
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


def reload_open_browse(host: Any, node_id: str) -> bool:
    """Reload one branch of the Browse Stations window, from outside it.

    **Station > Add YouTube Link...** adds a row to a window it is not in, and
    the window it added to went on showing the list from before ("when adding a
    url for a video I have to manually refresh the treeview", 2026-08-23). The
    frame keeps the open dialog so the two can talk; a closed window, or a
    build with no such window, answers False and nothing happens.
    """
    dialog = getattr(host, "_radio_browse_dialog", None)
    reload_source = getattr(dialog, "_reload_source_branch", None)
    if dialog is None or not callable(reload_source):
        return False
    try:
        if not dialog._tree:  # the window has closed
            return False
        reload_source(node_id)
    except Exception:  # noqa: BLE001 - a courtesy refresh never breaks the add
        return False
    return True


def apply_pending_select(host: Any, node: Any) -> bool:
    """Land the cursor on the row a reload was asked to reveal. True when done.

    Called as each level's rows arrive. One-shot: finding the row clears the
    request, and a reload that never produces it simply leaves the cursor where
    the listener had it, which is the safe failure.
    """
    wanted = str(getattr(host, "_pending_select", "") or "")
    if not wanted:
        return False
    tree = host._tree
    child, cookie = tree.GetFirstChild(node)
    while child is not None and child.IsOk():
        data = host._node_data(child) or {}
        if str(data.get("node_id") or "") == wanted:
            host._pending_select = ""
            tree.SelectItem(child)
            tree.EnsureVisible(child)
            tree.SetFocus()
            return True
        child, cookie = tree.GetNextChild(node, cookie)
    return False
