"""Canonical station keys and URL normalization (pure).

The one rule that keeps the catalog and the favorites store agreeing: a
station's canonical key is **its source uuid when it has one, else its
normalized stream URL** - the same precedence `RadioFavoritesStore` has always
used (`station_uuid or stream_url`), so the read-time overlay joins exactly.

Measured caution baked in (Station Catalog PRD, Section 2b): 7,135 normalized
stream URLs are shared by more than one distinct station within Radio Browser
alone - relays and network feeds. A URL therefore identifies a *record* well
enough to key it, but never proves two records are the same station; merging
additionally requires a name match (:func:`same_station`).
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

#: Query parameters that vary per listener or per fetch and say nothing about
#: which stream this is. Dropped during normalization so the same stream keyed
#: on two days keys identically.
_JUNK_PARAMS = frozenset({"sid", "sessionid", "session", "uid", "token", "cb", "cachebust"})

#: Default ports that add nothing: stripping them keys "host:80" and "host"
#: the same, which they are.
_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_stream_url(url: str) -> str:
    """A stream URL in canonical form (pure).

    Lowercases scheme and host, strips a default port, drops the fragment and
    the junk query parameters, and removes a lone trailing slash. Anything
    unparseable comes back stripped-but-otherwise-untouched: a malformed URL
    is still a usable dictionary key, and raising here would let one bad
    record poison an import batch.
    """
    text = (url or "").strip()
    if not text:
        return ""
    try:
        parts = urlsplit(text)
    except ValueError:
        return text
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not scheme or not host:
        return text
    port = parts.port
    netloc = host if port is None or _DEFAULT_PORTS.get(scheme) == port else f"{host}:{port}"
    query = "&".join(
        pair
        for pair in parts.query.split("&")
        if pair and pair.split("=", 1)[0].lower() not in _JUNK_PARAMS
    )
    path = parts.path if parts.path != "/" else ""
    return urlunsplit((scheme, netloc, path, query, ""))


def canonical_key(station_uuid: str, stream_url: str) -> str:
    """The station's canonical key: uuid first, normalized URL as the fallback.

    Matches the favorites store's precedence exactly, which is what makes the
    saved-station overlay a plain equality join.
    """
    uuid = (station_uuid or "").strip()
    if uuid:
        return uuid
    return normalize_stream_url(stream_url)


def same_station(name_a: str, url_a: str, name_b: str, url_b: str) -> bool:
    """Whether two records are the same station, conservatively (pure).

    A shared URL alone never merges (7,135 shared URLs, measured); the names
    must also match case-insensitively after whitespace collapse. Ambiguity
    keeps two rows: two rows and honesty beat one row and a guess.
    """
    if normalize_stream_url(url_a) != normalize_stream_url(url_b):
        return False
    fold_a = " ".join((name_a or "").split()).casefold()
    fold_b = " ".join((name_b or "").split()).casefold()
    return bool(fold_a) and fold_a == fold_b
