"""iHeart directory client: a public-sitemap station index + lazy stream
resolution. No API, no key.

iHeart publishes a standard XML sitemap (``https://www.iheart.com/sitemap.xml``;
robots permits ``/sitemap/`` and ``/live/``) whose index points to a single
``livestations`` sub-sitemap listing every live station's page URL of the form
``https://www.iheart.com/live/<slug>-<id>/``. A directory refresh is therefore
just two GETs -- the stable index, then the current livestations sub-sitemap --
yielding the whole station list (id, human name from the slug, page URL). New or
removed stations are picked up because the index's livestations entry lives at a
dated path that iHeart republishes.

Each station page embeds its real, directly playable stream as a literal quoted
string in an inline ``<script>`` -- either the iHeart-native HLS
(``stream.revma.ihrhls.com/zc<id>/hls.m3u8``) or, for Triton-aggregated
stations, a StreamTheWorld redirect
(``playerservices.streamtheworld.com/api/livestream-redirect/<mount>.m3u8``).
So a station's stream is resolved **lazily, on demand** with one page GET (the
same inline-string extraction :mod:`quill.core.radio.link_finder` already does),
never by bulk-fetching thousands of pages just to refresh the list.

Everything here is a plain HTTPS GET of a public iHeart page -- no browser, no
JavaScript, no API terms to violate -- resolving only what the sitemap and each
page already advertise. Requests funnel through the single reviewed egress site
(:func:`_fetch` -- see ``quill/tools/network_egress_audit.py``), HTTPS-only over
a verified TLS context with a bounded timeout, reached only by an explicit
refresh/play action and disabled in Safe Mode via :func:`refuse_in_safe_mode`.
wx-free, strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core import safe_xml
from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation

_SITEMAP_INDEX = "https://www.iheart.com/sitemap.xml"
_USER_AGENT: str | None = None  # set lazily to avoid a module-load version import
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 4_000_000

#: A ``/live/<slug>-<id>/`` iHeart station page URL -> (slug, numeric id).
_LIVE_URL_RE = re.compile(r"/live/([a-z0-9-]+?)-(\d+)/?$", re.IGNORECASE)
#: The two stream forms iHeart pages embed, most-preferred first.
_STREAM_URL_RES = (
    re.compile(r"https://stream\.revma\.ihrhls\.com/zc\d+/hls\.m3u8", re.IGNORECASE),
    re.compile(
        r"https://playerservices\.streamtheworld\.com/api/livestream-redirect/[A-Za-z0-9._-]+",
        re.IGNORECASE,
    ),
)


class IHeartError(CodedError):
    """An iHeart directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-IHEART-REQUEST"


@dataclass(slots=True)
class IHeartStation:
    """One iHeart live station from the sitemap; ``stream_url`` filled lazily."""

    station_id: str
    name: str
    slug: str
    page_url: str
    stream_url: str = ""


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`IHeartError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service; browsing
    or refreshing the iHeart directory is one. Kept in core (flag passed in) so
    the refusal is unit-testable without wx, mirroring the sibling radio sources.
    """
    if safe_mode:
        raise IHeartError(
            "The iHeart directory is disabled in Safe Mode. Restart QUILL normally to use it."
        )


# --- pure parsers -----------------------------------------------------------


def _sitemap_locs(xml_text: str) -> list[str]:
    """Every ``<loc>`` URL in a sitemap or sitemap-index document (pure)."""
    try:
        root = safe_xml.fromstring(xml_text)
    except (safe_xml.ParseError, safe_xml.UnsafeXMLError):
        return []
    locs: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "loc" and element.text:
            locs.append(element.text.strip())
    return locs


def livestations_sitemap_url(index_xml: str) -> str | None:
    """The current ``livestations-*.xml`` sub-sitemap URL from the index (pure).

    The dated path changes whenever iHeart republishes, so reading it fresh each
    refresh is what picks up new/removed stations.
    """
    for loc in _sitemap_locs(index_xml):
        if "livestations" in loc.lower():
            return loc
    return None


def _name_from_slug(slug: str) -> str:
    """A human-readable station name from a ``/live`` slug (pure).

    ``973-kbco`` -> ``973 Kbco``; ``delilah`` -> ``Delilah``. Best-effort title
    casing of the hyphenated slug -- the display name of last resort until the
    station page (which has a proper title) is fetched.
    """
    words = [word for word in slug.replace("_", "-").split("-") if word]
    return " ".join(word.upper() if word.isupper() else word.capitalize() for word in words)


def parse_livestations_sitemap(xml_text: str) -> list[IHeartStation]:
    """Parse the livestations sub-sitemap into stations (pure).

    Reads every ``/live/<slug>-<id>/`` page URL. A ``<loc>`` that is not a
    station page is skipped. ``stream_url`` is left empty -- resolved lazily by
    :func:`resolve_stream` when the user actually plays the station.
    """
    stations: list[IHeartStation] = []
    for loc in _sitemap_locs(xml_text):
        match = _LIVE_URL_RE.search(loc)
        if not match:
            continue
        slug, station_id = match.group(1), match.group(2)
        stations.append(
            IHeartStation(
                station_id=station_id,
                name=_name_from_slug(slug),
                slug=slug,
                page_url=loc,
            )
        )
    return stations


def extract_stream_url(page_html: str) -> str:
    """The real playable stream URL embedded in a station page, or "" (pure).

    Prefers the iHeart-native ``revma.ihrhls.com/.../hls.m3u8`` HLS, then the
    Triton/StreamTheWorld redirect. Handles the backslash-escaped quoting the
    inline JSON player config uses. Empty when the page advertises neither.
    """
    # Inline JSON escapes forward slashes/quotes; normalise the escapes so the
    # literal URL matches, without otherwise touching the page.
    unescaped = page_html.replace("\\/", "/").replace('\\"', '"')
    for pattern in _STREAM_URL_RES:
        match = pattern.search(unescaped)
        if match:
            return match.group(0)
    return ""


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str) -> str:
    """One HTTPS GET of a public iHeart URL -- the reviewed egress site.

    HTTPS-only over a verified TLS context, bounded timeout and response size.
    """
    import ssl
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise IHeartError(f"Could not reach the iHeart directory: {error}") from error
    return payload.decode("utf-8", errors="replace")


def fetch_station_index(*, safe_mode: bool = False) -> list[IHeartStation]:
    """The full iHeart live-station list -- two GETs (index + sub-sitemap).

    Stream URLs are NOT resolved here (that is lazy, per station, on play). An
    index missing its livestations entry yields an empty list rather than an
    error. Raises :class:`IHeartError` only for a genuine network failure or a
    Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    sub_url = livestations_sitemap_url(_fetch(_SITEMAP_INDEX))
    if not sub_url:
        return []
    return parse_livestations_sitemap(_fetch(sub_url))


def resolve_stream(page_url: str, *, safe_mode: bool = False) -> str:
    """Resolve one station page to its playable stream URL, or "" (one GET).

    A page that advertises no recognised stream yields "" rather than an error,
    so a dead/changed station degrades to "nothing found".
    """
    refuse_in_safe_mode(safe_mode)
    if not page_url.strip():
        return ""
    return extract_stream_url(_fetch(page_url))


def to_radio_station(station: IHeartStation, stream_url: str = "") -> RadioStation:
    """Build a :class:`RadioStation` from an iHeart station."""
    return RadioStation(
        name=station.name,
        stream_url=stream_url or station.stream_url,
        station_uuid=f"iheart:{station.station_id}",
        homepage=station.page_url,
        source="iHeart",
    )
