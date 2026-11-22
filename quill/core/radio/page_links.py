"""Read one fetched web page for the places a station puts its stream address.

Split from :mod:`quill.core.radio.link_finder` (GATE-11), which fetches pages
and decides what to follow; this module only reads HTML text it is given, so it
is pure and needs no network. It finds:

* ``<audio>`` and ``<source>`` tags, and ``<a href>`` links shaped like a
  stream or a playlist;
* quoted stream-shaped addresses in inline ``<script>`` text;
* ``data-*`` attributes on player markup -- ``data-src``, ``data-url``,
  ``data-stream*``, ``data-audio*``, ``data-dt-stream`` -- including several
  addresses in one attribute separated by commas;
* configuration written as ``key: "url"`` (``streamUrl:``, ``mount:``,
  ``hls_url:`` and the like), even when the address has no file extension,
  after undoing JSON escapes such as ``\\/``;
* addresses printed on the page as plain text;
* ``<base href>``, which changes what every relative link means;
* a Radio.co embedded player (``player.radio.co/s<id>``), mapped to its stream
  at ``streaming.radio.co/s<id>/listen``;
* the page's own player scripts and ``window.open`` pop-up players, which the
  caller fetches;
* links to an Icecast status page or a SHOUTcast server's statistics, which
  the caller reads with :mod:`quill.core.radio.server_listings`.

The ``data-*`` attributes, the ``key: "url"`` configuration, the same-site
script files, ``window.open`` targets, plain-text addresses, ``<base href>``,
the Radio.co mapping and the status-page links are all ideas from Andre Louis's
StreamSift (https://github.com/OnjLouis/StreamSift). This is QUILL's own
implementation, not a port.

It never runs JavaScript: an address computed at run time cannot be found,
only one written somewhere in the text. wx-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser

from quill.core.radio.address_kind import is_player_page_url
from quill.core.radio.server_listings import status_kind

#: File extensions that are almost always a direct audio stream/playlist.
STREAM_EXTENSIONS = (".mp3", ".aac", ".ogg", ".opus", ".m3u", ".m3u8", ".pls", ".flac")
#: Path fragments common on Shoutcast/Icecast-style mount points.
STREAM_PATH_HINTS = ("/stream", "/listen", "/live", "icecast", "shoutcast", ";stream")
#: Quoted string literals inside script text that look like a stream URL.
_SCRIPT_STRING_URL_RE = re.compile(r"""['"]((?:https?:)?//[^'"\s]+)['"]""")
#: ``streamUrl: "..."``, ``"hls_url":"..."``, ``mount = '...'``: a key that names
#: a stream, then the quoted address it is given.
_ASSIGNED_URL_RE = re.compile(
    r"""\b(\w*?(?:stream|audio|mount|hls)\w*)["']?\s*[:=]\s*["']([^"'\s<>]{4,2048})["']""",
    re.IGNORECASE,
)
_WINDOW_OPEN_RE = re.compile(r"""window\.open\(\s*["']([^"'\s<>]{4,1024})["']""")
_PLAIN_URL_RE = re.compile(r"""https?://[^\s<>"'`]{4,2048}""")
_COMMA_BEFORE_URL_RE = re.compile(r",\s*(?=(?:https?:)?//)")
_NOT_A_STREAM = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".css", ".js", ".json", ".ico")
_RADIO_CO_RE = re.compile(r"^/(s[0-9a-f]{9})(?:/|$)", re.IGNORECASE)
_PLAYER_SCRIPT_WORDS = ("player", "radio", "stream", "audio", "listen", "live")
_APP_BUNDLE_RE = re.compile(r"^(?:main|app|index|bundle)(?:[.-][0-9a-f]{8,32})?(?:\.min)?\.m?js$")
_STATUS_PAGES = ("/status.xsl", "/status-json.xsl")

#: Words in a link's visible text or its href that mark it as the station's
#: "Listen Live"/"Play"/"Tune In" entry point (issue #1065). Kept small.
LISTEN_LINK_HINTS = (
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


@dataclass(slots=True)
class PageStreamCandidate:
    """One candidate stream link found on a scanned page."""

    url: str
    #: Why it was flagged, e.g. "audio tag", "playlist link" -- shown to the
    #: user so they can judge plausibility before testing it.
    reason: str
    #: Visible link text or the audio tag's nearby label, if any.
    label: str = ""
    #: The live check's verdict (:mod:`quill.core.radio.live_check`): "live",
    #: "file", "not checked", or "" when no check was asked for.
    check: str = ""
    codec: str = ""
    bitrate_kbps: int = 0
    #: The stream's own name (``icy-name``) and genre, when it sent them.
    stream_name: str = ""
    genre: str = ""
    #: Why the check said what it said, mostly why a link is "not checked".
    check_note: str = ""
    #: How many were listening, when a server's own listing said (else ``None``).
    listeners: int | None = None

    @property
    def live(self) -> bool:
        """True when the live check heard live audio at this address."""
        return self.check == "live"


def looks_like_listen_link(lowered_href: str, label: str) -> bool:
    """True when an ``<a>`` is a "Listen Live"/"Play"/"Tune In" entry point."""
    haystack = f"{label.lower()} {lowered_href}"
    return any(hint in haystack for hint in LISTEN_LINK_HINTS)


def is_stream_shaped(url: str) -> bool:
    """True when *url* ends like a stream or playlist, or has a mount-point hint."""
    lowered = url.lower()
    path = urllib.parse.urlsplit(lowered).path
    return path.endswith(STREAM_EXTENSIONS) or any(hint in lowered for hint in STREAM_PATH_HINTS)


def unescape_script(text: str) -> str:
    """Undo the JSON escapes that hide an address from a plain search."""
    return (
        text
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u002f", "/")
        .replace("\\u003A", ":")
        .replace("\\u003a", ":")
        .replace("\\u0026", "&")
    )


def radio_co_stream(url: str) -> str:
    """``streaming.radio.co/<id>/listen`` for a Radio.co embedded player, else ""."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() != "player.radio.co":
        return ""
    match = _RADIO_CO_RE.match(parsed.path)
    return f"https://streaming.radio.co/{match.group(1).lower()}/listen" if match else ""


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")


def same_site(url: str, page: str) -> bool:
    """Same host as *page*, ignoring a leading ``www.``."""
    return bool(_host(url)) and _host(url) == _host(page)


def is_status_page(url: str) -> bool:
    """True for an Icecast ``status.xsl`` or ``status-json.xsl`` address."""
    return urllib.parse.urlsplit(url).path.lower().endswith(_STATUS_PAGES)


def _absolute(base: str, raw: str) -> str:
    """*raw* joined to *base* when it is a web address, else ""."""
    raw = raw.strip()
    if not raw or raw.startswith(("#", "javascript:", "mailto:", "data:", "tel:")):
        return ""
    if not raw.startswith(("http://", "https://", "//", "/")):
        return ""
    url = urllib.parse.urljoin(base, raw)
    return url if url.startswith(("http://", "https://")) else ""


def _is_player_markup(tag: str, attr_map: dict[str, str]) -> bool:
    words = f"{attr_map.get('class', '')} {attr_map.get('id', '')}".lower().split()
    return tag in ("audio", "source") or any(
        word == "player" or word.endswith("-player") for word in words
    )


class StreamLinkParser(HTMLParser):
    """Everything on one page that might be, or lead to, a stream."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._page_url = base_url
        self._base_url = base_url
        self._seen_base = False
        self.title = ""
        self.favicon = ""
        self.candidates: list[PageStreamCandidate] = []
        #: <iframe src="..."> URLs found, followed one level deep by the caller.
        self.iframe_urls: list[str] = []
        #: "Listen Live"-shaped <a href> URLs, followed when nothing else was found.
        self.listen_urls: list[str] = []
        #: Portal/player page URLs (iHeart, TuneIn, SecureNet Cirrus): never
        #: candidates, always followed by the caller.
        self.portal_urls: list[str] = []
        #: The page's own player scripts, fetched and read by the caller.
        self.script_urls: list[str] = []
        #: ``window.open`` pop-up players, followed like an iframe.
        self.popup_urls: list[str] = []
        #: Icecast status pages and SHOUTcast statistics linked from the page.
        self.status_urls: list[str] = []
        self._app_bundles = 0
        self._in_title = False
        self._in_script = False
        self._pending_href: str | None = None
        self._pending_text: list[str] = []

    def _add(self, url: str, reason: str, label: str = "") -> None:
        radio_co = radio_co_stream(url)
        if radio_co:
            url, reason = radio_co, "Radio.co stream behind its embedded player"
        self.candidates.append(PageStreamCandidate(url=url, reason=reason, label=label))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: (value or "") for name, value in attrs}
        if tag == "base" and attr_map.get("href") and not self._seen_base:
            self._seen_base = True
            self._base_url = urllib.parse.urljoin(self._page_url, attr_map["href"])
        elif tag == "title":
            self._in_title = True
        elif tag == "script":
            self._in_script = True
            self._note_script(attr_map.get("src", ""))
        elif tag in ("audio", "source") and attr_map.get("src"):
            url = urllib.parse.urljoin(self._base_url, attr_map["src"])
            self._add(url, f"<{tag}> tag")
        elif tag == "iframe" and attr_map.get("src"):
            url = _absolute(self._base_url, attr_map["src"])
            if radio_co_stream(url):
                self._add(url, "embedded player")
            elif url:  # http:// is fine: link_finder tries https first
                self.iframe_urls.append(url)
        elif tag == "link" and "icon" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.favicon = urllib.parse.urljoin(self._base_url, attr_map["href"])
        elif tag == "a" and attr_map.get("href"):
            self._pending_href = attr_map["href"]
            self._pending_text = []
        self._read_data_attributes(tag, attr_map)
        onclick = attr_map.get("onclick", "")
        if onclick:
            self._read_window_open(onclick)

    def _read_data_attributes(self, tag: str, attr_map: dict[str, str]) -> None:
        player = _is_player_markup(tag, attr_map)
        for name, value in attr_map.items():
            if not name.startswith("data-") or not value:
                continue
            audio_named = "stream" in name or "audio" in name
            if not (audio_named or name in ("data-src", "data-url")):
                continue
            for part in _COMMA_BEFORE_URL_RE.split(value)[:8]:
                url = _absolute(self._base_url, part)
                if not url or urllib.parse.urlsplit(url).path.lower().endswith(_NOT_A_STREAM):
                    continue
                # data-src is also how images load lazily: only a stream-named
                # attribute, player markup, or a stream-shaped address counts.
                if audio_named or player or is_stream_shaped(url):
                    self._add(url, f"player setting ({name})")

    def _note_script(self, src: str) -> None:
        url = _absolute(self._base_url, src)
        if not url or not same_site(url, self._page_url):
            return
        filename = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1].lower()
        if any(word in filename for word in _PLAYER_SCRIPT_WORDS):
            self.script_urls.append(url)
        elif (
            self._app_bundles < 2
            and urllib.parse.urlsplit(self._page_url).path in ("", "/")
            and _APP_BUNDLE_RE.match(filename)
        ):
            self._app_bundles += 1
            self.script_urls.append(url)

    def _read_window_open(self, text: str) -> None:
        for match in _WINDOW_OPEN_RE.finditer(text):
            url = _absolute(self._base_url, match.group(1))
            if url:
                self.popup_urls.append(url)

    def read_script(self, text: str, reason: str = "inline script") -> None:
        """Read script text for addresses (also used for fetched script files)."""
        text = unescape_script(text)
        for match in _ASSIGNED_URL_RE.finditer(text):
            value = match.group(2)
            # Only a full address: a bare "/live" mount belongs to a stream
            # server the script names elsewhere, not to this page.
            url = _absolute(self._base_url, value) if "//" in value[:8] else ""
            if url and not urllib.parse.urlsplit(url).path.lower().endswith(_NOT_A_STREAM):
                if not is_player_page_url(url):
                    self._add(url, f"stream setting ({match.group(1)}) in {reason}")
        for match in _SCRIPT_STRING_URL_RE.finditer(text):
            url = _absolute(self._base_url, match.group(1))
            if url and (is_stream_shaped(url) or radio_co_stream(url)):
                self._add(url, f"stream URL found in {reason}")
        self._read_window_open(text)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_script:
            self.read_script(data)
        elif "://" in data:
            for match in _PLAIN_URL_RE.finditer(data):
                url = match.group(0).rstrip(").,;]")
                if is_stream_shaped(url):
                    self._add(url, "address written on the page")
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
            self._read_link(href, label)

    def _read_link(self, href: str, label: str) -> None:
        lowered = href.lower()
        if lowered.startswith(("mailto:", "javascript:", "#")):
            if lowered.startswith("javascript:"):
                self._read_window_open(href)
            return
        joined = urllib.parse.urljoin(self._base_url, href)
        if not joined.startswith(("https://", "http://")):
            return
        if is_player_page_url(joined):
            # issues #1087 and #1491: a portal/player page is a landing page,
            # never a stream -- follow it instead of offering it.
            self.portal_urls.append(joined)
            return
        if is_status_page(joined) or status_kind(joined):
            self.status_urls.append(joined)
            return
        lowered_path = urllib.parse.urlsplit(lowered).path
        if lowered.endswith(STREAM_EXTENSIONS) or lowered_path.endswith(STREAM_EXTENSIONS):
            self._add(joined, "playlist/stream link", label)
        elif radio_co_stream(joined):
            self._add(joined, "link to an embedded player", label)
        elif any(hint in lowered for hint in STREAM_PATH_HINTS):
            self._add(joined, "stream-shaped link", label)
        elif looks_like_listen_link(lowered, label):
            self.listen_urls.append(joined)
