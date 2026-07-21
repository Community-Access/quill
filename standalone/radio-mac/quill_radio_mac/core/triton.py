"""Resolve a Triton Digital / StreamTheWorld player page to a playable stream.

Ported near-verbatim from upstream ``quill.core.radio.triton``. Many
broadcast stations (thousands of US AM/FM stations, and the whole
``player.listenlive.co`` network) put their "Listen Live" button behind a
Triton Digital web player. That player is a JavaScript PWA: the actual stream
URL is *not* in the page HTML -- it is computed at runtime when the player's JS
calls Triton's provisioning API. So the plain-HTML scanner in
:mod:`quill_radio_mac.core.link_finder` (which deliberately never runs
JavaScript) finds nothing on those pages, even though a Play button is
plainly visible.

The good news: the stream is fully derivable without running any JavaScript.
Two static facts on the page are enough:

* The station **callsign** (mount name), which appears verbatim in the Triton
  PWA's own asset URLs -- e.g. the station-logo image on ``pwaimg.listenlive.co``
  is named ``KMGLFM_1115091_config_station_logo_image_...png``. See
  :func:`callsign_from_page`.
* Triton's **provisioning API**, a plain HTTPS GET that returns an XML
  ``<live_stream_config>`` document listing every mountpoint (one per codec:
  MP3, HE-AAC, ...), each with a set of CDN servers. A playable URL is simply
  ``https://<server-ip>/<mount>``. See :func:`resolve_station_streams`.

This module does exactly that -- one small GET, an XML parse, no browser, no
JavaScript -- so :mod:`link_finder` can surface the real Play-button stream(s)
as ordinary scan candidates. It resolves only what the page already advertises
(the callsign) and validates it against the API (a non-Triton page, or a
callsign the API rejects, simply yields no candidates), so it never guesses a
wrong stream.

The single egress call funnels through :func:`_fetch_api`, HTTPS-only over a
verified TLS context with a bounded timeout, reached only by the same
explicit "Scan" button as the rest of :mod:`link_finder` and disabled in
Safe Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.

Threading contract: pure XML parsing plus one blocking network call
(:func:`_fetch_api`); callers invoke :func:`resolve_station_streams` off the
UI thread.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from quill_radio_mac import __version__
from quill_radio_mac.core import safe_xml
from quill_radio_mac.core.error_codes import CodedError

_USER_AGENT = f"QuillRadioMac/{__version__}"
_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 1_000_000

#: Triton's public provisioning endpoint. ``station`` is the callsign/mount;
#: ``transports=http`` asks for direct progressive streams (not just HLS) so a
#: simple ``https://<server>/<mount>`` URL is playable by any audio backend.
_API_BASE = "https://playerservices.streamtheworld.com/api/livestream"
_API_VERSION = "1.9"

#: Hosts whose presence on a scanned page marks it as a Triton player, so we
#: only ever hit Triton's API for pages that actually are Triton players.
_TRITON_MARKERS = (
    "streamtheworld.com",
    "tritondigital.com",
    "listenlive.co",
    "playerservices",
)

#: The station logo the Triton/listenlive PWA renders is named after the mount,
#: e.g. ``KMGLFM_1115091_config_station_logo_image_1514560282.png``. The leading
#: token (letters/digits, typically a broadcast callsign) is the mount name the
#: provisioning API expects.
_LOGO_CALLSIGN_RE = re.compile(r"/([A-Za-z0-9]{3,})_\d+_config_station_logo", re.IGNORECASE)
#: Fallback: a bare ``station=CALLSIGN`` query anywhere in the page's scripts.
_STATION_PARAM_RE = re.compile(r"[?&]station=([A-Za-z0-9]{3,})\b", re.IGNORECASE)


class TritonResolverError(CodedError):
    """A Triton/StreamTheWorld resolution failed (network, or Safe Mode)."""

    code = "QUILL-RADIO-TRITON-REQUEST"


@dataclass(slots=True)
class TritonStream:
    """One playable mountpoint resolved from a Triton player page."""

    #: A directly playable ``https://<server>/<mount>`` URL.
    url: str
    #: The mount name (== callsign for the primary MP3 stream, e.g. ``KMGLFM``;
    #: codec-specific mounts append a suffix, e.g. ``KMGLFMAAC``).
    mount: str
    #: Upper-cased codec label for the station browser, e.g. ``MP3``, ``AAC``.
    codec: str
    #: Bitrate in bits per second (0 when the API omits it).
    bitrate: int = 0


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`TritonResolverError` when Safe Mode is active.

    Safe Mode disables every network service, and resolving a Triton
    player is one. Kept in core (flag passed in) so the refusal is
    unit-testable without wx, mirroring the sibling radio sources.
    """
    if safe_mode:
        raise TritonResolverError(
            "Finding stream links from a website is disabled in Safe Mode. "
            "Restart Quill Radio normally to use it."
        )


def page_is_triton_player(url: str, html: str) -> bool:
    """True when *url*/*html* look like a Triton Digital web player.

    Pure and cheap: a substring scan over the page the scanner already
    fetched. Used to gate the extra provisioning-API round trip so this app
    only ever contacts Triton for pages that actually are Triton players.
    """
    haystack = f"{url}\n{html}".lower()
    return any(marker in haystack for marker in _TRITON_MARKERS)


def callsign_from_page(url: str, html: str) -> str | None:
    """Extract the Triton mount/callsign advertised on the page, or ``None``.

    Pure. Tries the station-logo asset name first (the most reliable signal on
    a ``player.listenlive.co`` page), then any explicit ``station=`` query in
    the page's scripts. Returns the callsign uppercased (Triton mounts are
    conventionally upper-case) or ``None`` when the page advertises none.
    """
    for pattern in (_LOGO_CALLSIGN_RE, _STATION_PARAM_RE):
        match = pattern.search(html)
        if match:
            return match.group(1).upper()
    return None


def _api_url(callsign: str) -> str:
    query = urllib.parse.urlencode({
        "station": callsign,
        "transports": "http",
        "version": _API_VERSION,
    })
    return f"{_API_BASE}?{query}"


def _fetch_api(callsign: str) -> str:
    """One HTTPS GET of Triton's provisioning API -- the reviewed egress site.

    HTTPS-only over a verified TLS context, bounded timeout and response size.
    """
    request = urllib.request.Request(_api_url(callsign), headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise TritonResolverError(
            f"Could not reach the station's stream service: {error}"
        ) from error
    return payload.decode("utf-8", errors="replace")


def _codec_label(raw: str) -> str:
    """Map a Triton ``codec`` attribute to a short station-browser label."""
    lowered = raw.strip().lower()
    if lowered.startswith("mp3"):
        return "MP3"
    if "aac" in lowered:  # aac, heaacv2, aacp, ...
        return "AAC"
    if lowered.startswith("ogg") or "vorbis" in lowered or "opus" in lowered:
        return "OGG"
    return raw.strip().upper()


def parse_livestream_config(xml_text: str) -> list[TritonStream]:
    """Parse Triton's ``<live_stream_config>`` XML into playable streams (pure).

    Each ``<mountpoint>`` with an OK ``<status-code>`` yields one stream,
    built from its first server and its ``<mount>`` name. Codec-specific
    mounts (MP3, HE-AAC, ...) each produce their own entry, MP3 first (the
    order Triton returns, which puts the widely-compatible MP3 mount ahead of
    AAC). Tolerant of junk: an unparsable document or a mountpoint missing a
    server/mount is skipped, never fatal.
    """
    try:
        root = safe_xml.fromstring(xml_text)
    except (safe_xml.ParseError, safe_xml.UnsafeXMLError):
        return []

    streams: list[TritonStream] = []
    for mountpoint in root.iter():
        if _localname(mountpoint.tag) != "mountpoint":
            continue
        if not _mountpoint_ok(mountpoint):
            continue
        mount = _first_child_text(mountpoint, "mount")
        server_host = _first_server_host(mountpoint)
        if not mount or not server_host:
            continue
        codec, bitrate = _mountpoint_media(mountpoint)
        streams.append(
            TritonStream(
                url=f"https://{server_host}/{mount}",
                mount=mount,
                codec=codec,
                bitrate=bitrate,
            )
        )
    return streams


def resolve_station_streams(callsign: str, *, safe_mode: bool = False) -> list[TritonStream]:
    """Resolve *callsign* to its playable Triton streams (one GET + parse).

    Returns an empty list -- never raises for a "no such station" answer --
    when the API reports no OK mountpoints, so a wrong guess degrades to
    "nothing found" rather than an error. Raises :class:`TritonResolverError`
    only for a genuine network/transport failure or a Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    normalized = callsign.strip().upper()
    if not normalized:
        return []
    return parse_livestream_config(_fetch_api(normalized))


# --- XML helpers (namespace-agnostic; Triton stamps a version namespace) ---


def _localname(tag: str) -> str:
    """Strip the ``{namespace}`` prefix ElementTree puts on namespaced tags."""
    return tag.rsplit("}", 1)[-1]


def _iter_local(parent: Element, name: str) -> Iterator[Element]:
    for child in parent.iter():
        if _localname(child.tag) == name:
            yield child


def _first_child_text(parent: Element, name: str) -> str:
    for child in _iter_local(parent, name):
        return (child.text or "").strip()
    return ""


def _mountpoint_ok(mountpoint: Element) -> bool:
    code = _first_child_text(mountpoint, "status-code")
    return code in ("", "200")  # tolerate a missing status; reject explicit non-200


def _first_server_host(mountpoint: Element) -> str:
    for server in _iter_local(mountpoint, "server"):
        host = _first_child_text(server, "ip")
        if host:
            return host
    return ""


def _mountpoint_media(mountpoint: Element) -> tuple[str, int]:
    for audio in _iter_local(mountpoint, "audio"):
        codec = _codec_label(audio.get("codec", ""))
        try:
            bitrate = int(audio.get("bitrate", "0"))
        except ValueError:
            bitrate = 0
        return codec, bitrate
    # Fall back to the mountpoint-level <format>/<bitrate> if present.
    fmt = _codec_label(_first_child_text(mountpoint, "format"))
    try:
        bitrate = int(_first_child_text(mountpoint, "bitrate") or "0")
    except ValueError:
        bitrate = 0
    return fmt, bitrate
