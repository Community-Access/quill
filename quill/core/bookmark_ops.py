"""What the bookmark verbs do, without a window (list.md 4.4).

Add, jump, delete, share -- four verbs over
:class:`~quill.core.media.bookmarks.BookmarkStore`, anchored by
:mod:`quill.core.bookmark_anchors`. Everything here is pure or store-only, so
the same four verbs serve Quill Radio's player, QUILL Cast's episode list, and
the shared Bookmarks window without any of them owning the rules.

**Why "add" is not just ``store.add``.** A bookmark is dropped mid-listen, one
keystroke, usually while doing something else. So the verb has to answer three
things the store does not:

* *there is nothing playing* -- which is a sentence, not a silent no-op;
* *there is already a bookmark within a second or two of here* -- somebody
  pressed the key twice, and a second bookmark 900 ms after the first is a
  duplicate wearing a different timestamp;
* *what is this thing called?* -- the title is written onto the row rather than
  resolved later, because a shared list has to name a station QUILL Cast has
  never heard of.

wx-free, strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core import bookmark_anchors
from quill.core.media.bookmarks import MediaBookmark, format_bookmark_line
from quill.core.media.timecode import format_timecode

#: Two bookmarks closer together than this are the same bookmark. Generous,
#: because the gesture is "mark here" and nobody means two marks two seconds
#: apart -- and because a double keypress is the commonest way to make one.
DUPLICATE_WINDOW_MS = 3_000

NOTHING_PLAYING = "Nothing is playing, so there is no moment to bookmark."


def add(
    store: Any,
    anchor: str,
    position_ms: object,
    *,
    title: str = "",
    note: str = "",
    label: str = "",
) -> tuple[MediaBookmark | None, str]:
    """Drop a bookmark. Returns ``(bookmark or None, what to say)``.

    ``None`` with a sentence covers both refusals -- nothing anchored, and a
    duplicate -- so a caller never has to work out which happened to know
    whether to speak.
    """
    if not str(anchor or "").strip():
        return (None, NOTHING_PLAYING)
    where = _position(position_ms)
    existing = _near(store.list(anchor), where)
    if existing is not None and not note.strip() and not label.strip():
        return (None, f"There is already a bookmark at {spoken_position(existing.position_ms)}.")
    mark = store.add(anchor, where, label=label, note=note, title=title)
    named = f" in {title.strip()}" if title.strip() else ""
    return (mark, f"Bookmarked {spoken_position(where)}{named}.")


def remove(store: Any, anchor: str, position_ms: object) -> tuple[bool, str]:
    """Delete one bookmark. Returns ``(whether it existed, what to say)``."""
    where = _position(position_ms)
    if store.remove(anchor, where):
        return (True, f"Removed the bookmark at {spoken_position(where)}.")
    return (False, "That bookmark is no longer there.")


def share_text(anchor: str, mark: MediaBookmark) -> str:
    """One bookmark as text somebody else can use.

    The place, the note if there is one, and what it is in -- because the
    useful thing to hand over is not the note alone but *where in what* it
    points. The same argument ``episode_notes.format_note_for_sharing``
    makes, and the same shape, so a shared bookmark and a shared note read
    alike whichever surface produced them.
    """
    line = format_bookmark_line(mark.position_ms, note=mark.note or mark.label, title=mark.title)
    body = bookmark_anchors.body_of(anchor)
    kind = bookmark_anchors.kind_of(anchor)
    if kind in (bookmark_anchors.STATION, bookmark_anchors.VIDEO, bookmark_anchors.OTHER) and body:
        return f"{line}\n{body}"
    return line


def row_label(anchor: str, mark: MediaBookmark) -> str:
    """One list row, read aloud in the order somebody listens for it.

    Position first, because a list of bookmarks is scanned by *where*; then
    the note, which is why this one was kept; then what it is in, and last the
    kind, which only matters when two rows share a name.
    """
    parts = [spoken_position(mark.position_ms)]
    said = (mark.note or mark.label).strip()
    if said:
        parts.append(said.splitlines()[0])
    if mark.title.strip():
        parts.append(mark.title.strip())
    parts.append(bookmark_anchors.label_for(anchor))
    return ", ".join(parts)


def spoken_position(position_ms: object) -> str:
    """``1 hour 2 minutes 3 seconds`` -- said, not written.

    A screen reader given ``1:02:03`` reads punctuation. Every announcement in
    the podcast and radio stacks spells the units out for exactly that reason,
    and a bookmark is announced far more often than it is written down.
    """
    total = max(0, _position(position_ms)) // 1000
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'' if seconds == 1 else 's'}")
    return " ".join(parts)


def written_position(position_ms: object) -> str:
    """``1:02:03`` -- for the clipboard and for a written list."""
    return format_timecode(max(0, _position(position_ms)), always_hours=False)


def summarise(rows: list[tuple[str, MediaBookmark]]) -> str:
    """What the list window says when it opens."""
    if not rows:
        return "No bookmarks yet. Bookmark This Moment while something is playing."
    anchors = len({anchor for anchor, _mark in rows})
    thing = "thing" if anchors == 1 else "things"
    return f"{len(rows)} bookmark{'' if len(rows) == 1 else 's'} across {anchors} {thing}."


def _near(marks: list[MediaBookmark], position_ms: int) -> MediaBookmark | None:
    for mark in marks:
        if abs(mark.position_ms - position_ms) <= DUPLICATE_WINDOW_MS:
            return mark
    return None


def _position(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


__all__ = [
    "DUPLICATE_WINDOW_MS",
    "NOTHING_PLAYING",
    "add",
    "remove",
    "row_label",
    "share_text",
    "spoken_position",
    "summarise",
    "written_position",
]
