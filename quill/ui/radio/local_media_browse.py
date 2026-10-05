"""Local Media's rows in Browse Stations: their menus, their action rows, Delete.

The tree knows that a row opens, plays or acts; what a Local Media row *offers*
is decided in :mod:`quill.core.radio.browse_local_media` (wx-free), and what
each offer *does* is here -- by calling the same functions the Local Media
window calls. The browse menu hands Local Media rows to :func:`show_menu`
before it builds the general station menu, so Play Next, Remove from Playlist
and Rename Playlist never have to be taught to every other row in the tree.

The tree's own verbs on these rows -- Open, Close, Hide This Source, Reset
Sources to Default -- are still the tree's: they come from the browse menu's
handler table, so they behave exactly as they do on every other branch.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import browse_local_media as rows
from quill.core.radio import row_actions
from quill.core.radio.browse_nodes import split_id
from quill.ui.radio import local_media_ui as ui

__all__ = [
    "ACTIONS",
    "TREE_ONLY",
    "build_popup",
    "delete_selected",
    "perform",
    "show_menu",
]

#: Verbs only the tree offers: the window *is* where Open in Local Media goes.
TREE_ONLY = frozenset({
    row_actions.OPEN_FOLDER,
    row_actions.CLOSE_FOLDER,
    rows.OPEN_IN_WINDOW,
})


def _open_window(host: Any, playlist_id: str = "", item_id: int = 0) -> None:
    from quill.ui.radio import local_media_commands

    local_media_commands.open_window(host, playlist_id=playlist_id, item_id=item_id)


def _add(host: Any, playlist_id: str, *, folder: bool) -> None:
    if folder:
        chosen = ui.ask_folder(host)
        paths = [chosen] if chosen else []
    else:
        paths = ui.ask_files(host)
    if paths:
        ui.add_paths(
            host,
            paths,
            playlist_id=playlist_id,
            folder=paths[0] if folder and not playlist_id else "",
        )


def perform(source: Any, playlist_id: str, action_id: str, item_id: int = 0) -> None:
    """Run one Local Media verb on a playlist (and an item in it)."""
    from quill.ui.radio import local_media_edit_ui as edit_ui
    from quill.ui.radio import local_media_manage as manage
    from quill.ui.radio import local_media_playback as playback

    host = ui.app_of(source)
    playlist = ui.library(host).find(playlist_id) if playlist_id else None
    item = playlist.find(item_id) if playlist is not None and item_id else None
    simple: dict[str, Callable[[], object]] = {
        rows.PLAY_PLAYLIST: lambda: playback.play_playlist(host, playlist_id),
        rows.SHUFFLE_PLAY: lambda: playback.play_playlist(host, playlist_id, shuffle=True),
        rows.CONTINUE: lambda: playback.continue_playlist(host, playlist_id),
        rows.OPEN_IN_WINDOW: lambda: _open_window(host, playlist_id, item_id),
        rows.ADD_FILES_HERE: lambda: _add(host, playlist_id, folder=False),
        rows.ADD_FOLDER_HERE: lambda: _add(host, playlist_id, folder=True),
        rows.NEW: lambda: manage.new_playlist(host),
        rows.IMPORT_PLAYLIST: lambda: manage.import_playlist(host),
        rows.RENAME: lambda: manage.rename_playlist(host, playlist_id),
        rows.SAVE_OPENED: lambda: manage.save_opened(host, playlist_id),
        rows.DUPLICATE: lambda: manage.duplicate_playlist(host, playlist_id),
        rows.DELETE: lambda: manage.delete_playlist(host, playlist_id),
        rows.EXPORT: lambda: manage.export_playlist(host, playlist_id),
        rows.RESCAN: lambda: ui.rescan_folder(host, playlist_id),
    }
    if action_id in simple:
        simple[action_id]()
        return
    if playlist is None or item is None:
        return
    if action_id == rows.PLAY:
        playback.play_item(host, playlist_id, item_id)
    elif action_id == rows.STOP:
        controller = playback.controller_of(host)
        if controller is not None:
            controller.stop()
            ui.announce(host, "Stopped.")
    elif action_id == rows.PLAY_NEXT:
        playback.play_next(host, playlist_id, [item_id])
    elif action_id == rows.UP_NEXT:
        playback.add_up_next(host, playlist_id, [item_id])
    elif action_id == rows.REMOVE_ITEM:
        edit_ui.remove_rows(host, playlist, [playlist.index_of(item_id)])
    elif action_id == rows.LOCATE:
        manage.locate(host, playlist_id, item_id)
    elif action_id == rows.SHOW_IN_FOLDER:
        manage.show_in_folder(host, item)
    elif action_id == rows.COPY_PATH:
        if manage.copy_paths(host, [item]):
            ui.announce(host, f"Copied the path of {item.file_name}.")
    elif action_id == rows.PROPERTIES:
        manage.properties(host, playlist_id, item_id)
    elif action_id == row_actions.PLAYING_WHERE:
        from quill.ui.radio import transport_keys

        transport_keys.perform(host, action_id)


#: The action rows of the Local Media branch, for ``browse_actions``.
ACTIONS: dict[str, Callable[[Any], None]] = {
    rows.ADD_FILES: lambda dialog: _add(ui.app_of(dialog), "", folder=False),
    rows.ADD_FOLDER: lambda dialog: _add(ui.app_of(dialog), "", folder=True),
    rows.NEW_PLAYLIST: lambda dialog: perform(dialog, "", rows.NEW),
    rows.IMPORT: lambda dialog: perform(dialog, "", rows.IMPORT_PLAYLIST),
    rows.OPEN_WINDOW: lambda dialog: _open_window(ui.app_of(dialog)),
}


def build_popup(wx: Any, actions: list[Any], run: Callable[[str], None]) -> Any:
    """A popup of *actions* (``RowAction``), dimmed ones saying why."""
    menu = wx.Menu()
    refs = []
    for action in actions:
        item_id = wx.NewIdRef()
        refs.append(item_id)
        item = menu.Append(item_id, row_actions.menu_label(action))
        if not action.enabled:
            item.Enable(False)
            item.SetHelp(action.unavailable_sentence())
        menu.Bind(wx.EVT_MENU, lambda _e, aid=action.id: run(aid), id=item_id)
    menu._refs = refs  # pinned with the menu: a freed id fires nothing
    return menu


def _row_facts(dialog: Any, kind: str, args: list[str]) -> tuple[Any, Any, bool]:
    from quill.ui.radio import local_media_playback as playback

    lib = ui.library(dialog)
    playlist = lib.find(args[0]) if args else None
    item = None
    if kind == rows.ITEM and playlist is not None and len(args) > 1 and args[1].isdigit():
        item = playlist.find(int(args[1]))
    _playing_list, playing = playback.current(dialog)
    return playlist, item, bool(item is not None and playing is not None and playing.id == item.id)


def show_menu(dialog: Any, node: Any, data: dict, kind: str, args: list[str]) -> bool:
    """The context menu for a Local Media row. True when the row was ours."""
    if kind not in rows.KINDS:
        return False
    from quill.ui.radio import browse_tree_menu

    playlist, item, playing = _row_facts(dialog, kind, args)
    expanded = bool(node is not None and dialog._tree.IsExpanded(node))
    actions = rows.menu_actions(
        kind, playlist=playlist, item=item, playing=playing, expanded=expanded
    )
    handlers = browse_tree_menu._handlers(dialog, node, data, kind, args)
    playlist_id = playlist.id if playlist is not None else ""
    item_id = item.id if item is not None else 0
    for action in actions:
        if action.id not in handlers or action.id.startswith("local."):
            handlers[action.id] = lambda aid=action.id: perform(dialog, playlist_id, aid, item_id)
    browse_tree_menu._popup(dialog, actions, handlers)
    return True


def delete_selected(dialog: Any, node: Any, kind: str, args: list[str]) -> bool:
    """Delete on a Local Media row: remove the item, or delete the playlist.

    An item asks first through the tree's own question -- the one with "do not
    ask again" in it -- and is undoable either way. A playlist always asks:
    that question is the playlist's own, because it is a bigger thing to lose.
    """
    from quill.ui.radio import browse_delete

    if kind == rows.PLAYLIST and args:
        from quill.ui.radio import local_media_manage

        return local_media_manage.delete_playlist(dialog, args[0])
    playlist_id, item_id = rows.parse_item_id(":".join([kind, "\t".join(args)]))
    playlist = ui.library(dialog).find(playlist_id)
    item = playlist.find(item_id) if playlist is not None else None
    if playlist is None or item is None:
        return False
    if not browse_delete.confirm(
        dialog, f"Remove {item.display_title} from {playlist.name}? The file stays."
    ):
        dialog._announce("Nothing was removed.")
        return False
    from quill.ui.radio import local_media_edit_ui

    local_media_edit_ui.remove_rows(dialog, playlist, [playlist.index_of(item_id)])
    return True


def handles_delete(kind: str) -> bool:
    return kind in (rows.PLAYLIST, rows.ITEM)


def node_kind(node_id: str) -> str:
    return split_id(node_id)[0]
