"""Find candidate audio-stream links on a station's own website.

Ported near-verbatim from upstream ``quill.core.radio.link_finder``.
RadioBrowser doesn't carry every station in existence -- smaller, local, or
niche stations often only publish a stream link on their own site. This
module fetches one user-typed page (a plain HTTPS GET, not an embedded
browser: this app has no general-purpose accessible WebView for
arbitrary-site navigation) and parses the HTML with the standard library
parser for anything that looks like a stream: ``<audio>``/``<source>``
tags, links whose extension or path matches common streaming patterns,
quoted stream-shaped string literals inside inline ``<script>`` text (the
common "the player is a bit of JavaScript that reads a URL constant" case,
handled without running any JavaScript -- just a literal string scan), and
one level of ``<iframe src="...">`` -- many station sites embed a
third-party player (Zeno.fm, Radio.co, and similar embed widgets) rather
than linking a stream directly, so the iframe's own page is fetched and
scanned the same way, with its candidates carrying a "found via embedded
iframe" reason. This still never executes JavaScript and never renders a
page -- it cannot find a URL that is computed at runtime (built from an
API response, obfuscated, etc.), only ones that appear as literal text
somewhere in the fetched HTML/JS.

Every request funnels through the single reviewed egress site
(:func:`_fetch_html`), HTTPS-only with a verified TLS context, reached only
by the explicit "Scan" button in the Find Streams from a Website dialog,
disabled in Safe Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.

Threading contract: HTML parsing (:class:`_StreamLinkParser`) is pure;
network functions are blocking and called off the UI thread by
:func:`scan_page_for_streams`'s caller.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

from quill_radio_mac import __version__
from quill_radio_mac.core.error_codes import CodedError

_USER_AGENT = f"QuillRadioMac/{__version__}"
_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 2_000_000

#: File extensions that are almost always a direct audio stream/playlist.
_STREAM_EXTENSIONS = (".mp3", ".aac", ".ogg", ".opus", ".m3u", ".m3u8", ".pls", ".flac")
#: Path fragments common on Shoutcast/Icecast-style mount points.
_STREAM_PATH_HINTS = ("/stream", "/listen", "/live", "icecast", "shoutcast", ";stream")
#: Quoted string literals inside inline <script> text that look like a
#: stream URL -- catches "the player is a few lines of JS with the URL as a
#: string constant" without executing anything.
_SCRIPT_STRING_URL_RE = re.compile(r"""['"](https?://[^'"\s]+)['"]""")
_MAX_IFRAMES_TO_FOLLOW = 3

#: Words in a link's visible text or its href that mark it as the station's
#: "Listen Live"/"Play"/"Tune In" entry point. Many station homepages don't
#: embed the player on the front page -- they link to it -- so following such a
#: link one level deep and scanning *that* page is often what actually reaches
#: the stream. Kept deliberately small and specific to avoid wandering off into
#: unrelated navigation.
_LISTEN_LINK_HINTS = (
    "listen live",
    "listen now",
    "listen online",
    # The Triton player network's own hostname (player.listenlive.co) --
    # matches by href alone when the anchor's label is only an image.
    "listenlive",
    "live stream",
    "livestream",
    "tune in",
    "tunein",
    "play live",
    "listen-live",
    "/listen",
    "/live",
    "/player",
    "/stream",
)
_MAX_LISTEN_LINKS_TO_FOLLOW = 3


class LinkFinderError(CodedError):
    """A website scan failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-LINKFINDER-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`LinkFinderError` when Safe Mode is active.

    Safe Mode disables every network service; scanning an arbitrary
    user-typed website is one. Kept in core (flag passed in) so the
    refusal is unit-testable without wx.
    """
    if safe_mode:
        raise LinkFinderError(
            "Finding stream links from a website is disabled in Safe Mode. "
            "Restart Quill Radio normally to use it."
        )


@dataclass(slots=True)
class PageStreamCandidate:
    """One candidate stream link found on a scanned page."""

    url: str
    #: Why it was flagged, e.g. "audio tag", "playlist link" -- shown to the
    #: user so they can judge plausibility before testing it.
    reason: str
    #: Visible link text or the audio tag's nearby label, if any.
    label: str = ""


@dataclass(slots=True)
class PageScanResult:
    """Everything usable for pre-filling the Add Custom Station dialog."""

    page_title: str
    favicon_url: str
    candidates: list[PageStreamCandidate]


class _StreamLinkParser(HTMLParser):
    """Collects ``<audio>``/``<source>`` src attributes, stream-looking
    ``<a href>`` links, the page ``<title>``, and a favicon ``<link>``."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self.title = ""
        self.favicon = ""
        self.candidates: list[PageStreamCandidate] = []
        #: <iframe src="..."> URLs found, followed one level deep by the caller.
        self.iframe_urls: list[str] = []
        #: "Listen Live"/"Play"-shaped <a href> URLs, followed one level deep
        #: by the caller when the page itself yielded no direct candidate.
        self.listen_urls: list[str] = []
        self._in_title = False
        self._in_script = False
        self._pending_href: str | None = None
        self._pending_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: (value or "") for name, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "script":
            self._in_script = True
        elif tag in ("audio", "source") and attr_map.get("src"):
            url = urllib.parse.urljoin(self._base_url, attr_map["src"])
            self.candidates.append(PageStreamCandidate(url=url, reason=f"<{tag}> tag"))
        elif tag == "iframe" and attr_map.get("src"):
            url = urllib.parse.urljoin(self._base_url, attr_map["src"])
            # http:// is fine here: _fetch_html upgrades it to https before
            # any request is made (stations commonly still write http links).
            if url.startswith(("https://", "http://")):
                self.iframe_urls.append(url)
        elif tag == "link" and "icon" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.favicon = urllib.parse.urljoin(self._base_url, attr_map["href"])
        elif tag == "a" and attr_map.get("href"):
            self._pending_href = attr_map["href"]
            self._pending_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_script:
            for match in _SCRIPT_STRING_URL_RE.finditer(data):
                url = match.group(1)
                lowered = url.lower()
                if lowered.endswith(_STREAM_EXTENSIONS) or any(
                    hint in lowered for hint in _STREAM_PATH_HINTS
                ):
                    self.candidates.append(
                        PageStreamCandidate(url=url, reason="stream URL found in inline script")
                    )
        if self._pending_href is not None:
            self._pending_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_script = False
        elif tag == "a" and self._pending_href is not None:
            href = self._pending_href
            label = "".join(self._pending_text).strip()
            self._pending_href = None
            self._pending_text = []
            lowered = href.lower()
            if lowered.startswith(("mailto:", "javascript:", "#")):
                return
            if lowered.endswith(_STREAM_EXTENSIONS):
                url = urllib.parse.urljoin(self._base_url, href)
                self.candidates.append(
                    PageStreamCandidate(url=url, reason="playlist/stream link", label=label)
                )
            elif any(hint in lowered for hint in _STREAM_PATH_HINTS):
                url = urllib.parse.urljoin(self._base_url, href)
                self.candidates.append(
                    PageStreamCandidate(url=url, reason="stream-shaped link", label=label)
                )
            elif _looks_like_listen_link(lowered, label):
                url = urllib.parse.urljoin(self._base_url, href)
                # http:// is fine: _fetch_html upgrades before any request.
                if url.startswith(("https://", "http://")):
                    self.listen_urls.append(url)


def _looks_like_listen_link(lowered_href: str, label: str) -> bool:
    """True when an ``<a>`` is a "Listen Live"/"Play"/"Tune In" entry point.

    Matches the small :data:`_LISTEN_LINK_HINTS` allowlist against the link's
    visible text or its href, so the scanner can follow it one level deeper to
    the page that actually hosts the player. Deliberately narrow so a scan
    never wanders off into unrelated site navigation.
    """
    haystack = f"{label.lower()} {lowered_href}"
    return any(hint in haystack for hint in _LISTEN_LINK_HINTS)


_FETCH_ERRORS = (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError)


def _http_get_text(url: str) -> str:
    """One GET returning decoded text, certificates always fully verified."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
        payload: bytes = resp.read(_MAX_BYTES)
    return payload.decode("utf-8", errors="replace")


def _is_cert_verification_failure(error: Exception) -> bool:
    reason = getattr(error, "reason", error)
    return isinstance(reason, ssl.SSLCertVerificationError) or isinstance(
        error, ssl.SSLCertVerificationError
    )


def _www_variant(url: str) -> str:
    """The same https URL with ``www.`` toggled on the host ("" if no host)."""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if not host:
        return ""
    swapped = host.removeprefix("www.") if host.startswith("www.") else f"www.{host}"
    netloc = swapped if parsed.port is None else f"{swapped}:{parsed.port}"
    return urllib.parse.urlunsplit(parsed._replace(netloc=netloc))


def _fetch_html(url: str) -> str:
    """GET *url* returning decoded text -- the reviewed egress site.

    HTTPS-first, always: an ``http://`` URL (a relative link joined against
    an http base, or a typed one) is upgraded before fetching. Some station
    sites carry a certificate that does not cover the exact host the
    listener typed -- e.g. a station's cert may name only the bare domain,
    not the ``www.`` host. On a certificate hostname failure (and only that
    failure) two safe retries run in order: the ``www.``-toggled variant of
    the same host over https (fully verified like any other fetch), then the
    plain-http entry point, following the server's own redirect to wherever
    its valid https home is. Certificate verification itself is never
    relaxed at any step; a site that stays on plain http merely has its
    public HTML read, which is all this scanner ever does.
    """
    if url.startswith("http://"):
        url = "https://" + url.removeprefix("http://")
    if not url.startswith("https://"):
        raise LinkFinderError("Only http(s):// pages can be scanned.")
    try:
        return _http_get_text(url)
    except _FETCH_ERRORS as error:
        if not _is_cert_verification_failure(error):
            raise LinkFinderError(f"Could not reach that page: {error}") from error
        first_error = error
    variant = _www_variant(url)
    if variant:
        try:
            return _http_get_text(variant)
        except _FETCH_ERRORS:
            pass
    fallback = "http://" + url.removeprefix("https://")
    try:
        return _http_get_text(fallback)
    except _FETCH_ERRORS:
        raise LinkFinderError(f"Could not reach that page: {first_error}") from first_error


def normalize_page_url(text: str) -> str:
    """Turn a loosely-typed site name/URL into an https:// URL, best effort."""
    candidate = text.strip()
    if not candidate:
        return ""
    if not re.match(r"^https?://", candidate, re.IGNORECASE):
        candidate = f"https://{candidate}"
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urllib.parse.urlunsplit(parsed)


def scan_page_for_streams(url: str, *, safe_mode: bool = False) -> PageScanResult:
    """Fetch *url* and return every candidate stream link found on it.

    Follows up to :data:`_MAX_IFRAMES_TO_FOLLOW` embedded ``<iframe>`` pages
    one level deep (station sites commonly embed a third-party player rather
    than linking a stream directly), and up to
    :data:`_MAX_LISTEN_LINKS_TO_FOLLOW` "Listen Live"/"Play"/"Tune In" ``<a>``
    links one level deep when the page itself yielded no direct candidate
    (many homepages *link* to the player rather than hosting it). A failed
    sub-fetch is skipped, not fatal to the overall scan.

    JavaScript players (Triton Digital / StreamTheWorld, the whole
    ``player.listenlive.co`` network) compute their stream URL at runtime, so
    it is never a literal string in the HTML. For those, the callsign the page
    *does* advertise (in the Triton PWA's own asset URLs) is resolved to a real
    playable stream through Triton's JS-free provisioning API -- see
    :mod:`quill_radio_mac.core.triton`. This is the only way the visible Play
    button on such a page can be surfaced without running JavaScript.
    """
    refuse_in_safe_mode(safe_mode)
    normalized = normalize_page_url(url)
    if not normalized:
        raise LinkFinderError("Type a website address to scan.")
    html_text = _fetch_html(normalized)
    parser = _StreamLinkParser(normalized)
    parser.feed(html_text)

    # SecureNet first: its mount is a real, page-advertised stream, while the
    # generic parser's picks off the same page are only stream-*shaped*.
    all_candidates = _securenet_candidates(normalized, html_text)
    all_candidates.extend(parser.candidates)
    all_candidates.extend(
        _follow_pages(parser.iframe_urls, _MAX_IFRAMES_TO_FOLLOW, "embedded iframe")
    )
    all_candidates.extend(_triton_candidates(normalized, html_text, safe_mode=safe_mode))

    # Only chase "Listen Live"/"Play" links when the page and its iframes gave
    # us nothing directly -- following them otherwise just adds noise and extra
    # fetches when a stream was already in hand.
    if not all_candidates:
        all_candidates.extend(
            _follow_pages(
                parser.listen_urls,
                _MAX_LISTEN_LINKS_TO_FOLLOW,
                "Listen link",
                normalized,
                safe_mode=safe_mode,
            )
        )

    # De-duplicate by URL, preserving first-seen order and reason.
    seen: dict[str, PageStreamCandidate] = {}
    for candidate in all_candidates:
        seen.setdefault(candidate.url, candidate)
    return PageScanResult(
        page_title=parser.title.strip(),
        favicon_url=parser.favicon,
        candidates=list(seen.values()),
    )


def _follow_pages(
    urls: list[str],
    cap: int,
    reason_suffix: str,
    base: str = "",
    *,
    safe_mode: bool = False,
) -> list[PageStreamCandidate]:
    """Fetch up to *cap* sub-pages and return their candidates, each tagged
    ``(found via <reason_suffix>)``.

    Used for both embedded ``<iframe>`` pages and followed "Listen Live" links.
    For the latter, each sub-page is *also* run through the Triton resolver
    (``base`` non-empty), since a station's linked player page is exactly where
    a Triton/StreamTheWorld player tends to live. A failed sub-fetch is skipped.
    """
    out: list[PageStreamCandidate] = []
    for sub_url in urls[:cap]:
        try:
            sub_html = _fetch_html(sub_url)
        except LinkFinderError:
            continue
        sub_parser = _StreamLinkParser(sub_url)
        sub_parser.feed(sub_html)
        # Triton-resolved streams first: they are API-validated, playable
        # mounts, while a player page's other links (its own help articles,
        # for instance) are only stream-*shaped*.
        page_candidates: list[PageStreamCandidate] = []
        if base:  # a followed Listen link may itself be a Triton player page
            page_candidates.extend(_triton_candidates(sub_url, sub_html, safe_mode=safe_mode))
            page_candidates.extend(_securenet_candidates(sub_url, sub_html))
        page_candidates.extend(sub_parser.candidates)
        for candidate in page_candidates:
            out.append(
                PageStreamCandidate(
                    url=candidate.url,
                    reason=f"{candidate.reason} (found via {reason_suffix})",
                    label=candidate.label,
                )
            )
    return out


def _triton_candidates(url: str, html: str, *, safe_mode: bool) -> list[PageStreamCandidate]:
    """Resolve a Triton Digital / StreamTheWorld player page to stream
    candidates, or ``[]`` when the page is not a Triton player.

    A Triton player's stream is JS-computed and absent from the HTML, so the
    static parser above finds nothing on it. When the page looks like a Triton
    player and advertises a callsign, this resolves it through Triton's JS-free
    provisioning API and offers the real mount(s) as candidates. Any failure
    (not a Triton page, no callsign, API unreachable, Safe Mode) degrades to an
    empty list so it never breaks the rest of the scan.
    """
    from quill_radio_mac.core import triton

    if not triton.page_is_triton_player(url, html):
        return []
    callsign = triton.callsign_from_page(url, html)
    if not callsign:
        return []
    try:
        streams = triton.resolve_station_streams(callsign, safe_mode=safe_mode)
    except triton.TritonResolverError:
        return []
    return [
        PageStreamCandidate(
            url=stream.url,
            reason=f"{stream.codec} stream from the station's player ({stream.mount})",
            label=stream.mount,
        )
        for stream in streams
    ]


def _securenet_candidates(url: str, html: str) -> list[PageStreamCandidate]:
    """Resolve a SecureNet Systems (Cirrus) player page to stream candidates,
    or ``[]`` when the page is not a SecureNet player.

    Unlike the Triton resolver above, this one needs no API call -- a Cirrus
    player carries its own mount in the page HTML. The generic parser still
    misses it, because that mount is a bare Icecast path
    (``https://ice66.securenetsystems.net/ROM``) with no file extension and no
    ``/stream``-style hint, so it fails the shape heuristics that keep ordinary
    page links out of the results. Recognising the platform is what makes the
    URL trustworthy here; the shape alone never could be.

    Being fetch-free, this also runs in Safe Mode: it only reads the page the
    caller already has.
    """
    from quill_radio_mac.core import securenet

    if not securenet.page_is_securenet_player(url, html):
        return []
    callsign = securenet.callsign_from_page(url, html)
    return [
        PageStreamCandidate(
            url=stream_url,
            reason=f"stream from the station's player ({callsign})"
            if callsign
            else "stream from the station's player",
            label=callsign,
        )
        for stream_url in securenet.stream_urls_from_page(html)
    ]
