"""The SHOUTcast directory (directory.shoutcast.com): ~60,000 stations, by
genre, by live audience, or by search. Keyless.

Quill Radio has always known what a SHOUTcast *server* is --
:mod:`quill.core.radio.my_servers` reads a v2 ``/stat`` or a v1 ``/7.html``,
:mod:`quill.core.radio.station_status` reads its now-playing, :mod:`icy` reads
its stream titles -- and has never had its **directory**, which is the largest
index of small Icecast/SHOUTcast broadcasters anywhere and the only one that
publishes *live listener counts*.

**Why this is reachable at all.** The Winamp "yellow pages" API was retired
after the 2014 Radionomy acquisition and no key has been obtainable by an
open-source desktop application since. What replaced it is the directory
website's own small set of form-POST endpoints, which answer JSON to anyone;
they are what the site itself calls, they have survived two changes of
ownership and a decade unchanged, and they need no account, no key and no
browser. Every one of them was verified against the live service on 2026-08-26
before this module was written, including with Quill Radio's own honest
User-Agent -- so nothing here pretends to be a web browser.

**What the probe changed about the design**, because the two open-source
clients that use these endpoints get some of it wrong:

* A genre reply is capped at **500 rows**. It is a slice, not the genre, and
  the source label says so rather than implying completeness.
* ``Listeners`` is *sparse* on a genre page -- 39 of 500 in a live Jazz reply --
  and universal on ``/Home/Top``. It is the field that separates a station on
  the air from a parked mount, so rows arrive **sorted by it, descending**.
* ``StreamUrl`` is always ``null`` and ``IceUrl`` is nearly always empty (5 of
  500). The public tune-in ``.pls`` is the only reliable route to audio, and
  there is deliberately no fallback built on either field.
* Station **names collide but ids do not** (25 duplicate names in one genre
  reply), so de-duplication is by ``ID``.
* The reply is UTF-8 and will break a locale-default decode, which is why
  :func:`_request` decodes explicitly.

There is deliberately **no "all stations" node**. The directory has no such
endpoint, and synthesising one means sweeping 313 genres -- 313 requests behind
a tree node that looks like every other tree node. If that is ever wanted it is
a background job with spoken progress, not a folder.

One HTTPS request per action to a single reviewed egress site
(:func:`_request` -- see ``quill/tools/network_egress_audit.py``), HTTPS-only
over a verified TLS context with a bounded timeout and size cap, reached only by
an explicit browse, search or refresh, and refused in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import html as _html
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_BASE = "https://directory.shoutcast.com"
_BROWSE_URL = f"{_BASE}/Home/BrowseByGenre"
_TOP_URL = f"{_BASE}/Home/Top"
_SEARCH_URL = f"{_BASE}/Search/UpdateSearch"
_GENRE_INDEX_URL = f"{_BASE}/Genre"
#: The public tune-in **playlist** for one station id. It is a ``.pls`` holding
#: the real stream address, and handing that URL to the player does not work --
#: reported 2026-08-26 ("many of the stations from the shoutcast directory are
#: not playing"), on a station with 293 listeners that was demonstrably on the
#: air. A player is given a stream, not a playlist of one; every other source
#: here already knows that (:mod:`quill.core.radio.soma_fm` resolves its own
#: ``.pls`` for exactly this reason). So a SHOUTcast row is resolved at play
#: time -- one request, on the station you actually chose, rather than 500 for
#: a genre page you are only reading.
_TUNEIN_URL = "https://yp.shoutcast.com/sbin/tunein-station.pls?id={station_id}"

_TIMEOUT_SECONDS = 20.0
#: A genre reply measured 116 KB and Top 133 KB; the genre index page 101 KB.
#: Two megabytes is generous enough that growth is not a surprise and small
#: enough that a redirect to something else entirely is caught.
_MAX_BYTES = 2_000_000
_USER_AGENT: str | None = None

CATEGORY_LABEL = "SHOUTcast"
#: Spoken/shown attribution. It names the cap because a listener hearing "500
#: stations" about a genre with thousands should know which 500.
CATALOG_CREDIT = "the SHOUTcast directory, up to 500 stations per genre, most listeners first"

#: A genre link on the directory's genre index: ``href="/Genre?name=Hip%20Hop"``.
_GENRE_LINK_RE = re.compile(r'href="/Genre\?name=([^"&]+)"', re.IGNORECASE)

#: Strings the index serves that are not genres a listener would browse.
_NOT_A_GENRE = frozenset({"", "null", "none", "n/a", "unknown"})

#: SHOUTcast's ``Format`` MIME to the short codec name the row shows. Anything
#: unlisted falls back to the MIME subtype, uppercased, so a new codec appears
#: as itself rather than as nothing.
_CODECS: dict[str, str] = {
    "audio/mpeg": "MP3",
    "audio/mp3": "MP3",
    "audio/aacp": "AAC+",
    "audio/aac": "AAC",
    "audio/ogg": "OGG",
    "video/nsv": "NSV",
}


class ShoutcastError(CodedError):
    """A SHOUTcast directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-SHOUTCAST-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`ShoutcastError` when Safe Mode is active."""
    if safe_mode:
        raise ShoutcastError(
            "The SHOUTcast directory is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


# --- pure parsers -----------------------------------------------------------


def tunein_url(station_id: object) -> str:
    """The public tune-in ``.pls`` URL for a station id (pure)."""
    return _TUNEIN_URL.format(station_id=urllib.parse.quote(str(station_id), safe=""))


def codec_of(mime: str) -> str:
    """A short codec name from SHOUTcast's ``Format`` MIME (pure)."""
    value = str(mime or "").strip().lower()
    if not value:
        return ""
    known = _CODECS.get(value)
    if known:
        return known
    return value.split("/")[-1].upper()


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


#: The lazy node id a browse row carries until it is played:
#: ``shoutcaststation:<id>``. See :func:`resolve_stream`.
STATION_KIND = "shoutcaststation"


def station_id_of(station: RadioStation) -> str:
    """The SHOUTcast id behind a row built by this module (pure), or ``""``.

    Read back out of the tune-in URL rather than stored in a second field: the
    id is already in the row, and a duplicate would be one more thing that can
    disagree with itself.
    """
    url = str(getattr(station, "stream_url", "") or "")
    if "tunein-station.pls?id=" not in url:
        return ""
    return url.rsplit("id=", 1)[-1].split("&")[0].strip()


def station_from_entry(entry: dict[str, Any]) -> RadioStation | None:
    """One directory row as a :class:`RadioStation` (pure), or ``None``.

    ``None`` for an entry with no ``ID``: the id is the only route to audio
    here, so a row without one is not a station this app can offer.
    """
    station_id = entry.get("ID")
    if station_id in (None, ""):
        return None
    name = str(entry.get("Name") or "").strip()
    if not name:
        return None
    genre = str(entry.get("Genre") or "").strip()
    track = str(entry.get("CurrentTrack") or "").strip()
    return RadioStation(
        # Verbatim. SHOUTcast names shout ("[EN] HUBU.FM | AD FREE"), and a
        # broadcaster's name is theirs -- tidying it would make the station
        # unfindable by the name its own listeners know it by.
        name=name,
        stream_url=tunein_url(station_id),
        # NOT station_uuid: that field is Radio Browser's namespace, and
        # radio_browser.register_click() posts whatever is in it to Radio
        # Browser's click endpoint. A SHOUTcast id there would be sent to a
        # directory that has never heard of it.
        station_uuid="",
        tags=(genre,) if genre else (),
        codec=codec_of(str(entry.get("Format") or "")),
        bitrate_kbps=_as_int(entry.get("Bitrate")),
        listeners=_as_int(entry.get("Listeners")),
        source=CATEGORY_LABEL,
        # The directory's snapshot of what was on when the list was fetched --
        # worth a lot when choosing a station, and worded so it is never
        # mistaken for live now-playing, which arrives from ICY on play.
        notes=f"Was playing: {track}" if track else "",
    )


def parse_stations(payload: str) -> list[RadioStation]:
    """Stations from a browse/top/search reply (pure), most listeners first.

    De-duplicated by station id, then **sorted by live listeners descending**,
    stably, so the directory's own order survives among the stations that
    report nothing. That sort is the single most useful thing this module does:
    a genre reply is 500 rows of which fewer than one in ten had an audience
    when measured, and without it the first screen is parked mounts.

    Tolerant: anything that is not a JSON list of objects yields ``[]``.
    """
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("ID", ""))
        if not key or key in seen:
            continue
        station = station_from_entry(entry)
        if station is None:
            continue
        seen.add(key)
        stations.append(station)
    stations.sort(key=lambda station: station.listeners, reverse=True)
    return only_live(stations)


def only_live(stations: list[RadioStation]) -> list[RadioStation]:
    """Drop the stations nobody is listening to, if that is what was asked for.

    The declared option (``source_options.SHOUTCAST_SHOW``) defaults to showing
    everything, because "the directory lists it" is the honest default and a
    filter that hides four hundred rows by surprise is worse than a list that
    needs sorting. A listener who has said "only stations with listeners"
    means it -- and on this directory it typically turns 500 rows into 40.
    """
    from quill.core.radio import source_options

    if source_options.chosen(source_options.SHOUTCAST_SHOW.key) != "live":
        return stations
    return [station for station in stations if station.listeners > 0]


def is_useful_genre(name: str) -> bool:
    """True when *name* is a genre worth showing (pure)."""
    value = str(name or "").strip()
    if value.casefold() in _NOT_A_GENRE:
        return False
    return 1 < len(value) <= 32


def parse_genres(page_html: str) -> list[str]:
    """Genre names from the directory's genre index (pure), A-Z.

    The index is a page of ``/Genre?name=<urlencoded>`` links -- the same markup
    both open-source StreamTuner generations matched, still present after the
    page began redirecting to ``/Search``. Names are percent-decoded (``Hip%20Hop``
    -> ``Hip Hop``), HTML-unescaped, de-duplicated case-insensitively keeping the
    first spelling seen, and sorted, because unlike Xiph's index this one is in
    no useful order of its own.
    """
    seen: dict[str, str] = {}
    for raw in _GENRE_LINK_RE.findall(page_html):
        name = _html.unescape(urllib.parse.unquote_plus(raw)).strip()
        key = name.casefold()
        if key not in seen and is_useful_genre(name):
            seen[key] = name
    return sorted(seen.values(), key=str.casefold)


def genre_display(name: str) -> str:
    """A human genre label (pure). The directory already capitalises its own
    genres (``Hip Hop``, ``R&B``, ``80s``), so this leaves them alone."""
    return str(name or "").strip()


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _request(url: str, fields: dict[str, str] | None = None) -> str:
    """One HTTPS request to the SHOUTcast directory -- the reviewed egress site.

    A **POST** when *fields* is given (the browse, top and search endpoints are
    form posts, which is the one way this source differs from every other
    directory Quill Radio reads), otherwise a GET that follows the genre index's
    redirect.

    Only a genre name or a search string is ever sent -- no account, no
    identifier, no listener detail -- with Quill Radio's ordinary descriptive
    User-Agent. Reads one byte past the cap so an over-long reply is *detected*
    rather than handed to a JSON parser as a truncated document, and decodes
    UTF-8 explicitly because the directory serves non-ASCII station names that a
    locale-default decode mangles or refuses outright.
    """
    if not url.startswith("https://"):
        raise ShoutcastError("Only https:// URLs can be fetched.")
    data: bytes | None = None
    headers = {"User-Agent": _user_agent(), "Accept": "application/json, text/html, */*"}
    if fields is not None:
        data = urllib.parse.urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise ShoutcastError(f"Could not reach the SHOUTcast directory: {error}") from error
    if len(payload) > _MAX_BYTES:
        raise ShoutcastError(
            f"The SHOUTcast directory reply is larger than {_MAX_BYTES} bytes, so it was "
            "not read. Reading part of it would silently drop stations."
        )
    return payload.decode("utf-8", errors="replace")


#: The genre index is a scrape of a page that changes about never, so it is
#: cached for a week: a stale genre list is a working browse tree, and a failed
#: one is an empty source.
_GENRES_CACHE_KEY = "shoutcast:genres"
_GENRES_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def fetch_genres(*, safe_mode: bool = False, refresh: bool = False) -> list[str]:
    """Every genre the directory offers (313 when last measured), cached a week."""
    genres, _age = fetch_genres_with_age(safe_mode=safe_mode, refresh=refresh)
    return genres


def fetch_genres_with_age(
    *, safe_mode: bool = False, refresh: bool = False
) -> tuple[list[str], float | None]:
    """:func:`fetch_genres`, plus how old the answer is in seconds (``None`` =
    fetched live). :func:`directory_cache.spoken_age` turns it into words."""
    refuse_in_safe_mode(safe_mode)
    payload, age = directory_cache.resolve(
        _GENRES_CACHE_KEY,
        lambda: parse_genres(_request(_GENRE_INDEX_URL)),
        max_age_seconds=_GENRES_MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    genres = [str(name) for name in payload] if isinstance(payload, list) else []
    return genres, age


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """The directory's stations for one genre -- **up to 500**, fetched fresh.

    Not cached: it is a live listing with live audience figures, and Refresh
    re-calls it. The 500 is the directory's own cap, not ours; ``CATALOG_CREDIT``
    and the source label both say so, because a browse list that silently
    truncates a genre reads as a complete one.
    """
    refuse_in_safe_mode(safe_mode)
    name = str(genre or "").strip()
    if not name:
        return []
    return parse_stations(_request(_BROWSE_URL, {"genrename": name}))


def top_stations(*, safe_mode: bool = False) -> list[RadioStation]:
    """The directory's Top 500 by live audience, across every genre.

    Never cached, for the same reason a clock is never cached: the whole value
    of this list is that it is true right now.
    """
    refuse_in_safe_mode(safe_mode)
    return parse_stations(_request(_TOP_URL, {}))


def resolve_stream(station_id: object, *, safe_mode: bool = False) -> str:
    """The real stream address behind a station id, or ``""``.

    One GET of the public tune-in ``.pls`` and one pure parse
    (:func:`quill.core.radio.playlist_formats.parse_pls`, which already knows
    that a playlist entry may be unplayable and skips it). Never raises: a
    station that will not resolve is a station the caller reports as
    unplayable, not an exception in a tree or a search.
    """
    key = str(station_id or "").strip()
    if not key:
        return ""
    from quill.core.radio.playlist_formats import parse_pls

    try:
        refuse_in_safe_mode(safe_mode)
        body = _request(tunein_url(key))
    except ShoutcastError:
        return ""
    for station in parse_pls(body):
        if station.stream_url:
            return station.stream_url
    return ""


def resolved_station(station: RadioStation, *, safe_mode: bool = False) -> RadioStation | None:
    """*station* with its tune-in URL replaced by the real stream, or ``None``.

    ``None`` means the directory listed it and it could not be resolved, which
    for a SHOUTcast row means it is not playable right now -- the honest answer,
    and better than a row that fails silently when Enter is pressed.
    """
    station_id = station_id_of(station)
    if not station_id:
        return station  # already a direct address (a row from somewhere else)
    stream = resolve_stream(station_id, safe_mode=safe_mode)
    if not stream:
        return None
    from dataclasses import replace

    return replace(station, stream_url=stream)


def resolve_many(
    stations: list[RadioStation], *, safe_mode: bool = False, limit: int = 12
) -> list[RadioStation]:
    """Resolve up to *limit* rows concurrently, dropping what will not play.

    For the **search** path, where the caller hands rows straight to a player
    and cannot resolve them later. Bounded twice over: at most *limit* rows are
    resolved (the rest are dropped rather than offered unplayable), and they go
    out on a small pool so a search costs one round trip's wall-clock rather
    than twenty-five.
    """
    from concurrent.futures import ThreadPoolExecutor

    head = stations[: max(0, limit)]
    if not head:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(head))) as pool:
        resolved = list(pool.map(lambda row: resolved_station(row, safe_mode=safe_mode), head))
    return [row for row in resolved if row is not None]


def search_stations(
    query: str, *, safe_mode: bool = False, resolve: bool = True, limit: int = 12
) -> list[RadioStation]:
    """Stations matching *query*. Never raises into a search fan-out.

    *resolve* is the difference between the two callers. Find Stations hands a
    row straight to a player and cannot resolve it later, so it takes the
    default and pays for one round trip per row (concurrently, and capped). The
    browse tree does **not**: its rows are resolved when they are activated, so
    it passes ``resolve=False`` and a SHOUTcast search there costs exactly one
    request.
    """
    wanted = str(query or "").strip()
    if not wanted:
        return []
    try:
        refuse_in_safe_mode(safe_mode)
        found = parse_stations(_request(_SEARCH_URL, {"query": wanted}))
    except ShoutcastError:
        return []
    if not resolve:
        return found
    # Resolved here only for the caller that has no second chance -- and only
    # the top few, because resolving 500 tune-in files to answer one search
    # would be worse than the fault it fixes.
    return resolve_many(found, safe_mode=safe_mode, limit=limit)
