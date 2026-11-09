"""IPRD, the International Public Radio Directory: about 24,000 stations.

IPRD (https://github.com/iprd-org/iprd, MIT) is an open, community-kept list of
internet radio from every country, published as one catalogue file on GitHub
Pages for players to read. Its own description is a "public listing of internet
radios from all around the world"; its licence and its robots policy put no
limit on a player reading it, which is why it is here and Internet-Radio.com is
not (see ``docs/design/blindradio-ideas/networks-and-directories.md``).

The idea, and the catalogue's address, come from BlindRadio by serrebidev (MIT),
``crates/blindradio-core/src/sources/iprd.rs``.

What a listener gets: Browse Stations > IPRD, By Country and By Genre (the
hundred most-used genres; the catalogue has over a thousand, most of them one
station's word for itself), each list a hundred stations at a time with a
"More..." row; and Find Stations searches it by name.

The catalogue is one 2 MB download (17 MB unpacked). It is fetched only when the
branch is opened or searched, kept for a day in the directory cache in a trimmed
form, and held in memory for ten minutes so moving between folders costs
nothing. A failed refresh keeps the last good copy. One reviewed egress site
(``_fetch``), HTTPS-only with a verified TLS context, refused in Safe Mode.
wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import math
import ssl
import threading
import time
import urllib.error
import urllib.request
import zlib
from collections import Counter

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

SOURCE = "IPRD"
CATALOG_URL = "https://iprd-org.github.io/iprd/site_data/metadata/catalog.json"
HOMEPAGE = "https://iprd-org.github.io/iprd/"
#: The file is 2 MB gzipped: more than a short timeout allows on a slow line.
_TIMEOUT_SECONDS = 30.0
_MAX_BYTES = 64_000_000
_CACHE_KEY = "iprd:catalog"
#: Rows per folder before a "More..." row.
PAGE_SIZE = 100
#: Genres offered for browsing, the most used first.
GENRE_LIMIT = 100
SEARCH_LIMIT = 100
_MEMO_SECONDS = 600.0

#: One trimmed catalogue row: name, url, country, genres, codec, kbps, homepage.
Row = tuple[str, str, str, tuple[str, ...], str, int, str]

_memo: tuple[float, list[Row]] | None = None
_memo_lock = threading.Lock()
#: One catalogue fetch at a time, held apart from ``_memo_lock`` so a slow
#: fetch never stalls a reader that already has a copy.
_fetch_lock = threading.Lock()
#: ``time.monotonic()`` of the last fetch that came back with nothing.
_last_failure = float("-inf")


class IprdError(CodedError):
    """An IPRD request failed (network, unreadable reply, or Safe Mode)."""

    code = "QUILL-RADIO-IPRD-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`IprdError` when Safe Mode is active."""
    if safe_mode:
        raise IprdError(
            "Internet Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or play stations."
        )


def _fetch() -> object:
    """One HTTPS GET of the catalogue, decoded -- the single reviewed egress site."""
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"User-Agent": http_client.user_agent(), "Accept-Encoding": "gzip"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            data: bytes = resp.read(_MAX_BYTES + 1)
            packed = resp.headers.get("Content-Encoding", "").casefold() == "gzip"
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        TimeoutError,
        ssl.SSLError,
        OSError,
    ) as error:
        raise IprdError(f"Could not reach IPRD: {error}") from error
    if len(data) > _MAX_BYTES:
        raise IprdError("IPRD sent far more than its catalogue.")
    try:
        if packed:
            data = _inflate(data)
        return json.loads(data.decode("utf-8", errors="replace"))
    except (OSError, ValueError, zlib.error) as error:
        raise IprdError("IPRD returned an unreadable catalogue.") from error


def _inflate(data: bytes) -> bytes:
    """Gunzip *data*, refusing more than ``_MAX_BYTES`` once unpacked."""
    unpacker = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = unpacker.decompress(data, _MAX_BYTES + 1)
    if len(out) > _MAX_BYTES or unpacker.unconsumed_tail:
        raise IprdError("IPRD sent far more than its catalogue.")
    return out


def _listed(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _kbps(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0
    return int(value) if math.isfinite(value) and 0 < value < 100_000 else 0


def _playable(url: str) -> bool:
    return url.startswith(("https://", "http://")) and "@" not in url.split("/", 3)[2]


def trim_catalog(payload: object) -> list[list[object]]:
    """The catalogue as compact, JSON-shaped rows, each stream once (pure).

    A station keeps its first HTTPS stream, or its first HTTP one when it has no
    other; genres are folded to lower case, because the catalogue has both
    ``pop`` and ``Pop``.
    """
    stations = payload.get("stations") if isinstance(payload, dict) else None
    rows: list[list[object]] = []
    seen: set[str] = set()
    for item in stations if isinstance(stations, list) else []:
        if not isinstance(item, dict):
            continue
        name = " ".join(str(item.get("name") or "").split())
        streams = [s for s in _listed(item.get("streams")) if isinstance(s, dict)]
        urls = [str(s.get("url") or "").strip() for s in streams]
        playable = [u for u in urls if _playable(u)]
        url = next(
            (u for u in playable if u.startswith("https://")), playable[0] if playable else ""
        )
        if not name or not url or url in seen:
            continue
        seen.add(url)
        stream = streams[urls.index(url)]
        codec = str(stream.get("format") or "").strip()
        genres = sorted({
            str(g).strip().casefold() for g in _listed(item.get("genres")) if str(g).strip()
        })
        rows.append([
            name,
            url,
            str(item.get("country") or "").strip(),
            genres,
            "" if codec.casefold() == "unknown" else codec.upper(),
            _kbps(stream.get("bitrate")),
            str(item.get("website") or "").strip(),
        ])
    return rows


def _coerce(payload: object) -> list[Row]:
    rows: list[Row] = []
    for item in payload if isinstance(payload, list) else []:
        if not (isinstance(item, list) and len(item) == 7):
            continue
        name, url, country, genres, codec, bitrate, homepage = item
        rows.append((
            str(name),
            str(url),
            str(country),
            tuple(str(g) for g in genres) if isinstance(genres, list) else (),
            str(codec),
            int(bitrate) if isinstance(bitrate, int) else 0,
            str(homepage),
        ))
    return rows


def _fresh_memo() -> list[Row] | None:
    with _memo_lock:
        if _memo is not None and time.monotonic() - _memo[0] < _MEMO_SECONDS:
            return _memo[1]
    return None


def catalog(*, safe_mode: bool = False, refresh: bool = False) -> list[Row]:
    """Every station: memory, then the day-long cache, then live, then stale.

    While another thread fetches, a caller holding an older copy gets that copy
    at once; one with none waits for that fetch, and when it came back empty
    gets nothing too, rather than starting a second 30-second wait of its own.
    """
    global _memo, _last_failure
    refuse_in_safe_mode(safe_mode)
    if not refresh and (rows := _fresh_memo()) is not None:
        return rows
    with _memo_lock:
        stale = _memo[1] if _memo is not None else None
    asked = time.monotonic()
    if not _fetch_lock.acquire(blocking=stale is None):
        return stale or []
    try:
        if _last_failure > asked:
            return []
        if not refresh and (rows := _fresh_memo()) is not None:
            return rows
        payload, _age = directory_cache.resolve(
            _CACHE_KEY, lambda: trim_catalog(_fetch()), refresh=refresh, empty=[]
        )
        rows = _coerce(payload)
        with _memo_lock:
            if rows:
                _memo = (time.monotonic(), rows)
            else:
                _last_failure = time.monotonic()
        return rows
    finally:
        _fetch_lock.release()


def to_station(row: Row, *, with_country: bool = True) -> RadioStation:
    """One catalogue row as a station that plays, records and saves."""
    name, url, country, genres, codec, bitrate, homepage = row
    return RadioStation(
        name=name,
        stream_url=url,
        homepage=homepage,
        country=country if with_country else "",
        tags=tuple(g.title() for g in genres),
        codec=codec,
        bitrate_kbps=bitrate,
        source=SOURCE,
    )


def countries(*, safe_mode: bool = False) -> list[tuple[str, int]]:
    """``[(country, station count), ...]`` A to Z, the unplaced left out."""
    counts = Counter(row[2] for row in catalog(safe_mode=safe_mode) if row[2])
    return sorted(counts.items(), key=lambda pair: pair[0].casefold())


def genres(*, safe_mode: bool = False, limit: int = GENRE_LIMIT) -> list[tuple[str, int]]:
    """The *limit* most-used genres with their counts, then A to Z among those."""
    counts = Counter(g for row in catalog(safe_mode=safe_mode) for g in row[3])
    top = counts.most_common(limit) if limit > 0 else list(counts.items())
    return sorted(top, key=lambda pair: pair[0])


def page(rows: list[RadioStation], number: int) -> tuple[list[RadioStation], int]:
    """Page *number* (from 1) of *rows*, and how many there are in all (pure)."""
    start = max(0, number - 1) * PAGE_SIZE
    return rows[start : start + PAGE_SIZE], len(rows)


def country_stations(country: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Every station in *country*, A to Z, without the country in each label."""
    rows = [row for row in catalog(safe_mode=safe_mode) if row[2] == country]
    stations = [to_station(row, with_country=False) for row in rows]
    return sorted(stations, key=lambda s: s.name.casefold())


def genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Every station filed under *genre*, A to Z."""
    wanted = genre.casefold()
    rows = [row for row in catalog(safe_mode=safe_mode) if wanted in row[3]]
    return sorted((to_station(row) for row in rows), key=lambda s: s.name.casefold())


def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Stations whose name holds every word of *query* (at most a hundred).

    Blank finds nothing. Errors come back as an empty list, the contract every
    Find Stations extra honours, so a directory that is down never blanks the
    rest of a search.
    """
    words = query.casefold().split()
    if not words:
        return []
    try:
        rows = catalog(safe_mode=safe_mode)
    except IprdError:
        return []
    found = [to_station(row) for row in rows if all(w in row[0].casefold() for w in words)]
    return found[:SEARCH_LIMIT]


def forget_memo() -> None:
    """Drop the in-memory copy (tests, and Refresh on the branch)."""
    global _memo, _last_failure
    with _memo_lock:
        _memo = None
        _last_failure = float("-inf")


__all__ = [
    "CATALOG_URL",
    "PAGE_SIZE",
    "SOURCE",
    "IprdError",
    "catalog",
    "countries",
    "country_stations",
    "forget_memo",
    "genre_stations",
    "genres",
    "page",
    "search_stations",
    "to_station",
    "trim_catalog",
]
