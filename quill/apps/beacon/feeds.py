"""Podcast feed parsing and subscriptions (PRD 11.8, Phase 3).

Uses ``feedparser`` for robust RSS/Atom parsing. Extracts episodes, durations,
enclosure URLs, Podcasting 2.0 chapter and transcript links, and normalizes
them into the QuillBeacon model. Refresh adds new episodes as Beacons without
duplicating. Pure logic over the store; wx-free and unit-testable.

Network access (fetching a feed) is isolated in :func:`fetch_feed` so the
parsing path can be tested with fixture XML and no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import feedparser

from quill.apps.beacon import capture, media
from quill.apps.beacon.model import (
    TYPE_PODCAST_EPISODE,
    TYPE_PODCAST_SHOW,
    Beacon,
    MediaChapter,
    Resource,
)


@dataclass
class Episode:
    title: str = ""
    guid: str = ""
    enclosure_url: str = ""
    duration_ms: int = 0
    published: str = ""
    chapters_url: str = ""
    transcript_url: str = ""
    summary: str = ""

    def to_beacon(self, show_resource_id: str) -> tuple[Beacon, Resource]:
        beacon, res = capture.capture(
            self.enclosure_url or self.guid,
            title=self.title,
            capture_source="feed",
            tags=["podcast"],
            media_start_ms=0,
        )
        res.type = TYPE_PODCAST_EPISODE
        res.canonical_id = self.guid or res.canonical_id
        res.metadata["show_resource_id"] = show_resource_id
        res.metadata["duration_ms"] = self.duration_ms
        res.metadata["published"] = self.published
        if self.summary:
            beacon.note = self.summary
        return beacon, res


@dataclass
class Show:
    title: str = ""
    feed_url: str = ""
    homepage: str = ""
    author: str = ""
    summary: str = ""
    episodes: list[Episode] = field(default_factory=list)

    def to_beacon(self) -> tuple[Beacon, Resource]:
        beacon, res = capture.capture(
            self.feed_url,
            title=self.title,
            capture_source="feed",
            tags=["podcast"],
        )
        res.type = TYPE_PODCAST_SHOW
        res.metadata["homepage"] = self.homepage
        res.metadata["author"] = self.author
        return beacon, res


def parse_feed(text: str, *, feed_url: str = "") -> Show:
    """Parse feed XML/Atom text into a Show with Episodes."""
    parsed = feedparser.parse(text)
    feed = parsed.get("feed", {})
    show = Show(
        title=feed.get("title", ""),
        feed_url=feed_url or feed.get("link", ""),
        homepage=feed.get("link", ""),
        author=feed.get("author", feed.get("itunes_author", "")),
        summary=feed.get("summary", feed.get("subtitle", "")),
    )
    for entry in parsed.get("entries", []):
        enc = _first_enclosure(entry)
        show.episodes.append(
            Episode(
                title=entry.get("title", ""),
                guid=entry.get("id", entry.get("guid", "")),
                enclosure_url=enc.get("href", "") if enc else "",
                duration_ms=_duration_ms(entry, enc),
                published=entry.get("published", entry.get("updated", "")),
                chapters_url=_p20_link(entry, "chapters"),
                transcript_url=_p20_link(entry, "transcript"),
                summary=entry.get("summary", ""),
            )
        )
    return show


def fetch_feed(url: str) -> Show:
    """Fetch a feed URL over the network and parse it. Isolated for testability."""
    import requests

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return parse_feed(resp.text, feed_url=url)


def _first_enclosure(entry: dict) -> dict | None:
    encs = entry.get("enclosures") or []
    audio = [e for e in encs if (e.get("type", "") or "").startswith("audio")]
    return (audio or encs or [None])[0]


def _duration_ms(entry: dict, enc: dict | None) -> int:
    itunes_duration = entry.get("itunes_duration")
    if itunes_duration:
        return (
            media._parse_ts(str(itunes_duration))
            if isinstance(itunes_duration, str)
            else int(itunes_duration) * 1000
        )
    length = enc.get("length") if enc else None
    if length:
        try:
            return int(float(length)) * 1000
        except (ValueError, TypeError):
            pass
    return 0


def _p20_link(entry: dict, rel: str) -> str:
    """Extract a Podcasting 2.0 link (chapters/transcript) from an entry."""
    links = entry.get("links") or []
    for link in links:
        if rel in (link.get("rel", ""), link.get("type", "")):
            return link.get("href", "")
    # feedparser sometimes surfaces these as entry keys
    return entry.get(f"podcast_{rel}_url", "") or ""


def fetch_chapters(url_or_json: str, resource_id: str = "") -> list[MediaChapter]:
    """Fetch and parse Podcasting 2.0 JSON chapters from a URL or literal JSON."""
    if url_or_json.strip().startswith("{"):
        return media.parse_podcasting2_chapters(url_or_json, resource_id)
    import requests

    resp = requests.get(url_or_json, timeout=20)
    resp.raise_for_status()
    return media.parse_podcasting2_chapters(resp.json(), resource_id)


def subscribe(store, feed_url: str, *, show: Show | None = None) -> str:
    """Subscribe to a feed: save the show as a Beacon, return its beacon id."""
    if show is None:
        show = fetch_feed(feed_url)
    beacon, res = show.to_beacon()
    store.put_beacon(beacon, resource=res)
    return beacon.beacon_id


def refresh(store, feed_url: str) -> tuple[Show, int]:
    """Refresh a feed and add new episodes. Returns (show, new_count).

    An episode is new if no resource with its GUID exists. Duplicates are
    skipped (PRD 25.3: never create silent duplicates).
    """
    show = fetch_feed(feed_url)
    show_res = store.find_resource_by_canonical(feed_url)
    show_resource_id = show_res.resource_id if show_res else ""
    new = 0
    for ep in show.episodes:
        if ep.guid and store.find_resource_by_canonical(ep.guid):
            continue
        beacon, res = ep.to_beacon(show_resource_id)
        store.put_beacon(beacon, resource=res)
        new += 1
    return show, new


def listen_later(store, beacon_id: str) -> None:
    """Add a beacon to the Listen Later collection (PRD 13.1)."""
    b = store.get_beacon(beacon_id)
    if not b:
        return
    b.collections = list(dict.fromkeys(b.collections + ["Listen Later"]))
    store.put_beacon(b)
