"""The library and the Inbox, laid out the way the listener chose.

Pure plans -- a list of nodes for the library tree, a list of rows for the
Inbox -- built from the settings in :mod:`settings_defs_views`, so the window
only draws what it is given and every layout is testable without a window.

**Nothing is ever hidden by a layout.** Folders only still reaches every
podcast (inside its folder, or in "Podcasts in no folder"); Podcasts only
still lists every podcast; the Inbox's folder rows each open to exactly that
folder's Inbox episodes. Only "Leave out folders with nothing in them" omits
anything, and what it omits holds nothing.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "NO_FOLDER",
    "InboxRow",
    "Node",
    "inbox_rows",
    "iter_inbox_rows",
    "library_nodes",
    "setting",
    "set_setting",
    "sort_folders",
]

#: The id of the "Podcasts in no folder" group, in both the tree and the Inbox.
NO_FOLDER = "__none__"
NO_FOLDER_LABEL = "Podcasts in no folder"


def setting(library: Any, setting_id: str) -> Any:
    """The current value of one view setting (its default when never set)."""
    from quill.core.podcasts import settings_catalog
    from quill.core.podcasts.settings_resolver import value_of

    definition = settings_catalog.definition(setting_id)
    if definition is None:
        raise KeyError(setting_id)
    return value_of(library, definition)


def set_setting(library: Any, setting_id: str, value: object) -> bool:
    """Store one view setting as the shared default. True when it changed."""
    from quill.core.podcasts import settings_catalog
    from quill.core.podcasts.settings_resolver import set_value
    from quill.core.podcasts.settings_types import LEVEL_GLOBAL

    definition = settings_catalog.definition(setting_id)
    if definition is None or setting(library, setting_id) == value:
        return False
    return bool(set_value(library, definition, value, level=LEVEL_GLOBAL))


@dataclass(slots=True)
class Node:
    """One row of the library tree: a folder or a podcast, and what is in it."""

    kind: str  # "folder" | "show"
    id: str
    label: str
    children: list[Node] = field(default_factory=list)
    open: bool = False


def _show_counts(library: Any) -> dict[str, int]:
    from quill.core.podcasts.sorting import unheard_count

    return {show.id: unheard_count(show) for show in library.shows}


def _subtree_folder_ids(library: Any, folder_id: str) -> set[str]:
    found = {folder_id}
    changed = True
    while changed:
        changed = False
        for folder in library.folders:
            if folder.parent_folder_id in found and folder.id not in found:
                found.add(folder.id)
                changed = True
    return found


def _folder_totals(
    library: Any, shows: list[Any], unheard: dict[str, int]
) -> dict[str, tuple[int, int]]:
    """Folder id -> (podcasts, unheard episodes), over the whole subtree."""
    parents = {folder.id: folder.parent_folder_id for folder in library.folders}
    totals = {folder.id: (0, 0) for folder in library.folders}
    from quill.core.podcasts.folder_membership import placements

    for show in shows:
        seen: set[str] = set()
        for current in placements(library, show):
            while current is not None and current in parents and current not in seen:
                seen.add(current)
                podcasts, episodes = totals[current]
                totals[current] = (podcasts + 1, episodes + unheard.get(show.id, 0))
                current = parents[current]
    return totals


def sort_folders(
    library: Any, folders: list[Any], mode: str, totals: dict[str, tuple[int, int]]
) -> list[Any]:
    if mode == "name_az":
        return sorted(folders, key=lambda f: f.name.casefold())
    if mode == "name_za":
        return sorted(folders, key=lambda f: f.name.casefold(), reverse=True)
    if mode == "most_unheard":
        return sorted(folders, key=lambda f: (-totals.get(f.id, (0, 0))[1], f.name.casefold()))
    if mode == "most_podcasts":
        return sorted(folders, key=lambda f: (-totals.get(f.id, (0, 0))[0], f.name.casefold()))
    # My own order: Move Up / Move Down's sort_order, then library order.
    position = {f.id: index for index, f in enumerate(library.folders)}
    return sorted(folders, key=lambda f: (getattr(f, "sort_order", 0), position.get(f.id, 0)))


def _folder_label(name: str, podcasts: int, unheard: int, counts: str) -> str:
    parts: list[str] = []
    if counts in ("podcasts", "both") and podcasts:
        parts.append(f"{podcasts} podcast{'' if podcasts == 1 else 's'}")
    if counts in ("unheard", "both") and unheard:
        parts.append(f"{unheard} unheard")
    return f"{name} ({', '.join(parts)})" if parts else name


def _show_label(show: Any, unheard: int, counts: str) -> str:
    if counts in ("unheard", "both"):
        return f"{show.title} ({unheard} unheard)"
    return str(show.title)


def library_nodes(
    library: Any, shows: list[Any], *, unheard: dict[str, int] | None = None
) -> list[Node]:
    """The library tree for *shows* (already filtered and sorted), as chosen."""
    layout = str(setting(library, "library_layout"))
    counts = str(setting(library, "library_counts"))
    opened = str(setting(library, "library_folders_open")) == "open"
    hide_empty = bool(setting(library, "library_hide_empty_folders"))
    folder_mode = str(setting(library, "folder_sort_mode"))
    if unheard is None:
        unheard = _show_counts(library)
    totals = _folder_totals(library, shows, unheard)

    def show_node(show: Any) -> Node:
        return Node("show", show.id, _show_label(show, unheard.get(show.id, 0), counts))

    if layout == "podcasts_only":
        return [show_node(show) for show in shows]

    known = {folder.id for folder in library.folders}
    from quill.core.podcasts.folder_membership import placements

    children_by_parent: dict[str | None, list[Any]] = {}
    for folder in library.folders:
        children_by_parent.setdefault(folder.parent_folder_id or None, []).append(folder)
    members_by_folder: dict[str, list[Any]] = {folder_id: [] for folder_id in known}
    loose_shows: list[Any] = []
    for show in shows:
        is_loose = False
        for folder_id in placements(library, show):
            if folder_id is not None and folder_id in known:
                members_by_folder[folder_id].append(show)
            else:
                is_loose = True
        if is_loose:
            loose_shows.append(show)

    def folder_nodes(parent: str | None) -> list[Node]:
        children = children_by_parent.get(parent, [])
        nodes: list[Node] = []
        for folder in sort_folders(library, children, folder_mode, totals):
            podcasts, heard = totals.get(folder.id, (0, 0))
            if hide_empty and not podcasts:
                continue
            node = Node(
                "folder",
                folder.id,
                _folder_label(folder.name, podcasts, heard, counts),
                open=opened,
            )
            sub = folder_nodes(folder.id)
            members = [show_node(s) for s in members_by_folder[folder.id]]
            node.children = _arrange(sub, members, layout)
            nodes.append(node)
        return nodes

    top_folders = folder_nodes(None)
    loose = [show_node(show) for show in loose_shows]
    if layout == "folders_only":
        if loose:
            podcasts = len(loose)
            heard = sum(unheard.get(node.id, 0) for node in loose)
            top_folders.append(
                Node(
                    "folder",
                    NO_FOLDER,
                    _folder_label(NO_FOLDER_LABEL, podcasts, heard, counts),
                    children=loose,
                    open=False,
                )
            )
        for node in top_folders:
            node.open = False  # folders only: the top level is the point
        return top_folders
    return _arrange(top_folders, loose, layout)


def _arrange(folders: list[Node], shows: list[Node], layout: str) -> list[Node]:
    if layout == "mixed":
        return sorted([*folders, *shows], key=lambda node: node.label.casefold())
    return [*folders, *shows]


@dataclass(slots=True)
class InboxRow:
    """One Inbox row: a folder (Enter opens it) or an episode."""

    kind: str  # "inbox_folder" | "episode"
    folder_id: str = ""
    label: str = ""
    pair: tuple[Any, Any] | None = None


def _top_folder(library: Any, folder_id: str | None) -> str | None:
    """The top-level folder a show's folder sits in (the Inbox groups by these)."""
    seen: set[str] = set()
    current = library.find_folder(folder_id) if folder_id else None
    while current is not None and current.parent_folder_id and current.id not in seen:
        seen.add(current.id)
        parent = library.find_folder(current.parent_folder_id)
        if parent is None:
            break
        current = parent
    return current.id if current is not None else None


def inbox_rows(library: Any, pairs: list[tuple[Any, Any]]) -> list[InboxRow]:
    """The Inbox as chosen: one list, folders then loose episodes, or folders only."""
    return list(iter_inbox_rows(library, lambda: iter(pairs)))


def iter_inbox_rows(
    library: Any, pairs: Callable[[], Iterable[tuple[Any, Any]]]
) -> Iterator[InboxRow]:
    """Stream the same layout, revisiting detached pairs after counting folders."""
    layout = str(setting(library, "inbox_layout"))
    if layout == "episodes":
        for pair in pairs():
            yield InboxRow("episode", pair=pair)
        return
    groups: dict[str, int] = {}
    loose = 0
    for show, _episode in pairs():
        top = _top_folder(library, show.folder_id)
        if top is None:
            loose += 1
        else:
            groups[top] = groups.get(top, 0) + 1
    folders = [f for f in library.folders if f.id in groups]
    totals = {fid: (0, count) for fid, count in groups.items()}
    mode = str(setting(library, "folder_sort_mode"))
    for folder in sort_folders(library, folders, mode, totals):
        yield InboxRow(
            "inbox_folder",
            folder_id=folder.id,
            label=f"{folder.name}, folder, {groups[folder.id]} in the Inbox",
        )
    if layout == "folders_only":
        if loose:
            yield InboxRow(
                "inbox_folder",
                folder_id=NO_FOLDER,
                label=f"{NO_FOLDER_LABEL}, folder, {loose} in the Inbox",
            )
        return
    for pair in pairs():
        if _top_folder(library, pair[0].folder_id) is None:
            yield InboxRow("episode", pair=pair)


def inbox_folder_pairs(
    library: Any, pairs: list[tuple[Any, Any]], folder_id: str
) -> list[tuple[Any, Any]]:
    """The Inbox episodes one folder row opens to."""
    return list(iter_inbox_folder_pairs(library, pairs, folder_id))


def iter_inbox_folder_pairs(
    library: Any, pairs: Iterable[tuple[Any, Any]], folder_id: str
) -> Iterator[tuple[Any, Any]]:
    wanted = None if folder_id == NO_FOLDER else folder_id
    for pair in pairs:
        if _top_folder(library, pair[0].folder_id) == wanted:
            yield pair
