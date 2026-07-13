"""Podcast RSS/Atom feed fetching and parsing.

The network fetch and the parsing are deliberately two separate steps: QUILL
fetches the raw feed bytes itself (:func:`_fetch_feed_bytes`, the one
reviewed egress site -- see ``quill/tools/network_egress_audit.py``), then
hands those bytes to ``feedparser`` for parsing only. ``feedparser`` can
fetch a URL itself, but doing that would move the actual HTTP request outside
QUILL's own audited code -- fetching first keeps QUILL in control of
HTTPS-only enforcement, the timeout, and HTTP Basic auth for private feeds,
and it is also the reviewed egress site GATE-9 requires.

``feedparser`` gives reliable access to `itunes:*` tags out of the box;
Podcasting 2.0's `podcast:chapters` / `podcast:transcript` tags are newer and
not consistently exposed under a friendly attribute name across feedparser
versions, so those two are additionally extracted with a direct, tolerant
regex pass over the raw feed text as a robust fallback -- correctness here
does not depend on guessing feedparser's exact internal key mapping.

wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

import feedparser

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.podcasts.models import PodcastEpisode

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 20_000_000

_CHAPTERS_TAG_RE = re.compile(r'<podcast:chapters\b[^>]*\burl\s*=\s*"([^"]+)"', re.IGNORECASE)
_TRANSCRIPT_TAG_RE = re.compile(
    r'<podcast:transcript\b[^>]*\burl\s*=\s*"([^"]+)"'
    r'(?:[^>]*\btype\s*=\s*"([^"]*)")?',
    re.IGNORECASE,
)


class FeedReaderError(CodedError):
    """A feed fetch/parse failed (network, auth, or Safe Mode refusal)."""

    code = "QUILL-PODCASTS-FEED-READ"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`FeedReaderError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service.
    Subscribing to / refreshing a podcast feed is a network service.
    """
    if safe_mode:
        raise FeedReaderError(
            "Podcast feeds are disabled in Safe Mode. Restart QUILL normally to use them."
        )


@dataclass(slots=True)
class FeedInfo:
    """Show-level metadata plus every episode found in the feed."""

    title: str
    homepage: str
    artwork_url: str
    episodes: list[PodcastEpisode]


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _fetch_feed_bytes(url: str, *, username: str = "", password: str = "") -> bytes:
    """One HTTPS GET returning raw feed bytes -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise FeedReaderError("Only https:// feeds can be subscribed to.")
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/rss+xml, application/xml, */*"}
    if username:
        # Sent preemptively rather than waiting for a 401 challenge: some
        # hosts never issue a proper WWW-Authenticate challenge, and
        # urllib's HTTPBasicAuthHandler only engages after one, so sending
        # the header up front matches every other client's behavior for
        # feeds that expect it unconditionally.
        headers["Authorization"] = _basic_auth_header(username, password)
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise FeedReaderError(f"Could not reach that feed: {error}") from error


def _parse_duration(raw: object) -> int:
    """``itunes:duration`` as HH:MM:SS, MM:SS, or a bare second count."""
    text = str(raw or "").strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if not all(p.isdigit() for p in parts) or not (1 <= len(parts) <= 3):
        return 0
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _episode_extra_tags(entry_xml: str) -> tuple[str, str, str]:
    """Best-effort ``(chapters_url, transcript_url, transcript_type)`` for one
    entry's raw XML fragment."""
    chapters_match = _CHAPTERS_TAG_RE.search(entry_xml)
    transcript_match = _TRANSCRIPT_TAG_RE.search(entry_xml)
    chapters_url = chapters_match.group(1) if chapters_match else ""
    transcript_url = transcript_match.group(1) if transcript_match else ""
    transcript_type = (transcript_match.group(2) or "") if transcript_match else ""
    return chapters_url, transcript_url, transcript_type


def _split_item_fragments(raw_text: str) -> list[str]:
    """Split raw feed text into one string per ``<item>``/``<entry>`` block,
    good enough to scope the chapters/transcript regex search per-episode
    without a full second XML parse."""
    return re.split(r"(?=<item\b)|(?=<entry\b)", raw_text, flags=re.IGNORECASE)


def _entry_to_episode(entry: object, entry_xml: str) -> PodcastEpisode | None:
    title = str(getattr(entry, "title", "")).strip()
    enclosures = getattr(entry, "enclosures", None) or []
    audio_url = ""
    for enclosure in enclosures:
        href = enclosure.get("href") if isinstance(enclosure, dict) else None
        if href:
            audio_url = str(href)
            break
    if not audio_url:
        link = getattr(entry, "link", "")
        if link:
            audio_url = str(link)
    if not title or not audio_url:
        return None
    guid = str(getattr(entry, "id", "") or getattr(entry, "guid", "") or audio_url)
    chapters_url, transcript_url, transcript_type = _episode_extra_tags(entry_xml)
    duration = _parse_duration(getattr(entry, "itunes_duration", ""))
    description = str(getattr(entry, "summary", "") or getattr(entry, "description", ""))
    published = str(getattr(entry, "published", ""))
    return PodcastEpisode(
        guid=guid,
        title=title,
        audio_url=audio_url,
        published=published,
        duration_seconds=duration,
        description=description,
        chapters_url=chapters_url,
        transcript_url=transcript_url,
        transcript_type=transcript_type,
    )


def parse_feed(raw_bytes: bytes) -> FeedInfo:
    """Parse already-fetched feed bytes (pure; tolerant of malformed XML)."""
    parsed = feedparser.parse(raw_bytes)
    feed = getattr(parsed, "feed", None)
    title = str(getattr(feed, "title", "")) if feed is not None else ""
    homepage = str(getattr(feed, "link", "")) if feed is not None else ""
    image = getattr(feed, "image", None) if feed is not None else None
    artwork_url = str(image.get("href", "")) if isinstance(image, dict) else ""

    raw_text = raw_bytes.decode("utf-8", errors="replace")
    fragments = _split_item_fragments(raw_text)
    entries = list(getattr(parsed, "entries", []) or [])

    episodes: list[PodcastEpisode] = []
    for index, entry in enumerate(entries):
        # fragments[0] is anything before the first <item>/<entry>; entry
        # fragments start at index 1, aligned with feedparser's entry order
        # for well-formed feeds. A misaligned/odd feed just loses the
        # chapters/transcript extras for that entry, not the episode itself.
        fragment = fragments[index + 1] if index + 1 < len(fragments) else ""
        episode = _entry_to_episode(entry, fragment)
        if episode is not None:
            episodes.append(episode)
    return FeedInfo(title=title, homepage=homepage, artwork_url=artwork_url, episodes=episodes)


def fetch_and_parse_feed(
    url: str,
    *,
    username: str = "",
    password: str = "",
    safe_mode: bool = False,
) -> FeedInfo:
    """Fetch *url* and parse it in one step."""
    refuse_in_safe_mode(safe_mode)
    raw_bytes = _fetch_feed_bytes(url, username=username, password=password)
    return parse_feed(raw_bytes)
