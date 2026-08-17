"""Saved YouTube playlists and single videos -- the YouTube branch's shelf.

The channels a listener follows already persist (``youtube_channels``), but a
single video or a playlist somebody handed them as a link had nowhere to
live: the browse tree could only reach one through a channel, and the QA pass
called out that a pasted YouTube link had no easy way in. This store is that
way in -- paste the link once (browse tree action row, or Station > Add
YouTube Link...) and it becomes a permanent row under YouTube.

Same contract as ``youtube_channels.ChannelStore``: pure URL normalization up
front, one small JSON file, no Google account and no API key anywhere.
wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quill.core.paths import app_data_dir
from quill.core.radio.youtube_urls import canonical_youtube_url, is_youtube_url, youtube_video_id
from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-youtube-saved.json"

VIDEO = "video"
PLAYLIST = "playlist"


@dataclass(frozen=True, slots=True)
class SavedItem:
    """One saved playlist or video."""

    kind: str  # VIDEO | PLAYLIST
    url: str
    name: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.url


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
                name = str(row.get("name", "")).strip()
                items.append(SavedItem(kind=row_kind, url=url, name=name))
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

    def remove(self, url: str) -> None:
        wanted = (url or "").strip()
        self._write([i for i in self.all() if i.url != wanted])

    def _write(self, items: list[SavedItem]) -> None:
        try:
            write_json_atomic(
                self._path(), [{"kind": i.kind, "url": i.url, "name": i.name} for i in items]
            )
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return
