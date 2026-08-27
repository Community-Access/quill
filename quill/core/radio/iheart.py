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

Browse-by-genre uses iHeart's free, keyless JSON content API
(``us.api.iheart.com``): ``/content/genre`` for the genre list and
``/content/liveStations?genreId=`` for one genre's stations, where each row
already embeds its own stream URLs -- so a genre's stations resolve in a single
GET, no per-station page fetch. The XML sitemap has no genre data, which is why
the browse path uses this API while Search stays on the sitemap.

Every request is a plain HTTPS GET of a public iHeart endpoint -- no browser, no
JavaScript, no key or auth -- resolving only what the sitemap, each page, or the
content API already advertise. Requests funnel through the single reviewed
egress site (:func:`_fetch` -- see ``quill/tools/network_egress_audit.py``),
HTTPS-only over a verified TLS context with a bounded timeout, reached only by
an explicit refresh/browse/play action and disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core import safe_xml
from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation

_SITEMAP_INDEX = "https://www.iheart.com/sitemap.xml"
#: iHeart's free, keyless JSON content API, used for browse-by-genre (the XML
#: sitemap carries no category). Genres list + live stations for one genre;
#: each station row embeds its own stream URLs, so no per-station page GET.
_API_GENRES = "https://us.api.iheart.com/api/v2/content/genre"
#: The same keyless content API's market (city) directory. 317 markets on
#: 2026-08-13, each carrying its city, state, country and station count, and
#: ``liveStations`` accepts ``marketId`` exactly as it accepts ``genreId``. This
#: is the "by city" axis commercial catalogues charge for.
_API_MARKETS = "https://us.api.iheart.com/api/v2/content/markets"
_API_LIVE_STATIONS = "https://us.api.iheart.com/api/v2/content/liveStations"
#: iHeart's own keyless relevance search (the web player's). Asked with
#: station=true and everything else false, it answers ranked station ids for a
#: text query -- "kiss" comes back as Kiss 108 and KIIS FM, not as whatever
#: happens to contain the letters. One GET here plus one batch liveStations GET
#: (ids are comma-separable in the path) replaces what Search used to do: two
#: sitemap GETs to build a 3,700-row index, a local substring filter over it,
#: and one page fetch per match. Verified live 2026-08-27.
_API_SEARCH = "https://us.api.iheart.com/api/v3/search/all"
#: Stations pulled per genre for the browse tree (bounded; one genre is then
#: grouped A-Z under its folder). Generous enough to cover a genre in full
#: without an unbounded pull.
_GENRE_STATION_LIMIT = 250
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


@dataclass(slots=True)
class IHeartGenre:
    """One browsable iHeart genre from the JSON content API."""

    genre_id: int
    name: str


@dataclass(slots=True)
class IHeartMarket:
    """One browsable iHeart market -- a city, with the state that disambiguates
    it and the number of stations in it.

    The station count is why this is worth a browse node rather than a search:
    a folder can say "Phoenix, 34 stations" before the listener spends a round
    trip opening it.
    """

    market_id: int
    city: str
    state: str = ""
    country: str = ""
    station_count: int = 0

    @property
    def display_name(self) -> str:
        """ "Phoenix, AZ" -- the state disambiguates the many repeated city
        names, and is omitted when the market has none."""
        return f"{self.city}, {self.state}" if self.state else self.city


#: iHeart's per-station ``streams`` dict, most-preferred key first: encrypted
#: before plain, and **progressive before HLS**.
#:
#: The progressive preference is deliberate and was a bug fix (John, 2026-08-13:
#: "KFI plays for about 20 seconds and then stops"). iHeart's HLS form is
#: structurally fragile for a listener: requesting
#: ``https://stream.revma.ihrhls.com/zc177/hls.m3u8`` answers 302 to a
#: *per-listener* host carrying ``rj-ttl=5`` -- a five-second token -- plus a
#: session cookie, and the media playlist behind it holds three segments, a
#: thirty-second window that must be topped up every ten seconds. One failed
#: refresh drains the buffer and the audio runs out twenty to thirty seconds
#: later, which is exactly what was reported.
#:
#: ``secure_shoutcast_stream`` is the same audio as one long HTTP body: no
#: segment window, no per-refresh token, no per-listener session to lose. It
#: streamed sixty seconds clean under probe (59/59 unique one-second PCM
#: hashes, so no replayed audio either) where the HLS form is the one that
#: fails intermittently in the field. HLS stays as the fallback, because some
#: stations publish nothing else.
_STREAM_KEYS = (
    "secure_shoutcast_stream",
    "shoutcast_stream",
    "secure_hls_stream",
    "secure_pls_stream",
    "hls_stream",
    "pls_stream",
)


def _best_stream(streams: object) -> str:
    """The most-preferred playable URL from a station's ``streams`` dict, or ""."""
    if not isinstance(streams, dict):
        return ""
    for key in _STREAM_KEYS:
        value = streams.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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


#: Runs of anything that is not a letter or digit -- the token separators a
#: search normalises away so "103.1", "103-1", "K276EL" and "khfi hd2" all
#: reduce to the same alphanumeric shape the sitemap slug carries.
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercased, alphanumeric-token form of *text* (pure).

    ``"103.1 Austin's 80s"`` -> ``"103 1 austin s 80s"``. Collapsing punctuation
    to single spaces lets a query match a slug/name regardless of dots, hyphens,
    apostrophes or casing.
    """
    return _NON_ALNUM_RE.sub(" ", text.lower()).strip()


def station_matches(station: IHeartStation, query: str) -> bool:
    """Whether *station* matches the search *query* (pure, punctuation-insensitive).

    The sitemap only carries a station's slug-derived name, slug and numeric id,
    so those are all a directory search can see (call signs, taglines and former
    aliases live only on the lazily-fetched station page). Matching is done over
    all three, normalised so branding punctuation does not defeat it:

    - The station id matches as a plain substring, so ``"8403"`` finds station
      ``8403``.
    - The de-punctuated query matches the de-punctuated name+slug, so
      ``"103.1 Austin"`` finds slug ``1031-austin`` / name ``1031 Austin``.
    - Otherwise every query *token* must appear, so a partial ``"kbco"`` or
      ``"973 kbco"`` still matches ``973 KBCO``.

    An empty query never matches (callers filter it earlier, but this is safe).
    """
    normalized_query = _normalize(query)
    if not normalized_query:
        return False
    if normalized_query in station.station_id.lower():
        return True
    haystack = f"{_normalize(station.name)} {_normalize(station.slug)}"
    if normalized_query.replace(" ", "") in haystack.replace(" ", ""):
        return True
    return all(token in haystack for token in normalized_query.split())


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


def parse_search_station_ids(json_text: str) -> list[int]:
    """Ranked station ids from a v3 search reply (pure). ``[]`` on anything odd."""
    import json

    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    results = data.get("results") if isinstance(data, dict) else None
    stations = results.get("stations") if isinstance(results, dict) else None
    if not isinstance(stations, list):
        return []
    ids: list[int] = []
    for entry in stations:
        if isinstance(entry, dict) and isinstance(entry.get("id"), int):
            ids.append(entry["id"])
    return ids


def search_stations(query: str, *, limit: int = 15, safe_mode: bool = False) -> list[RadioStation]:
    """Stations for *query*, by iHeart's own relevance search. Two GETs.

    The service's search API is both the fastest route and the most compliant
    one: the terms reading that barred bulk-copying the directory (PRD, class
    B) is exactly why a search should ask the service rather than filter a
    local copy of it. Ranked ids come from ``/api/v3/search/all``; one batch
    ``liveStations/<id,id,...>`` GET returns those stations with their streams
    already embedded, parsed by the same :func:`parse_genre_stations` the genre
    browse uses. Never raises into a search fan-out.
    """
    import urllib.parse

    wanted = str(query or "").strip()
    if not wanted:
        return []
    try:
        refuse_in_safe_mode(safe_mode)
        params = urllib.parse.urlencode({
            "keywords": wanted,
            "maxRows": max(1, int(limit)),
            "bundle": "false",
            "station": "true",
            "artist": "false",
            "track": "false",
            "playlist": "false",
            "podcast": "false",
        })
        ids = parse_search_station_ids(_fetch(f"{_API_SEARCH}?{params}"))
        if not ids:
            return []
        joined = ",".join(str(station_id) for station_id in ids[: max(1, int(limit))])
        return parse_genre_stations(_fetch(f"{_API_LIVE_STATIONS}/{joined}"))
    except IHeartError:
        return []


def to_radio_station(station: IHeartStation, stream_url: str = "") -> RadioStation:
    """Build a :class:`RadioStation` from an iHeart station."""
    return RadioStation(
        name=station.name,
        stream_url=stream_url or station.stream_url,
        station_uuid=f"iheart:{station.station_id}",
        homepage=station.page_url,
        source="iHeart",
    )


# --- genre browse (JSON content API) ----------------------------------------


def parse_genres(json_text: str) -> list[IHeartGenre]:
    """Parse the genre-list JSON into displayable genres, in the API's sort
    order. Undisplayed genres are dropped; malformed input yields ``[]``."""
    import json

    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        return []
    rows: list[tuple[int, IHeartGenre]] = []
    for hit in hits:
        if not isinstance(hit, dict) or not hit.get("display", True):
            continue
        genre_id = hit.get("id")
        name = hit.get("name")
        if not isinstance(genre_id, int) or not isinstance(name, str) or not name.strip():
            continue
        sort = hit.get("sort")
        rows.append((
            sort if isinstance(sort, int) else 10_000,
            IHeartGenre(genre_id, name.strip()),
        ))
    rows.sort(key=lambda row: row[0])
    return [genre for _sort, genre in rows]


def parse_genre_stations(json_text: str) -> list[RadioStation]:
    """Parse a genre's live-station JSON into playable RadioStations.

    Each station row carries its own ``streams`` dict, so the stream is
    resolved here with no extra GET. A station with no usable stream is
    dropped; malformed input yields ``[]``.
    """
    import json

    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        return []
    stations: list[RadioStation] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        station_id = hit.get("id")
        name = hit.get("name")
        stream = _best_stream(hit.get("streams"))
        if not isinstance(station_id, int) or not isinstance(name, str) or not name.strip():
            continue
        if not stream:
            continue
        call_letters = hit.get("callLetters")
        tags = (call_letters,) if isinstance(call_letters, str) and call_letters.strip() else ()
        stations.append(
            RadioStation(
                name=name.strip(),
                stream_url=stream,
                station_uuid=f"iheart:{station_id}",
                homepage=f"https://www.iheart.com/live/{station_id}/",
                tags=tags,
                source="iHeart",
            )
        )
    return stations


def fetch_genres(*, safe_mode: bool = False) -> list[IHeartGenre]:
    """The iHeart browsable-genre list -- one keyless JSON GET.

    Raises :class:`IHeartError` on a network failure or a Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    return parse_genres(_fetch(_API_GENRES))


def fetch_genre_stations(
    genre_id: int, *, limit: int = _GENRE_STATION_LIMIT, safe_mode: bool = False
) -> list[RadioStation]:
    """The live stations for one iHeart genre -- one keyless JSON GET, streams
    already embedded (no per-station page fetch). Raises :class:`IHeartError`
    on a network failure or a Safe Mode refusal."""
    refuse_in_safe_mode(safe_mode)
    url = f"{_API_LIVE_STATIONS}?genreId={int(genre_id)}&limit={int(limit)}"
    return parse_genre_stations(_fetch(url))


def parse_markets(json_text: str) -> list[IHeartMarket]:
    """Parse the market directory into :class:`IHeartMarket` (pure).

    Sorted by city so the A-Z grouping above it is stable; markets without a
    city name are dropped, and malformed input yields ``[]``.
    """
    import json

    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        return []
    markets: list[IHeartMarket] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        market_id = hit.get("marketId")
        city = str(hit.get("city", "")).strip()
        if not isinstance(market_id, int) or not city:
            continue
        markets.append(
            IHeartMarket(
                market_id=market_id,
                city=city,
                state=str(hit.get("stateAbbreviation", "")).strip(),
                country=str(hit.get("countryName", "")).strip(),
                station_count=int(hit.get("stationCount") or 0),
            )
        )
    markets.sort(key=lambda m: (m.city.casefold(), m.state))
    return markets


def fetch_markets(*, limit: int = 400, safe_mode: bool = False) -> list[IHeartMarket]:
    """Every iHeart market -- one keyless JSON GET.

    The whole directory is 317 markets, so a single request covers it; the
    limit is a guard against the list growing without anyone noticing, not a
    page size.
    """
    refuse_in_safe_mode(safe_mode)
    return parse_markets(_fetch(f"{_API_MARKETS}?limit={int(limit)}"))


def fetch_market_stations(
    market_id: int, *, limit: int = _GENRE_STATION_LIMIT, safe_mode: bool = False
) -> list[RadioStation]:
    """The live stations in one iHeart market -- one keyless JSON GET.

    Same row shape as a genre's stations, streams already embedded, so it
    reuses the same parser rather than a near-copy of it.
    """
    refuse_in_safe_mode(safe_mode)
    url = f"{_API_LIVE_STATIONS}?marketId={int(market_id)}&limit={int(limit)}"
    return parse_genre_stations(_fetch(url))
