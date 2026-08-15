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
from quill.core.podcasts import feed_auth

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
    """One chapter marker: a start time and a title, plus optional extras.

    The four fields below ``link_url`` are what turn a chapter list from
    something you *have* into something you can *trust*. An inferred chapter is
    a claim, and a claim you cannot inspect is one you have to take on faith:

    * ``end_ms`` makes "3 of 12, four minutes long" sayable, and gives the last
      chapter an honest end instead of an implied one.
    * ``source`` is which tier produced *this* chapter -- carried per chapter,
      not only per set, because a cascade that keeps the best answer per region
      can mix them.
    * ``confidence`` (0.0-1.0) lets a marginal boundary be presented differently
      from a published one. Published chapters are 1.0 by definition: a person
      wrote them.
    * ``reason``, in words -- "a 2.4 second silence", "the topic changed", "from
      the show notes". This is what makes a *"How were these found?"* report
      possible at all.

    All four default to the empty/zero case, so every existing construction of a
    published chapter is unchanged and reads as "published, certain, no
    explanation needed".
    """

    start_ms: int
    title: str
    image_url: str = ""
    link_url: str = ""
    end_ms: int | None = None
    source: str = ""
    confidence: float = 1.0
    reason: str = ""

    @property
    def duration_ms(self) -> int:
        """How long this chapter runs, or 0 when its end is not known."""
        if self.end_ms is None:
            return 0
        return max(0, int(self.end_ms) - int(self.start_ms))


def _fetch_chapters_bytes(url: str, *, auth_header: str = "") -> bytes:
    """One HTTPS GET returning raw chapters JSON bytes -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise ChaptersError("Only https:// chapters links can be fetched.")
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()
    try:
        with feed_auth.urlopen_auth_safe(
            request, timeout=_TIMEOUT_SECONDS, context=context
        ) as resp:
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


def fetch_and_parse_chapters(
    url: str, *, safe_mode: bool = False, auth_header: str = ""
) -> list[PodcastChapter]:
    """Fetch *url* and parse it in one step."""
    refuse_in_safe_mode(safe_mode)
    if not url:
        return []
    raw_bytes = _fetch_chapters_bytes(url, auth_header=auth_header)
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
