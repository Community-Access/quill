"""Feed autodiscovery from page HTML and common-path fallbacks."""

from __future__ import annotations

from quill_social.services.feed_discovery import (
    common_feed_paths,
    discover_feed_links,
)

PAGE = """
<html><head>
  <title>A Blog</title>
  <link rel="alternate" type="application/rss+xml" title="Main RSS" href="/feed.xml">
  <link rel="alternate" type="application/atom+xml" href="https://blog.example/atom">
  <link rel="alternate" type="application/feed+json" href="/feed.json">
  <link rel="stylesheet" href="/style.css">
  <link rel="alternate" type="application/rss+xml" href="/feed.xml">
</head><body>hi</body></html>
"""


def test_discovers_rss_atom_json_and_resolves_relative():
    cands = discover_feed_links(PAGE, "https://blog.example/posts/")
    urls = [c.url for c in cands]
    # Relative hrefs resolved against the page URL; duplicate /feed.xml removed.
    assert "https://blog.example/feed.xml" in urls
    assert "https://blog.example/atom" in urls
    assert "https://blog.example/feed.json" in urls
    assert urls.count("https://blog.example/feed.xml") == 1
    assert len(cands) == 3


def test_kinds_and_titles():
    cands = discover_feed_links(PAGE, "https://blog.example/")
    by_url = {c.url: c for c in cands}
    assert by_url["https://blog.example/feed.xml"].kind == "rss"
    assert by_url["https://blog.example/feed.xml"].title == "Main RSS"
    assert by_url["https://blog.example/atom"].kind == "atom"
    assert by_url["https://blog.example/feed.json"].kind == "json"


def test_no_feeds_returns_empty():
    assert discover_feed_links("<html><head></head></html>", "https://x.example/") == []
    assert discover_feed_links("", "https://x.example/") == []


def test_malformed_html_does_not_raise():
    assert discover_feed_links("<link rel=alternate type=", "https://x.example/") == []


def test_common_feed_paths_rooted_at_host():
    paths = common_feed_paths("https://news.example/section/page")
    urls = [c.url for c in paths]
    assert "https://news.example/feed" in urls
    assert "https://news.example/rss.xml" in urls
    assert all(u.startswith("https://news.example/") for u in urls)


def test_common_feed_paths_accepts_bare_host():
    urls = [c.url for c in common_feed_paths("news.example")]
    assert "https://news.example/feed" in urls
