"""F1's words about the selected row of Quill Radio's Favorites tree (FUX-10).

The tree's own help says "Enter plays", which is true of most rows and not of
two: the station the player already holds, where Enter and Space pause,
resume or restart it (``RadioPlayerController.toggle_play_pause``), and a
folder, where Enter plays nothing. F1 also never mentioned a station marked
for move or the note you wrote on a station. This module says those things,
and only those: a row that needs nothing beyond "Enter plays" gets "".

wx-free; :mod:`quill.apps.radio_favorites_tree` gathers the facts.
"""

from __future__ import annotations

__all__ = ["HELD", "PAUSED", "RUNNING", "folder_situation", "station_situation"]

#: What the player is doing with the selected station, when it holds it.
RUNNING = "running"
PAUSED = "paused"
HELD = "held"
"""Held but stopped, connecting, reconnecting or failed: Enter starts it again."""

_ENTER_ON_HELD = {
    RUNNING: "This station is playing. Enter or Space pauses it.",
    PAUSED: "This station is paused. Enter or Space resumes it.",
    HELD: "Enter or Space starts this station again.",
}


def station_situation(
    *,
    held: str = "",
    marked_label: str = "",
    marked_is_this: bool = False,
    note: str = "",
) -> str:
    """The selected station's paragraph, or "" when the list's help covers it.

    *held* is :data:`RUNNING`, :data:`PAUSED` or :data:`HELD` when the player
    holds this station, else "". *marked_label* names the station marked for
    move, if any. The note goes on its own line, last, so a long one does not
    bury what Enter does.
    """
    lines: list[str] = []
    if held in _ENTER_ON_HELD:
        lines.append(_ENTER_ON_HELD[held])
    if marked_is_this:
        lines.append(
            "Marked for move. On the station it should go next to, Shift+F10 has "
            "Move Marked Above and Move Marked Below."
        )
    elif marked_label:
        lines.append(
            f"{marked_label} is marked for move. Shift+F10 here has Move Marked "
            "Above and Move Marked Below."
        )
    if note.strip():
        lines.append(f"Your note: {note.strip()}")
    return "\n".join(lines)


def folder_situation(stations: int) -> str:
    """The selected folder's paragraph. The screen reader already says its name."""
    held = "1 station" if stations == 1 else f"{stations} stations"
    return (
        f"This folder holds {held}, counting its subfolders. Enter does not play a "
        "folder: Right Arrow opens it and Left Arrow closes it."
    )
