"""Search YouTube with Filters: upload date, length, sort order, type -- and YouTube Music.

YouTube's own Filters menu encodes every choice into one ``sp`` parameter on
its results page: a tiny protocol-buffer message, base64 encoded. Search
YouTube... (:mod:`quill.core.radio.youtube_search`) uses the three one-filter
values for type; this module builds the combined value for any mix of

* **sort** (field 1): relevance, upload date, view count, rating;
* **upload date** (field 2.1): last hour, today, this week, this month, this year;
* **type** (field 2.2): video, channel, playlist;
* **duration** (field 2.3): under 4 minutes, 4 to 20 minutes, over 20 minutes;
* **live** (field 2.8): only what is live now,

so the answer is the page YouTube itself would show with those filters set.
yt-dlp reads it with the same flat results-page extractor, one request.

**YouTube Music** is a second source: yt-dlp reads ``music.youtube.com``'s
search page too, and its *Songs* section answers with songs rather than music
videos. Those rows play through the same resolver as any YouTube video.

wx-free, strict-typed. The only network call is
:func:`quill.core.radio.youtube_requests.run`.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import quote, quote_plus

from quill.core.radio.youtube_requests import Fetch, run
from quill.core.radio.youtube_search import (
    CHANNEL,
    PLAYLIST,
    TYPE_LABELS,
    VIDEO,
    YouTubeResult,
    parse_results,
)

YOUTUBE = "youtube"
MUSIC = "music"

#: ``(value, what the chooser reads)``. The first of each is "no filter".
SOURCES: tuple[tuple[str, str], ...] = ((YOUTUBE, "YouTube"), (MUSIC, "YouTube Music songs"))
SORTS: tuple[tuple[int, str], ...] = (
    (0, "Relevance"),
    (2, "Upload date, newest first"),
    (3, "View count"),
    (1, "Rating"),
)
DATES: tuple[tuple[int, str], ...] = (
    (0, "Any time"),
    (1, "Last hour"),
    (2, "Today"),
    (3, "This week"),
    (4, "This month"),
    (5, "This year"),
)
DURATIONS: tuple[tuple[int, str], ...] = (
    (0, "Any length"),
    (1, "Under 4 minutes"),
    (3, "4 to 20 minutes"),
    (2, "Over 20 minutes"),
)
#: Type values as YouTube numbers them, and "live" as its own feature flag.
LIVE = "live"
TYPES: tuple[tuple[str, str], ...] = (
    (VIDEO, "Videos"),
    (LIVE, "Live now"),
    (PLAYLIST, "Playlists"),
    (CHANNEL, "Channels"),
)
_TYPE_NUMBERS = {VIDEO: 1, LIVE: 1, CHANNEL: 2, PLAYLIST: 3}

#: How many rows one filtered search asks for.
LIMIT = 30


@dataclass(frozen=True, slots=True)
class Filters:
    """What the listener chose. Defaults are YouTube's own: no filter at all."""

    source: str = YOUTUBE
    kind: str = VIDEO
    sort: int = 0
    upload_date: int = 0
    duration: int = 0

    @property
    def result_kind(self) -> str:
        return VIDEO if self.kind == LIVE or self.source == MUSIC else self.kind

    def describe(self) -> str:
        """The filters in words, for the spoken summary (pure)."""
        if self.source == MUSIC:
            return "YouTube Music songs"
        words = [dict(TYPES)[self.kind].lower()]
        if self.upload_date:
            words.append(dict(DATES)[self.upload_date].lower())
        if self.duration:
            words.append(dict(DURATIONS)[self.duration].lower())
        if self.sort:
            words.append("sorted by " + dict(SORTS)[self.sort].split(",")[0].lower())
        return ", ".join(words)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def sp_value(filters: Filters) -> str:
    """The base64 ``sp`` value for *filters*, URL-quoted (pure).

    ``Filters(kind=VIDEO)`` gives ``EgIQAQ%3D%3D`` -- the same value Search
    YouTube... uses for videos, which is how the encoder is checked.
    """
    inner = bytearray()
    if filters.upload_date:
        inner += b"\x08" + _varint(filters.upload_date)
    inner += b"\x10" + _varint(_TYPE_NUMBERS.get(filters.kind, 1))
    if filters.duration:
        inner += b"\x18" + _varint(filters.duration)
    if filters.kind == LIVE:
        inner += b"\x40\x01"
    message = bytearray()
    if filters.sort:
        message += b"\x08" + _varint(filters.sort)
    message += b"\x12" + _varint(len(inner)) + bytes(inner)
    return quote(base64.b64encode(bytes(message)).decode("ascii"), safe="")


def search_url(query: str, filters: Filters) -> str:
    """The results page for *query* under *filters* (pure)."""
    words = query.strip()
    if filters.source == MUSIC:
        return f"https://music.youtube.com/search?q={quote_plus(words)}#songs"
    return (
        f"https://www.youtube.com/results?search_query={quote_plus(words)}&sp={sp_value(filters)}"
    )


def search(
    query: str, filters: Filters, *, fetch: Fetch | None = None, limit: int = LIMIT
) -> list[YouTubeResult]:
    """One filtered search; raises ``YouTubeRequestError`` with a reason."""
    if not query.strip():
        return []
    info = run(
        search_url(query, filters),
        {"extract_flat": "in_playlist", "playlistend": limit},
        fetch=fetch,
    )
    found = parse_results(info, filters.result_kind, cap=limit)
    if filters.kind == LIVE:
        found = [result for result in found if result.is_live] or found
    return found


def summary(count: int, filters: Filters) -> str:
    """What is said when the answer arrives (pure)."""
    noun = TYPE_LABELS.get(filters.result_kind, "result").lower()
    if not count:
        return f"Nothing found on YouTube for those filters ({filters.describe()})."
    return f"{count} {noun}{'' if count == 1 else 's'} found, {filters.describe()}."


__all__ = [
    "DATES",
    "DURATIONS",
    "LIVE",
    "MUSIC",
    "SORTS",
    "SOURCES",
    "TYPES",
    "YOUTUBE",
    "Filters",
    "search",
    "search_url",
    "sp_value",
    "summary",
]
