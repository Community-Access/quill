"""Keep Manager filing and selection anchored to the selected folder placement."""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.folder_membership import placements
from quill.core.podcasts.sorting import sort_shows
from quill.ui.podcasts.manager_lookups import item_key


def source_folder(dialog: Any, show: Any) -> str | None:
    tree = getattr(dialog, "_tree", None)
    if tree is None:
        return show.folder_id
    selected = tree.GetSelection()
    if not selected.IsOk():
        return show.folder_id
    if dialog._tree_item_show.get(item_key(selected)) != show.id:
        return show.folder_id
    parent = tree.GetItemParent(selected)
    return dialog._tree_item_folder.get(item_key(parent)) if parent.IsOk() else None


def neighbor_anchor(dialog: Any, show_id: str) -> tuple[Any, ...] | None:
    show = dialog._library.find_show(show_id)
    if show is None:
        return None
    folder_id = source_folder(dialog, show)
    siblings = sort_shows(
        [item for item in dialog._library.shows if folder_id in placements(dialog._library, item)],
        dialog._selected_show_sort_mode(),
    )
    ids = [item.id for item in siblings]
    if show_id in ids:
        index = ids.index(show_id)
        for candidate in (index + 1, index - 1):
            if 0 <= candidate < len(ids) and ids[candidate] != show_id:
                return ("show", ids[candidate], folder_id)
    return ("folder", folder_id) if folder_id else None


def restore_anchor(dialog: Any, anchor: tuple[Any, ...] | None) -> None:
    if anchor is None:
        return
    kind, target_id = anchor[:2]
    mapping = dialog._tree_item_show if kind == "show" else dialog._tree_item_folder
    tree = dialog._tree
    stack = [tree.GetRootItem()]
    while stack:
        current = stack.pop()
        if mapping.get(item_key(current)) == target_id:
            parent = tree.GetItemParent(current)
            folder_id = dialog._tree_item_folder.get(item_key(parent)) if parent.IsOk() else None
            if kind != "show" or len(anchor) == 2 or folder_id == anchor[2]:
                tree.SelectItem(current)
                return
        child, cookie = tree.GetFirstChild(current)
        while child.IsOk():
            stack.append(child)
            child, cookie = tree.GetNextChild(current, cookie)
