"""What a bookmark is attached to, said one way (list.md 4.3, 4.5).

A bookmark is a position plus *the thing the position is in*. QUILL had two
answers to the second half and no way to write a third:

* ``core/media/bookmarks.py`` keyed by a book's resume key -- an opaque string,
  which is exactly the right shape and was documented as belonging to books;
* ``core/podcasts/episode_notes.py`` keyed by ``show_id`` plus ``episode_guid``,
  its own store, its own file;
* and nothing at all for a station, a YouTube row or a recording, which is most
  of what Quill Radio actually plays.

Three stores would have meant three list windows, and a bookmark made in one
app invisible in the other -- the thing 4.5 exists to prevent. So there is one
store, and this is its vocabulary: **every playable thing reduces to one anchor
string**, and the store neither knows nor cares which kind it got.

The anchors are deliberately human-readable rather than hashed. A bookmarks
file somebody opens should say ``podcast:the-daily|ep-412``, not forty hex
characters: it is their data, on their disk, and a store you cannot read is a
store you cannot repair.

**A podcast episode anchors the same way from either app.** That is the whole
of 4.5 -- Quill Radio and QUILL Cast build the identical string for the
identical episode, so a bookmark dropped in one is in the other's list with no
sync, no merge and no protocol. The same trick ``radio_listens`` and
``cross_app_resume`` already play with positions.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

#: The kinds. Written into the anchor so a list window can group and name rows
#: without resolving anything, and so an unknown kind from a future version
#: reads as "something else" rather than as corruption.
PODCAST = "podcast"
STATION = "station"
VIDEO = "video"
RECORDING = "recording"
BOOK = "book"
OTHER = "media"

KINDS: tuple[str, ...] = (PODCAST, STATION, VIDEO, RECORDING, BOOK, OTHER)

#: Separates kind from body. A colon rather than a slash so the body can be a
#: URL without the anchor reading as one.
_SEP = ":"
#: Separates the two halves of a podcast anchor.
_PART = "|"

#: Human names, for a list window that groups by kind.
KIND_LABELS: dict[str, str] = {
    PODCAST: "Podcast episode",
    STATION: "Station",
    VIDEO: "Video",
    RECORDING: "Recording",
    BOOK: "Book",
    OTHER: "Media",
}


def for_episode(show_id: object, episode_guid: object) -> str:
    """The anchor for a podcast episode -- identical in Radio and in Cast.

    Empty when either half is missing: an anchor that names half an episode
    would collect bookmarks from every episode of that show.
    """
    show = _clean(show_id)
    guid = _clean(episode_guid)
    if not show or not guid:
        return ""
    return f"{PODCAST}{_SEP}{show}{_PART}{guid}"


def for_station(stream_url: object) -> str:
    """The anchor for a live station, by its stream address.

    The stream URL rather than the station's name or uuid: a favourite renamed
    is the same station, and the same station reached through two directories
    has two uuids and one address.
    """
    return _url_anchor(STATION, stream_url)


def for_video(url: object) -> str:
    """A YouTube (or other video) row, by its address."""
    return _url_anchor(VIDEO, url)


def for_recording(path: object) -> str:
    """A recording on this disk, by its path.

    Local, and deliberately so: a recording is not shared between machines, so
    a bookmark in one is meaningless in another. It still lives in the one
    store, because the *list* is shared even when a row is not portable.
    """
    return _url_anchor(RECORDING, path)


def for_book(book_key: object) -> str:
    """An audiobook, by the resume key the Media Player already uses.

    Passed through unchanged rather than re-derived: the Media Player's
    existing bookmarks are keyed by it, and a migration that renamed everybody's
    keys would lose every bookmark it could not translate.
    """
    body = _clean(book_key)
    return f"{BOOK}{_SEP}{body}" if body else ""


def for_media(url: object) -> str:
    """Anything else playable, by address. The fallback, not the default."""
    return _url_anchor(OTHER, url)


def kind_of(anchor: object) -> str:
    """Which kind an anchor names, or ``media`` for anything unrecognised."""
    text = _clean(anchor)
    head, sep, _rest = text.partition(_SEP)
    if not sep:
        return OTHER
    return head if head in KINDS else OTHER


def episode_parts(anchor: object) -> tuple[str, str]:
    """``(show_id, episode_guid)`` for a podcast anchor, or two empty strings.

    Both halves or neither: a caller that got one would go looking for an
    episode in no show.
    """
    text = _clean(anchor)
    head, sep, rest = text.partition(_SEP)
    if not sep or head != PODCAST:
        return ("", "")
    show, part, guid = rest.partition(_PART)
    if not part or not show or not guid:
        return ("", "")
    return (show, guid)


def body_of(anchor: object) -> str:
    """Everything after the kind -- the URL, the path, or the key."""
    text = _clean(anchor)
    _head, sep, rest = text.partition(_SEP)
    return rest if sep else text


def label_for(anchor: object) -> str:
    """What kind of thing this is, in words, for a grouped list."""
    return KIND_LABELS.get(kind_of(anchor), KIND_LABELS[OTHER])


def is_portable(anchor: object) -> bool:
    """Whether this anchor still means something on another computer.

    A recording is one machine's file; everything else is an address or an id
    that travels. Used by setup transfer and by any sync so a bookmark that
    could only ever dangle is not carried across as if it would work.
    """
    return kind_of(anchor) != RECORDING


def _url_anchor(kind: str, value: object) -> str:
    body = _clean(value)
    return f"{kind}{_SEP}{body}" if body else ""


def _clean(value: object) -> str:
    return str(value or "").strip()


__all__ = [
    "BOOK",
    "KINDS",
    "KIND_LABELS",
    "OTHER",
    "PODCAST",
    "RECORDING",
    "STATION",
    "VIDEO",
    "body_of",
    "episode_parts",
    "for_book",
    "for_episode",
    "for_media",
    "for_recording",
    "for_station",
    "for_video",
    "is_portable",
    "kind_of",
    "label_for",
]
