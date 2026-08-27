"""Live365: normalize a station link into its stream URL, and browse the lot.

Two halves, and the first one is still a pure string transform with no network
call at all -- read it below. The second half is the **directory**, added
2026-08-26, and the note in the first half that said Live365's station list was
out of reach needs its correction stated plainly rather than quietly deleted:

    Resolving a station needs Live365's auth-gated API, which we deliberately
    do not use.

That is still true of the *API*, and the decision has not changed. What was
missed is that Live365 also publishes a **public XML sitemap** -- advertised by
its own ``robots.txt``, which disallows nothing but a few blog paths -- listing
every station page as ``/station/<Name-Slug>-a<id>``. The ``a#####`` id is right
there in the path, and the id is the one thing the transform below needs. One
GET of ~900 KB yields the whole directory (5,493 stations when measured on
2026-08-26), with no key, no account, no scraping of a login-walled page, and
nothing that Live365 has not published for search engines to read.

That is not a new argument for this project, either: :mod:`quill.core.radio.iheart`
builds its station index from iHeart's public sitemap for exactly the same
reason. This is the same shape applied to the other directory that had been
written off.

What the sitemap does **not** carry is metadata -- no genre, no bitrate, no
real display name beyond what can be read off the slug. Those live in each
stream's ICY headers, which is one request *per station*, so they are fetched
lazily when a listener looks at a station and never for five thousand rows.

The transform, unchanged
------------------------

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

That part is deliberately a **pure string transform**: the ``a#####`` id is
already present in every stream/player link, so no network call, no scraping,
and no use of Live365's authenticated directory API is needed. Nothing in it is
gated in Safe Mode because nothing in it leaves the machine. (Resolving a bare
station *slug* with no id would still need the auth-gated API, which we still
do not use; those links are left untouched -- though a slug that appears in the
sitemap can now be looked up in the directory below instead.)

The directory functions further down *do* reach the network, once, and are
gated: :func:`refuse_in_safe_mode`, a single reviewed egress site
(:func:`_fetch`), HTTPS-only over a verified TLS context with a bounded timeout
and size cap, and a day-long cache.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request

from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation
from quill.core.radio.natural_order import natural_key

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


# --- the directory ----------------------------------------------------------
#
# Everything below reaches the network exactly once per day and is gated. The
# transform above stays pure, and callers that only normalize a pasted link
# never touch any of this.

_SITEMAP_URL = "https://live365.com/sitemap-main.xml"
_STATION_PAGE_BASE = "https://live365.com"
_TIMEOUT_SECONDS = 25.0
#: The sitemap measured 923 KB on 2026-08-26 and grows with the directory. Four
#: megabytes leaves room for that without leaving room for a redirect to
#: something that is not a sitemap at all.
_MAX_BYTES = 4_000_000
_USER_AGENT: str | None = None

CATEGORY_LABEL = "Live365"
#: Spoken/shown attribution. It names the source of the list because "5,493
#: stations" invites the question of where they came from.
CATALOG_CREDIT = "Live365's public sitemap"

#: One station page in the sitemap: ``/station/<Name-Slug>-a<id>``. The id is
#: anchored to the end so a slug containing its own ``a1234`` token cannot win.
_SITEMAP_STATION_RE = re.compile(r"/station/(?P<slug>[^/<>]+?)-(?P<id>[aA]\d{3,8})/?$")
#: A ``<loc>`` element in any sitemap.
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)

_CACHE_KEY = "live365:stations"
#: A day. The directory turns over slowly, the payload is nearly a megabyte,
#: and a stale list of stations is a working branch -- every id in it still
#: resolves to the same stream.
_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60


class Live365Error(CodedError):
    """A Live365 directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-LIVE365-DIRECTORY"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`Live365Error` when Safe Mode is active."""
    if safe_mode:
        raise Live365Error(
            "The Live365 directory is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


def name_from_slug(slug: str) -> str:
    """A readable station name from a sitemap slug (pure).

    ``AIFM-Pop`` -> ``AIFM Pop``. Hyphens become spaces and runs of whitespace
    collapse; **capitalisation is left exactly as the slug has it**, because the
    slug preserves the broadcaster's own casing (``AIFM``, ``KHYI``) and
    title-casing it would turn a callsign into a word.
    """
    return re.sub(r"\s+", " ", str(slug or "").replace("-", " ")).strip()


def parse_sitemap_entries(xml: str) -> list[tuple[str, str]]:
    """``(slug, station_id)`` for every station in a sitemap (pure).

    De-duplicated by id, in sitemap order. Anything that is not a station page
    -- the blog, the home page, a malformed ``<loc>`` -- is skipped rather than
    guessed at.
    """
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for loc in _LOC_RE.findall(xml):
        match = _SITEMAP_STATION_RE.search(loc.strip())
        if match is None:
            continue
        station_id = match.group("id")
        if station_id in seen:
            continue
        seen.add(station_id)
        entries.append((match.group("slug"), station_id))
    return entries


def station_from_entry(slug: str, station_id: str) -> RadioStation:
    """One sitemap entry as a playable :class:`RadioStation` (pure).

    The stream URL is built the same way the transform at the top of this module
    builds it, which is why this directory is cheap: the id in the sitemap path
    *is* the stream key, so nothing has to be resolved or fetched per station.
    """
    return RadioStation(
        name=name_from_slug(slug) or station_id,
        stream_url=f"{_STREAM_BASE}{station_id}",
        # Live365 is not in Radio Browser's namespace and station_uuid is --
        # see the same note in shoutcast.station_from_entry.
        station_uuid="",
        homepage=f"{_STATION_PAGE_BASE}/station/{slug}-{station_id}",
        tags=(CATEGORY_LABEL,),
        source=CATEGORY_LABEL,
    )


def parse_sitemap(xml: str) -> list[RadioStation]:
    """Every station in the sitemap (pure), sorted by name, case-insensitively."""
    stations = [
        station_from_entry(slug, station_id) for slug, station_id in parse_sitemap_entries(xml)
    ]
    stations.sort(key=lambda station: natural_key(station.name))
    return stations


def letter_of(name: str) -> str:
    """The A-Z bucket a station name belongs to (pure); ``#`` for anything else.

    Numbers, punctuation and non-Latin scripts all land in ``#`` -- one honest
    bucket rather than twenty-six letters plus a scattering of one-row folders
    nobody can find again.
    """
    first = str(name or "").strip()[:1].upper()
    return first if "A" <= first <= "Z" else "#"


def letters() -> list[str]:
    """The browse letters, in reading order: ``#`` then ``A`` to ``Z``."""
    return ["#"] + [chr(code) for code in range(ord("A"), ord("Z") + 1)]


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str) -> str:
    """One HTTPS GET of Live365's public sitemap -- the reviewed egress site.

    Reads one byte past the cap so a grown sitemap is **detected** rather than
    parsed as a truncated document, which would quietly drop the tail of the
    alphabet and change the station count on every refresh.
    """
    if not url.startswith("https://"):
        raise Live365Error("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise Live365Error(f"Could not reach the Live365 directory: {error}") from error
    if len(payload) > _MAX_BYTES:
        raise Live365Error(
            f"The Live365 sitemap is larger than {_MAX_BYTES} bytes, so it was not read. "
            "Reading part of it would silently drop stations."
        )
    return payload.decode("utf-8", errors="replace")


def fetch_stations(*, safe_mode: bool = False, refresh: bool = False) -> list[RadioStation]:
    """Every Live365 station, from the cached sitemap."""
    stations, _age = fetch_stations_with_age(safe_mode=safe_mode, refresh=refresh)
    return stations


def fetch_stations_with_age(
    *, safe_mode: bool = False, refresh: bool = False
) -> tuple[list[RadioStation], float | None]:
    """:func:`fetch_stations`, plus how old the answer is in seconds.

    What is cached is the ``(slug, id)`` pair list -- not the near-megabyte XML
    and not the built rows. The pairs are a fraction of the size, they are the
    only part that cannot be recomputed, and rebuilding a row from one is a
    string format.
    """
    refuse_in_safe_mode(safe_mode)
    payload, age = directory_cache.resolve(
        _CACHE_KEY,
        lambda: [list(pair) for pair in parse_sitemap_entries(_fetch(_SITEMAP_URL))],
        max_age_seconds=_CACHE_MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    stations: list[RadioStation] = []
    if isinstance(payload, list):
        for pair in payload:
            # A cache entry has been through JSON, so a tuple comes back a list.
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                stations.append(station_from_entry(str(pair[0]), str(pair[1])))
    stations.sort(key=lambda station: natural_key(station.name))
    return stations, age


def fetch_letter(letter: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """The stations whose names start with *letter* (``#`` for the rest).

    Browsing by letter rather than as one list is not cosmetic: five and a half
    thousand rows in a single node is not a list anybody can work with, least of
    all by ear.
    """
    wanted = str(letter or "").strip().upper()[:1] or "#"
    return [
        station
        for station in fetch_stations(safe_mode=safe_mode)
        if letter_of(station.name) == wanted
    ]


def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Stations whose name contains *query*. Never raises into a search fan-out."""
    wanted = str(query or "").strip().casefold()
    if not wanted:
        return []
    try:
        stations = fetch_stations(safe_mode=safe_mode)
    except Live365Error:
        return []
    return [station for station in stations if wanted in station.name.casefold()]
