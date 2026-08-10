"""Browse position memory for the Radio station tree.

Remembers which top-level source you were last in, so reopening Browse Stations
lands there instead of collapsed at the top. Session-scoped (a module-level
value that survives across dialog reopens within one run). Kept out of
``browse_tree_dialog`` so that module stays under the GATE-11 size budget; the wx
tree and item handles are passed in, so this holds no widgets itself.
"""

from __future__ import annotations

from typing import Any

#: The text of the top-level source last selected, or ``None`` before any browse.
_last_top_source: str | None = None


def remember(tree: Any, node: Any) -> None:
    """Record which top-level source *node* sits under (its child-of-root
    ancestor), so the next open can return there."""
    global _last_top_source
    if not node or not node.IsOk():
        return
    root = tree.GetRootItem()
    parent = tree.GetItemParent(node)
    while parent.IsOk() and parent != root:
        node = parent
        parent = tree.GetItemParent(node)
    if node.IsOk() and tree.GetItemParent(node) == root:
        _last_top_source = tree.GetItemText(node)


def restore_selection(tree: Any, root: Any) -> None:
    """Select the last-visited top-level source after the tree is (re)built,
    falling back to the first source when nothing is remembered or it is gone."""
    target = None
    if _last_top_source:
        child, cookie = tree.GetFirstChild(root)
        while child.IsOk():
            if tree.GetItemText(child) == _last_top_source:
                target = child
                break
            child, cookie = tree.GetNextChild(root, cookie)
    if target is None:
        target, _cookie = tree.GetFirstChild(root)
    if target.IsOk():
        tree.SelectItem(target)
