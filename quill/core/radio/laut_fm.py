"""laut.fm: thousands of listener-made stations, through laut.fm's public API.

laut.fm is a German platform where anyone can run a station: oldies from a
village in Westphalia, round-the-clock jazz, a Hamburg club's own channel. It
publishes a documented, keyless API (https://docs.api.laut.fm/) for exactly this
kind of player, which is what makes it a network Quill Radio can carry whole
rather than a scrape.

What a listener gets: Browse Stations > laut.fm, the platform's most-listened
genres (its own popularity order, so the first folders are the full ones), each
opening its stations; and Find Stations searches laut.fm alongside everything
else. Every stream carries now-playing (ICY) metadata, checked October 2026.

The genre list is cached for a day and survives a failed refresh
(:mod:`quill.core.radio.directory_cache`), so the branch never goes blank because
the API blinked. One reviewed egress site (``_fetch``) against ``api.laut.fm``,
HTTPS-only with a verified TLS context, refused in Safe Mode. wx-free,
strict-typed.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

NETWORK = "laut.fm"
_API = "https://api.laut.fm"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 8_000_000
#: How many genres the branch offers: laut.fm lists 600-odd, most of them a
#: single station's own word for itself, and a browse list that long is not one.
GENRE_LIMIT = 60
#: Stations fetched per genre or search, the busiest first.
_STATION_LIMIT = 250
_GENRES_CACHE_KEY = "lautfm:genres"


class LautFmError(CodedError):
    """A laut.fm request failed (network, unreadable reply, or Safe Mode)."""

    code = "QUILL-RADIO-LAUTFM-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`LautFmError` when Safe Mode is active."""
    if safe_mode:
        raise LautFmError(
            "Internet Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or play stations."
        )


def _fetch(path: str) -> object:
    """One HTTPS GET against the API, decoded -- the single reviewed egress site."""
    url = f"{_API}{path}"
    request = urllib.request.Request(
        url, headers={"User-Agent": http_client.user_agent(), "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            data: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise LautFmError(f"Could not reach laut.fm: {error}") from error
    if len(data) > _MAX_BYTES:
        raise LautFmError("laut.fm sent more than a station list.")
    try:
        return json.loads(data.decode("utf-8", errors="replace"))
    except ValueError as error:
        raise LautFmError("laut.fm returned an unreadable reply.") from error


def genres_from_json(payload: object, *, limit: int = GENRE_LIMIT) -> list[str]:
    """The *limit* most popular genre names, in laut.fm's own score order (pure)."""
    if not isinstance(payload, list):
        return []
    scored = [
        (float(item.get("score") or 0), str(item.get("name") or "").strip())
        for item in payload
        if isinstance(item, dict)
    ]
    names = [name for _score, name in sorted(scored, key=lambda pair: -pair[0]) if name]
    return names[:limit] if limit > 0 else names


def station_from_json(item: object) -> RadioStation | None:
    """One API station record as a playable station, or None if it cannot play."""
    if not isinstance(item, dict) or item.get("active") is False:
        return None
    url = str(item.get("stream_url") or "").strip()
    name = " ".join(str(item.get("display_name") or item.get("name") or "").split())
    if not url.startswith("https://") or not name:
        return None
    genres = item.get("genres")
    tags = [str(g).strip() for g in genres if str(g).strip()] if isinstance(genres, list) else []
    images = item.get("images")
    favicon = str(images.get("station_120x120") or "") if isinstance(images, dict) else ""
    return RadioStation(
        name=name,
        stream_url=url,
        homepage=str(item.get("page_url") or "").strip(),
        favicon=favicon,
        # No country: Browse adds it to every label, and "(Germany)" on every
        # station of one platform says nothing the branch name did not.
        tags=(*tags, NETWORK),
        codec="MP3",
        source=NETWORK,
    )


def _stations(payload: object) -> list[RadioStation]:
    rows = payload if isinstance(payload, list) else []
    seen: set[str] = set()
    out: list[RadioStation] = []
    for item in rows:
        station = station_from_json(item)
        if station is not None and station.stream_url not in seen:
            seen.add(station.stream_url)
            out.append(station)
    return out


def search_results_from_json(payload: object) -> list[object]:
    """The station records inside a ``/search/stations`` reply (pure).

    The reply groups matches by what they matched on -- name, genre, description
    -- each group holding ``items`` of ``{"station": {...}}``.
    """
    if not isinstance(payload, dict):
        return []
    found: list[object] = []
    for group in payload.get("results") or []:
        if not isinstance(group, dict):
            continue
        for entry in group.get("items") or []:
            if isinstance(entry, dict) and isinstance(entry.get("station"), dict):
                found.append(entry["station"])
    return found


# -- the shared genre protocol (browse_genres.GENRE_MODULES) ---------------


def fetch_genres(*, safe_mode: bool = False, refresh: bool = False) -> list[str]:
    """laut.fm's most-listened genres, cached for a day."""
    refuse_in_safe_mode(safe_mode)
    payload, _age = directory_cache.resolve(
        _GENRES_CACHE_KEY, lambda: genres_from_json(_fetch("/genres")), refresh=refresh, empty=[]
    )
    return [str(name) for name in payload] if isinstance(payload, list) else []


def genre_display(name: str) -> str:
    """A genre's spoken name. laut.fm's own words, including its German decades
    ("80er" is the 80s), which a listener of the platform will know."""
    return name


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """The stations in *genre*, the busiest first."""
    refuse_in_safe_mode(safe_mode)
    if not genre.strip():
        return []
    quoted = urllib.parse.quote(genre.strip(), safe="")
    return _stations(_fetch(f"/stations/genre/{quoted}?limit={_STATION_LIMIT}"))


_NETWORK_QUERY_RE = re.compile(r"^\s*laut\s*\.?\s*fm\s*$", re.IGNORECASE)


def search_stations(query: str = "", *, safe_mode: bool = False) -> list[RadioStation]:
    """Stations whose name, genre or description matches *query*. A blank query,
    or one naming the platform itself, returns nothing: laut.fm has thousands of
    stations, and Browse is the way into all of them."""
    refuse_in_safe_mode(safe_mode)
    if not query.strip() or _NETWORK_QUERY_RE.match(query):
        return []
    params = urllib.parse.urlencode({"query": query.strip(), "limit": 50})
    return _stations(search_results_from_json(_fetch(f"/search/stations?{params}")))
