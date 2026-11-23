"""Find candidate audio-stream links on a station's own website.

RadioBrowser doesn't carry every station in existence -- smaller, local, or
niche stations often only publish a stream link on their own site. This
module fetches one user-typed page (a plain GET, not an embedded browser: QUILL
has no general-purpose accessible WebView for arbitrary-site navigation, and
``core/browser_reader.py`` shows a deliberate house pattern of preferring the
user's real browser over an embedded one whenever a task is
accessibility-sensitive) and reads it with :mod:`quill.core.radio.page_links`
for anything that looks like a stream. One level of ``<iframe>``, pop-up
player, portal page and "Listen Live" link is followed, a few of the site's own
player scripts are read, and an Icecast status page is listed mount by mount.
This never executes JavaScript and never renders a page -- it cannot find a URL
that is computed at runtime, only ones written somewhere in the text.

**HTTPS first, plain http when the site has no HTTPS.** Many small community
stations still serve their site only over http, and their HTTPS port refuses
the connection or times out. So :func:`_fetch_html` tries https, and on a
refusal, a timeout or a TLS failure reads the http:// page instead. Only public
HTML is ever read, and certificate verification itself is never relaxed. When a
stream is offered both ways, the https copy is kept.

**The live check** (``check_live=True``): every candidate is opened, its
headers and first 4 KB read, and judged by :mod:`quill.core.radio.live_check`,
so the list says which links are live audio and which could not be checked,
and leaves out the ones that answered with a web page.

**Server listings and directories.** Given a streaming server itself (an
Icecast front page, Global's ``media-ssl.musicradio.com`` catalogue), or a page
linking to a server's status page, every stream the server lists is offered,
with its listener count: Icecast's ``status-json.xsl`` or its HTML status page,
and SHOUTcast v2's ``/statistics?json=1`` (:mod:`server_listings`). A Global
Player station page, the Locus Sonus Soundmap page, and the stations IPRD lists
for the website (from the catalogue already cached) are added too.

The HTTP fallback, the live check, the extra places a page is read, the
Icecast and SHOUTcast server listings, Global Player pages, the soundmap and
the directory match are ideas from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift), written here in QUILL's own code.

Every request funnels through the single reviewed egress site
(:func:`_http_get` -- see ``quill/tools/network_egress_audit.py``), reached by
the explicit Scan button in the Find Streams from a Website dialog and by
stream recovery, and disabled in Safe Mode via :func:`refuse_in_safe_mode`.
wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import global_player, live_check, server_listings
from quill.core.radio.address_kind import is_help_page_url, same_page
from quill.core.radio.address_kind import is_player_page_url as _is_player_page_url
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import PageStreamCandidate, StreamLinkParser
from quill.core.radio.page_links import (  # noqa: F401 - kept reachable here for callers
    looks_like_listen_link as _looks_like_listen_link,
)
from quill.core.radio.page_resolvers import directory_candidates as _directory_candidates
from quill.core.radio.page_resolvers import global_player_candidates as _global_candidates
from quill.core.radio.page_resolvers import securenet_candidates as _securenet_candidates
from quill.core.radio.page_resolvers import soundmap_candidates as _soundmap_candidates
from quill.core.radio.page_resolvers import triton_candidates as _triton_candidates
from quill.core.radio.page_resolvers import tunein_candidates as _tunein_candidates
from quill.core.radio.page_url import normalize_page_url
from quill.stability.redaction import format_args_for_log

__all__ = [
    "LinkFinderError",
    "PageScanResult",
    "PageStreamCandidate",
    "normalize_page_url",
    "refuse_in_safe_mode",
    "scan_page_for_streams",
]

logger = logging.getLogger(__name__)

#: The parser's old private name, which callers still reach through this module.
_StreamLinkParser = StreamLinkParser

_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 2_000_000
_MAX_IFRAMES_TO_FOLLOW = 3
_MAX_LISTEN_LINKS_TO_FOLLOW = 3
_MAX_POPUPS_TO_FOLLOW = 2
#: The site's own player scripts read per scan, and Icecast servers listed.
_MAX_SCRIPTS_TO_READ = 3
_MAX_STATUS_SERVERS = 2
#: Checks when a server listing is in the results: a whole catalogue, so more
#: than a page's handful, under the same overall deadline.
_LISTING_CHECKS = 48
#: Notes for a listed link QUILL never contacted (the scan's limits).
_NEVER_ASKED = (live_check.TOO_MANY, live_check.OUT_OF_TIME)
_CHECK_RANK = {live_check.LIVE: 0, live_check.UNCHECKED: 1, "": 1, live_check.FILE: 2}


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
class PageScanResult:
    """Everything usable for pre-filling the Add Custom Station dialog."""

    page_title: str
    favicon_url: str
    candidates: list[PageStreamCandidate]
    #: True when the live check ran; then ``left_out`` links answered with
    #: something that is not audio (a web page, a 404) and are not listed.
    checked: bool = False
    left_out: int = 0
    #: The most links this scan would check (16, or 48 with a server listing
    #: or the soundmap), and how many of the listed links QUILL never
    #: contacted because of that limit or the 20-second deadline.
    check_limit: int = 0
    skipped: int = 0


_FETCH_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    ssl.SSLError,
    OSError,
    http.client.HTTPException,
)


def _http_get(
    url: str, *, max_bytes: int = _MAX_BYTES, timeout: float = _TIMEOUT_SECONDS
) -> HttpReply:
    """One GET -- the reviewed egress site. Certificates are always verified.

    Reads at most *max_bytes* of the body: a whole page for the scan, the first
    4 KB of a candidate for the live check. Raises on failure, including
    ``HTTPError`` for a 4xx/5xx answer, which the live check reads.
    """
    if not url.startswith(("https://", "http://")):
        raise LinkFinderError("Only http(s):// addresses can be read.")
    request = urllib.request.Request(url, headers={"User-Agent": http_client.user_agent()})
    context = verified_ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as resp:  # noqa: S310
        body: bytes = resp.read(max_bytes)
        return HttpReply(int(resp.status), dict(resp.headers.items()), body, str(resp.geturl()))


def _http_get_text(url: str) -> str:
    """One GET of a whole page, decoded."""
    return _http_get(url).body.decode("utf-8", errors="replace")


def _probe(url: str, timeout: float) -> HttpReply:
    """The live check's read of one candidate: headers and the first 4 KB."""
    budget = max(1.0, min(_TIMEOUT_SECONDS, timeout))
    return _http_get(url, max_bytes=live_check.PROBE_BYTES, timeout=budget)


def _is_cert_verification_failure(error: BaseException) -> bool:
    reason = getattr(error, "reason", error)
    return isinstance(reason, ssl.SSLCertVerificationError) or isinstance(
        error, ssl.SSLCertVerificationError
    )


_NO_HTTPS = (ssl.SSLError, ConnectionRefusedError, ConnectionResetError, TimeoutError)


def _https_unavailable(error: BaseException) -> bool:
    """True when a failure says "this site has no working HTTPS": a refused or
    reset connection, a timeout, or any TLS failure. A missing host, a 404 or a
    server error says nothing of the kind, so it earns no second try."""
    if isinstance(error, urllib.error.HTTPError):
        return False
    return isinstance(getattr(error, "reason", error), _NO_HTTPS) or isinstance(error, _NO_HTTPS)


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
    """GET *url* returning decoded text, HTTPS first.

    An ``http://`` URL is upgraded before fetching. When the https request is
    refused, times out or fails TLS, the site may simply have no HTTPS -- many
    small community stations do not -- so its plain-http page is read instead.
    On a certificate failure the ``www.``-toggled host is tried over https
    first (www.magic104.com's certificate names only magic104.com). Certificate
    verification itself is never relaxed at any step; a site that stays on
    plain http merely has its public HTML read, which is all this scanner does.
    """
    if url.startswith("http://"):
        url = "https://" + url.removeprefix("http://")
    if not url.startswith("https://"):
        raise LinkFinderError("Only http(s):// pages can be scanned.")
    try:
        return _http_get_text(url)
    except _FETCH_ERRORS as error:
        if not _https_unavailable(error):
            raise LinkFinderError(f"Could not reach that page: {error}") from error
        first_error = error
    if _is_cert_verification_failure(first_error):
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


def scan_page_for_streams(
    url: str, *, safe_mode: bool = False, check_live: bool = False
) -> PageScanResult:
    """Fetch *url* and return every candidate stream link found on it.

    Follows up to :data:`_MAX_IFRAMES_TO_FOLLOW` embedded ``<iframe>`` pages and
    :data:`_MAX_POPUPS_TO_FOLLOW` ``window.open`` pop-up players one level deep,
    reads up to :data:`_MAX_SCRIPTS_TO_READ` of the site's own player scripts,
    lists the mounts of a linked Icecast status page, and follows up to
    :data:`_MAX_LISTEN_LINKS_TO_FOLLOW` "Listen Live" links when the page itself
    yielded nothing (issue #1065). A failed sub-fetch is skipped.

    JavaScript players (Triton Digital / StreamTheWorld, the whole
    ``player.listenlive.co`` network) compute their stream URL at runtime; the
    callsign the page *does* advertise is resolved through Triton's JS-free
    provisioning API instead -- see :mod:`quill.core.radio.triton`.

    With *check_live*, every candidate is then checked: live streams first,
    then those that could not be checked, then audio files; the links that are
    not audio are counted in ``left_out`` rather than listed.
    """
    refuse_in_safe_mode(safe_mode)
    normalized = normalize_page_url(url)
    if not normalized:
        raise LinkFinderError("Type a website address to scan.")
    html_text = _fetch_html(normalized)
    parser = StreamLinkParser(normalized)
    parser.feed(html_text)
    _read_site_scripts(parser)

    # SecureNet first: its mount is a real, page-advertised stream, while the
    # generic parser's picks off the same page are only stream-*shaped*.
    all_candidates = _securenet_candidates(normalized, html_text)
    all_candidates.extend(_global_candidates(normalized, html_text))
    # The soundmap is a listing too: a whole catalogue, checked as one.
    listed = _soundmap_candidates(normalized, safe_mode=safe_mode)
    status_pages = _status_pages(normalized, html_text, parser)
    listed.extend(_server_candidates(status_pages, html_text))
    all_candidates.extend(listed)
    # A server page that listed its mounts says nothing more: its own links are
    # the same mounts again as ".m3u" files, rows that would only be repeats.
    if not (listed and status_pages and status_pages[0][0] == normalized):
        all_candidates.extend(_own_links(normalized, parser))
    all_candidates.extend(
        _follow_pages(parser.iframe_urls, _MAX_IFRAMES_TO_FOLLOW, "embedded iframe")
    )
    all_candidates.extend(_follow_pages(parser.popup_urls, _MAX_POPUPS_TO_FOLLOW, "pop-up player"))
    all_candidates.extend(_triton_candidates(normalized, html_text, safe_mode=safe_mode))
    all_candidates.extend(_tunein_candidates(normalized, html_text, safe_mode=safe_mode))
    all_candidates.extend(_directory_candidates(normalized, safe_mode=safe_mode))

    # Also follow any player page that reached the candidate list some other
    # way than an <a href> -- a front-end host quoted in the player's own inline
    # JS, say (#1491). A bare host names no station, so skip a bare path. These
    # are dropped from the results below, so following them adds no noise. A
    # player page links to itself (#36); following that only fetches it twice.
    portal_urls = [u for u in parser.portal_urls if not same_page(u, normalized)]
    portal_urls.extend(
        c.url
        for c in all_candidates
        if _is_player_page_url(c.url) and urllib.parse.urlsplit(c.url).path.strip("/")
    )
    all_candidates.extend(
        _follow_pages(
            list(dict.fromkeys(portal_urls)),
            _MAX_LISTEN_LINKS_TO_FOLLOW,
            "player page",
            normalized,
            safe_mode=safe_mode,
        )
    )

    # Only chase "Listen Live"/"Play" links when nothing else turned up --
    # otherwise they only add noise and fetches.
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

    # De-duplicate by URL, preserving first-seen order and reason, and drop
    # every player/portal page -- nothing that answers HTML is offered (#1491).
    seen: dict[str, PageStreamCandidate] = {}
    for candidate in all_candidates:
        if _is_player_page_url(candidate.url) or is_help_page_url(candidate.url):
            continue
        seen.setdefault(candidate.url, candidate)
    kept = list(seen.values())
    left_out = 0
    limit = _LISTING_CHECKS if listed else live_check.MAX_CHECKS
    if check_live and kept:
        kept, left_out = _apply_live_check(kept, limit)
    kept = _prefer_https(kept)
    # #5 observability: which links were kept, and why -- the argv-style
    # redaction masks any token a candidate URL might carry.
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Find Streams scanned %s: %d candidate(s), %d left out [%s]",
            format_args_for_log([normalized]),
            len(kept),
            left_out,
            "; ".join(f"{c.reason} [{c.check}]: {format_args_for_log([c.url])}" for c in kept)
            or "none",
        )
    return PageScanResult(
        page_title=parser.title.strip(),
        favicon_url=parser.favicon,
        candidates=kept,
        checked=check_live,
        left_out=left_out,
        check_limit=limit if check_live else 0,
        skipped=sum(1 for c in kept if c.check_note in _NEVER_ASKED),
    )


def _apply_live_check(
    candidates: list[PageStreamCandidate], limit: int = live_check.MAX_CHECKS
) -> tuple[list[PageStreamCandidate], int]:
    """Check each candidate; leave out what is not audio; live ones first."""
    verdicts = live_check.check_urls([c.url for c in candidates], _probe, limit=limit)
    kept: list[PageStreamCandidate] = []
    left_out = 0
    for candidate in candidates:
        verdict = verdicts.get(candidate.url) or live_check.Verdict(live_check.UNCHECKED)
        if verdict.state == live_check.NOT_AUDIO:
            left_out += 1
            continue
        candidate.check = verdict.state
        candidate.codec = verdict.codec
        candidate.bitrate_kbps = verdict.bitrate_kbps or candidate.bitrate_kbps
        candidate.stream_name = verdict.name or candidate.stream_name
        candidate.genre = verdict.genre
        candidate.check_note = verdict.note
        kept.append(candidate)
    kept.sort(key=lambda c: _CHECK_RANK.get(c.check, 1))  # stable: page order within a rank
    return kept, left_out


def _prefer_https(candidates: list[PageStreamCandidate]) -> list[PageStreamCandidate]:
    """One copy of a stream offered over both http and https: the better-checked
    one, and the https one when they check the same."""

    def rank(candidate: PageStreamCandidate) -> tuple[int, bool]:
        return _CHECK_RANK.get(candidate.check, 1), not candidate.url.startswith("https://")

    best: dict[str, PageStreamCandidate] = {}
    for candidate in candidates:
        key = live_check.https_twin_url(candidate.url)
        held = best.get(key)
        if held is None or rank(candidate) < rank(held):
            best[key] = candidate
    chosen = {id(c) for c in best.values()}
    return [c for c in candidates if id(c) in chosen]


def _read_site_scripts(parser: StreamLinkParser) -> None:
    """Read a few of the site's own player scripts into *parser*.

    Only same-site scripts whose names look like a player (or, on a home page,
    up to two app bundles) are fetched; a failed fetch is skipped.
    """
    for script_url in list(dict.fromkeys(parser.script_urls))[:_MAX_SCRIPTS_TO_READ]:
        try:
            text = _fetch_html(script_url)
        except LinkFinderError:
            continue
        parser.read_script(text, "the site's own script")


def _own_links(url: str, parser: StreamLinkParser) -> list[PageStreamCandidate]:
    """The page's own stream-shaped links -- none on a Global Player station
    page, whose page state also names the streams kept for subscribers."""
    return [] if global_player.is_station_page(url) else parser.candidates


def _status_pages(url: str, html_text: str, parser: StreamLinkParser) -> list[tuple[str, str]]:
    """``(status page, server kind)`` for the scanned page and what it links to.

    The scanned page counts when it is a status address, or a server's front
    page that names Icecast or SHOUTcast in its title or shows Icecast's
    "Mount Point" cards (Global's catalogue names neither).
    """
    here = server_listings.status_kind(url) or server_listings.server_kind(url, parser.title)
    if not here and server_listings.is_front_page(url):
        if server_listings.parse_icecast_html(html_text, url):
            here = server_listings.ICECAST
    pages = [(url, here)] if here else []
    pages.extend((u, server_listings.status_kind(u)) for u in parser.status_urls)
    return pages


def _listed(mounts: list[server_listings.ServerMount], reason: str) -> list[PageStreamCandidate]:
    return [
        PageStreamCandidate(
            url=mount.url,
            reason=reason,
            label=mount.name,
            stream_name=mount.name,
            label_is_name=bool(mount.name),
            bitrate_kbps=mount.bitrate_kbps,
            listeners=mount.listeners,
        )
        for mount in mounts
    ]


def _server_candidates(pages: list[tuple[str, str]], page_html: str) -> list[PageStreamCandidate]:
    """Every stream the first :data:`_MAX_STATUS_SERVERS` servers list.

    Icecast: ``status-json.xsl``; when that gives nothing -- the JSON turned
    off, or a mount hidden behind a proxy -- the HTML status page's "Mount
    Point" cards, and failing those its ``.m3u`` links. SHOUTcast v2:
    ``/statistics?json=1``. Every mount is built on the server that answered,
    never on a backend host the statistics name. *page_html* is the scanned
    page, read again for nothing when it is itself the status page.
    """
    by_root: dict[str, tuple[str, str]] = {}
    for status_url, kind in pages:
        root = server_listings.server_root(status_url)
        if root and kind:
            by_root.setdefault(root, (status_url, kind))
    scanned = pages[0][0] if pages else ""
    out: list[PageStreamCandidate] = []
    for root, (status_url, kind) in list(by_root.items())[:_MAX_STATUS_SERVERS]:
        if kind == server_listings.SHOUTCAST:
            mounts = _read_listing(root + server_listings.SHOUTCAST_JSON, root, kind)
            out.extend(_listed(mounts, "stream listed by the SHOUTcast server"))
            continue
        reason = "mount listed on the server's Icecast status page"
        mounts = _read_listing(root + server_listings.ICECAST_JSON, root, kind)
        if mounts:
            out.extend(_listed(mounts, reason))
        elif not status_url.lower().endswith(server_listings.ICECAST_JSON):
            html_text = page_html if status_url == scanned else ""
            out.extend(_icecast_html_candidates(status_url, html_text, reason))
    return out


def _read_listing(address: str, root: str, kind: str) -> list[server_listings.ServerMount]:
    """One server's JSON listing, read and parsed; ``[]`` when it does not answer."""
    try:
        text = _fetch_html(address)
    except LinkFinderError:
        return []
    if kind == server_listings.SHOUTCAST:
        return server_listings.parse_shoutcast_json(text, root)
    return server_listings.parse_icecast_json(text, root)


def _icecast_html_candidates(
    status_url: str, html_text: str, reason: str
) -> list[PageStreamCandidate]:
    """An Icecast HTML status page's mounts, or its ``.m3u`` links if it shows none."""
    if not html_text:
        try:
            html_text = _fetch_html(status_url)
        except LinkFinderError:
            return []
    mounts = server_listings.parse_icecast_html(html_text, status_url)
    if mounts:
        return _listed(mounts, reason)
    sub_parser = StreamLinkParser(status_url)
    sub_parser.feed(html_text)
    return [
        PageStreamCandidate(
            url=c.url, reason=f"{c.reason} (found via Icecast status page)", label=c.label
        )
        for c in sub_parser.candidates
    ]


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

    Used for embedded ``<iframe>`` pages, pop-up players and followed "Listen
    Live" links. For the latter, each sub-page is *also* run through the
    Triton, TuneIn, SecureNet and Global Player resolvers (``base`` non-empty), since a
    station's linked player page is exactly where such a player tends to live.
    A failed sub-fetch is skipped.
    """
    out: list[PageStreamCandidate] = []
    for sub_url in urls[:cap]:
        try:
            sub_html = _fetch_html(sub_url)
        except LinkFinderError:
            continue
        sub_parser = StreamLinkParser(sub_url)
        sub_parser.feed(sub_html)
        # Resolved streams first: they are API-validated, playable mounts,
        # while a player page's other links are only stream-*shaped*.
        page_candidates: list[PageStreamCandidate] = []
        if base:
            page_candidates.extend(_triton_candidates(sub_url, sub_html, safe_mode=safe_mode))
            page_candidates.extend(_tunein_candidates(sub_url, sub_html, safe_mode=safe_mode))
            page_candidates.extend(_securenet_candidates(sub_url, sub_html))
            page_candidates.extend(_global_candidates(sub_url, sub_html))
        page_candidates.extend(_own_links(sub_url, sub_parser))
        for candidate in page_candidates:
            out.append(replace(candidate, reason=f"{candidate.reason} (found via {reason_suffix})"))
    return out
