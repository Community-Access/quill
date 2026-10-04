"""Rearranging a playlist from the keyboard: moves, cut and paste, removal, sort.

The list arithmetic is :mod:`quill.core.radio.local_media_edit`'s, pure and
tested; this module is the other half -- doing it to the library, making it
undoable, keeping the playing order in step, and saying where things went.

**Cut and paste move; they never delete.** Ctrl+X marks the items to move and
says so; nothing leaves the list until Ctrl+V puts them before the selected
item (or Paste After, after it). Quill Radio's favorites call the same idea
Mark for Move, and QUILL Cast's Play Queue does it too -- the clipboard keys are
simply the ones every Windows user already has under their fingers. Copy then
Paste puts a second copy in, in this playlist or another one.

**One sentence per edit, and only what the reader cannot say.** It announces
the row the cursor lands on; it cannot say that the row just moved from fifth
to second, so that -- "Moved to 2 of 12" -- is what is said, once.

Undo is the family's own (``undo_last_ui``): Ctrl+Z takes back the last edit,
and Undo History reaches the ones before it. Every undo works by *id*, so
taking back an old move never loses an item added since.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import local_media_edit as edit
from quill.core.radio.local_media import MediaItem, Playlist
from quill.ui.radio import local_media_ui as ui

__all__ = [
    "clip",
    "copy_items",
    "cut_items",
    "move",
    "move_to",
    "paste",
    "remove_rows",
    "sort",
]

_CLIP_ATTR = "_local_media_clip"


def _after_edit(host: Any, playlist: Playlist, source: Any) -> None:
    from quill.ui.radio import local_media_playback

    local_media_playback.sync(host, playlist.id)
    ui.commit(host, source=source)


def _remember_order(host: Any, playlist: Playlist, verb: str, before: list[int]) -> None:
    """Ctrl+Z puts the playlist back in the order it had before *verb*."""
    from quill.ui import undo_last_ui

    playlist_id, name = playlist.id, playlist.name

    def _undo() -> None:
        target = ui.library(host).find(playlist_id)
        if target is not None:
            target.items = edit.restore_order(target.items, before)
            _after_edit(host, target, None)

    undo_last_ui.remember(verb, name, "the order it had", _undo)


def move(
    host: Any, playlist: Playlist, rows: list[int], delta: int, *, source: Any = None
) -> list[int]:
    """Move Up / Move Down: the selection, one place, as a block."""
    chosen = edit.normalize(rows, len(playlist.items))
    if not chosen:
        ui.announce(host, "Nothing is selected to move.")
        return []
    before = playlist.ids()
    moved, new_rows = edit.move_by(playlist.items, chosen, delta)
    if [item.id for item in moved] == before:
        ui.announce(host, "Already at the top." if delta < 0 else "Already at the bottom.")
        return chosen
    playlist.items = moved
    _remember_order(host, playlist, "Move", before)
    _after_edit(host, playlist, source)
    ui.announce(host, edit.moved_sentence(new_rows, len(playlist.items)))
    return new_rows


def move_to(
    host: Any, playlist: Playlist, rows: list[int], position: int, *, source: Any = None
) -> list[int]:
    """Move to Top / Bottom / Position: the first selected lands at *position*."""
    chosen = edit.normalize(rows, len(playlist.items))
    if not chosen:
        ui.announce(host, "Nothing is selected to move.")
        return []
    before = playlist.ids()
    moved, new_rows = edit.move_to(playlist.items, chosen, position)
    if [item.id for item in moved] == before:
        ui.announce(host, f"Already at {new_rows[0] + 1} of {len(moved)}.")
        return new_rows
    playlist.items = moved
    _remember_order(host, playlist, "Move", before)
    _after_edit(host, playlist, source)
    ui.announce(host, edit.moved_sentence(new_rows, len(playlist.items)))
    return new_rows


def remove_rows(
    host: Any, playlist: Playlist, rows: list[int], *, verb: str = "Remove", source: Any = None
) -> int:
    """Remove from Playlist: the rows go, the files stay. Returns the row to land on."""
    kept, removed = edit.remove_at(playlist.items, rows)
    if not removed:
        ui.announce(host, "Nothing is selected to remove.")
        return -1
    playlist.items = kept
    playlist_id, name = playlist.id, playlist.name
    from quill.ui import undo_last_ui

    def _undo() -> None:
        target = ui.library(host).find(playlist_id)
        if target is None:
            return
        present = set(target.ids())
        for index, item in removed:
            if item.id not in present:
                target.items.insert(min(index, len(target.items)), item)
        _after_edit(host, target, None)

    count = len(removed)
    what = removed[0][1].display_title if count == 1 else f"{count} items"
    undo_last_ui.remember(verb, what, f"its place in {name}" if count == 1 else "", _undo)
    _after_edit(host, playlist, source)
    files = "The file is" if count == 1 else "The files are"
    ui.announce(
        host,
        undo_last_ui.offer(f"Removed {what} from {name}. {files} still on your computer"),
    )
    return min(removed[0][0], len(playlist.items) - 1)


def sort(host: Any, playlist: Playlist, key: str, *, source: Any = None) -> None:
    """Sort Playlist: once, by *key*. The order is yours again afterwards."""
    if len(playlist.items) < 2:
        ui.announce(host, "There is nothing to sort.")
        return
    before = playlist.ids()
    playlist.items = edit.sort_items(playlist.items, key)
    _remember_order(host, playlist, "Sort", before)
    _after_edit(host, playlist, source)
    from quill.ui import undo_last_ui

    words = (
        "Shuffled into a random order" if key == "random" else f"Sorted by {edit.sort_label(key)}"
    )
    ui.announce(host, undo_last_ui.offer(words))


# --- the clipboard -------------------------------------------------------------------


def clip(host: Any) -> dict[str, Any] | None:
    held = getattr(ui.app_of(host), _CLIP_ATTR, None)
    return held if isinstance(held, dict) and held.get("items") else None


def _hold(host: Any, held: dict[str, Any]) -> None:
    try:
        setattr(ui.app_of(host), _CLIP_ATTR, held)
    except AttributeError:
        pass


def cut_items(host: Any, playlist: Playlist, rows: list[int]) -> None:
    """Cut: mark these items to move. Nothing leaves the list until Paste."""
    chosen = edit.normalize(rows, len(playlist.items))
    if not chosen:
        ui.announce(host, "Nothing is selected to cut.")
        return
    items = [playlist.items[index] for index in chosen]
    _hold(host, {"mode": "cut", "playlist_id": playlist.id, "items": items})
    noun = items[0].display_title if len(items) == 1 else f"{len(items)} items"
    ui.announce(
        host,
        f"Cut {noun}. Go to where it belongs and press Ctrl+V to put it before that item, "
        "or Ctrl+Alt+V for after.",
    )


def copy_items(host: Any, playlist: Playlist, rows: list[int]) -> None:
    """Copy: hold copies to paste, and put the paths on the clipboard as text."""
    chosen = edit.normalize(rows, len(playlist.items))
    if not chosen:
        ui.announce(host, "Nothing is selected to copy.")
        return
    items = [playlist.items[index] for index in chosen]
    _hold(host, {"mode": "copy", "playlist_id": playlist.id, "items": list(items)})
    from quill.ui.radio import local_media_manage

    pasted = local_media_manage.copy_paths(host, items)
    noun = "1 item" if len(items) == 1 else f"{len(items)} items"
    tail = " Its path is on the clipboard too." if len(items) == 1 else " Their paths are too."
    # announce-punctuation: exempt -- each part is a whole sentence
    ui.announce(host, f"Copied {noun}.{tail if pasted else ''}")


def paste(host: Any, playlist: Playlist, position: int, *, source: Any = None) -> list[int]:
    """Paste before row *position* (or after, when the caller adds one)."""
    held = clip(host)
    if held is None:
        ui.announce(host, "Nothing has been cut or copied yet.")
        return []
    items: list[MediaItem] = list(held["items"])
    from_id = str(held.get("playlist_id", ""))
    lib = ui.library(host)
    before = playlist.ids()
    if held.get("mode") == "cut" and from_id == playlist.id:
        rows = [playlist.index_of(item.id) for item in items]
        rows = [row for row in rows if row >= 0]
        if not rows:
            ui.announce(host, "What was cut is not in this playlist any more.")
            return []
        target = position - sum(1 for row in rows if row < position)
        playlist.items, new_rows = edit.move_to(playlist.items, rows, target)
        _hold(host, {})
        _remember_order(host, playlist, "Move", before)
        _after_edit(host, playlist, source)
        ui.announce(host, edit.moved_sentence(new_rows, len(playlist.items)))
        return new_rows
    fresh = [
        playlist.make_item(
            item.path,
            title=item.title,
            artist=item.artist,
            album=item.album,
            duration_seconds=item.duration_seconds,
        )
        for item in items
    ]
    playlist.items, new_rows = edit.insert_at(playlist.items, fresh, position)
    if held.get("mode") == "cut":
        origin = lib.find(from_id)
        if origin is not None:
            gone = {item.id for item in items}
            origin.items = [item for item in origin.items if item.id not in gone]
            _after_edit(host, origin, None)
        _hold(host, {})
    _remember_paste(host, playlist, [item.id for item in fresh], held, from_id)
    _after_edit(host, playlist, source)
    verb = "Moved" if held.get("mode") == "cut" else "Pasted"
    count = len(fresh)
    noun = "1 item" if count == 1 else f"{count} items"
    ui.announce(host, f"{verb} {noun} to {new_rows[0] + 1} of {len(playlist.items)}.")
    return new_rows


def _remember_paste(
    host: Any, playlist: Playlist, ids: list[int], held: dict[str, Any], from_id: str
) -> None:
    from quill.ui import undo_last_ui

    playlist_id, name = playlist.id, playlist.name
    moved = list(held["items"]) if held.get("mode") == "cut" else []

    def _undo() -> None:
        lib = ui.library(host)
        target = lib.find(playlist_id)
        if target is not None:
            gone = set(ids)
            target.items = [item for item in target.items if item.id not in gone]
            _after_edit(host, target, None)
        origin = lib.find(from_id)
        if origin is not None and moved:
            present = set(origin.ids())
            origin.items.extend(item for item in moved if item.id not in present)
            _after_edit(host, origin, None)

    undo_last_ui.remember("Paste", name, "what it held before", _undo)
