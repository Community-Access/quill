"""Best-effort matching of a Spotify episode to a public RSS enclosure.

Spotify's own episode audio is DRM-protected and playable only through the Web
Playback SDK, so it can never be downloaded. Many podcasts, however, *also*
publish the same episode as a plain MP3 enclosure in their own public RSS feed.
This module tries to find that public enclosure so a Spotify-surfaced episode can
be downloaded from the **publisher's own feed** -- it never touches Spotify audio.

It is explicitly best-effort. The match is a two-stage fuzzy search:

1. Find candidate feeds for the show by name + publisher, reusing
   :mod:`quill.core.podcasts.itunes_search` (the same keyless directory the Add
   Podcast dialog uses) for the directory half.
2. In the top-ranked feeds, fuzzily match the episode title against each
   ``<item>``'s title, accepting the best enclosure only at or above
   :data:`EPISODE_MATCH_THRESHOLD` (0.78) so a wrong episode is never returned.

Both the directory search and the feed fetch are injectable, so the ranking and
threshold logic are unit-tested with no network. The defaults reuse existing
reviewed egress sites (``itunes_search`` and ``feed_reader``), so this module
adds **no new network-egress site** of its own.

wx-free, strict-typed.
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

from quill.core import safe_xml
from quill.core.error_codes import CodedError
from quill.core.podcasts.itunes_search import PodcastSearchResult
from quill.core.spotify.models import SpotifyEpisode

#: Minimum show+publisher similarity for a directory feed to be considered.
DIRECTORY_MATCH_THRESHOLD = 0.55
#: Minimum episode-title similarity to accept an enclosure as the same episode.
EPISODE_MATCH_THRESHOLD = 0.78
#: How many top-ranked candidate feeds to actually open and scan.
_MAX_FEEDS = 3

#: Look up candidate feeds for a search term (name + publisher).
FeedSearch = Callable[[str], "list[PodcastSearchResult]"]
#: Fetch one feed's raw bytes by URL.
FeedFetch = Callable[[str], bytes]


class SpotifyRssMatchError(CodedError):
    """RSS matching was refused (Safe Mode)."""

    code = "QUILL-SPOTIFY-RSS-MATCH"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`SpotifyRssMatchError` when Safe Mode is active.

    The match reaches the podcast directory and a publisher's feed, both network
    services, so it is refused in Safe Mode like every other network surface.
    """
    if safe_mode:
        raise SpotifyRssMatchError(
            "Finding a downloadable version is disabled in Safe Mode. "
            "Restart QUILL normally to use it."
        )


@dataclass(frozen=True, slots=True)
class EpisodeEnclosure:
    """A matched public download: the enclosure URL and where it was found."""

    title: str
    url: str
    feed_url: str


def directory_feeds(show: str, publisher: str, *, search: FeedSearch | None = None) -> list[str]:
    """Rank candidate feed URLs for *show* by *publisher* (best first).

    Feeds are scored by show-title similarity (weighted 0.8) plus publisher
    similarity (0.2); only those at or above :data:`DIRECTORY_MATCH_THRESHOLD`
    survive, and at most :data:`_MAX_FEEDS` are returned.
    """
    finder = search if search is not None else _default_search
    term = f"{show} {publisher}".strip()
    if not term:
        return []
    ranked: list[tuple[float, str]] = []
    for result in finder(term):
        if not result.feed_url:
            continue
        score = _similarity(show, result.title) * 0.8 + _similarity(publisher, result.artist) * 0.2
        ranked.append((score, result.feed_url))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [url for score, url in ranked[:_MAX_FEEDS] if score >= DIRECTORY_MATCH_THRESHOLD]


def episode_from_feed(
    feed_url: str,
    episode_name: str,
    *,
    fetch: FeedFetch | None = None,
) -> EpisodeEnclosure | None:
    """Find the enclosure whose ``<item>`` title best matches *episode_name*.

    Returns ``None`` when the feed cannot be fetched or parsed, or when no
    episode clears :data:`EPISODE_MATCH_THRESHOLD`.
    """
    fetcher = fetch if fetch is not None else _default_fetch
    try:
        root = safe_xml.fromstring(fetcher(feed_url))
    except (OSError, ValueError, ET.ParseError, CodedError):
        return None
    wanted = _normalise(episode_name)
    best: EpisodeEnclosure | None = None
    best_score = 0.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        enclosure = item.find("enclosure")
        url = str(enclosure.get("url", "")) if enclosure is not None else ""
        if not title or not url:
            continue
        score = 1.0 if wanted and wanted == _normalise(title) else _similarity(episode_name, title)
        if score > best_score:
            best_score = score
            best = EpisodeEnclosure(title=title, url=url, feed_url=feed_url)
    if best is None or best_score < EPISODE_MATCH_THRESHOLD:
        return None
    return best


def find_public_enclosure(
    episode: SpotifyEpisode,
    *,
    search: FeedSearch | None = None,
    fetch: FeedFetch | None = None,
    safe_mode: bool = False,
) -> EpisodeEnclosure | None:
    """Best-effort public download for a Spotify *episode*, or ``None``.

    Searches the podcast directory for the episode's show, then scans the
    top-ranked feeds for a matching enclosure. Never returns Spotify audio -- the
    result is the publisher's own public RSS enclosure.
    """
    refuse_in_safe_mode(safe_mode)
    show = episode.show_name.strip()
    if not show:
        return None
    for feed_url in directory_feeds(show, episode.show_publisher, search=search):
        match = episode_from_feed(feed_url, episode.name, fetch=fetch)
        if match is not None:
            return match
    return None


def _default_search(term: str) -> list[PodcastSearchResult]:
    from quill.core.podcasts.itunes_search import search_podcasts

    return search_podcasts(term)


def _default_fetch(feed_url: str) -> bytes:
    from quill.core.podcasts.feed_reader import _fetch_feed_bytes

    return _fetch_feed_bytes(feed_url)


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    kept = (
        character if character.isalnum() else " "
        for character in value
        if not unicodedata.combining(character)
    )
    return " ".join("".join(kept).split())


def _similarity(left: str, right: str) -> float:
    normalised_left = _normalise(left)
    normalised_right = _normalise(right)
    if not normalised_left or not normalised_right:
        return 0.0
    return SequenceMatcher(None, normalised_left, normalised_right).ratio()


__all__ = [
    "DIRECTORY_MATCH_THRESHOLD",
    "EPISODE_MATCH_THRESHOLD",
    "EpisodeEnclosure",
    "SpotifyRssMatchError",
    "directory_feeds",
    "episode_from_feed",
    "find_public_enclosure",
    "refuse_in_safe_mode",
]
