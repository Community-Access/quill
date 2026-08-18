"""After a subscription edit, refresh the tree and walk back to the row.

The verbs that edit the shared podcast library from the browse tree (Move to
Folder, Mark All as Played, folder rename/delete) used to end with *"Refresh
Podcasts to update."* -- an instruction to the listener to do the part the app
skipped. This module does that part: refetch the Subscriptions branch and,
because the reload is asynchronous and level-by-level, carry a one-shot
"pending reveal" that re-expands folders as their rows arrive until the moved
or edited row is found, then put the cursor on it. The unheard badges come
back right too, for free, because every reloaded level re-renders its labels
from the library.

Kept out of ``browse_tree_dialog`` (GATE-11): that module's only part is a
two-line call at the end of ``_add_children``.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import split_id

#: The Subscriptions subtree's node kinds -- the only levels a reveal walks.
_SUBSCRIPTION_LEVELS = frozenset({"mypodcasts", "mypodcastfolder"})


def _subscriptions_ancestor(dialog: Any) -> Any:
    """The Subscriptions node above the current selection, or ``None``.

    The verbs this serves all act on rows *inside* that subtree, so walking
    up from the selection is enough -- no whole-tree search.
    """
    tree = dialog._tree
    node = tree.GetSelection()
    while node is not None and node.IsOk():
        data = dialog._node_data(node) or {}
        kind, _args = split_id(str(data.get("node_id") or ""))
        if kind == "mypodcasts":
            return node
        node = tree.GetItemParent(node)
    return None


def refetch_subscriptions(dialog: Any) -> bool:
    """Reload the Subscriptions branch in place. True when it could."""
    node = _subscriptions_ancestor(dialog)
    if node is None:
        return False
    from quill.ui.radio import browse_refresh

    data = dialog._node_data(node)
    if data is None:
        return False
    browse_refresh._refetch(dialog, node, data)
    return True


def refetch_and_reveal(dialog: Any, *, feed_url: str = "", folder_id: str = "") -> bool:
    """Reload Subscriptions, then land the cursor on a show or folder.

    Exactly one of *feed_url* (reveal that show) or *folder_id* (reveal that
    folder) should be given. Returns False when the selection is not inside
    the Subscriptions subtree -- the caller falls back to the old spoken
    "Refresh Podcasts to update." so the truth is always told.
    """
    if not refetch_subscriptions(dialog):
        return False
    dialog._pending_reveal = {"feed_url": feed_url, "folder_id": folder_id}
    return True


def on_children_added(dialog: Any, node: Any) -> None:
    """Called by ``_add_children`` after *node*'s rows exist.

    While a reveal is pending: select the target if it is among the new rows;
    otherwise expand the level's folders (a local library read, no network)
    so the next load looks deeper. One-shot -- found clears it.
    """
    pending = getattr(dialog, "_pending_reveal", None)
    if not pending:
        return
    data = dialog._node_data(node) or {}
    node_kind, _args = split_id(str(data.get("node_id") or ""))
    if node_kind not in _SUBSCRIPTION_LEVELS:
        return
    target_kind = "mypodcastshow" if pending["feed_url"] else "mypodcastfolder"
    target_arg = pending["feed_url"] or pending["folder_id"]
    tree = dialog._tree
    folders = []
    child, cookie = tree.GetFirstChild(node)
    while child is not None and child.IsOk():
        child_data = dialog._node_data(child) or {}
        kind, args = split_id(str(child_data.get("node_id") or ""))
        if kind == target_kind and args and args[0] == target_arg:
            dialog._pending_reveal = None
            tree.SelectItem(child)
            tree.EnsureVisible(child)
            tree.SetFocus()
            return
        if kind == "mypodcastfolder":
            folders.append(child)
        child, cookie = tree.GetNextChild(node, cookie)
    for folder in folders:
        tree.Expand(folder)  # triggers that folder's own (local) load
