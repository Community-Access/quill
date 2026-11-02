"""Split into Songs, and the Recordings list's context menu.

**Split into Songs** (Alt+Shift+T, on the Recordings menu and the list's
context menu) cuts a finished recording into one file per song, at the song
changes the recorder noted while it recorded
(:mod:`quill.core.radio.recording_song_log`). The songs go into a folder beside
the recording, named "Artist - Title"; the recording itself is kept. With
recordings marked (``.``), every marked one is split; otherwise the selected
one is.

The cut is an ffmpeg stream copy, so it is quick, but a long show is still a
large file, and it runs on the app's task manager rather than the UI thread.
Nothing is said when it starts -- the next thing heard is the one sentence at
the end, with the count (GATE-BULK-COUNT), or the plain reason a recording was
not split: most often that no song changes were recorded for it, because the
station sends no song titles or it was recorded before Quill Radio kept them.

Why Alt+Shift+T (T for tracks): the list's plain letters are its Winamp
keys, and every Ctrl+Shift and Ctrl+Alt letter is already a command somewhere
in Quill Radio -- Ctrl+Alt+O, the first choice, is both Browse Spotify and
Local Media's Add a Folder. Alt+Shift+T is bound nowhere in Quill Radio, no
menu in the main window this list can be shown in opens on T, and no control
in this window has T as its access key, so the chord cannot press one by
accident. (In QUILL it is New Rich Text Document, but there this window is
modal and the editor's keys do not reach it.)

Split from ``recordings_manager_dialog`` under GATE-11, which holds that
module at its budget.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio.recordings_index import STATUS_RECORDED, STATUS_RECORDING
from quill.ui.radio.marks_shared import mark_menu_entries, marks_on

__all__ = [
    "MENU_LABEL",
    "add_menu_row",
    "is_split_key",
    "show_context_menu",
    "split_into_songs",
    "targets",
]

#: The menu row, with its key; the same words on the menu bar and the context
#: menu, so a listener who learns it in one finds it in the other.
MENU_LABEL = "Split into &Songs\tAlt+Shift+T"


def is_split_key(wx: Any, event: Any) -> bool:
    """Alt+Shift+T, and nothing else held."""
    return bool(
        event.AltDown()
        and event.ShiftDown()
        and not event.ControlDown()
        and event.GetKeyCode() == ord("T")
    )


def _finished(entry: Any) -> bool:
    return entry is not None and entry.status == STATUS_RECORDED and entry.path is not None


def targets(dialog: Any) -> list[Path]:
    """What Split into Songs works on: every marked recording, or the
    selected one when none is marked."""
    marks = marks_on(dialog)
    marks.keep_only(entry.id for entry in dialog._entries if _finished(entry))
    if marks:
        return [entry.path for entry in dialog._entries if _finished(entry) and entry.id in marks]
    entry = dialog._selected()
    return [entry.path] if _finished(entry) else []


def split_into_songs(
    dialog: Any,
    *,
    split: Callable[[Path], Any] | None = None,
) -> bool:
    """Start splitting the targets off the UI thread. Returns whether it started.

    *split* cuts one recording and returns its outcome
    (:func:`quill.core.radio.recording_song_log.split_finished` by default; the
    tests pass a fake). The single sentence at the end comes back on the UI
    thread through the app's task manager.
    """
    if getattr(dialog, "_splitting", False):
        dialog._announce("Still splitting; the result will be said when it is done.")
        return False
    paths = targets(dialog)
    if not paths:
        entry = dialog._selected()
        if entry is not None and entry.status == STATUS_RECORDING:
            dialog._announce("Still recording; it can be split once it has finished.")
        else:
            dialog._announce("Select a finished recording to split it into songs.")
        return False
    from quill.core.radio.recording_song_log import describe_splits, split_finished

    cut = split or split_finished

    def work(**_kwargs: Any) -> str:
        return describe_splits([cut(path) for path in paths])

    def done(_op: str, said: object) -> None:
        dialog._splitting = False
        dialog._announce(str(said))

    def failed(_op: str, _error: BaseException) -> None:
        dialog._splitting = False
        dialog._announce("The recording could not be split. It is unchanged.")

    tasks = getattr(dialog._app_host, "_task_manager", None)
    if tasks is None:
        # Every app that opens this window has one; a host without one gets a
        # plain sentence rather than a cut on the UI thread.
        dialog._announce("Split into Songs is not available here.")
        return False
    dialog._splitting = True
    tasks.submit("radio-split-recording", work, on_success=done, on_failure=failed)
    return True


def add_menu_row(dialog: Any, menu: Any) -> None:
    """The Recordings menu's Split into Songs row (the modeless window's menu
    bar; its key is the row's accelerator there)."""
    wx = dialog._wx
    item_id = wx.NewIdRef()
    menu.Append(item_id, MENU_LABEL)
    dialog._win.Bind(wx.EVT_MENU, lambda _e: split_into_songs(dialog), id=item_id)
    dialog._menu_id_refs.append(item_id)


def show_context_menu(dialog: Any, _event: Any = None) -> None:
    """Shift+F10 or the Applications key on a recording: its actions, each
    with its key, then the marking rows."""
    from quill.ui.radio import recordings_marks

    wx = dialog._wx
    entry = dialog._selected()
    if entry is None:
        return
    marks = marks_on(dialog)
    entries: list[tuple[str, Callable[[], None]]] = []
    if _finished(entry):
        entries += [
            ("&Play\tEnter", dialog._on_play),
            ("&Open in Folder", dialog._on_open_in_folder),
            (MENU_LABEL, lambda: split_into_songs(dialog)),
        ]
        if not marks:
            # While recordings are marked, Delete removes them all, so the
            # one-row delete gives the key up to the marked row.
            entries.append(("&Delete...\tDelete", dialog._on_remove))
    elif entry.status == STATUS_RECORDING:
        entries.append(("S&top Recording", dialog._on_stop_recording))

    def clear() -> None:
        recordings_marks.clear(dialog)

    entries += mark_menu_entries(
        marks,
        toggle=lambda: recordings_marks.toggle_selected(dialog),
        remove=lambda: recordings_marks.remove_marked(dialog),
        clear=clear,
    )
    menu = wx.Menu()
    id_refs = []
    for label, handler in entries:
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        menu.Append(item_id, label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
    dialog._context_menu_id_refs = id_refs  # pinned while the popup can fire
    dialog._list.PopupMenu(menu)
    menu.Destroy()
