"""Normalize a Live365 station link into its playable stream URL.

Live365 hosts thousands of stations, each identified by a stable ``a#####`` id
(KHYI 95.3 The Range is ``a25891``). Its playable stream lives at a predictable
address::

    https://streaming.live365.com/<id>

but the links a listener actually has in hand are usually *not* that stream:

* ``https://player.live365.com/<id>``            -- the web player **page** (HTML)
* ``https://live365.com/station/<slug>-<id>``    -- the station **page** (HTML)
* ``http://streaming.live365.com/<id>#.mp3``      -- the stream, but http + a
                                                     player-hint fragment

Pasted as a custom station those first two don't play at all (they're web
pages), and the third is plain-http with a junk fragment. This module rewrites
any of them -- or a bare ``a#####`` id -- to the one canonical ``https``
stream URL, so "paste a Live365 link" just works.

It is deliberately a **pure string transform**: the ``a#####`` id is already
present in every stream/player link, so no network call, no scraping, and no
use of Live365's authenticated directory API is needed. That keeps it safe by
construction -- nothing to gate in Safe Mode, no new network-egress site.
(Resolving a bare station *slug* with no id would need Live365's auth-gated
API, which we deliberately do not use; those links are left untouched.)

wx-free, strict-typed.
"""

from __future__ import annotations

import re

#: A Live365 station id: a lowercase/uppercase ``a`` then 3-8 digits (e.g.
#: ``a25891``, ``a06375``, ``a551803``, ``A1820``). 3+ digits avoids matching a
#: stray ``a12`` inside a station-name slug; the ids Live365 issues are 4-7.
_LIVE365_ID_RE = re.compile(r"[aA]\d{3,8}")

#: The canonical stream host. A station's live audio is always served here,
#: keyed by its id (the entry point 302-redirects to the current CDN edge).
_STREAM_BASE = "https://streaming.live365.com/"


def _looks_live365(text: str) -> bool:
    """True when *text* references Live365 (any host) or is a bare station id."""
    lowered = text.lower()
    if "live365.com" in lowered:
        return True
    return re.fullmatch(r"[aA]\d{3,8}", text.strip()) is not None


def live365_station_id(text: str) -> str | None:
    """Return the ``a#####`` station id in *text*, or ``None``.

    Only looks when *text* actually references Live365 (or is a bare id), so a
    non-Live365 URL that happens to contain an ``a1234`` token is left alone.
    The **last** id in the string wins, so a station-page slug that carries the
    id at its end (``.../Some-Station-a25891``) resolves to the trailing id
    rather than a digit run inside the slug.
    """
    if not _looks_live365(text):
        return None
    matches = _LIVE365_ID_RE.findall(text.strip())
    return matches[-1] if matches else None


def live365_stream_url(text: str) -> str | None:
    """The canonical ``https`` stream URL for a Live365 link/id, or ``None``.

    Returns ``None`` for anything that is not a recognizable Live365 reference
    (so callers can fall through to their normal handling). Idempotent: a URL
    that is already ``https://streaming.live365.com/<id>`` maps to itself.
    """
    station_id = live365_station_id(text)
    if station_id is None:
        return None
    return f"{_STREAM_BASE}{station_id}"


def normalize_live365(url: str) -> str:
    """Rewrite a Live365 link/id to its canonical stream URL, else return *url*.

    Safe to call on any string: a non-Live365 URL comes back unchanged, so this
    can sit in a generic "clean up the pasted URL" step.
    """
    return live365_stream_url(url) or url
