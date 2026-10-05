"""Skip Sponsor Segments: the community's SponsorBlock marks, used while a video plays.

SponsorBlock is a public, volunteer-kept list of the stretches of YouTube
videos that are sponsor reads, self-promotion, intros and the like. yt-dlp
uses it to cut or mark those stretches in a *download*; Quill Radio uses the
same list while a video *plays*, jumping over a marked stretch the moment
playback enters it and saying "Skipped a sponsor segment." once.

**Off by default**, and the listener chooses which kinds to skip. Turning it
on is the consent: the dialog says, before the switch is on, exactly what is
sent.

**What is sent.** Never the video's address and never anything about the
listener. Exactly as yt-dlp does it, the request carries only the first four
characters of a SHA-256 hash of the video's id; the server answers with every
video sharing that prefix, and the match is picked out here. So the
SponsorBlock server cannot tell which video is being watched.

The settings file holds two things -- whether it is on, and which kinds --
and nothing about any video.

wx-free, strict-typed. The single network call is :func:`fetch_segments`.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

API_URL = "https://sponsor.ajay.app/api/skipSegments"
_FILE_NAME = "radio-youtube-sponsorblock.json"
_TIMEOUT_SECONDS = 15.0

#: ``(SponsorBlock category, what the check box reads)``, in dialog order.
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("sponsor", "Sponsor reads"),
    ("selfpromo", "Self-promotion and merchandise"),
    ("interaction", "Reminders to like, subscribe or comment"),
    ("intro", "Intros and intermission animations"),
    ("outro", "End cards and credits"),
    ("preview", "Previews and recaps"),
    ("music_offtopic", "Talking in music videos"),
    ("filler", "Off-topic tangents"),
)

#: What is checked the first time somebody turns skipping on.
DEFAULT_CATEGORIES: tuple[str, ...] = ("sponsor", "selfpromo", "interaction")

#: The spoken noun for each category, after "Skipped".
SPOKEN: dict[str, str] = {
    "sponsor": "a sponsor segment",
    "selfpromo": "a self-promotion segment",
    "interaction": "a subscribe reminder",
    "intro": "the intro",
    "outro": "the end credits",
    "preview": "a preview",
    "music_offtopic": "a non-music section",
    "filler": "a tangent",
}


class SponsorBlockError(CodedError):
    """The SponsorBlock list could not be read."""

    code = "QUILL-RADIO-YOUTUBE-SPONSORBLOCK"


@dataclass(frozen=True, slots=True)
class SkipSettings:
    enabled: bool = False
    categories: tuple[str, ...] = DEFAULT_CATEGORIES


@dataclass(frozen=True, slots=True)
class Segment:
    start: float
    end: float
    category: str


def _path(data_dir: Path | None) -> Path:
    return (data_dir or app_data_dir()) / _FILE_NAME


def load(data_dir: Path | None = None) -> SkipSettings:
    """The stored choice, or the off default. Never raises."""
    try:
        raw = read_json(_path(data_dir), {})
    except OSError:
        return SkipSettings()
    if not isinstance(raw, dict):
        return SkipSettings()
    known = dict(CATEGORIES)
    picked = raw.get("categories")
    chosen = tuple(str(c) for c in (picked if isinstance(picked, list) else []) if str(c) in known)
    return SkipSettings(
        enabled=bool(raw.get("enabled", False)),
        categories=chosen if isinstance(picked, list) else DEFAULT_CATEGORIES,
    )


def save(settings: SkipSettings, data_dir: Path | None = None) -> None:
    try:
        write_json_atomic(
            _path(data_dir),
            {"enabled": settings.enabled, "categories": list(settings.categories)},
        )
    except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
        return


def hash_prefix(video_id: str) -> str:
    """The four hash characters that are all the server is told (pure)."""
    return hashlib.sha256(video_id.encode("ascii", errors="ignore")).hexdigest()[:4]


def request_url(video_id: str, categories: tuple[str, ...]) -> str:
    """The k-anonymous request for *video_id* (pure)."""
    query = urllib.parse.urlencode({
        "service": "YouTube",
        "categories": json.dumps(list(categories)),
        "actionTypes": json.dumps(["skip"]),
    })
    return f"{API_URL}/{hash_prefix(video_id)}?{query}"


def parse_segments(payload: object, video_id: str) -> list[Segment]:
    """The skip segments for *video_id* out of a prefix answer (pure)."""
    found: list[Segment] = []
    for video in payload if isinstance(payload, list) else []:
        if not isinstance(video, dict) or video.get("videoID") != video_id:
            continue
        for raw in video.get("segments") or []:
            if not isinstance(raw, dict):
                continue
            pair = raw.get("segment")
            if not (isinstance(pair, list) and len(pair) == 2):
                continue
            try:
                start, end = float(pair[0]), float(pair[1])
            except (TypeError, ValueError):
                continue
            if end - start >= 1.0 and raw.get("actionType", "skip") == "skip":
                found.append(Segment(max(0.0, start), end, str(raw.get("category", ""))))
    return sorted(found, key=lambda s: s.start)


Getter = Callable[[str], "tuple[int, bytes]"]


def fetch_segments(
    video_id: str, categories: tuple[str, ...], *, getter: Getter | None = None
) -> list[Segment]:
    """Ask SponsorBlock about *video_id* -- the reviewed egress site.

    A 404 is SponsorBlock's way of saying "nothing marked", and is an empty
    list, not an error. Refused in Safe Mode.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise SponsorBlockError("SponsorBlock is not used in Safe Mode.")
    if not video_id or not categories:
        return []
    url = request_url(video_id, categories)
    if getter is not None:
        status, raw = getter(url)
    else:
        from quill.core.net import verified_ssl_context

        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
            ) as resp:
                status, raw = int(resp.status or 200), resp.read()
        except urllib.error.HTTPError as error:
            status, raw = int(error.code), b""
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise SponsorBlockError("SponsorBlock could not be reached.") from error
    if status == 404:
        return []
    if status >= 400:
        raise SponsorBlockError(f"SponsorBlock did not answer (error {status}).")
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace") or "[]")
    except json.JSONDecodeError as error:
        raise SponsorBlockError("SponsorBlock sent an unreadable answer.") from error
    return parse_segments(payload, video_id)


@dataclass
class Skipper:
    """Decides, from the playback position, whether to jump and where to.

    Each segment is skipped once: seeking back into one on purpose (to hear
    the sponsor after all) is respected rather than fought.
    """

    segments: list[Segment] = field(default_factory=list)
    done: set[int] = field(default_factory=set)

    def check(self, position: float) -> Segment | None:
        for index, segment in enumerate(self.segments):
            if index in self.done:
                continue
            if segment.start <= position < segment.end - 0.5:
                self.done.add(index)
                return segment
        return None


def spoken(segment: Segment) -> str:
    """ "Skipped a sponsor segment." (pure)."""
    return f"Skipped {SPOKEN.get(segment.category, 'a marked segment')}."


__all__ = [
    "API_URL",
    "CATEGORIES",
    "DEFAULT_CATEGORIES",
    "Segment",
    "SkipSettings",
    "Skipper",
    "SponsorBlockError",
    "fetch_segments",
    "hash_prefix",
    "load",
    "parse_segments",
    "request_url",
    "save",
    "spoken",
]
