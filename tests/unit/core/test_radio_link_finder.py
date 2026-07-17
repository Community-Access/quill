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


def test_scan_resolves_triton_player_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    # A Triton/listenlive player page: no stream in the HTML, but a callsign in
    # the logo asset name. The scan must resolve it via the Triton API and
    # surface the real mount as a candidate.
    import quill.core.radio.triton as triton
    from quill.core.radio.triton import TritonStream

    html = (
        "<html><head><title>Magic 104.1</title></head><body>"
        "Powered by Triton Digital"
        '<img src="//pwaimg.listenlive.co/'
        'KMGLFM_1115091_config_station_logo_image_1514560282.png">'
        "</body></html>"
    )
    monkeypatch.setattr(lf, "_fetch_html", lambda url: html)
    monkeypatch.setattr(
        triton,
        "resolve_station_streams",
        lambda callsign, *, safe_mode=False: [
            TritonStream(
                url="https://29306.live.streamtheworld.com/KMGLFM",
                mount="KMGLFM",
                codec="MP3",
                bitrate=64000,
            )
        ],
    )
    result = scan_page_for_streams("https://player.listenlive.co/34461")
    urls = [c.url for c in result.candidates]
    assert "https://29306.live.streamtheworld.com/KMGLFM" in urls
    candidate = next(c for c in result.candidates if "streamtheworld" in c.url)
    assert "MP3 stream from the station's player" in candidate.reason


def test_scan_ignores_triton_resolution_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # A Triton API failure must degrade to the normal (empty) scan result, not
    # break the whole scan.
    import quill.core.radio.triton as triton
    from quill.core.radio.triton import TritonResolverError

    html = 'Triton Digital<img src="//pwaimg.listenlive.co/KMGLFM_1_config_station_logo_x.png">'
    monkeypatch.setattr(lf, "_fetch_html", lambda url: html)

    def _boom(callsign: str, *, safe_mode: bool = False):
        raise TritonResolverError("offline")

    monkeypatch.setattr(triton, "resolve_station_streams", _boom)
    result = scan_page_for_streams("https://player.listenlive.co/34461")
    assert result.candidates == []


def test_scan_does_not_call_triton_for_a_normal_site(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.radio.triton as triton

    monkeypatch.setattr(lf, "_fetch_html", lambda url: "<html><body>plain site</body></html>")
    monkeypatch.setattr(
        triton,
        "resolve_station_streams",
        lambda *a, **k: pytest.fail("must not hit Triton for a non-Triton page"),
    )
    result = scan_page_for_streams("https://example.com")
    assert result.candidates == []


def test_scan_follows_a_listen_live_link_when_page_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #1065: a homepage that only *links* to its player. The scan should follow
    # the "Listen Live" link one level and find the stream on that page.
    home = '<html><body><a href="/player">Listen Live</a></body></html>'
    player = '<html><body><audio src="/live/stream.mp3"></audio></body></html>'
    pages = {
        "https://station.example.com": home,
        "https://station.example.com/player": player,
    }
    monkeypatch.setattr(lf, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("station.example.com")
    urls = [c.url for c in result.candidates]
    assert "https://station.example.com/live/stream.mp3" in urls
    candidate = next(c for c in result.candidates if c.url.endswith("stream.mp3"))
    assert "Listen link" in candidate.reason


def test_scan_does_not_follow_listen_links_when_a_direct_stream_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # If the page already yields a stream, don't waste fetches chasing links.
    fetched: list[str] = []

    def fake_fetch(url: str) -> str:
        fetched.append(url)
        return '<audio src="/s.mp3"></audio><a href="/player">Listen Live</a>'

    monkeypatch.setattr(lf, "_fetch_html", fake_fetch)
    scan_page_for_streams("station.example.com")
    assert fetched == ["https://station.example.com"]  # the Listen link was not followed


def test_scan_ignores_ordinary_links(monkeypatch: pytest.MonkeyPatch) -> None:
    # A normal "About" link is not a listen link and must not be followed.
    fetched: list[str] = []

    def fake_fetch(url: str) -> str:
        fetched.append(url)
        return '<html><body><a href="/about">About Us</a></body></html>'

    monkeypatch.setattr(lf, "_fetch_html", fake_fetch)
    result = scan_page_for_streams("station.example.com")
    assert fetched == ["https://station.example.com"]
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


# -- certificate-mismatch fallback + http listen links (the magic104.com case) --


def test_www_variant_toggles_the_host() -> None:
    assert lf._www_variant("https://www.magic104.com/") == "https://magic104.com/"
    assert lf._www_variant("https://magic104.com/x") == "https://www.magic104.com/x"


def test_fetch_retries_www_variant_on_certificate_hostname_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # www.magic104.com's certificate names only magic104.com: the https
    # fetch of the typed host fails verification, and the www-toggled
    # variant (fully verified) must be tried before giving up.
    import ssl as ssl_module

    calls: list[str] = []

    def fake_get(url: str) -> str:
        calls.append(url)
        if url == "https://www.magic104.com/":
            raise ssl_module.SSLCertVerificationError("hostname mismatch")
        return "<html><title>ok</title></html>"

    monkeypatch.setattr(lf, "_http_get_text", fake_get)
    html = lf._fetch_html("https://www.magic104.com/")
    assert "ok" in html
    assert calls == ["https://www.magic104.com/", "https://magic104.com/"]


def test_fetch_falls_back_to_plain_http_when_both_https_hosts_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ssl as ssl_module

    calls: list[str] = []

    def fake_get(url: str) -> str:
        calls.append(url)
        if url.startswith("https://"):
            raise ssl_module.SSLCertVerificationError("hostname mismatch")
        return "<html>plain</html>"

    monkeypatch.setattr(lf, "_http_get_text", fake_get)
    html = lf._fetch_html("https://www.example.com/")
    assert "plain" in html
    assert calls[-1] == "http://www.example.com/"


def test_fetch_does_not_retry_on_non_certificate_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Only a certificate hostname failure earns the fallback; a plain
    # network error must not multiply into three fetch attempts.
    calls: list[str] = []

    def fake_get(url: str) -> str:
        calls.append(url)
        raise TimeoutError("no route")

    monkeypatch.setattr(lf, "_http_get_text", fake_get)
    with pytest.raises(lf.LinkFinderError):
        lf._fetch_html("https://station.example.com/")
    assert calls == ["https://station.example.com/"]


def test_http_listen_link_is_followed_not_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    # magic104.com writes its player link as http://player.listenlive.co/...;
    # it must be followed (upgraded by _fetch_html), not silently dropped.
    home = (
        "<html><body>"
        '<a href="http://player.listenlive.co/34461"><span>Listen Live</span></a>'
        "</body></html>"
    )
    player = '<html><body><audio src="/live/kmgl.mp3"></audio></body></html>'
    pages = {
        "https://station.example.com": home,
        "http://player.listenlive.co/34461": player,
    }
    monkeypatch.setattr(lf, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("station.example.com")
    assert any("kmgl.mp3" in c.url for c in result.candidates)


def test_listenlive_href_matches_even_with_an_image_only_label() -> None:
    assert lf._looks_like_listen_link("http://player.listenlive.co/34461", "")


# -- iHeart/TuneIn portal pages: follow, don't offer the page URL (issue #1087) --


def test_iheart_live_link_is_followed_not_offered_as_a_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #1087: delilah.com links to an iHeart /live/ page. Because /live is a
    # stream-path hint, the scanner used to offer the iHeart *page* URL as a
    # stream (unplayable) and never fetch it. It must instead follow the portal
    # page one level deep and surface the real HLS stream embedded in it.
    home = (
        "<html><body>"
        '<a href="https://www.iheart.com/live/delilah-4846/?autoplay=true">Listen</a>'
        "</body></html>"
    )
    # The iHeart page embeds the real stream as an escaped quoted string in an
    # inline player-config <script> (the shape verified against the live page).
    iheart = (
        "<html><body><script>"
        'var cfg = {"streams":{"secure_hls_stream":'
        '"https://stream.revma.ihrhls.com/zc4846/hls.m3u8"}};'
        "</script></body></html>"
    )
    pages = {
        "https://delilah.com": home,
        "https://www.iheart.com/live/delilah-4846/?autoplay=true": iheart,
    }
    monkeypatch.setattr(lf, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("delilah.com")
    urls = [c.url for c in result.candidates]
    assert "https://stream.revma.ihrhls.com/zc4846/hls.m3u8" in urls
    # The iHeart page URL itself must NOT be offered as a playable stream.
    assert not any("iheart.com/live" in u for u in urls)


def test_tunein_radio_link_is_followed_not_offered_as_a_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A TuneIn /radio/ station page is a portal page too: follow it, don't
    # offer the tunein.com page URL as a stream candidate.
    home = (
        "<html><body>"
        '<a href="https://tunein.com/radio/BBC-Radio-1-s24939/">BBC Radio 1</a>'
        "</body></html>"
    )
    tunein = '<html><body><audio src="https://cdn.example.com/bbc.mp3"></audio></body></html>'
    pages = {
        "https://directory.example.com": home,
        "https://tunein.com/radio/BBC-Radio-1-s24939/": tunein,
    }
    monkeypatch.setattr(lf, "_fetch_html", lambda url: pages[url])
    result = scan_page_for_streams("directory.example.com")
    urls = [c.url for c in result.candidates]
    assert "https://cdn.example.com/bbc.mp3" in urls
    assert not any("tunein.com/radio" in u for u in urls)


def test_is_portal_page_url_matches_hosts_and_paths() -> None:
    assert lf._is_portal_page_url("https://www.iheart.com/live/delilah-4846/")
    assert lf._is_portal_page_url("https://tunein.com/radio/BBC-Radio-1-s24939/")
    # Same path fragment on a station's own domain is NOT a portal page.
    assert not lf._is_portal_page_url("https://station.example.com/live/stream.mp3")
    # An iHeart URL that isn't a station page path is not a portal page.
    assert not lf._is_portal_page_url("https://www.iheart.com/news/")
