"""Writing the line you leave yourself about a station or a podcast.

One multiline box, pre-filled with whatever is already there, and that is the
whole window. Writing a note and clearing one are the same action: emptying the
box and pressing OK removes it, so there is no second menu row to keep in step
with the first.

**Why it is not a prompt with one line.** A note is somebody's own words about
their own listening -- "only worth it on Sundays", "the 6am repeat is the one
with the interview" -- and the shape of the box is what tells them how much is
welcome. A single-line field says "a label"; a box says "say what you like".

The text goes straight back into the details pane, so the outcome is read on
the very next arrow key. That is also why the announcement here is about the
*saving* rather than the text: repeating the note back would be saying twice
what the listener is about to hear anyway.
"""

from __future__ import annotations

from typing import Any

__all__ = ["edit_note", "edit_row_note"]

_TITLE = "Note to Self"


def edit_note(dialog: Any, item: Any, *, announce: Any = None) -> bool:
    """Ask for the note on *item* and save it. Did it change?

    Returns False when there is nothing that can hold a note, when the listener
    cancelled, or when the text came back the same -- so a caller can refresh
    the row only when there is something new to show.
    """
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.radio.item_notes import MAX_NOTE_CHARS, note_for, note_key, set_note
    from quill.ui import modal_stack

    say = announce or getattr(dialog, "_announce", None) or (lambda _m: None)
    if not note_key(item):
        # A row with no stable handle (a lazily-resolved stream with no URL
        # yet) cannot hold a note that would still be on the right row later.
        say("This row cannot hold a note until it has been played once.")
        return False

    data_dir = app_data_dir()
    existing = note_for(data_dir, item)
    name = str(getattr(item, "name", "") or getattr(item, "title", "") or "this")

    with wx.TextEntryDialog(
        modal_stack.parent_window(dialog),
        f"Your note about {name}. Leave it empty to remove the note.",
        _TITLE,
        existing,
        style=wx.TE_MULTILINE | wx.OK | wx.CANCEL,
    ) as box:
        text_ctrl = getattr(box, "GetTextValidator", None)  # not all builds expose the field
        if text_ctrl is None:
            try:
                box.SetMaxLength(MAX_NOTE_CHARS)
            except Exception:  # noqa: BLE001 - a length cap is not the feature
                pass
        if box.ShowModal() != wx.ID_OK:
            return False
        wanted = str(box.GetValue() or "").strip()

    if wanted == existing:
        return False
    if not set_note(data_dir, item, wanted):
        say("The note could not be saved.")
        return False
    # What happened, not what was written: the details pane reads the note back
    # on the next arrow key, and saying it here as well is the over-announcing
    # GATE-13 exists to stop.
    say("Note removed." if not wanted else "Note saved.")
    return True


def edit_row_note(dialog: Any, data: dict, station: Any) -> None:
    """The context-menu entry point: edit the note, then re-read the pane.

    Takes whatever the row actually *is* -- a station, or the podcast behind a
    subscription row -- because item_notes keys a station by its stream URL and
    a show by its id, and only the row knows which of those it has.
    """
    from quill.ui.radio import browse_details

    item = station if station is not None else data.get("show")
    if edit_note(dialog, item):
        # Straight back into the details pane, so the new note is what the next
        # arrow key reads rather than the previous one.
        browse_details.describe_selection(dialog, data)
