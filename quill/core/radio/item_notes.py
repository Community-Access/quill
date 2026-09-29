"""A note you wrote to yourself about a station or a podcast.

Not metadata, not a review, not a tag: a line you leave for your own benefit
and read again when you arrow back onto that row. "The morning show is the good
one." "Only worth it on Sundays." "Ask about the interval -- this one publishes
at 3am." The app has no opinion about what belongs here and never shows it to
anybody else.

**Why it goes in the details pane rather than a window of its own.** Arrowing a
list is how somebody using a screen reader reads it, and the details pane is
already what that arrow key fills -- it is the one place a note is read *without
being asked for*. A note you have to open a dialog to see is a note you have to
remember you wrote, which defeats the point of writing it.

### What identifies a row

A station is keyed by its stream URL and a podcast by its show id, because
those are what survive a rename, a re-sort, and a catalogue refresh -- the
things a name does not. A station with no URL cannot be keyed, and simply
cannot hold a note rather than holding one that attaches to the wrong row
later.

wx-free, strict-typed. One small JSON map in the shared app data dir, so a note
written in Quill Radio is the same note QUILL Cast would read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_NOTE_CHARS",
    "clear_note",
    "load_notes",
    "note_for",
    "note_key",
    "notes_path",
    "set_note",
]

#: A note is a reminder to yourself, not a document. Long enough for a few
#: sentences, short enough that the details pane stays skimmable when a screen
#: reader reads it on every arrow key.
MAX_NOTE_CHARS = 2000

_FILENAME = "item-notes.json"


def notes_path(data_dir: Path) -> Path:
    return data_dir / _FILENAME


def note_key(item: Any) -> str:
    """The stable handle for *item*, or ``""`` when it cannot hold a note.

    A podcast show is its id; a station is its stream URL. Both survive the
    renames and re-sorts a display name does not, which is what stops a note
    reappearing on somebody else's row after a catalogue refresh.
    """
    if item is None:
        return ""
    show_id = str(getattr(item, "id", "") or "").strip()
    feed = str(getattr(item, "feed_url", "") or "").strip()
    if show_id and feed:
        return f"show:{show_id}"
    url = str(getattr(item, "stream_url", "") or "").strip()
    if url:
        return f"stream:{url.lower()}"
    if show_id:
        return f"show:{show_id}"
    return ""


def load_notes(data_dir: Path) -> dict[str, str]:
    """Every stored note. ``{}`` when there is no file or it cannot be read."""
    try:
        raw = read_json(notes_path(data_dir), {})
    except Exception:  # noqa: BLE001 - an unreadable map is an empty one
        return {}
    if not isinstance(raw, dict):
        return {}
    notes: dict[str, str] = {}
    for key, value in raw.items():
        text = str(value or "").strip()
        if str(key).strip() and text:
            notes[str(key)] = text[:MAX_NOTE_CHARS]
    return notes


def note_for(data_dir: Path, item: Any) -> str:
    """The note on *item*, or ``""``. Never raises."""
    key = note_key(item)
    return load_notes(data_dir).get(key, "") if key else ""


def set_note(data_dir: Path, item: Any, text: str) -> bool:
    """Write (or replace) the note on *item*. Did it save?

    An empty note removes the entry rather than storing a blank one, so
    "clear it" and "never wrote one" are the same state -- there is no third
    thing for the details pane to have to describe.
    """
    key = note_key(item)
    if not key:
        return False
    notes = load_notes(data_dir)
    cleaned = str(text or "").strip()[:MAX_NOTE_CHARS]
    if cleaned:
        notes[key] = cleaned
    else:
        notes.pop(key, None)
    try:
        write_json_atomic(notes_path(data_dir), notes)
    except Exception:  # noqa: BLE001 - losing a note beats crashing the browser
        return False
    return True


def clear_note(data_dir: Path, item: Any) -> bool:
    """Remove the note on *item*."""
    return set_note(data_dir, item, "")
