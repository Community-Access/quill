"""Find candidate audio-stream links on a station's own website.

RadioBrowser doesn't carry every station in existence -- smaller, local, or
niche stations often only publish a stream link on their own site. This
module fetches one user-typed page (a plain HTTPS GET, not an embedded
browser: QUILL has no general-purpose accessible WebView for arbitrary-site
navigation, and ``core/browser_reader.py`` shows a deliberate house pattern of
preferring the user's real browser over an embedded one whenever a task is
accessibility-sensitive; a static fetch-and-parse also covers the common case,
since station pages almost always list their stream as a literal link rather
than injecting it via JavaScript) and parses the HTML with the standard
library parser for anything that looks like a stream: ``<audio>``/``<source>``
tags, and links whose extension or path matches common streaming patterns.

Every request funnels through the single reviewed egress site
(:func:`_fetch_html` -- see ``quill/tools/network_egress_audit.py``),
HTTPS-only with a verified TLS context, reached only by the explicit "Scan"
button in the Find Streams from a Website dialog, disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

from quill import __version__
from quill.core.error_codes import CodedError

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 2_000_000

#: File extensions that are almost always a direct audio stream/playlist.
_STREAM_EXTENSIONS = (".mp3", ".aac", ".ogg", ".opus", ".m3u", ".m3u8", ".pls", ".flac")
#: Path fragments common on Shoutcast/Icecast-style mount points.
_STREAM_PATH_HINTS = ("/stream", "/listen", "/live", "icecast", "shoutcast", ";stream")


class LinkFinderError(CodedError):
    """A website scan failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-LINKFINDER-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`LinkFinderError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service; scanning
    an arbitrary user-typed website is one. Kept in core (flag passed in) so
    the refusal is unit-testable without wx.
    """
    if safe_mode:
        raise LinkFinderError(
            "Finding stream links from a website is disabled in Safe Mode. "
            "Restart QUILL normally to use it."
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
        self._in_title = False
        self._pending_href: str | None = None
        self._pending_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: (value or "") for name, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag in ("audio", "source") and attr_map.get("src"):
            url = urllib.parse.urljoin(self._base_url, attr_map["src"])
            self.candidates.append(PageStreamCandidate(url=url, reason=f"<{tag}> tag"))
        elif tag == "link" and "icon" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.favicon = urllib.parse.urljoin(self._base_url, attr_map["href"])
        elif tag == "a" and attr_map.get("href"):
            self._pending_href = attr_map["href"]
            self._pending_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._pending_href is not None:
            self._pending_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
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


def _fetch_html(url: str) -> str:
    """One HTTPS GET returning decoded text -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise LinkFinderError("Only https:// pages can be scanned.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise LinkFinderError(f"Could not reach that page: {error}") from error
    return payload.decode("utf-8", errors="replace")


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
    """Fetch *url* and return every candidate stream link found on it."""
    refuse_in_safe_mode(safe_mode)
    normalized = normalize_page_url(url)
    if not normalized:
        raise LinkFinderError("Type a website address to scan.")
    html_text = _fetch_html(normalized)
    parser = _StreamLinkParser(normalized)
    parser.feed(html_text)
    # De-duplicate by URL, preserving first-seen order and reason.
    seen: dict[str, PageStreamCandidate] = {}
    for candidate in parser.candidates:
        seen.setdefault(candidate.url, candidate)
    return PageScanResult(
        page_title=parser.title.strip(),
        favicon_url=parser.favicon,
        candidates=list(seen.values()),
    )
