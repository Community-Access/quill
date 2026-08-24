"""Saved YouTube playlists and single videos -- the YouTube branch's shelf.

The channels a listener follows already persist (``youtube_channels``), but a
single video or a playlist somebody handed them as a link had nowhere to
live: the browse tree could only reach one through a channel, and the QA pass
called out that a pasted YouTube link had no easy way in. This store is that
way in -- paste the link once (browse tree action row, or Station > Add
YouTube Link...) and it becomes a permanent row under YouTube.

**A saved row carries the video's own facts, not its address.** Until now it
carried only the URL, so the shelf read back as
"https://www.youtube.com/watch?v=iG9CE55wbtY" -- eleven characters of random
id spelled out one at a time by a screen reader, for a row whose whole job is
to be recognised at a glance (reported 2026-08-23). :func:`fetch_video_details`
asks YouTube once, at add time, for the title, the channel, the length and the
description; they are stored beside the URL and are what the tree, the spoken
row note, and the details panel show from then on. The fetch is the *only*
network thing in this module and it is optional: a video whose details cannot
be read is still saved, still plays, and simply falls back to its address.

Same contract as ``youtube_channels.ChannelStore``: pure URL normalization up
front, one small JSON file, no Google account and no API key anywhere.
wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quill.core.paths import app_data_dir
from quill.core.radio.youtube_urls import canonical_youtube_url, is_youtube_url, youtube_video_id
from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-youtube-saved.json"

VIDEO = "video"
PLAYLIST = "playlist"

#: How much of a description is kept. YouTube descriptions run to link farms,
#: sponsor reads and full transcripts; a details panel is not a web page, and
#: nobody arrowing through one wants four thousand lines of it.
DESCRIPTION_LIMIT = 2000


@dataclass(frozen=True, slots=True)
class SavedItem:
    """One saved playlist or video, with whatever YouTube told us about it."""

    kind: str  # VIDEO | PLAYLIST
    url: str
    name: str = ""
    #: The uploading channel (a video) -- "TED", "BBC Radio 4".
    uploader: str = ""
    #: Length in milliseconds. 0 for a live broadcast, and for a playlist.
    duration_ms: int = 0
    #: True when the link is a broadcast that is simply on, rather than a
    #: finished video that seeks and resumes.
    is_live: bool = False
    #: The publisher's own description, plain text, capped.
    description: str = ""
    #: How many videos a saved playlist holds, when that is known. 0 = unknown.
    item_count: int = 0

    @property
    def display_name(self) -> str:
        return self.name or self.url

    @property
    def note(self) -> str:
        """Spoken after the label in the tree -- "TED, 20 minutes 3 seconds".

        The browse tree's own idiom for "what else is worth knowing before you
        press Enter". Empty when nothing is known, which is exactly how the row
        behaved before the details were fetched at all.
        """
        from quill.core.speech_text import speak_duration

        parts = [self.uploader] if self.uploader else []
        if self.is_live:
            parts.append("live")
        elif self.duration_ms > 0:
            parts.append(speak_duration(self.duration_ms / 1000.0))
        if self.item_count:
            parts.append(f"{self.item_count} video{'' if self.item_count == 1 else 's'}")
        return ", ".join(parts)


def normalize_playlist_url(url: str) -> str:
    """A canonical playlist URL from whatever was pasted (pure), or ``""``.

    Accepts ``/playlist?list=ID`` and a watch link that carries ``list=`` --
    here the listener is explicitly saving *a playlist*, so unlike playback
    (where a watch link means the video), the ``list=`` parameter is the part
    they mean.
    """
    candidate = (url or "").strip()
    if not candidate.lower().startswith(("http://", "https://")):
        return ""
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return ""
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host not in ("youtube.com", "music.youtube.com"):
        return ""
    values = parse_qs(parsed.query).get("list") or [""]
    playlist_id = values[0].strip()
    return f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else ""


def normalize_video_url(url: str) -> str:
    """A canonical single-video URL (pure), or ``""``.

    Anything :func:`is_youtube_url` can play qualifies -- watch links,
    ``youtu.be``, shorts, embeds, and channel-live pages (which have no video
    id but are exactly the "station that broadcasts on YouTube" case).
    """
    candidate = (url or "").strip()
    if not is_youtube_url(candidate):
        return ""
    canonical = canonical_youtube_url(candidate)
    # A watch link with no parseable id is a malformed link, not a video.
    if "/watch" in canonical and not youtube_video_id(canonical):
        return ""
    return canonical


def classify_link(url: str) -> tuple[str, str]:
    """``(kind, canonical)`` for whatever YouTube link was pasted (pure).

    Kind is ``"playlist"``, ``"video"``, ``"channel"``, or ``""`` for a link
    this module cannot place. Precedence: an explicit ``/playlist`` link is a
    playlist; anything playable (watch, youtu.be, shorts, a channel's /live
    page) is a video; a bare channel page is a channel. So ``@name`` follows
    the channel while ``@name/live`` saves the broadcast, which is what each
    of those links names.
    """
    playlist = normalize_playlist_url(url)
    if playlist:
        return PLAYLIST, playlist
    video = normalize_video_url(url)
    if video:
        return VIDEO, video
    from quill.core.radio.youtube_channels import normalize_channel_url

    channel = normalize_channel_url(url)
    return ("channel", channel) if channel else ("", "")


def clean_description(text: str) -> str:
    """A description fit for a details panel (pure): trimmed and capped.

    Blank runs collapse to one blank line -- YouTube descriptions are padded
    with them, and a screen reader reads every one of them as a pause.
    """
    lines = [line.rstrip() for line in (text or "").replace("\r\n", "\n").split("\n")]
    cleaned: list[str] = []
    for line in lines:
        if not line and cleaned and not cleaned[-1]:
            continue
        cleaned.append(line)
    joined = "\n".join(cleaned).strip()
    if len(joined) <= DESCRIPTION_LIMIT:
        return joined
    return joined[:DESCRIPTION_LIMIT].rstrip() + "..."


def details_from_stream(url: str, stream: object) -> SavedItem:
    """A :class:`SavedItem` from a resolved :class:`~quill.core.radio.youtube.YouTubeStream`
    (pure).

    Split from the fetch so everything this records is testable without
    yt-dlp, the network, or a consent prompt.
    """
    duration = int(getattr(stream, "duration_ms", 0) or 0)
    is_live = bool(getattr(stream, "is_live", False))
    return SavedItem(
        kind=VIDEO,
        url=url,
        name=str(getattr(stream, "title", "") or "").strip(),
        uploader=str(getattr(stream, "uploader", "") or "").strip(),
        duration_ms=0 if is_live else max(0, duration),
        is_live=is_live,
        description=clean_description(str(getattr(stream, "description", "") or "")),
    )


def fetch_video_details(url: str, *, resolver: object = None) -> SavedItem:
    """Ask YouTube what this video *is* -- one request, at add time.

    The same resolve playing the link would make, so a video that cannot be
    played is found out now rather than after it has been filed as an
    unreadable address. Raises whatever
    :func:`~quill.core.radio.youtube.ensure_and_resolve` raises (Safe Mode, no
    yt-dlp, a private or removed video); callers keep the row and fall back to
    the URL. ``resolver`` is injectable for tests.
    """
    from quill.core.radio.youtube import ensure_and_resolve

    canonical = normalize_video_url(url)
    if not canonical:
        return SavedItem(kind=VIDEO, url=(url or "").strip())
    stream = ensure_and_resolve(canonical, resolver=resolver)  # type: ignore[arg-type]
    return details_from_stream(canonical, stream)


def fetch_playlist_details(url: str, *, resolver: object = None) -> SavedItem:
    """The playlist's own name and how many videos are in it (one flat request).

    Flat, like every other playlist listing here: no video's audio is resolved
    to learn what the list is called.
    """
    from quill.core.radio.youtube import resolve_youtube_playlist_details

    canonical = normalize_playlist_url(url)
    if not canonical:
        return SavedItem(kind=PLAYLIST, url=(url or "").strip())
    title, entries = resolve_youtube_playlist_details(canonical, resolver=resolver)  # type: ignore[arg-type]
    return SavedItem(
        kind=PLAYLIST,
        url=canonical,
        name=str(title or "").strip(),
        item_count=len(entries),
    )


class SavedStore:
    """The saved playlists and videos, in the order they were added."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir

    def _path(self) -> Path:
        return (self._dir or app_data_dir()) / _FILE_NAME

    def all(self, kind: str | None = None) -> list[SavedItem]:
        try:
            data = read_json(self._path(), [])
        except OSError:
            return []
        items: list[SavedItem] = []
        for row in data if isinstance(data, list) else []:
            if not isinstance(row, dict):
                continue
            row_kind = str(row.get("kind", ""))
            url = str(row.get("url", "")).strip()
            if row_kind in (VIDEO, PLAYLIST) and url:
                items.append(
                    SavedItem(
                        kind=row_kind,
                        url=url,
                        name=str(row.get("name", "")).strip(),
                        uploader=str(row.get("uploader", "")).strip(),
                        duration_ms=_as_int(row.get("duration_ms")),
                        is_live=bool(row.get("is_live", False)),
                        description=str(row.get("description", "")).strip(),
                        item_count=_as_int(row.get("item_count")),
                    )
                )
        return [i for i in items if kind is None or i.kind == kind]

    def add(self, kind: str, url: str, name: str = "") -> SavedItem | None:
        """Save a playlist or video. ``None`` when the address is not one."""
        canonical = normalize_playlist_url(url) if kind == PLAYLIST else normalize_video_url(url)
        if not canonical:
            return None
        items = self.all()
        for existing in items:
            if existing.url == canonical:
                return existing
        item = SavedItem(kind=kind, url=canonical, name=name.strip())
        self._write([*items, item])
        return item

    def describe(self, details: SavedItem) -> SavedItem | None:
        """Fill in a saved row's title and facts, keeping its place in the list.

        Called when the add-time fetch lands. The URL is the identity, so a
        row the listener removed while the request was in flight is *not*
        resurrected -- ``None`` says so.
        """
        items = self.all()
        found = next((i for i in items if i.url == details.url), None)
        if found is None:
            return None
        updated = replace(
            found,
            name=details.name or found.name,
            uploader=details.uploader or found.uploader,
            duration_ms=details.duration_ms or found.duration_ms,
            is_live=details.is_live,
            description=details.description or found.description,
            item_count=details.item_count or found.item_count,
        )
        self._write([updated if i.url == details.url else i for i in items])
        return updated

    def remove(self, url: str) -> None:
        wanted = (url or "").strip()
        self._write([i for i in self.all() if i.url != wanted])

    def _write(self, items: list[SavedItem]) -> None:
        try:
            write_json_atomic(
                self._path(),
                [
                    {
                        "kind": i.kind,
                        "url": i.url,
                        "name": i.name,
                        "uploader": i.uploader,
                        "duration_ms": i.duration_ms,
                        "is_live": i.is_live,
                        "description": i.description,
                        "item_count": i.item_count,
                    }
                    for i in items
                ],
            )
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return


def _as_int(value: object) -> int:
    """A non-negative int from stored JSON, or 0. Never raises."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))
