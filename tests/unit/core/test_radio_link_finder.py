"""Tests for the website stream-link finder (HTML parsing; no network)."""

from __future__ import annotations

import pytest

import quill.core.radio.link_finder as lf
from quill.core.radio.link_finder import (
    LinkFinderError,
    normalize_page_url,
    refuse_in_safe_mode,
    scan_page_for_streams,
)


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(LinkFinderError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("http://example.com", "https://example.com"),
        ("https://example.com/page", "https://example.com/page"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_page_url(raw: str, expected: str) -> None:
    assert normalize_page_url(raw) == expected


_SAMPLE_HTML = """
<html>
<head>
<title>WXYZ Radio</title>
<link rel="icon" href="/favicon.ico">
</head>
<body>
<audio src="/live/stream.mp3"></audio>
<a href="https://example.com/listen.pls">Listen Live</a>
<a href="https://example.com/stream;stream.mp3">Direct Stream</a>
<a href="https://example.com/about">About Us</a>
<a href="mailto:hi@example.com">Email</a>
<a href="#top">Back to top</a>
</body>
</html>
"""


def test_scan_page_for_streams_finds_candidates_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lf, "_fetch_html", lambda url: _SAMPLE_HTML)
    result = scan_page_for_streams("example.com")
    assert result.page_title == "WXYZ Radio"
    assert result.favicon_url == "https://example.com/favicon.ico"
    urls = [c.url for c in result.candidates]
    assert "https://example.com/live/stream.mp3" in urls
    assert "https://example.com/listen.pls" in urls
    assert "https://example.com/stream;stream.mp3" in urls
    # "About Us" is a normal page link, not stream-shaped -- must not appear.
    assert "https://example.com/about" not in urls
    # mailto: and #fragment links are explicitly excluded.
    assert not any(u.startswith("mailto:") for u in urls)
    assert not any(u.endswith("#top") for u in urls)


def test_scan_page_for_streams_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    html = '<audio src="/s.mp3"></audio><a href="/s.mp3">Same link</a>'
    monkeypatch.setattr(lf, "_fetch_html", lambda url: html)
    result = scan_page_for_streams("example.com")
    assert len(result.candidates) == 1


def test_scan_page_for_streams_refuses_in_safe_mode() -> None:
    with pytest.raises(LinkFinderError):
        scan_page_for_streams("example.com", safe_mode=True)


def test_scan_page_for_streams_requires_a_url() -> None:
    with pytest.raises(LinkFinderError):
        scan_page_for_streams("   ")


def test_scan_page_for_streams_finds_url_in_inline_script(monkeypatch: pytest.MonkeyPatch) -> None:
    html = """
    <html><body>
    <script>
      var player = {
        streamUrl: "https://example.com/live/stream.mp3",
        other: "https://example.com/about"
      };
    </script>
    </body></html>
    """
    monkeypatch.setattr(lf, "_fetch_html", lambda url: html)
    result = scan_page_for_streams("example.com")
    urls = [c.url for c in result.candidates]
    assert "https://example.com/live/stream.mp3" in urls
    assert "https://example.com/about" not in urls
    stream_candidate = next(c for c in result.candidates if c.url.endswith("stream.mp3"))
    assert "inline script" in stream_candidate.reason


def test_scan_page_for_streams_follows_iframe_one_level(monkeypatch: pytest.MonkeyPatch) -> None:
    main_html = '<html><body><iframe src="https://player.example.com/embed"></iframe></body></html>'
    iframe_html = '<html><body><audio src="/stream.mp3"></audio></body></html>'
    pages = {
        "https://example.com": main_html,
        "https://player.example.com/embed": iframe_html,
    }
    monkeypatch.setattr(lf, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("example.com")
    urls = [c.url for c in result.candidates]
    assert "https://player.example.com/stream.mp3" in urls
    candidate = next(c for c in result.candidates if c.url.endswith("stream.mp3"))
    assert "embedded iframe" in candidate.reason


def test_scan_page_for_streams_skips_iframe_that_fails_to_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_html = '<html><body><iframe src="https://player.example.com/embed"></iframe></body></html>'

    def fake_fetch(url: str) -> str:
        if url == "https://example.com":
            return main_html
        raise LinkFinderError("could not reach")

    monkeypatch.setattr(lf, "_fetch_html", fake_fetch)
    result = scan_page_for_streams("example.com")
    assert result.candidates == []


def test_scan_page_for_streams_caps_iframes_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    main_html = "".join(
        f'<iframe src="https://player{i}.example.com/embed"></iframe>' for i in range(5)
    )
    fetched: list[str] = []

    def fake_fetch(url: str) -> str:
        fetched.append(url)
        if url == "https://example.com":
            return main_html
        return "<html><body></body></html>"

    monkeypatch.setattr(lf, "_fetch_html", fake_fetch)
    scan_page_for_streams("example.com")
    # One fetch for the main page, plus at most _MAX_IFRAMES_TO_FOLLOW iframes.
    assert len(fetched) == 1 + lf._MAX_IFRAMES_TO_FOLLOW
