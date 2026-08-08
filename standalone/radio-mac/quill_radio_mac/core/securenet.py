"""SecureNet Systems (Cirrus) player resolver.

SecureNet Systems hosts the "Cirrus" web player used by a large number of
US broadcasters. Its player pages look like::

    https://streamdb3web.securenetsystems.net/v5/ROM
    https://radio.securenetsystems.net/v5/warl

and the last path segment is the station's callsign. Unlike Triton or TuneIn,
the real stream URL **is** present in the page HTML::

    https://ice66.securenetsystems.net/ROM

...but the generic scanner in :mod:`quill_radio_mac.core.link_finder` throws it
away, because that URL has no file extension and no ``/stream``-style path
hint -- it is a bare Icecast mount whose path is just the callsign. It is
indistinguishable, by shape alone, from an ordinary web page link. Hence this
module: recognise the platform, then trust the platform-specific pattern
instead of the generic shape heuristic.

The ice-server number is **not** derivable from the callsign (``ROM`` is on
``ice66``, ``WARL`` on ``ice25``), so it has to be read from the page rather
than computed. When the page is reachable but carries no ice URL, a bare
``https://ice<N>.securenetsystems.net/<CALLSIGN>`` cannot be guessed and the
resolver reports nothing rather than offering a link that will not play.

wx-free, strict-typed. Parsing only -- the page fetch belongs to the caller,
so this module makes no network calls of its own and needs no egress entry.
"""

from __future__ import annotations

import re
import urllib.parse

__all__ = [
    "page_is_securenet_player",
    "callsign_from_page",
    "stream_urls_from_page",
]

#: Hosts that serve the Cirrus player. The player is served from several
#: front-ends (``radio.``, ``streamdb<N>web.``), so match the domain rather
#: than enumerate every prefix.
_PLAYER_DOMAIN = "securenetsystems.net"

#: ``/v5/<CALLSIGN>`` (also ``/v4/``, ``/v6/`` as the platform versions its
#: player) is the player page path.
_PLAYER_PATH_RE = re.compile(r"^/v\d+/([A-Za-z0-9_\-]{2,32})/?$")

#: The playable mount as it appears in the page: an ``ice<N>`` host plus the
#: callsign. The optional query carries a per-visit ``playSessionID`` used for
#: the platform's own listener metrics; it is deliberately dropped -- a saved
#: favourite must not pin one visit's session id forever.
_ICE_URL_RE = re.compile(
    r"https?://(ice\d+\.securenetsystems\.net)/([A-Za-z0-9_\-]{2,32})(?:\?[^\s\"'<>]*)?",
    re.IGNORECASE,
)


def page_is_securenet_player(url: str, html: str = "") -> bool:
    """True when *url* (or *html*) looks like a SecureNet Cirrus player page."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host.endswith(_PLAYER_DOMAIN):
        return True
    return _PLAYER_DOMAIN in html.lower() and bool(_ICE_URL_RE.search(html))


def callsign_from_page(url: str, html: str = "") -> str:
    """The station callsign advertised by a player page, or ``""``.

    Prefers the callsign on the page's own ice mount, because that is the
    canonical casing: the player URL's casing is whatever the person linking
    happened to type, so ``/v5/warl`` still streams from ``/WARL`` and the
    station should be labelled ``WARL``. Falls back to the URL path for a page
    that names no mount.
    """
    ice = _ICE_URL_RE.search(html)
    if ice and ice.group(2).lower() != "media":
        return ice.group(2)
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower().endswith(_PLAYER_DOMAIN):
        match = _PLAYER_PATH_RE.match(parsed.path or "")
        if match:
            return match.group(1)
    return ""


def stream_urls_from_page(html: str) -> list[str]:
    """Every distinct playable stream URL advertised by a Cirrus player page.

    Session-tracking query strings are stripped and duplicates collapsed, so a
    page that mentions its mount several times (bare, and again with a
    ``playSessionID``) yields exactly one saveable URL. Order is first-seen.
    """
    found: list[str] = []
    seen: set[str] = set()
    for match in _ICE_URL_RE.finditer(html):
        host, callsign = match.group(1).lower(), match.group(2)
        # "media" is the platform's shared ad/interstitial mount, not a station.
        if callsign.lower() == "media":
            continue
        stream = f"https://{host}/{callsign}"
        if stream not in seen:
            seen.add(stream)
            found.append(stream)
    return found
