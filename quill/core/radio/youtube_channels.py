"""Follow a YouTube channel without a Google account.

Paste a channel address once and it becomes a permanent branch: its uploads and
its playlists as folders, the videos inside them as rows you can play. No
subscription, no login, no API key, no Google account -- which for a listener who
follows a lecture series, a talk show, or a station that only publishes to
YouTube is the whole feature.

This is the closest thing to a podcast subscription that YouTube offers a
keyless client, and it is built on machinery Quill Radio already has: yt-dlp
enumerates a channel exactly as it resolves a single video, the consent gate and
the rights notice already exist, and **Station > Update YouTube Support...**
already repairs extraction when YouTube changes something.

Enumeration is **flat** (``extract_flat``): it lists what is there without
resolving each video's stream, so opening a channel with four thousand uploads
costs one request rather than four thousand. A video's real stream is resolved
when it is played, by the same path a pasted link takes.

It is also **paged**, with a ``More...`` node, for the same reason: a channel
with four thousand uploads must not try to be one level of a tree.

yt-dlp is never bundled and is not a dependency of this module -- it installs on
demand after the existing one-time consent, and its absence is reported as
"YouTube support is not installed" rather than an import error. Safe Mode
refuses before anything is attempted. wx-free, strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir
from quill.core.radio.models import RadioStation
from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-youtube-channels.json"

#: How many entries one level shows before offering "More...".
PAGE_SIZE = 50

#: A channel address in any of the forms a listener actually has: a handle, a
#: /channel/ id, a legacy /user/ or /c/ vanity name.
_CHANNEL_RE = re.compile(
    r"(?:youtube\.com/)(?:(?P<handle>@[\w.-]+)|(?:channel|user|c)/(?P<id>[\w.-]+))",
    re.IGNORECASE,
)


class YouTubeChannelsError(CodedError):
    """A channel could not be read (yt-dlp missing, network, or Safe Mode)."""

    code = "QUILL-RADIO-YTCHANNEL-REQUEST"


@dataclass(frozen=True, slots=True)
class Channel:
    """One channel the listener added."""

    url: str
    name: str = ""

    @property
    def display_name(self) -> str:
        return self.name or normalize_channel_url(self.url) or self.url


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`YouTubeChannelsError` when Safe Mode is active."""
    if safe_mode:
        raise YouTubeChannelsError(
            "YouTube channels are disabled in Safe Mode. Restart QUILL normally to browse them."
        )


def normalize_channel_url(url: str) -> str:
    """A canonical channel URL from whatever was pasted (pure), or ``""``.

    A bare ``@handle`` is accepted too, because that is what people copy out of
    a video description. A *video* link is deliberately rejected: it names a
    video, not a channel, and silently turning one into the other would follow
    a channel the listener never chose.
    """
    value = (url or "").strip()
    if not value:
        return ""
    if value.startswith("@") and "/" not in value:
        return f"https://www.youtube.com/{value}"
    match = _CHANNEL_RE.search(value)
    if not match:
        return ""
    if match.group("handle"):
        return f"https://www.youtube.com/{match.group('handle')}"
    kind = (
        "channel" if "/channel/" in value.lower() else "user" if "/user/" in value.lower() else "c"
    )
    return f"https://www.youtube.com/{kind}/{match.group('id')}"


class ChannelStore:
    """The channels a listener follows, in the order they added them."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir

    def _path(self) -> Path:
        return (self._dir or app_data_dir()) / _FILE_NAME

    def all(self) -> list[Channel]:
        try:
            data = read_json(self._path(), [])
        except OSError:
            return []
        channels: list[Channel] = []
        for row in data if isinstance(data, list) else []:
            if not isinstance(row, dict):
                continue
            url = normalize_channel_url(str(row.get("url", "")))
            if url:
                channels.append(Channel(url=url, name=str(row.get("name", "")).strip()))
        return channels

    def add(self, url: str, name: str = "") -> Channel | None:
        """Follow a channel. ``None`` when the address is not one."""
        canonical = normalize_channel_url(url)
        if not canonical:
            return None
        channels = self.all()
        for existing in channels:
            if existing.url == canonical:
                return existing
        channel = Channel(url=canonical, name=name.strip())
        self._write([*channels, channel])
        return channel

    def remove(self, url: str) -> None:
        wanted = normalize_channel_url(url)
        self._write([c for c in self.all() if c.url != wanted])

    def rename(self, url: str, name: str) -> None:
        wanted = normalize_channel_url(url)
        self._write([
            Channel(url=c.url, name=name.strip()) if c.url == wanted else c for c in self.all()
        ])

    def _write(self, channels: list[Channel]) -> None:
        try:
            write_json_atomic(self._path(), [{"url": c.url, "name": c.name} for c in channels])
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return


# --- enumeration --------------------------------------------------------------


def _flat_entries(url: str, *, limit: int, offset: int) -> tuple[str, list[dict]]:
    """``(title, entries)`` for a channel or playlist page, without resolving.

    ``extract_flat`` is what makes this affordable: it reads the listing and
    stops, so a four-thousand-video channel costs one request instead of four
    thousand stream resolutions nobody asked for.
    """
    try:
        import yt_dlp
    except ImportError as error:
        raise YouTubeChannelsError(
            "YouTube support is not installed. Use Station, Update YouTube Support to add it."
        ) from error
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playliststart": offset + 1,
        "playlistend": offset + limit,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:  # noqa: BLE001 - yt-dlp raises many shapes
        raise YouTubeChannelsError(f"Could not read that channel: {error}") from error
    if not isinstance(info, dict):
        return "", []
    entries = [entry for entry in (info.get("entries") or []) if isinstance(entry, dict)]
    return str(info.get("title", "") or ""), entries


def _is_playlist(entry: dict) -> bool:
    kind = str(entry.get("_type", "") or "").lower()
    url = str(entry.get("url", "") or "")
    return kind in ("playlist", "url") and ("list=" in url or "/playlist" in url)


def playlists(channel_url: str, *, safe_mode: bool = False) -> list[tuple[str, str]]:
    """A channel's playlists as ``(title, url)`` (one flat request)."""
    refuse_in_safe_mode(safe_mode)
    canonical = normalize_channel_url(channel_url)
    if not canonical:
        return []
    _title, entries = _flat_entries(f"{canonical}/playlists", limit=PAGE_SIZE, offset=0)
    found: list[tuple[str, str]] = []
    for entry in entries:
        title = str(entry.get("title", "") or "").strip()
        url = str(entry.get("url", "") or "").strip()
        if title and url:
            found.append((title, url))
    return found


def videos(url: str, *, page: int = 1, safe_mode: bool = False) -> tuple[list[RadioStation], bool]:
    """``(videos, there_are_more)`` for a channel's uploads or one playlist.

    Each row's stream URL is the *page* address, never a resolved stream:
    YouTube's stream addresses expire after a few hours, so a saved favourite
    has to be re-resolved at play time. This is the same rule Add Custom Station
    already follows for a pasted link.
    """
    refuse_in_safe_mode(safe_mode)
    target = normalize_channel_url(url) or url.strip()
    if not target:
        return [], False
    if target.startswith("https://www.youtube.com/") and "list=" not in target:
        target = f"{target}/videos"
    offset = max(0, (page - 1) * PAGE_SIZE)
    # One extra row tells us whether there is another page, without a second
    # request and without claiming a total we cannot know.
    _title, entries = _flat_entries(target, limit=PAGE_SIZE + 1, offset=offset)
    more = len(entries) > PAGE_SIZE
    rows: list[RadioStation] = []
    for entry in entries[:PAGE_SIZE]:
        if _is_playlist(entry):
            continue
        title = str(entry.get("title", "") or "").strip()
        video_id = str(entry.get("id", "") or "").strip()
        if not title or not video_id:
            continue
        duration = entry.get("duration")
        rows.append(
            RadioStation(
                name=title,
                stream_url=f"https://www.youtube.com/watch?v={video_id}",
                homepage=f"https://www.youtube.com/watch?v={video_id}",
                source="YouTube",
                # A finished video is a recording: it seeks, reports position,
                # and remembers where you stopped. A live stream is not, and
                # yt-dlp reports no duration for one.
                is_recording=bool(isinstance(duration, (int, float)) and duration > 0),
            )
        )
    return rows, more
