"""The Manage Favorites row menu -- station rows and folder rows.

Extracted from ``favorites_manager_dialog`` under GATE-11 when folder rows
gained actions of their own. The seam is a real one: this module is entirely
about *what a row offers*, and the dialog it came out of is about a tree that
refreshes in place without losing the cursor, which is the delicate part.

**A folder is a place you listen from.** Radio has had folders on favorites for
a long time and never had a single action on one, so filing forty stations into
"News" organised the list and did nothing for the listening. Play All, Shuffle
and Export close that. There is deliberately no folder-settings item: a station
has far fewer per-item settings than a podcast and there is nothing worth
batch-applying.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["entries_for", "popup"]


def _selected_folder(dialog: Any) -> str:
    selected = dialog._selected()
    return selected[1] if selected is not None and selected[0] == "folder" else ""


def _folder_host(dialog: Any) -> Any:
    """Where the folder queue lives, and what speaks.

    The app frame when there is one, because Next and Previous have to keep
    working after the window closes; the dialog itself otherwise, which is the
    embedded case where there is no frame to hand over to.
    """
    host = getattr(dialog, "_host", None)
    return host if host is not None else dialog


def _play_folder(dialog: Any, *, shuffle: bool) -> None:
    from quill.ui.radio import favorite_folder_actions

    folder = _selected_folder(dialog)
    if not folder:
        return
    favorite_folder_actions.play_folder(
        _folder_host(dialog),
        folder,
        store=dialog._store,
        controller=dialog._controller,
        shuffle=shuffle,
    )
    dialog._on_selection_changed()


def _export_folder(dialog: Any) -> None:
    from quill.ui.radio import favorite_folder_actions

    folder = _selected_folder(dialog)
    if not folder:
        return
    favorite_folder_actions.export_folder(_folder_host(dialog), folder, store=dialog._store)


def entries_for(dialog: Any) -> list[tuple[str, Callable[[], None]]]:
    """The menu for whatever is selected, or [] when nothing is."""
    selected = dialog._selected()
    if selected is None:
        return []
    if selected[0] == "station":
        entries: list[tuple[str, Callable[[], None]]] = [
            ("&Play", dialog._on_play),
            ("Rena&me Station...\tF2", dialog._on_rename_station),
            ("&Remove...\tDelete", dialog._on_remove),
            ("Move &Up", lambda: dialog._on_move(-1)),
            ("Move &Down", lambda: dialog._on_move(1)),
            ("&Mark for Move", dialog._on_mark),
            ("Move to F&older...", dialog._on_move_to_folder),
        ]
        if dialog._marked_key is not None:
            entries.insert(5, ("Move &Above", lambda: dialog._on_move_marked(True)))
            entries.insert(6, ("Move Be&low", lambda: dialog._on_move_marked(False)))
        return entries
    return [
        ("&Play All in Folder", lambda: _play_folder(dialog, shuffle=False)),
        ("&Shuffle Folder", lambda: _play_folder(dialog, shuffle=True)),
        ("&Export This Folder...", lambda: _export_folder(dialog)),
        ("Rena&me Folder...\tF2", dialog._on_rename_folder),
        ("&Delete Folder...", dialog._on_delete_folder),
    ]


def popup(dialog: Any, _event: Any) -> list[Any]:
    """Show the row menu. Returns the id refs the caller must pin.

    They are returned rather than stored here because a menu id that is garbage
    collected while its popup can still fire gets reused, and the observable
    symptom is a random menu item closing the window. The dialog keeps them in
    an attribute *separate* from its menu-bar refs for the same reason.
    """
    import wx

    entries = entries_for(dialog)
    if not entries:
        return []
    menu = wx.Menu()
    id_refs: list[Any] = []
    for label, handler in entries:
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        menu.Append(item_id, label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
    dialog._tree.PopupMenu(menu)
    menu.Destroy()
    return id_refs
