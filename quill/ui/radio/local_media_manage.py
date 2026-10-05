"""Local Media's playlist and file verbs, shared by the window and the tree.

New, Rename, Duplicate, Delete, Import and Export act on a whole playlist;
Properties, Locate, Show in File Explorer, Copy and Remove Missing act on the
files in one. Every one of them is a plain function of the app frame and ids,
so the Local Media window's menu, its keys, and the Browse tree's context menu
all run exactly the same code -- a verb that worked in one place and not the
other is the fault this shape rules out.

Two rules from the rest of Quill Radio, kept here:

* **Deleting asks, with No already chosen**, and is undoable with Ctrl+Z
  (``undo_last_ui``) -- the playlist comes back where it was, items and all.
  Removing an item from a playlist never touches the file on disk, and says so.
* **Nothing is silent.** Every verb ends by saying what happened, and a verb
  that cannot run says why rather than doing nothing.
"""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

from quill.core.radio import local_media
from quill.core.radio.local_media import MediaItem, Playlist
from quill.ui.radio import local_media_ui as ui

__all__ = [
    "PROPERTIES_TITLE",
    "copy_paths",
    "delete_playlist",
    "duplicate_playlist",
    "export_playlist",
    "import_playlist",
    "locate",
    "new_playlist",
    "properties",
    "remove_missing",
    "rename_playlist",
    "show_in_folder",
]

#: The Properties window's title (and its F1 purpose key).
PROPERTIES_TITLE = "Local Media Item Properties"


def _playlist(host: Any, playlist_id: str) -> Playlist | None:
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        ui.announce(host, "That playlist is not there any more.")
    return playlist


def new_playlist(host: Any) -> Playlist | None:
    """New Playlist...: a name, then an empty playlist ready for files."""
    name = ui.ask_text(host, "Name for the new playlist:", "New Playlist")
    if name is None:
        return None
    playlist = ui.library(host).add_playlist(name or "My Playlist")
    ui.commit(host, browse_select=f"localplaylist:{playlist.id}")
    ui.announce(
        host, f"Made {playlist.name}. It is empty; Add Media Files or Add a Folder fills it."
    )
    return playlist


def rename_playlist(host: Any, playlist_id: str) -> bool:
    playlist = _playlist(host, playlist_id)
    if playlist is None:
        return False
    name = ui.ask_text(host, "New name for the playlist:", "Rename Playlist", playlist.name)
    if not name or name == playlist.name:
        return False
    old = playlist.name
    others = [p for p in ui.library(host).playlists if p.id != playlist_id]
    playlist.name = local_media.LocalMediaLibrary(others).unique_name(name)
    _remember("Rename", playlist.name, f"its old name, {old}", host, playlist_id, "name", old)
    ui.commit(host, browse_select=f"localplaylist:{playlist.id}")
    ui.announce(host, f"Renamed to {playlist.name}.")
    return True


def _remember(
    verb: str, subject: str, restores: str, host: Any, playlist_id: str, field: str, value: object
) -> None:
    from quill.ui import undo_last_ui

    def _undo() -> None:
        target = ui.library(host).find(playlist_id)
        if target is not None:
            setattr(target, field, value)
            ui.commit(host)

    undo_last_ui.remember(verb, subject, restores, _undo)


def duplicate_playlist(host: Any, playlist_id: str) -> Playlist | None:
    """A copy, named "... copy", placed right after the original."""
    playlist = _playlist(host, playlist_id)
    if playlist is None:
        return None
    lib = ui.library(host)
    twin = lib.add_playlist(f"{playlist.name} copy")
    lib.playlists.remove(twin)
    twin.items = [copy.copy(item) for item in playlist.items]
    twin.next_item_id = playlist.next_item_id
    twin.folder, twin.watch = playlist.folder, playlist.watch
    twin.shuffle, twin.repeat = playlist.shuffle, playlist.repeat
    lib.playlists.insert(lib.index_of(playlist_id) + 1, twin)
    ui.commit(host, browse_select=f"localplaylist:{twin.id}")
    ui.announce(host, f"Made {twin.name}, with the same {len(twin.items)} items.")
    return twin


def delete_playlist(host: Any, playlist_id: str) -> bool:
    """Delete Playlist...: asks first (No is chosen), and Ctrl+Z brings it back.

    The files themselves are never touched, and the question says so: "delete"
    next to a list of songs reads, reasonably, as deleting songs.
    """
    playlist = _playlist(host, playlist_id)
    if playlist is None:
        return False
    count = len(playlist.items)
    if not ui.confirm(
        host,
        f"Delete the playlist {playlist.name}? Its {count} item{'' if count == 1 else 's'} "
        "stay on your computer; only the list goes.",
        "Delete Playlist",
    ):
        ui.announce(host, "Nothing was deleted.")
        return False
    lib = ui.library(host)
    position = lib.index_of(playlist_id)
    lib.playlists.remove(playlist)
    from quill.ui import undo_last_ui

    def _undo() -> None:
        current = ui.library(host)
        if current.find(playlist.id) is None:
            current.playlists.insert(min(position, len(current.playlists)), playlist)
            ui.commit(host, browse_select=f"localplaylist:{playlist.id}")

    undo_last_ui.remember("Delete Playlist", playlist.name, f"{count} items", _undo)
    ui.commit(host)
    ui.announce(host, undo_last_ui.offer(f"Deleted the playlist {playlist.name}"))
    return True


def export_playlist(host: Any, playlist_id: str) -> bool:
    """Export as M3U...: a playlist any media player can open."""
    import wx

    from quill.core.radio.local_media_files import EXPORT_WILDCARD, export_m3u

    playlist = _playlist(host, playlist_id)
    if playlist is None:
        return False
    if not playlist.items:
        ui.announce(host, f"{playlist.name} is empty, so there is nothing to export.")
        return False
    with wx.FileDialog(
        ui._parent(host),
        "Export as M3U",
        wildcard=EXPORT_WILDCARD,
        defaultFile=f"{_safe_file_name(playlist.name)}.m3u8",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as chooser:
        if ui.show_modal_dialog(host, chooser, "Export as M3U") != wx.ID_OK:
            return False
        target = Path(chooser.GetPath())
    text = export_m3u(playlist, playlist_dir=target.parent)
    encoding = "utf-8" if target.suffix.lower() == ".m3u8" else "cp1252"
    try:
        target.write_bytes(text.encode(encoding, errors="replace"))
    except OSError as error:
        ui.announce(host, f"The playlist could not be saved: {error}.")
        return False
    ui.announce(host, f"Exported {len(playlist.items)} items to {target.name}.")
    return True


def _safe_file_name(name: str) -> str:
    cleaned = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in name).strip(" .")
    return cleaned or "playlist"


def import_playlist(host: Any, *, into: str = "") -> None:
    """Import a Playlist...: an M3U, M3U8 or PLS, as a new playlist or into one."""
    import wx

    from quill.core.radio.local_media_files import IMPORT_WILDCARD, read_playlist_file

    with wx.FileDialog(
        ui._parent(host),
        "Import a Playlist",
        wildcard=IMPORT_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as chooser:
        if ui.show_modal_dialog(host, chooser, "Import a Playlist") != wx.ID_OK:
            return
        source = Path(chooser.GetPath())
    try:
        entries, skipped = read_playlist_file(source)
    except OSError as error:
        ui.announce(host, f"That playlist could not be read: {error}.")
        return
    if not entries:
        tail = f" It held {skipped} web addresses; Import Stations is for those." if skipped else ""
        # announce-punctuation: exempt -- each part is a whole sentence
        ui.announce(host, f"No files were found in {source.name}.{tail}")
        return
    lib = ui.library(host)
    target = lib.find(into) if into else None
    made = target is None
    if target is None:
        target = lib.add_playlist(source.stem)
    for entry in entries:
        target.items.append(
            target.make_item(entry.path, title=entry.title, duration_seconds=entry.duration_seconds)
        )
    ui.commit(host, browse_select=f"localplaylist:{target.id}")
    missing = sum(1 for item in target.items[-len(entries) :] if not item.exists())
    where = f"a new playlist, {target.name}" if made else target.name
    words = f"Imported {len(entries)} items into {where}."
    if missing:
        words += f" {missing} of them are not on this computer and are marked missing."
    if skipped:
        words += f" {skipped} web addresses were left out."
    ui.announce(host, words)
    ui.read_tags_later(host, target.id, [item.id for item in target.items[-len(entries) :]])


def remove_missing(host: Any, playlist_id: str) -> int:
    """Remove Missing Items: every file that is not there any more. Undoable."""
    playlist = _playlist(host, playlist_id)
    if playlist is None:
        return 0
    rows = [index for index, item in enumerate(playlist.items) if not item.exists()]
    if not rows:
        ui.announce(host, f"Nothing in {playlist.name} is missing.")
        return 0
    from quill.ui.radio import local_media_edit_ui

    local_media_edit_ui.remove_rows(host, playlist, rows, verb="Remove Missing")
    return len(rows)


def locate(host: Any, playlist_id: str, item_id: int) -> bool:
    """Locate...: point a missing item at where its file is now.

    When the file was found in a moved folder, every other missing item that
    was in the same old folder is looked for in the new one too -- a renamed
    album folder is fixed in one go, not one track at a time.
    """
    import wx

    playlist = _playlist(host, playlist_id)
    item = playlist.find(item_id) if playlist is not None else None
    if playlist is None or item is None:
        return False
    with wx.FileDialog(
        ui._parent(host),
        f"Locate {item.file_name}",
        wildcard=local_media.OPEN_WILDCARD,
        defaultFile=item.file_name,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as chooser:
        if ui.show_modal_dialog(host, chooser, "Locate") != wx.ID_OK:
            return False
        found = Path(chooser.GetPath())
    old_folder, new_folder = Path(item.path).parent, found.parent
    item.path = str(found)
    fixed = 1
    for other in playlist.items:
        if other is item or other.exists() or Path(other.path).parent != old_folder:
            continue
        candidate = new_folder / Path(other.path).name
        if candidate.is_file():
            other.path = str(candidate)
            fixed += 1
    ui.commit(host)
    tail = f" {fixed - 1} more from the same folder were found too." if fixed > 1 else ""
    # announce-punctuation: exempt -- each part is a whole sentence
    ui.announce(host, f"Found {item.display_title}.{tail}")
    return True


def show_in_folder(host: Any, item: MediaItem) -> None:
    """Show in File Explorer, with the file already selected there."""
    if not item.exists():
        ui.announce(host, f"{item.display_title} is missing, so there is nothing to show.")
        return
    # The shared, tested argv (Radio Recordings' Open in Folder uses it): the
    # split "/select," form opens Documents instead of selecting the file.
    from quill.core.file_manager import reveal_command

    try:
        subprocess.Popen(reveal_command(Path(item.path)))  # noqa: S603
    except OSError as error:
        ui.announce(host, f"File Explorer could not be opened: {error}.")
        return
    ui.announce(host, f"Showing {item.file_name} in File Explorer.")


def copy_paths(host: Any, items: list[MediaItem]) -> bool:
    """The paths of *items*, one per line, on the clipboard."""
    if not items:
        return False
    text = "\n".join(item.path for item in items)
    copier = getattr(ui.app_of(host), "_copy_to_clipboard", None)
    return bool(copier(text)) if callable(copier) else False


def properties_text(item: MediaItem, playlist: Playlist) -> str:
    """Everything known about one item, one fact a line (pure)."""
    lines = [f"Title: {item.display_title}"]
    if item.artist:
        lines.append(f"Artist: {item.artist}")
    if item.album:
        lines.append(f"Album: {item.album}")
    if item.duration_seconds > 0:
        lines.append(f"Length: {local_media.clock_length(item.duration_seconds)}")
    lines.append(f"Kind: {'video' if item.is_video else 'audio'}")
    lines.append(f"Position: {playlist.index_of(item.id) + 1} of {len(playlist.items)}")
    lines.append(f"Playlist: {playlist.name}")
    lines.append(f"File name: {item.file_name}")
    lines.append(f"Folder: {item.folder}")
    present = item.exists()
    lines.append("On this computer: yes" if present else "On this computer: no, missing")
    if present:
        try:
            size = Path(item.path).stat().st_size
            lines.append(f"Size: {size / 1_048_576:.1f} MB")
        except OSError:
            pass
    return "\n".join(lines)


def properties(host: Any, playlist_id: str, item_id: int) -> None:
    """Properties...: a box to read and copy, with the file's tags and path."""
    import wx

    playlist = _playlist(host, playlist_id)
    item = playlist.find(item_id) if playlist is not None else None
    if playlist is None or item is None:
        return
    dialog = wx.Dialog(
        ui._parent(host),
        title=PROPERTIES_TITLE,
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label=f"&About {item.display_title}:"), 0, wx.ALL, 8)
    box = wx.TextCtrl(
        dialog,
        value=properties_text(item, playlist),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
    )
    box.SetHelpText(
        "What this file says about itself and where it is, one fact a line. Arrow "
        "through it, or select and copy any of it."
    )
    box.SetMinSize((520, 260))
    sizer.Add(box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    close = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close.SetHelpText("Closes this and goes back to the list.")
    sizer.Add(close, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizerAndFit(sizer)
    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL)
    try:
        box.SetFocus()
        ui.show_modal_dialog(host, dialog, PROPERTIES_TITLE)
    finally:
        dialog.Destroy()
