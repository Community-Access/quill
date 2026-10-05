"""What a Local Media row says, column by column.

The fill site for the ``radio.local_media`` surface in Radio's column catalogue
(View > Choose Columns...). Every cell is produced by column id rather than by
position, so a listener who hides Album or moves Length first still hears the
right words in each place -- the same seam ``recordings_row_view`` follows.

The title cell carries the row's state, after the title: **playing**,
**paused** or **missing**. A screen reader reads a report row cell by cell, so
the word is heard the moment the cursor reaches the row, and changing it never
moves the cursor -- which is the whole reason the state rides in the text
rather than in a selection or a focus change.
"""

from __future__ import annotations

from datetime import datetime

from quill.core.radio.local_media import MediaItem, clock_length

__all__ = ["PAUSED", "PLAYING", "SURFACE", "cells", "title_cell"]

#: This list's id in Radio's column catalogue.
SURFACE = "radio.local_media"

PLAYING = "playing"
PAUSED = "paused"


def title_cell(item: MediaItem, state: str = "", *, exists: bool | None = None) -> str:
    """The title, then whichever of playing, paused or missing is true."""
    present = item.exists() if exists is None else exists
    words = [item.display_title]
    if state:
        words.append(state)
    if not present:
        words.append("missing")
    return ", ".join(words)


def cells(item: MediaItem, state: str = "", *, exists: bool | None = None) -> dict[str, str]:
    """Every cell *item* could show, keyed by column id."""
    added = ""
    if item.added_at > 0:
        added = datetime.fromtimestamp(item.added_at).strftime("%Y-%m-%d %H:%M")
    return {
        "title": title_cell(item, state, exists=exists),
        "artist": item.artist,
        "album": item.album,
        "length": clock_length(item.duration_seconds),
        "file": item.file_name,
        "folder": item.folder,
        "added": added,
    }
