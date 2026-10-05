"""What a YouTube video or channel says about itself, in words.

Behind the **YouTube Video** window and **About This Channel**: one yt-dlp
request answers with a video's description, its channel, whether it is live,
finished or still to come, and -- for a premiere or a scheduled stream -- when
it starts. This module turns that answer into what a listener reads:

* the description, whole;
* the **moments** in it: every line of the description that carries a time
  ("12:40 The interview"), as a list a listener can press Enter on to jump;
* a **countdown** for something not started yet: "Starts in 2 hours 5 minutes".

wx-free, strict-typed. The single network call is
:func:`quill.core.radio.youtube_requests.run`.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from quill.core.radio.youtube_requests import Fetch, run

_STAMP = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")


@dataclass(frozen=True, slots=True)
class Moment:
    seconds: int
    label: str

    @property
    def clock(self) -> str:
        hours, rest = divmod(self.seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class VideoInfo:
    video_id: str = ""
    title: str = ""
    channel: str = ""
    channel_url: str = ""
    description: str = ""
    #: yt-dlp's ``live_status``: is_live, is_upcoming, was_live, not_live, post_live.
    live_status: str = ""
    #: When an upcoming video starts, seconds since the epoch; 0 = not said.
    starts_at: float = 0.0
    duration: int = 0
    views: int = 0
    likes: int = 0
    moments: tuple[Moment, ...] = field(default_factory=tuple)

    @property
    def is_live(self) -> bool:
        return self.live_status == "is_live"

    @property
    def is_upcoming(self) -> bool:
        return self.live_status == "is_upcoming"

    @property
    def has_chat(self) -> bool:
        return self.live_status in ("is_live", "is_upcoming", "was_live", "post_live")


def moments_in(description: str) -> list[Moment]:
    """Every description line carrying a time, as a jump list (pure).

    The time is taken out of the label so the row reads "The interview, 12:40"
    rather than "12:40 The interview"; a line with only a time keeps the time.
    Times out of order are kept in the order written -- that is what the
    uploader meant.
    """
    found: list[Moment] = []
    for line in description.splitlines():
        match = _STAMP.search(line)
        if not match:
            continue
        hours = int(match.group(1) or 0)
        minutes, seconds = int(match.group(2)), int(match.group(3))
        if seconds > 59 or (hours and minutes > 59):
            continue
        total = hours * 3600 + minutes * 60 + seconds
        label = (line[: match.start()] + line[match.end() :]).strip(" -|:–—\t")
        found.append(Moment(total, label or line.strip()))
    return found


def countdown(starts_at: float, *, now: float | None = None) -> str:
    """ "Starts in 2 hours 5 minutes" -- or "Starting any moment now" (pure)."""
    if starts_at <= 0:
        return "Not started yet; YouTube has not said when it starts."
    left = int(starts_at - (time.time() if now is None else now))
    if left <= 60:
        return "Starting any moment now."
    days, rest = divmod(left, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} day{'' if days == 1 else 's'}")
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes and not days:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    return "Starts in " + " ".join(parts) + "."


def state_sentence(info: VideoInfo, *, now: float | None = None) -> str:
    """One line on what this video is right now (pure)."""
    if info.is_live:
        return "Live now."
    if info.is_upcoming:
        return countdown(info.starts_at, now=now)
    if info.live_status in ("was_live", "post_live"):
        return "A finished live stream."
    if info.duration:
        minutes = max(1, round(info.duration / 60))
        return f"A video, {minutes} minute{'' if minutes == 1 else 's'} long."
    return "A video."


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


def parse_info(raw: dict[str, object]) -> VideoInfo:
    """yt-dlp's answer for one video, as :class:`VideoInfo` (pure)."""
    description = str(raw.get("description") or "")
    starts = raw.get("release_timestamp") or 0
    return VideoInfo(
        video_id=str(raw.get("id") or ""),
        title=str(raw.get("title") or "").strip(),
        channel=str(raw.get("channel") or raw.get("uploader") or "").strip(),
        channel_url=str(raw.get("channel_url") or raw.get("uploader_url") or ""),
        description=description.strip(),
        live_status=str(raw.get("live_status") or ""),
        starts_at=float(starts) if isinstance(starts, (int, float)) else 0.0,
        duration=_int(raw.get("duration")),
        views=_int(raw.get("view_count")),
        likes=_int(raw.get("like_count")),
        moments=tuple(moments_in(description)),
    )


def fetch_video(url: str, *, fetch: Fetch | None = None) -> VideoInfo:
    """One video's details. Nothing is downloaded, no format is chosen."""
    raw = run(url, {"noplaylist": True, "ignore_no_formats_error": True}, fetch=fetch)
    return parse_info(raw)


def about_text(raw: dict[str, object]) -> str:
    """A channel's About page in words (pure)."""
    from quill.core.radio.youtube_search import count_words

    name = str(raw.get("channel") or raw.get("uploader") or raw.get("title") or "This channel")
    lines = [name]
    followers = _int(raw.get("channel_follower_count"))
    if followers:
        lines.append(f"{count_words(followers)} subscriber{'' if followers == 1 else 's'}.")
    handle = str(raw.get("uploader_id") or "")
    if handle.startswith("@"):
        lines.append(f"Handle: {handle}")
    description = str(raw.get("description") or "").strip()
    lines.append("")
    lines.append(description or "The channel has not written a description.")
    return "\n".join(lines)


def fetch_about(channel_url: str, *, fetch: Fetch | None = None) -> str:
    """A channel's name, subscribers and description, from its page."""
    from quill.core.radio.youtube_channels import normalize_channel_url

    base = normalize_channel_url(channel_url) or channel_url.rstrip("/")
    raw = run(base, {"extract_flat": True, "playlistend": 1}, fetch=fetch)
    return about_text(raw)


__all__ = [
    "Moment",
    "VideoInfo",
    "about_text",
    "countdown",
    "fetch_about",
    "fetch_video",
    "moments_in",
    "parse_info",
    "state_sentence",
]
