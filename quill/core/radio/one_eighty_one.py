"""181.FM: the whole network, by genre, from the publisher's own station list.

181.FM is a free network of about eighty music and comedy channels. Its support
page says the stream links may be used in your own player, and a listener in
Hawaii asked for it by name (October 2026) -- Radio Browser carries many of its
channels, but scattered and without the network's own genres, which is not the
same as having the network.

**Where the list comes from.** 181.FM's website is a single-page app: its genre
table (genre -> stations, each with the ``mount`` its stream is named after) is
part of the site's own published script, and the site builds every stream link
as ``https://listen.181fm.com/<mount>_128k.mp3``. So does this. Nothing is
guessed: a station is here only if the publisher's table lists it.

**When that fails** -- the site is down, or a redesign moves the table -- the
branch does not empty. :data:`quill.core.radio.one_eighty_one_snapshot.SNAPSHOT`
is the list as it stood when it was last checked, and the day-long directory
cache keeps the last good live answer in front of it, so a bad fetch never
replaces a good list with nothing.

What a listener gets: Browse Stations > 181.FM, the network's own genres plus
"All stations", each channel once however many genres list it, explicit channels
named as such, and the Christmas channels marked seasonal. Every channel carries
now-playing (ICY) metadata, checked October 2026.

One reviewed egress site (``_fetch``), HTTPS-only with a verified TLS context,
refused in Safe Mode. Playback goes to ``listen.181fm.com`` through the player
like any other stream. wx-free, strict-typed.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

NETWORK = "181.FM"
HOMEPAGE = "https://www.181.fm/"
_STREAM_URL = "https://listen.181fm.com/{mount}_128k.mp3"
_TIMEOUT_SECONDS = 15.0
#: The site's script is about 210 KB; anything far past this is not it.
_MAX_BYTES = 4_000_000
_CACHE_KEY = "181fm:catalog"

#: The pseudo-genre at the top of the branch: every channel, once.
ALL_STATIONS = "All stations"

#: The site's script, as the index page names it (the hash changes per release).
_SCRIPT_RE = re.compile(r'src="(/static/js/main\.[0-9a-f]+\.js)"')
#: A genre key opening its list of stations: ``"80's Decade":[{station:`` or
#: ``Pop:[{station:``.
_GENRE_RE = re.compile(r'(?:"((?:[^"\\]|\\.)+)"|([A-Za-z_][A-Za-z0-9_]*)):\[\{station:')
#: One station entry. Matched on its own rather than inside a bracketed list,
#: because a station's name can contain a bracket ("Power 181 [E]").
_ENTRY_RE = re.compile(r'\{station:"((?:[^"\\]|\\.)*)",mount:"([a-z0-9_-]+)"')
#: The publisher's own mark for an explicit channel.
_EXPLICIT_RE = re.compile(r"\s*\[E\]\s*$")
#: Genres whose channels are seasonal (the PRD: browsable, but said so).
_SEASONAL_GENRES = frozenset({"christmas"})


class OneEightyOneError(CodedError):
    """A 181.FM request failed (network, unreadable reply, or Safe Mode)."""

    code = "QUILL-RADIO-181FM-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`OneEightyOneError` when Safe Mode is active."""
    if safe_mode:
        raise OneEightyOneError(
            "Internet Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or play stations."
        )


def _fetch(url: str) -> str:
    """One HTTPS GET returning text -- the module's single reviewed egress site."""
    if not url.startswith("https://www.181.fm/"):
        raise OneEightyOneError("Only 181.FM's own site is fetched here.")
    request = urllib.request.Request(url, headers={"User-Agent": http_client.user_agent()})
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            data: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise OneEightyOneError(f"Could not reach 181.FM: {error}") from error
    if len(data) > _MAX_BYTES:
        raise OneEightyOneError("181.FM sent far more than its station list.")
    return data.decode("utf-8", errors="replace")


def _unescape(text: str) -> str:
    return text.replace('\\"', '"').replace("\\\\", "\\")


def parse_catalog(script: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """``[(genre, [(station, mount), ...]), ...]`` from the site's script (pure).

    Each station belongs to the genre key that comes before it, which survives
    a bracket inside a name; a genre with no stations is dropped.
    """
    genres = [(m.start(), _unescape(m.group(1) or m.group(2))) for m in _GENRE_RE.finditer(script)]
    if not genres:
        return []
    table: dict[str, list[tuple[str, str]]] = {}
    order: list[str] = []
    index = 0
    for entry in _ENTRY_RE.finditer(script):
        while index + 1 < len(genres) and genres[index + 1][0] < entry.start():
            index += 1
        if genres[index][0] > entry.start():
            continue  # a station before any genre: not part of the table
        genre = genres[index][1]
        if genre not in table:
            table[genre] = []
            order.append(genre)
        pair = (_unescape(entry.group(1)).strip(), entry.group(2))
        if pair[0] and pair not in table[genre]:
            table[genre].append(pair)
    return [(genre, table[genre]) for genre in order if table[genre]]


def script_url(index_html: str) -> str | None:
    """The site script's address, from its index page (pure)."""
    match = _SCRIPT_RE.search(index_html)
    return f"https://www.181.fm{match.group(1)}" if match else None


def _station(name: str, mount: str, genres: list[str]) -> RadioStation:
    explicit = bool(_EXPLICIT_RE.search(name))
    display = _EXPLICIT_RE.sub("", name) + (" (Explicit)" if explicit else "")
    tags = list(genres)
    if explicit:
        tags.append("Explicit")
    if any(g.casefold() in _SEASONAL_GENRES for g in genres):
        tags.append("Seasonal")
    tags.append(NETWORK)
    return RadioStation(
        name=display,
        stream_url=_STREAM_URL.format(mount=mount),
        homepage=HOMEPAGE,
        # No country: Browse adds it to every label, and "(United States)" on all
        # eighty channels of one network would be said eighty times for nothing.
        language="English",
        tags=tuple(tags),
        codec="MP3",
        bitrate_kbps=128,
        source=NETWORK,
    )


def stations_from_catalog(
    catalog: list[tuple[str, list[tuple[str, str]]]],
) -> list[RadioStation]:
    """Every channel once, with every genre that lists it, in the site's order."""
    genres_for: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for genre, entries in catalog:
        for name, mount in entries:
            names.setdefault(mount, name)
            genres_for.setdefault(mount, [])
            if genre not in genres_for[mount]:
                genres_for[mount].append(genre)
    return [_station(names[mount], mount, genres_for[mount]) for mount in names]


def _live_catalog() -> list[list[object]]:
    page = _fetch(HOMEPAGE)
    url = script_url(page)
    if url is None:
        raise OneEightyOneError("181.FM's page no longer names its script.")
    catalog = parse_catalog(_fetch(url))
    # JSON-shaped for the cache: [[genre, [[name, mount], ...]], ...]
    return [[genre, [list(pair) for pair in entries]] for genre, entries in catalog]


def _coerce(payload: object) -> list[tuple[str, list[tuple[str, str]]]]:
    out: list[tuple[str, list[tuple[str, str]]]] = []
    if not isinstance(payload, list):
        return out
    for item in payload:
        if not (isinstance(item, list | tuple) and len(item) == 2):
            continue
        genre, entries = item
        pairs = [
            (str(p[0]), str(p[1])) for p in entries if isinstance(p, list | tuple) and len(p) == 2
        ]
        if pairs:
            out.append((str(genre), pairs))
    return out


def catalog(
    *, safe_mode: bool = False, refresh: bool = False
) -> list[tuple[str, list[tuple[str, str]]]]:
    """The network's genre table: fresh cache, then live, then stale cache, then
    the checked-in snapshot -- never empty while any of them has an answer."""
    refuse_in_safe_mode(safe_mode)
    payload, _age = directory_cache.resolve(_CACHE_KEY, _live_catalog, refresh=refresh, empty=[])
    table = _coerce(payload)
    if table:
        return table
    from quill.core.radio.one_eighty_one_snapshot import SNAPSHOT

    return [(genre, list(entries)) for genre, entries in SNAPSHOT]


# -- the shared genre protocol (browse_genres.GENRE_MODULES) ---------------


def fetch_genres(*, safe_mode: bool = False, refresh: bool = False) -> list[str]:
    """ "All stations", then the network's own genres in its own order."""
    return [
        ALL_STATIONS,
        *(genre for genre, _entries in catalog(safe_mode=safe_mode, refresh=refresh)),
    ]


def genre_display(name: str) -> str:
    """A genre's spoken name: the publisher's own, Christmas marked seasonal."""
    return f"{name} (seasonal)" if name.casefold() in _SEASONAL_GENRES else name


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """The channels in *genre*, or every channel for "All stations" (A to Z)."""
    stations = stations_from_catalog(catalog(safe_mode=safe_mode))
    if genre == ALL_STATIONS:
        return sorted(stations, key=lambda s: s.name.casefold())
    return [s for s in stations if genre in s.tags]


def fetch_stations(*, safe_mode: bool = False) -> list[RadioStation]:
    """Every channel, once."""
    return stations_from_catalog(catalog(safe_mode=safe_mode))


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NON_ALNUM_RE.sub(" ", text.casefold()).strip()


def search_stations(query: str = "", *, safe_mode: bool = False) -> list[RadioStation]:
    """Channels whose name or genre matches *query*, spacing- and
    punctuation-insensitive ("awesome 80s" finds "Awesome 80's"); a query that
    names the network itself ("181", "181.fm") returns every channel."""
    stations = fetch_stations(safe_mode=safe_mode)
    wanted = _normalize(query)
    if not wanted or wanted.replace(" ", "") in {"181", "181fm", "181 fm"}:
        return stations
    found = []
    for station in stations:
        haystack = _normalize(" ".join((station.name, *station.tags)))
        squashed = haystack.replace(" ", "")
        if wanted.replace(" ", "") in squashed or all(t in haystack for t in wanted.split()):
            found.append(station)
    return found
