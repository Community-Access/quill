"""Local Media in Browse Stations: your playlists, as a branch of the tree.

Node ids (opaque to the tree, like every other source)::

    localmedia                          the branch: playlists, then ways in
    localplaylist:<playlist id>         a playlist, opening to its items
    localitem:<playlist id>\\t<item id>   one file in it (a playable leaf)

and five action rows: ``localaddfiles``, ``localaddfolder``,
``localnewplaylist``, ``localimport`` and ``localopenwindow``.

**What a row offers is decided here**, wx-free, the same way
:mod:`quill.core.radio.row_actions` decides it for every other row -- an id and
a label per item, never a callback. The browse menu hands Local Media rows to
this module because their verbs (Play Next, Remove from Playlist, Rename
Playlist) belong to nothing else in the tree, and threading eleven more cases
through the shared station menu would make it the menu of everything.

**Which playlist a played row belongs to** is remembered as the rows are built
(:data:`PLAYLIST_OF`): a file can sit in two playlists, and the one somebody was
standing in when they pressed Enter is the one whose next item should follow.
In memory only, and only a hint -- the player falls back to the first playlist
holding the file.

No network: everything here is a path on this machine, so the branch works in
Safe Mode exactly as it does otherwise.
"""

from __future__ import annotations

from quill.core.radio import local_media
from quill.core.radio.browse_nodes import BrowseNode, action, folder, leaf, make_id, split_id
from quill.core.radio.local_media import (
    LocalMediaLibrary,
    MediaItem,
    Playlist,
    clock_length,
    path_key,
)
from quill.core.radio.models import RadioStation
from quill.core.radio.row_actions import (
    CLOSE_FOLDER,
    HIDE_SOURCE,
    OPEN_FOLDER,
    PLAYING_WHERE,
    RESET_SOURCES,
    RowAction,
)

__all__ = [
    "ACTION_IDS",
    "HANDLERS",
    "ITEM",
    "KINDS",
    "PLAYLIST",
    "PLAYLIST_OF",
    "ROOT",
    "browse_local_media",
    "browse_local_playlist",
    "menu_actions",
    "station_for",
]

ROOT = "localmedia"
PLAYLIST = "localplaylist"
ITEM = "localitem"
KINDS = frozenset({ROOT, PLAYLIST, ITEM})

ADD_FILES = "localaddfiles"
ADD_FOLDER = "localaddfolder"
NEW_PLAYLIST = "localnewplaylist"
IMPORT = "localimport"
OPEN_WINDOW = "localopenwindow"
ACTION_IDS = (ADD_FILES, ADD_FOLDER, NEW_PLAYLIST, IMPORT, OPEN_WINDOW)

#: path key -> the playlist id it was last listed under.
PLAYLIST_OF: dict[str, str] = {}

# Menu action ids. Shared with the Local Media window, which binds the same
# verbs to the same functions, so a menu item and a key can never disagree.
PLAY = "local.play"
STOP = "local.stop"
PLAY_PLAYLIST = "local.play_playlist"
SHUFFLE_PLAY = "local.shuffle_play"
CONTINUE = "local.continue"
PLAY_NEXT = "local.play_next"
UP_NEXT = "local.up_next"
REMOVE_ITEM = "local.remove_item"
LOCATE = "local.locate"
SHOW_IN_FOLDER = "local.show_in_folder"
COPY_PATH = "local.copy_path"
PROPERTIES = "local.properties"
OPEN_IN_WINDOW = "local.open_in_window"
ADD_FILES_HERE = "local.add_files"
ADD_FOLDER_HERE = "local.add_folder"
NEW = "local.new_playlist"
IMPORT_PLAYLIST = "local.import"
RENAME = "local.rename"
SAVE_OPENED = "local.save_opened"
DUPLICATE = "local.duplicate"
DELETE = "local.delete"
EXPORT = "local.export"
RESCAN = "local.rescan"


def _item_note(item: MediaItem) -> str:
    parts: list[str] = []
    if item.artist:
        parts.append(item.artist)
    if item.duration_seconds > 0:
        from quill.core.speech_text import speak_duration

        parts.append(speak_duration(item.duration_seconds))
    if item.is_video:
        parts.append("video")
    if not item.exists():
        parts.append("missing")
    return ", ".join(parts)


def station_for(item: MediaItem) -> RadioStation:
    """The station the player is handed for *item*: a file, with an end.

    ``is_recording`` because a file has a beginning and an end -- that is what
    gives it a position, Go to Position, speed and resume, exactly as a
    downloaded episode has. No ``station_uuid``: that is a Radio Browser id,
    and handing it one would make the player report a "click" for a file.
    """
    details = [f"File: {item.path}"]
    if item.album:
        details.insert(0, f"Album: {item.album}")
    if item.artist:
        details.insert(0, f"Artist: {item.artist}")
    if item.duration_seconds > 0:
        details.append(f"Length: {clock_length(item.duration_seconds)}")
    return RadioStation(
        name=item.spoken(),
        stream_url=item.path,
        source=local_media.SOURCE_LABEL,
        is_recording=True,
        notes="\n".join(details),
    )


def _load(library: LocalMediaLibrary | None) -> LocalMediaLibrary:
    return library if library is not None else local_media.load_library()


def browse_local_media(
    args: list[str], *, safe_mode: bool, library: LocalMediaLibrary | None = None
) -> list[BrowseNode]:
    """The branch: every playlist, then the ways to add more."""
    del args, safe_mode  # local, so Safe Mode changes nothing
    nodes: list[BrowseNode] = [
        folder(make_id(PLAYLIST, playlist.id), playlist.name, note=local_media.summary(playlist))
        for playlist in _load(library).playlists
    ]
    nodes.append(action(ADD_FILES, "Add Media Files...", note="music, audiobooks or video"))
    nodes.append(action(ADD_FOLDER, "Add a Folder...", note="every file in it, in order"))
    nodes.append(action(NEW_PLAYLIST, "New Playlist..."))
    if len(nodes) == 3:
        # Only while there is nothing here: once there are playlists, Import
        # is on every Local Media row's menu, which is where a rare verb lives.
        nodes.append(action(IMPORT, "Import a Playlist...", note="M3U or PLS"))
    nodes.append(action(OPEN_WINDOW, "Open the Local Media Window"))
    return nodes


def browse_local_playlist(
    args: list[str], *, safe_mode: bool, library: LocalMediaLibrary | None = None
) -> list[BrowseNode]:
    """One playlist's items, in its order, each one playable."""
    del safe_mode
    playlist = _load(library).find(args[0]) if args else None
    if playlist is None:
        return []
    nodes: list[BrowseNode] = []
    for item in playlist.items:
        PLAYLIST_OF[path_key(item.path)] = playlist.id
        nodes.append(
            leaf(
                station_for(item),
                node_id=make_id(ITEM, playlist.id, str(item.id)),
                note=_item_note(item),
            )
        )
    return nodes


def parse_item_id(node_id: str) -> tuple[str, int]:
    """``(playlist id, item id)`` from a ``localitem`` id; ``("", 0)`` if not one."""
    kind, args = split_id(node_id)
    if kind != ITEM or len(args) < 2 or not args[1].isdigit():
        return "", 0
    return args[0], int(args[1])


def menu_actions(
    kind: str,
    *,
    playlist: Playlist | None = None,
    item: MediaItem | None = None,
    playing: bool = False,
    expanded: bool = False,
) -> list[RowAction]:
    """What a Local Media row's context menu offers, in order (pure).

    Access keys are unique within each menu; the tests walk every shape.
    """
    if kind == ITEM and item is not None:
        actions = [
            RowAction(STOP, "St&op") if playing else RowAction(PLAY, "&Play"),
            RowAction(PLAY_NEXT, "Play &Next"),
            RowAction(UP_NEXT, "Add to &Up Next"),
            RowAction(REMOVE_ITEM, "&Remove from Playlist"),
        ]
        if not item.exists():
            actions.append(RowAction(LOCATE, "&Locate..."))
        else:
            actions.append(RowAction(SHOW_IN_FOLDER, "Show in File &Explorer"))
        actions.append(RowAction(COPY_PATH, "&Copy Path"))
        actions.append(RowAction(PROPERTIES, "Propert&ies..."))
        actions.append(RowAction(OPEN_IN_WINDOW, "Open in Local Media &Window"))
        if playing:
            actions.append(RowAction(PLAYING_WHERE, "Where &Am I?"))
        return actions
    if kind == PLAYLIST and playlist is not None:
        has_items = bool(playlist.items)
        actions = [
            RowAction(CLOSE_FOLDER, "&Close") if expanded else RowAction(OPEN_FOLDER, "&Open"),
            RowAction(PLAY_PLAYLIST, "&Play This Playlist", enabled=has_items, reason=_EMPTY),
            RowAction(SHUFFLE_PLAY, "S&huffle and Play", enabled=has_items, reason=_EMPTY),
        ]
        if playlist.last_item_id and playlist.find(playlist.last_item_id) is not None:
            actions.append(RowAction(CONTINUE, "Contin&ue Where I Left Off"))
        actions += [
            RowAction(OPEN_IN_WINDOW, "Open in Local Media &Window"),
            RowAction(ADD_FILES_HERE, "Add &Media Files..."),
            RowAction(ADD_FOLDER_HERE, "Add a &Folder..."),
        ]
        if playlist.folder:
            actions.append(RowAction(RESCAN, "Check the Folder for New Fil&es"))
        actions += [
            # The Opened files list is kept by saving it, not by renaming it.
            RowAction(SAVE_OPENED, "&Save as Playlist...")
            if playlist.temporary
            else RowAction(RENAME, "&Rename..."),
            RowAction(DUPLICATE, "Dup&licate"),
            RowAction(EXPORT, "E&xport as M3U...", enabled=has_items, reason=_EMPTY),
            RowAction(DELETE, "&Delete Playlist..."),
        ]
        return actions
    if kind == ROOT:
        return [
            RowAction(CLOSE_FOLDER, "&Close") if expanded else RowAction(OPEN_FOLDER, "&Open"),
            RowAction(OPEN_IN_WINDOW, "Open in Local Media &Window"),
            RowAction(ADD_FILES_HERE, "Add &Media Files..."),
            RowAction(ADD_FOLDER_HERE, "Add a &Folder..."),
            RowAction(NEW, "&New Playlist..."),
            RowAction(IMPORT_PLAYLIST, "&Import a Playlist..."),
            RowAction(HIDE_SOURCE, "&Hide This Source"),
            RowAction(RESET_SOURCES, "Rese&t Sources to Default"),
        ]
    return []


#: Why a verb that needs items is dimmed on an empty playlist.
_EMPTY = "this playlist has nothing in it yet"


#: Registered into the tree's handler table by ``browse_sources``.
HANDLERS = {ROOT: browse_local_media, PLAYLIST: browse_local_playlist}
