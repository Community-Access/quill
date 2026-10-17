"""What kind of address is this: a stream, or a page with a Play button on it?

Extracted from :mod:`quill.core.radio.link_finder` under GATE-11 when #36
needed the same question answered in a second place: Add Custom Station, where
a listener pastes whatever the station's website gave them. John Gassman pasted
Altitude Sports Radio's address, the audio engine was handed a web page, and
the only thing anybody heard was "source not supported".

Four pure predicates:

* :func:`is_portal_page_url` -- an iHeart or TuneIn landing page (#1087).
* :func:`is_player_page_url` -- any page that hosts a player: those portals, a
  SecureNet Cirrus front-end (#1491), or a Triton ``player.listenlive.co`` page
  (#36). Each answers HTML and hides a real mount one fetch away.
* :func:`is_help_page_url` -- a help-centre article, which a player page links
  and whose URL can look stream-shaped (#36).
* :func:`is_web_page_address` -- the wider question Add Custom Station asks:
  a player page, or a site's own home page / ``.html`` page.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import urllib.parse

from quill.core.radio import securenet, triton

__all__ = [
    "is_help_page_url",
    "is_player_page_url",
    "is_portal_page_url",
    "is_web_page_address",
    "same_page",
]

#: Known third-party station directories/portals. A *page* URL on one of these
#: hosts (an iHeart ``/live/<slug>-<id>/`` or a TuneIn ``/radio/<name>-s<id>/``
#: landing page) is never itself a playable stream -- the real stream is
#: embedded in the page's inline player. Such links are followed one level deep
#: (like a "Listen Live" link) so the embedded stream is extracted, instead of
#: being offered as a bogus stream candidate. Without this, iHeart ``/live``
#: links were flagged as "stream-shaped" (``/live`` is a path hint) and the
#: unplayable portal page URL was handed to the user (issue #1087).
_PORTAL_HOSTS = ("iheart.com", "tunein.com")
_PORTAL_PAGE_PATH_HINTS = ("/live/", "/radio/", "/podcast/")

#: Help-centre hosts. Triton's player links its own support article,
#: ``.../s/article/Stream-doesn-t-start-in-V4-Player...``, which the ``/stream``
#: hint took for a stream and listed FIRST (#36). An article is never audio.
_HELP_HOSTS = ("force.com", "zendesk.com", "freshdesk.com", "helpscoutdocs.com")

#: Page suffixes no audio stream wears.
_PAGE_SUFFIXES = (".html", ".htm", ".php", ".asp", ".aspx", ".jsp")


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url.strip()).hostname or "").lower()


def is_portal_page_url(url: str) -> bool:
    """True when *url* is a known station-directory portal page (iHeart/TuneIn).

    Matching is host + path scoped: the same ``/live/`` path fragment on a
    station's own domain is unaffected, only true portal hosts count.
    """
    host = _host(url)
    if not any(host == portal or host.endswith("." + portal) for portal in _PORTAL_HOSTS):
        return False
    path = urllib.parse.urlsplit(url).path.lower()
    return any(hint in path for hint in _PORTAL_PAGE_PATH_HINTS)


def is_player_page_url(url: str) -> bool:
    """True when *url* is a page that hosts a player, not a stream to play.

    The station-directory portals, the SecureNet Cirrus front-ends and the
    Triton ``player.listenlive.co`` pages. All answer HTML, so handing one to
    the engine fails; all hide a real mount one fetch away.
    """
    return (
        is_portal_page_url(url)
        or securenet.is_player_page_url(url)
        or triton.is_player_page_url(url)
    )


def is_help_page_url(url: str) -> bool:
    """True when *url* is on a help-centre host (pure)."""
    host = _host(url)
    return any(host == h or host.endswith("." + h) for h in _HELP_HOSTS)


def is_web_page_address(url: str) -> bool:
    """True when *url* is plainly a web page rather than an audio stream (pure).

    A player page (above), or a site's own page: a bare home page on the
    standard port (``https://www.altitudesportsradio.com/``) or a path ending
    in ``.html``/``.php`` and the like. Deliberately narrow the other way: a
    Shoutcast server streams from its root too, but on a port of its own
    (``http://host:8000/``), so an explicit port is never called a page.
    """
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        return False
    if is_player_page_url(url):
        return True
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is not None:
        return False
    path = parsed.path.lower()
    if path.strip("/") == "" and not parsed.query:
        return True
    return path.endswith(_PAGE_SUFFIXES)


def same_page(first: str, second: str) -> bool:
    """True when two URLs name the same page, ignoring scheme, trailing slash
    and a trailing language segment (``/20551`` vs ``/20551/en``) -- a player
    page links to itself, and following that link only fetches it twice."""

    def key(url: str) -> tuple[str, str]:
        parsed = urllib.parse.urlsplit(url.strip())
        parts = [p for p in parsed.path.lower().split("/") if p]
        if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isalpha():
            parts = parts[:-1]
        return ((parsed.hostname or "").lower(), "/".join(parts))

    return key(first) == key(second)
