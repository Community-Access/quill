"""Tests for quill_radio_mac.core.link_finder.

Scans canned HTML documents covering the <audio>/<source> tag, stream-shaped
<a href> link, inline <script> string-literal, and <iframe> variants, plus
Safe Mode refusal and URL normalization. The network egress function
(_fetch_html) is monkeypatched throughout -- no real HTTP calls.
"""

from __future__ import annotations

import pytest

from quill_radio_mac.core import link_finder
from quill_radio_mac.core.link_finder import (
    LinkFinderError,
    PageStreamCandidate,
    normalize_page_url,
    scan_page_for_streams,
)

_AUDIO_TAG_HTML = """
<html><head><title>Local Radio</title>
<link rel="icon" href="/favicon.ico">
</head><body>
<audio src="/stream/live.mp3"></audio>
</body></html>
"""

_SOURCE_TAG_HTML = """
<html><head><title>Local Radio</title></head><body>
<audio><source src="https://cdn.example.com/live.aac"></audio>
</body></html>
</html>
"""

_ANCHOR_LINK_HTML = """
<html><head><title>Local Radio</title></head><body>
<a href="https://cdn.example.com/stream.pls">Listen (playlist)</a>
<a href="https://example.com/icecast/mount">Stream-shaped link</a>
<a href="mailto:someone@example.com">Contact</a>
<a href="#">Skip link</a>
</body></html>
"""

_SCRIPT_URL_HTML = """
<html><head><title>Local Radio</title></head><body>
<script>
var streamUrl = "https://cdn.example.com/live/stream.mp3";
var unrelated = "https://example.com/about";
</script>
</body></html>
"""

_IFRAME_HTML = """
<html><head><title>Embed host</title></head><body>
<iframe src="https://player.example.com/embed"></iframe>
</body></html>
"""

_IFRAME_TARGET_HTML = """
<html><head><title>Embedded player</title></head><body>
<audio src="https://cdn.example.com/embedded.mp3"></audio>
</body></html>
"""

_LISTEN_LINK_HTML = """
<html><head><title>Station homepage</title></head><body>
<a href="https://example.com/tune-in">Listen Live</a>
</body></html>
"""

_LISTEN_TARGET_HTML = """
<html><head><title>Player page</title></head><body>
<audio src="https://cdn.example.com/from-listen-page.mp3"></audio>
</body></html>
"""

_NO_CANDIDATES_HTML = """
<html><head><title>Nothing here</title></head><body>
<p>Just a page with no stream links.</p>
</body></html>
"""


def test_normalize_page_url_adds_scheme_and_forces_https():
    assert normalize_page_url("example.com") == "https://example.com"
    assert normalize_page_url("http://example.com/x") == "https://example.com/x"
    assert normalize_page_url("  ") == ""


def test_scan_refuses_in_safe_mode():
    with pytest.raises(LinkFinderError):
        scan_page_for_streams("example.com", safe_mode=True)


def test_scan_finds_audio_tag_src(monkeypatch):
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: _AUDIO_TAG_HTML)
    result = scan_page_for_streams("https://example.com")
    assert result.page_title == "Local Radio"
    assert result.favicon_url == "https://example.com/favicon.ico"
    urls = [c.url for c in result.candidates]
    assert "https://example.com/stream/live.mp3" in urls
    audio_candidate = next(c for c in result.candidates if c.url.endswith("live.mp3"))
    assert audio_candidate.reason == "<audio> tag"


def test_scan_finds_source_tag_src(monkeypatch):
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: _SOURCE_TAG_HTML)
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/live.aac" in urls
    candidate = next(c for c in result.candidates if c.url.endswith("live.aac"))
    assert candidate.reason == "<source> tag"


def test_scan_finds_anchor_links_and_skips_mailto_and_hash(monkeypatch):
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: _ANCHOR_LINK_HTML)
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/stream.pls" in urls
    assert "https://example.com/icecast/mount" in urls
    assert not any(u.startswith("mailto:") for u in urls)
    pls_candidate = next(c for c in result.candidates if c.url.endswith(".pls"))
    assert pls_candidate.reason == "playlist/stream link"
    assert pls_candidate.label == "Listen (playlist)"
    shaped_candidate = next(c for c in result.candidates if "icecast" in c.url)
    assert shaped_candidate.reason == "stream-shaped link"


def test_scan_finds_stream_url_in_inline_script(monkeypatch):
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: _SCRIPT_URL_HTML)
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/live/stream.mp3" in urls
    assert "https://example.com/about" not in urls
    candidate = next(c for c in result.candidates if c.url.endswith("stream.mp3"))
    assert candidate.reason == "stream URL found in inline script"


def test_scan_follows_iframe_one_level_deep(monkeypatch):
    pages = {
        "https://example.com": _IFRAME_HTML,
        "https://player.example.com/embed": _IFRAME_TARGET_HTML,
    }
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/embedded.mp3" in urls
    candidate = next(c for c in result.candidates if c.url.endswith("embedded.mp3"))
    assert "found via embedded iframe" in candidate.reason


def test_scan_follows_listen_live_link_only_when_no_direct_candidate(monkeypatch):
    pages = {
        "https://example.com": _LISTEN_LINK_HTML,
        "https://example.com/tune-in": _LISTEN_TARGET_HTML,
    }
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/from-listen-page.mp3" in urls
    candidate = next(c for c in result.candidates if c.url.endswith("from-listen-page.mp3"))
    assert "found via Listen link" in candidate.reason


def test_scan_returns_no_candidates_for_a_plain_page(monkeypatch):
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: _NO_CANDIDATES_HTML)
    result = scan_page_for_streams("https://example.com")
    assert result.candidates == []
    assert result.page_title == "Nothing here"


def test_scan_deduplicates_candidates_by_url(monkeypatch):
    html = """
    <html><head><title>Dup</title></head><body>
    <audio src="/live.mp3"></audio>
    <audio src="/live.mp3"></audio>
    </body></html>
    """
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: html)
    result = scan_page_for_streams("https://example.com")
    urls = [c.url for c in result.candidates]
    assert urls.count("https://example.com/live.mp3") == 1


def test_page_stream_candidate_defaults_label_to_empty_string():
    candidate = PageStreamCandidate(url="https://example.com/x.mp3", reason="test")
    assert candidate.label == ""
