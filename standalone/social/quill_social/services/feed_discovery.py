"""Feed autodiscovery: turn a site URL into subscribable feeds (plan xxx.md 3.1).

Two pure, network-free helpers the Add-Feed flow uses:

- :func:`discover_feed_links` scans a page's HTML for
  ``<link rel="alternate" type="application/rss+xml|atom+xml|feed+json">`` (the
  RSS Board autodiscovery convention) and resolves relative hrefs against the
  page URL.
- :func:`common_feed_paths` returns the well-known fallback paths to probe when
  a page advertises no ``<link>`` (``/feed``, ``/rss``, ``/atom.xml``, ...).

Both are deterministic and unit-testable with fixture HTML; the network fetch
that feeds them lives in the adapter/UI layer, so this module stays wx-free and
I/O-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

# MIME types that mark a discoverable feed, mapped to a normalized kind.
_FEED_TYPES = {
    "application/rss+xml": "rss",
    "application/atom+xml": "atom",
    "application/feed+json": "json",
    "application/json": "json",
    "text/xml": "rss",
    "application/xml": "rss",
}

# Well-known fallback paths, most-common first.
_COMMON_PATHS = (
    "/feed",
    "/feed/",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feed.xml",
    "/index.xml",
    "/feed.json",
    "/feeds/posts/default",
    "/?feed=rss2",
)


@dataclass(frozen=True)
class FeedCandidate:
    """A feed a page advertises (or a path worth probing)."""

    url: str
    title: str = ""
    kind: str = "rss"  # rss | atom | json


class _LinkScanner(HTMLParser):
    """Collect ``<link rel=alternate type=...feed...>`` tags from a page head."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str, str]] = []  # (href, type, title)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rels = a.get("rel", "").lower().split()
        if "alternate" not in rels and "feed" not in rels:
            return
        mime = a.get("type", "").split(";", 1)[0].strip().lower()
        href = a.get("href", "").strip()
        if href and mime in _FEED_TYPES:
            self.found.append((href, _FEED_TYPES[mime], a.get("title", "").strip()))


def discover_feed_links(html: str, base_url: str) -> list[FeedCandidate]:
    """Return the feeds a page advertises via ``<link rel="alternate">``.

    Relative hrefs are resolved against ``base_url``. Duplicate URLs are removed,
    preserving first-seen order. Never raises on malformed HTML.
    """
    scanner = _LinkScanner()
    try:
        scanner.feed(html or "")
        scanner.close()
    except Exception:  # noqa: BLE001 -- malformed markup must not break discovery
        pass
    out: list[FeedCandidate] = []
    seen: set[str] = set()
    for href, kind, title in scanner.found:
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        out.append(FeedCandidate(url=url, title=title, kind=kind))
    return out


def common_feed_paths(base_url: str) -> list[FeedCandidate]:
    """Well-known fallback feed URLs to probe when a page advertises none."""
    parts = urlsplit(base_url if "://" in base_url else f"https://{base_url}")
    root = f"{parts.scheme or 'https'}://{parts.netloc}"
    return [FeedCandidate(url=f"{root}{path}", kind="rss") for path in _COMMON_PATHS]
