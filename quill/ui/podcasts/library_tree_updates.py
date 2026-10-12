"""Incremental labels and bounded native drawing for Cast's library tree."""

from __future__ import annotations

import copy
import logging
from time import perf_counter
from typing import Any

from quill.core.podcasts.library_view import NO_FOLDER, library_nodes, set_setting
from quill.core.podcasts.sorting import sort_episodes, sort_shows
from quill.ui.podcasts.library_snapshot import TURN_BUDGET_SECONDS

logger = logging.getLogger(__name__)


def _key(node: Any) -> tuple[str, str]:
    return (
        ("show", node.id)
        if node.kind == "show"
        else ("group", node.id)
        if node.id == NO_FOLDER
        else ("folder", node.id)
    )


def _shape(nodes: list[Any]) -> tuple[Any, ...]:
    return tuple(
        (
            _key(node),
            node.open,
            None if node.kind == "show" else _shape(node.children),
        )
        for node in nodes
    )


def row_key(host: Any, item: Any) -> tuple[Any, ...] | None:
    tree = host._shows_tree
    if not item.IsOk():
        return None
    data = tree.GetItemData(item)
    if not isinstance(data, tuple) or len(data) != 2:
        return None
    show_id = data[1].partition("\x00")[0] if data[0] == "episode" else data[1]
    if data[0] not in ("show", "episode") or not getattr(
        host._podcast_library, "show_folder_copies", {}
    ).get(show_id):
        return data
    parent = tree.GetItemParent(item)
    while parent.IsOk():
        parent_data = tree.GetItemData(parent)
        if isinstance(parent_data, tuple) and len(parent_data) == 2:
            if parent_data[0] == "folder":
                return (*data, parent_data[1])
            if parent_data[0] == "group":
                return (*data, None)
        parent = tree.GetItemParent(parent)
    return (*data, None)


def _selected(host: Any) -> tuple[Any, ...] | None:
    tree = host._shows_tree
    item = tree.GetSelection()
    return row_key(host, item)


def cancel_tree_update(host: Any) -> None:
    host._cast_tree_generation = int(getattr(host, "_cast_tree_generation", 0)) + 1
    later = getattr(host, "_cast_tree_later", None)
    if later is not None:
        later.Stop()
    host._cast_tree_later = None
    chunks = getattr(host, "_cast_tree_chunks", None)
    if chunks is not None:
        chunks.close()
        host._cast_tree_shape = None
    host._cast_tree_chunks = None
    host._cast_tree_anchor = None


def reload_tree(host: Any, *, keep_key: tuple[Any, ...] | None = None) -> None:
    if getattr(host, "_cast_closed", False) or getattr(host, "_cast_closing", False):
        return
    if host._library_find_active():
        host._refresh_library_find()
        return
    cursor_revision = int(getattr(host, "_cast_cursor_revision", 0))
    pending_anchor = getattr(host, "_cast_tree_anchor", None)
    cancel_tree_update(host)
    generation = host._cast_tree_generation
    tree = host._shows_tree
    selected = _selected(host)
    if pending_anchor is not None and pending_anchor[1] == cursor_revision:
        selected = pending_anchor[0]
    if keep_key is not None and (selected is None or selected[:2] != keep_key):
        selected = keep_key
    host._cast_tree_anchor = (selected, cursor_revision)
    frozen = False

    def write(method: Any, *args: Any) -> Any:
        nonlocal frozen
        if not frozen:
            tree.Freeze()
            frozen = True
        return method(*args)

    library = host._podcast_library
    shows = sort_shows(host._visible_library_shows(), library.settings.show_sort_mode)
    by_id = {show.id: show for show in shows}
    unheard = None
    large_library = host._podcast_library_is_large()
    if large_library:
        unheard = getattr(host, "_cast_unheard_counts", {})
        if not unheard:
            library = copy.copy(library)
            library.extra_settings = dict(library.extra_settings)
            set_setting(library, "library_counts", "none")
    nodes = library_nodes(library, shows, unheard=unheard)
    shape = _shape(nodes)
    items = getattr(host, "_cast_tree_items", {})
    labels = getattr(host, "_cast_tree_labels", {})
    same_structure = bool(items) and shape == getattr(host, "_cast_tree_shape", None)
    expanded = set()
    if selected is not None and selected[0] == "episode":
        expanded.add(("show", selected[1].partition("\x00")[0], *selected[2:]))

    def indexed_key(node: Any, parent_id: str | None) -> tuple[Any, ...]:
        key = _key(node)
        return (
            (*key, parent_id)
            if node.kind == "show" and getattr(library, "show_folder_copies", {}).get(node.id)
            else key
        )

    def update_labels(plan: list[Any], parent_id: str | None = None) -> Any:
        for node in plan:
            key = indexed_key(node, parent_id)
            item = items[key]
            if labels.get(key) != node.label:
                write(tree.SetItemText, item, node.label)
                labels[key] = node.label
            if node.kind == "show":
                show = by_id[node.id]
                first, _cookie = tree.GetFirstChild(item)
                if not show.episodes and first.IsOk():
                    remove_episode_keys(item)
                    write(tree.DeleteChildren, item)
                elif show.episodes and not first.IsOk():
                    placeholder = write(tree.AppendItem, item, "Loading episodes...")
                    tree.SetItemData(placeholder, ("placeholder", node.id))
                elif show.episodes and tree.IsExpanded(item):
                    yield from refresh_expanded_show(item, show)
            else:
                yield from update_labels(node.children, None if node.id == NO_FOLDER else node.id)
            yield

    def remove_episode_keys(item: Any) -> None:
        episode_items = getattr(host, "_cast_tree_episode_items", {})
        child, cookie = tree.GetFirstChild(item)
        while child.IsOk():
            episode_items.pop(row_key(host, child), None)
            child, cookie = tree.GetNextChild(item, cookie)

    def refresh_expanded_show(item: Any, show: Any) -> Any:
        limit = getattr(host, "_EPISODES_PER_SHOW_NODE", 200)
        ordered = sort_episodes(show.episodes, "newest_first", limit=limit)
        expected = [
            ("episode", f"{show.id}\x00{episode.guid}", episode.title) for episode in ordered
        ]
        hidden = len(show.episodes) - limit
        if hidden > 0:
            expected.append((
                "more",
                show.id,
                f"{hidden} older episode(s) -- open the Podcast Manager to see them",
            ))
        actual = []
        children = []
        child, cookie = tree.GetFirstChild(item)
        while child.IsOk():
            data = tree.GetItemData(child)
            actual.append((*data, tree.GetItemText(child)) if isinstance(data, tuple) else data)
            children.append((child, data))
            child, cookie = tree.GetNextChild(item, cookie)
        if actual == expected:
            return
        episode_items = getattr(host, "_cast_tree_episode_items", {})

        def delete_child(child: Any) -> None:
            key = row_key(host, child)
            if episode_items.get(key) == child:
                del episode_items[key]
            write(tree.Delete, child)

        wanted = {(kind, value) for kind, value, _label in expected}
        for child, data in children:
            if data not in wanted:
                delete_child(child)
                yield

        # Keep unchanged native rows: deleting the selected child moves the
        # screen-reader cursor to its parent, even if it is restored later.
        child, _cookie = tree.GetFirstChild(item)
        previous = None
        for kind, value, label in expected:
            key = (kind, value)
            if child.IsOk() and tree.GetItemData(child) == key:
                row = child
                child = tree.GetNextSibling(child)
                if tree.GetItemText(row) != label:
                    write(tree.SetItemText, row, label)
            else:
                row = (
                    write(tree.PrependItem, item, label)
                    if previous is None
                    else write(tree.InsertItem, item, previous, label)
                )
                tree.SetItemData(row, key)
            if kind == "episode":
                episode_items[row_key(host, row)] = row
            previous = row
            yield
        while child.IsOk():
            following = tree.GetNextSibling(child)
            delete_child(child)
            child = following
            yield

    old_keys = {}
    children_by_parent = getattr(host, "_cast_tree_children", {})
    host._cast_tree_children = children_by_parent

    def forget(item: Any) -> Any:
        child, cookie = tree.GetFirstChild(item)
        while child.IsOk():
            yield from forget(child)
            child, cookie = tree.GetNextChild(item, cookie)
        key = old_keys.get(int(item.GetID()), row_key(host, item))
        if items.get(key) == item:
            items.pop(key, None)
            labels.pop(key, None)
        episode_items = getattr(host, "_cast_tree_episode_items", {})
        episode_key = key
        if episode_items.get(episode_key) == item:
            episode_items.pop(episode_key, None)
        children_by_parent.pop(int(item.GetID()), None)
        yield

    def draw(parent: Any, plan: list[Any], parent_id: str | None = None) -> Any:
        wanted = {_key(node) for node in plan}
        parent_key = int(parent.GetID())
        existing = children_by_parent.get(parent_key)
        if existing is None:
            existing = []
            child, cookie = tree.GetFirstChild(parent)
            while child.IsOk():
                existing.append((tree.GetItemData(child), child))
                child, cookie = tree.GetNextChild(parent, cookie)
            children_by_parent[parent_key] = existing
        for data, child in tuple(existing):
            if data not in wanted:
                yield from forget(child)
                existing.remove((data, child))
                write(tree.Delete, child)
                yield
        position = 0
        previous = None
        for node in plan:
            key = indexed_key(node, parent_id)
            retained = position < len(existing) and existing[position][0] == key[:2]
            if retained:
                item = existing[position][1]
                old_key = old_keys.get(int(item.GetID()))
                if old_key != key and items.get(old_key) == item:
                    items.pop(old_key, None)
                    labels.pop(old_key, None)
                    episode_items = getattr(host, "_cast_tree_episode_items", {})
                    episode, cookie = tree.GetFirstChild(item)
                    while episode.IsOk():
                        data = tree.GetItemData(episode)
                        if isinstance(data, tuple) and data[0] == "episode":
                            episode_items.pop((*data, *old_key[2:]), None)
                            episode_items[(*data, *key[2:])] = episode
                        episode, cookie = tree.GetNextChild(item, cookie)
                        yield
                if labels.get(key) != node.label:
                    write(tree.SetItemText, item, node.label)
            else:
                item = (
                    write(tree.PrependItem, parent, node.label)
                    if previous is None
                    else write(tree.InsertItem, parent, previous, node.label)
                )
                tree.SetItemData(item, key[:2])
                existing.insert(position, (key[:2], item))
            items[key] = item
            labels[key] = node.label
            if node.kind == "show":
                show = by_id[node.id]
                first, _cookie = tree.GetFirstChild(item)
                if not show.episodes and first.IsOk():
                    remove_episode_keys(item)
                    write(tree.DeleteChildren, item)
                elif show.episodes and not first.IsOk():
                    placeholder = write(tree.AppendItem, item, "Loading episodes...")
                    tree.SetItemData(placeholder, ("placeholder", node.id))
                if retained and tree.IsExpanded(item):
                    yield from refresh_expanded_show(item, show)
                elif key in expanded:
                    yield from refresh_expanded_show(item, show)
                    write(tree.Expand, item)
            else:
                yield from draw(item, node.children, None if node.id == NO_FOLDER else node.id)
                if not retained and (node.open or key in expanded) and node.children:
                    write(tree.Expand, item)
            previous = item
            position += 1
            yield
        while len(existing) > position:
            _data, child = existing[position]
            yield from forget(child)
            existing.pop(position)
            write(tree.Delete, child)
            yield

    if same_structure:
        chunks = update_labels(nodes)
    else:
        root = tree.GetRootItem()
        if not root.IsOk():
            root = tree.AddRoot("Library")

        def reconcile() -> Any:
            # Move the cursor before removing its old placement, not after an
            # asynchronous redraw (which a counts publication may supersede).
            anchor = items.get(selected)
            if (
                anchor is not None
                and cursor_revision == int(getattr(host, "_cast_cursor_revision", 0))
                and tree.GetSelection() != anchor
            ):
                write(tree.SelectItem, anchor)
                yield
            for key, item in tuple(items.items()):
                old_keys[int(item.GetID())] = key
                if tree.IsExpanded(item):
                    expanded.add(key)
                yield
            for key, item in tuple(getattr(host, "_cast_tree_episode_items", {}).items()):
                old_keys[int(item.GetID())] = key
                yield
            yield from draw(root, nodes)
            if not library.shows and not library.folders:
                for key, label in (
                    ("add", "Add a Podcast by URL..."),
                    ("import", "Import Podcasts from OPML..."),
                    ("search", "Find a Podcast..."),
                ):
                    item = write(tree.AppendItem, root, label)
                    tree.SetItemData(item, ("action", key))
                    items[("action", key)] = item
                    labels[("action", key)] = label
                    children_by_parent[int(root.GetID())].append((("action", key), item))
                    yield

        chunks = reconcile()
    host._cast_tree_items = items
    host._cast_tree_labels = labels
    host._cast_tree_chunks = chunks

    def finish() -> None:
        host._cast_tree_chunks = None
        host._cast_tree_anchor = None
        host._cast_tree_shape = shape
        wanted = (
            _selected(host)
            if cursor_revision != int(getattr(host, "_cast_cursor_revision", 0))
            else selected
        )
        item = items.get(wanted) or getattr(host, "_cast_tree_episode_items", {}).get(wanted)
        if item is None and wanted is not None and wanted[0] == "episode":
            parent_key = ("show", wanted[1].partition("\x00")[0], *wanted[2:])
            item = items.get(parent_key)
        if item is None and wanted is not None and wanted[0] == "show":
            item = next((row for key, row in items.items() if key[:2] == wanted[:2]), None)
        if item is None and not tree.GetSelection().IsOk():
            item, _cookie = tree.GetFirstChild(tree.GetRootItem())
        if item is not None and item.IsOk() and tree.GetSelection() != item:
            host._cast_tree_mutating = True
            try:
                write(tree.SelectItem, item)
            finally:
                host._cast_tree_mutating = False

    def advance() -> None:
        nonlocal frozen
        host._cast_tree_later = None
        if (
            generation != host._cast_tree_generation
            or getattr(host, "_cast_closed", False)
            or getattr(host, "_cast_closing", False)
        ):
            return
        deadline = perf_counter() + TURN_BUDGET_SECONDS
        call_later = getattr(host._wx, "CallLater", None)
        host._cast_tree_mutating = True
        try:
            while True:
                try:
                    next(chunks)
                except StopIteration:
                    finish()
                    return
                if callable(call_later) and perf_counter() >= deadline:
                    host._cast_tree_later = call_later(1, advance)
                    return
        except Exception:
            host._cast_tree_chunks = None
            logger.exception("Could not update the Cast library tree")
            host._announce("Could not update the podcast list. Try opening Podcasts again.")
        finally:
            if frozen:
                tree.Thaw()
                frozen = False
            host._cast_tree_mutating = False

    call_later = getattr(host._wx, "CallLater", None)
    if large_library and callable(call_later):
        host._cast_tree_later = call_later(1, advance)
    else:
        advance()
