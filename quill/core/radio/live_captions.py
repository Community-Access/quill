"""Which caption is being spoken right now, and what the window should show.

Captions had one home in Quill Radio and it was the wrong one for the person
this application is built for: mpv drew them *into the picture*. That is text
rendered as pixels -- unreadable by a screen reader, unreachable by a braille
display, uncopyable, unsearchable, and gone entirely for anyone who never opens
the Video Window. Turning captions on and having nothing appear anywhere you
could read them is exactly what was reported ("toggling captions on and off is
not showing the captions in a window", 2026-08-23).

So captions get a window of their own, and this module is the part of it that
can be tested without one: given the cues and where playback is, which line is
current, and what text belongs on screen.

Two decisions worth keeping:

**A running transcript, not a single flashing line.** A player that shows only
the current caption is usable if you can read at the speed it is replaced. A
window that keeps what has already been said can be arrowed back through, which
is what makes it work with a braille display and with a slow read -- and it
costs nothing, because the cues are all in hand before the window opens.

**The current line is marked in the text, not by colour.** Colour is not
available to a screen reader and is not reliable for a colour-blind reader
either, so the marker is a character (:data:`CURRENT_MARKER`) that reads aloud
as part of the line.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

#: Prefixes the caption being spoken right now. Read aloud it is a word, which
#: is the point: "now" is what a screen reader should say about this line.
CURRENT_MARKER = "> "

#: How many already-spoken lines the window keeps above the current one. Enough
#: to re-read a sentence you missed; not so many that the window becomes the
#: transcript reader, which exists separately and does that job better.
CONTEXT_LINES = 40


def cue_index_at(cues: Sequence[Any], position_ms: int) -> int:
    """Index of the cue covering *position_ms*, or the last one before it.

    ``-1`` when playback has not reached the first cue, or there are no cues.
    Deliberately tolerant of a gap between cues -- silence between two lines is
    normal, and the honest answer there is "the last thing said" rather than
    "nothing", which would blank the window between every sentence.
    """
    position = max(0, int(position_ms))
    found = -1
    for index, cue in enumerate(cues):
        start = int(getattr(cue, "start_ms", 0) or 0)
        if start > position:
            break
        found = index
    return found


def visible_text(cues: Sequence[Any], current: int, *, context: int = CONTEXT_LINES) -> str:
    """The window's whole text: the recent lines, with the current one marked.

    An empty string before the first cue -- the window opens saying what it is
    waiting for (the caller supplies that), rather than showing a line nobody
    has said yet.
    """
    if current < 0 or not cues:
        return ""
    start = max(0, current - max(0, int(context)))
    lines = []
    for index in range(start, current + 1):
        text = str(getattr(cues[index], "text", "") or "").strip()
        if not text:
            continue
        lines.append(f"{CURRENT_MARKER}{text}" if index == current else text)
    return "\n".join(lines)


def current_text(cues: Sequence[Any], current: int) -> str:
    """Just the line being spoken, unmarked. ``""`` before the first cue."""
    if current < 0 or current >= len(cues):
        return ""
    return str(getattr(cues[current], "text", "") or "").strip()
