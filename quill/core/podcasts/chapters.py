"""Podcast chapters: fetch and parse the Podcasting 2.0 JSON chapters format.

Spec: https://github.com/Podcastindex-org/podcast-namespace/blob/main/chapters/jsonChapters.md
-- a small JSON document (``{"version": "1.2.0", "chapters": [...]}``) an
episode's ``<podcast:chapters url="...">`` tag (already extracted by
``core/podcasts/feed_reader.py``) points at. The network fetch and the
parsing are deliberately two separate steps, the same split feed_reader.py
uses: QUILL fetches the JSON itself (the one reviewed egress site), then
parses the already-fetched bytes purely.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 10.0
_MAX_BYTES = 2_000_000


class ChaptersError(CodedError):
    """A chapters document could not be fetched or was unusable."""

    code = "QUILL-PODCASTS-CHAPTERS"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`ChaptersError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service.
    Fetching an episode's chapters document is a network service.
    """
    if safe_mode:
        raise ChaptersError(
            "Podcast chapters are disabled in Safe Mode. Restart QUILL normally to use them."
        )


@dataclass(slots=True)
class PodcastChapter:
    """One chapter marker: a start time and a title, plus optional extras."""

    start_ms: int
    title: str
    image_url: str = ""
    link_url: str = ""


def _fetch_chapters_bytes(url: str) -> bytes:
    """One HTTPS GET returning raw chapters JSON bytes -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise ChaptersError("Only https:// chapters links can be fetched.")
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise ChaptersError(f"Could not reach that chapters file: {error}") from error


def parse_chapters(raw_bytes: bytes) -> list[PodcastChapter]:
    """Parse already-fetched chapters JSON (pure; tolerant of junk entries)."""
    try:
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except ValueError as error:
        raise ChaptersError(f"That chapters file was not valid JSON: {error}") from error
    if not isinstance(data, dict):
        return []
    raw_chapters = data.get("chapters")
    if not isinstance(raw_chapters, list):
        return []
    chapters: list[PodcastChapter] = []
    for entry in raw_chapters:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        start_time = entry.get("startTime")
        if not title or not isinstance(start_time, (int, float)) or start_time < 0:
            continue
        chapters.append(
            PodcastChapter(
                start_ms=int(round(float(start_time) * 1000)),
                title=title,
                image_url=str(entry.get("img", "") or ""),
                link_url=str(entry.get("url", "") or ""),
            )
        )
    chapters.sort(key=lambda c: c.start_ms)
    return chapters


def fetch_and_parse_chapters(url: str, *, safe_mode: bool = False) -> list[PodcastChapter]:
    """Fetch *url* and parse it in one step."""
    refuse_in_safe_mode(safe_mode)
    if not url:
        return []
    raw_bytes = _fetch_chapters_bytes(url)
    return parse_chapters(raw_bytes)


def chapter_at_position(chapters: list[PodcastChapter], position_ms: int) -> PodcastChapter | None:
    """The chapter containing *position_ms* (the last one whose start is <= it)."""
    current: PodcastChapter | None = None
    for chapter in chapters:
        if chapter.start_ms <= position_ms:
            current = chapter
        else:
            break
    return current


def next_chapter(chapters: list[PodcastChapter], position_ms: int) -> PodcastChapter | None:
    """The next chapter after *position_ms*, or None if already in the last one."""
    for chapter in chapters:
        if chapter.start_ms > position_ms:
            return chapter
    return None


def previous_chapter(chapters: list[PodcastChapter], position_ms: int) -> PodcastChapter | None:
    """The chapter before the current one at *position_ms*, or None if already
    at (or before) the first chapter."""
    current = chapter_at_position(chapters, position_ms)
    if current is None:
        return None
    index = chapters.index(current)
    return chapters[index - 1] if index > 0 else None
