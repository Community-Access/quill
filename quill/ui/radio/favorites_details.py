"""The Manage Favorites details pane -- what the highlighted row is, and your note.

Notes on stations shipped in 3.1.0 and could only be *read* through the browse
tree, because that is the window with a details pane. Somebody who lives in
Manage Favorites -- which is where a listener with sixty saved stations
actually lives -- wrote a note and then never saw it again.

### Why this is the right surface for a note, not a dialog

Arrowing a list is how a screen-reader user reads it, and a details pane is the
one place text appears *without being asked for*: the pane is already filled by
the time somebody wonders about the row. A note you have to open a window to
see is a note you have to remember writing, which defeats writing it.

So the pane is read-only and never announced. The reader says the row; this is
here for the Tab that follows, and for the listener who keeps the pane in view.
Filling it on every arrow key and *also* speaking it would be the
over-announcing GATE-13 exists to stop.

### Folders get a line too

A folder row gets its path and how many stations are in it rather than an empty
box. An empty pane beside a highlighted row reads as a window that failed to
load; a short true sentence reads as a window that has nothing more to say.

Extracted rather than added to ``favorites_manager_dialog`` (GATE-11): this is
a question about *what a row says*, and that module's difficult part is a tree
that refreshes without losing the cursor.
"""

from __future__ import annotations

from typing import Any

__all__ = ["LABEL", "build", "describe", "edit_note", "refresh"]

#: The pane's own label. "&J" because every letter this window's other controls
#: and buttons would want is already claimed here (K, L, P, R, U, D, O, M, A,
#: N), and GATE-14's third rule applies: a duplicate mnemonic advertises a key
#: that may not work, which is worse than a letter nobody would have guessed.
LABEL = "Details and your note (&J)"

_HELP = (
    "What the highlighted favorite is, and any note you have written about "
    "it. Read-only -- use Note to Self on the row's menu (Shift+F10) to "
    "write or change a note."
)


def build(dialog: Any, surface: Any, sizer: Any) -> Any:
    """Add the pane to *sizer* and return it. Stored on the dialog as ``_details``.

    Read-only but still a real text control, so it is reachable by Tab and
    readable line by line. A ``StaticText`` would be announced as one
    unnavigable blob, which is unusable for anything longer than a sentence.
    """
    import wx

    sizer.Add(wx.StaticText(surface, label=LABEL), 0, wx.LEFT | wx.TOP, 10)
    pane = wx.TextCtrl(surface, value="", style=wx.TE_MULTILINE | wx.TE_READONLY)
    pane.SetName("Details and your note")
    pane.SetHelpText(_HELP)
    pane.SetMinSize((-1, 90))
    sizer.Add(pane, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
    dialog._details = pane
    return pane


def _note_for(station: Any) -> str:
    """The listener's own note about *station*, or ``""``. Never raises."""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio.item_notes import note_for

        return note_for(app_data_dir(), station)
    except Exception:  # noqa: BLE001 - a note that cannot load costs the note only
        return ""


def describe(favorite: Any) -> str:
    """One favorite as the pane's text: what it is, then what you said about it.

    The note goes **last**, the same order the browse tree uses: the details
    are what the app knows and the note is what you told yourself, and
    somebody arrowing the list wants the identification first. Labelled, so an
    appended paragraph is not mistaken for more of the station's own blurb.
    """
    if favorite is None:
        return ""
    station = getattr(favorite, "station", None)
    if station is None:
        return ""
    body = str(getattr(station, "details_text", "") or "").strip()
    note = _note_for(station)
    if not note:
        return body
    return f"{body}\n\nYour note: {note}" if body else f"Your note: {note}"


def describe_folder(store: Any, path: str) -> str:
    """A folder row's line: where it is, and how much is in it."""
    name = str(path or "").strip()
    if not name:
        return ""
    try:
        held = sum(1 for fav in getattr(store, "favorites", []) if fav.folder == name)
    except Exception:  # noqa: BLE001 - a count is not worth failing a selection over
        held = 0
    plural = "station" if held == 1 else "stations"
    return f"Folder: {name}\n{held} {plural}."


def refresh(dialog: Any) -> None:
    """Re-read the pane for whatever is selected now. Never raises.

    ``ChangeValue`` rather than ``SetValue``: this is the app answering a
    selection, not an edit, and a text event here would look like the listener
    typing into a read-only box.
    """
    pane = getattr(dialog, "_details", None)
    if pane is None:
        return
    try:
        selected = dialog._selected()
        if selected is not None and selected[0] == "folder":
            pane.ChangeValue(describe_folder(dialog._store, selected[1]))
        else:
            pane.ChangeValue(describe(dialog._selected_favorite()))
    except Exception:  # noqa: BLE001 - the pane is never worth a broken selection
        pane.ChangeValue("")


def edit_note(dialog: Any) -> None:
    """Write or clear the note on the selected station, then re-read the pane.

    The note box belongs to *this* window rather than to the app frame: Manage
    Favorites can be a real window of its own, and a child dialog parented
    somewhere else is one that comes back to the wrong place.
    """
    from types import SimpleNamespace

    from quill.ui.radio import item_note_dialog

    favorite = dialog._selected_favorite()
    if favorite is None:
        return
    host = SimpleNamespace(frame=dialog.dialog, _announce=dialog._announce)
    if item_note_dialog.edit_note(host, favorite.station):
        refresh(dialog)
