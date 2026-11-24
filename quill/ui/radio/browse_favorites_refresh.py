"""Browse Stations' Favorites branch, refreshed while somebody stands in it (FUX-06).

A favorite added or removed -- here, in Find Stations, in the main window --
rebuilds the branch so the change shows at once. The rebuild deletes the
branch's rows, the reader's among them, so it used to leave them on the
Favorites folder, and then said "N items." over the "Added X to Favorites."
that had just been said. Now the reader goes back to their own station, or
when it is the one that went, to the station that moved into its place, and
the refresh itself says nothing.
"""

from __future__ import annotations

from typing import Any

from quill.core.list_follow import land

__all__ = ["refresh"]


def _rows(tree: Any, node: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    child, cookie = tree.GetFirstChild(node)
    while child.IsOk():
        data = tree.GetItemData(child)
        key = str(data.get("node_id") or data.get("label") or "") if isinstance(data, dict) else ""
        rows.append((key, child))
        child, cookie = tree.GetNextChild(node, cookie)
    return rows


def refresh(dialog: Any) -> None:
    """Rebuild the loaded Favorites branch, keeping the reader on their row."""
    node = getattr(dialog, "_favorites_root", None)
    if node is None:
        return
    data = dialog._node_data(node)
    if not data or not data.get("loaded"):
        return
    tree = dialog._tree
    selection = tree.GetSelection()
    before = _rows(tree, node)
    keys = [key for key, _item in before]
    previous = next((i for i, (_k, item) in enumerate(before) if item == selection), -1)
    wanted = keys[previous] if previous >= 0 else None
    dialog._add_favorites(node, select=False)
    if wanted is None:
        return  # the reader was elsewhere in the tree, which was not touched
    after = _rows(tree, node)
    landing = land([key for key, _item in after], wanted, previous)
    if landing.index >= 0:
        tree.SelectItem(after[landing.index][1])
