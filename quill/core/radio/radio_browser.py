"""RadioBrowser client: free, keyless internet-radio station directory.

RadioBrowser (radio-browser.info) is a community-run, open-data directory of
internet radio streams with no API key and no commercial terms to violate --
the original station source and still the default. TuneIn and iHeart were once
left out here as a stated non-goal, but that decision was reversed (approved
2026-07-17; PRD §5.84f): both are now supported through their own no-auth,
open endpoints in :mod:`quill.core.radio.tunein` (RadioTime OPML) and
:mod:`quill.core.radio.iheart` (public sitemap), each returning only what the
user searched for or what a page already advertises -- the same shape as the
Triton provisioning resolver, not a scrape of a competitor's data files.

The service round-robins across community-hosted mirrors; per its own docs,
resolving ``all.api.radio-browser.info`` to a concrete mirror host once per
session (rather than hammering a single hardcoded host, as FastPlay does)
spreads load fairly. Every request funnels through the single reviewed egress
site (:func:`_http_json` -- see ``quill/tools/network_egress_audit.py``),
HTTPS-only with a verified TLS context, disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import random
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation, _coerce_int

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_ALL_HOSTS = "all.api.radio-browser.info"
_TIMEOUT_SECONDS = 10.0
_DEFAULT_LIMIT = 50

_cached_mirrors: list[str] | None = None


class RadioBrowserError(CodedError):
    """A RadioBrowser request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-BROWSER-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`RadioBrowserError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service.
    Internet Radio is a network service, so the UI calls this before
    constructing a request. Kept in core (with the flag passed in) so the
    refusal is unit-testable without wx.
    """
    if safe_mode:
        raise RadioBrowserError(
            "Internet Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or play stations."
        )


def _resolve_mirrors() -> list[str]:
    """Every current RadioBrowser mirror host, shuffled, resolved once and
    cached for the process. Mirrors the project's own documented recipe
    (https://api.radio-browser.info/, ``serverlist_python3.py``): a DNS
    lookup of ``all.api.radio-browser.info`` returns every mirror's IP;
    reverse-resolving each IP gives a real hostname (needed for TLS
    certificate validation -- the mirrors don't serve valid certs for a bare
    IP); the caller then tries hosts in random order and fails over to the
    next on error, which spreads load fairly instead of hammering one
    hardcoded host, as FastPlay does. Falls back to the round-robin host
    itself if DNS resolution fails outright (still a working endpoint, just
    without client-side load spreading).
    """
    global _cached_mirrors
    if _cached_mirrors is not None:
        return _cached_mirrors
    hosts: list[str] = []
    try:
        addr_info = socket.getaddrinfo(_ALL_HOSTS, 80, 0, 0, socket.IPPROTO_TCP)
        seen_ips: set[str] = set()
        for _family, *_rest, sockaddr in addr_info:
            ip = str(sockaddr[0])
            if ip in seen_ips:
                continue
            seen_ips.add(ip)
            try:
                hostname, _aliases, _addrs = socket.gethostbyaddr(ip)
            except OSError:
                continue
            if hostname not in hosts:
                hosts.append(hostname)
    except OSError:
        pass
    if not hosts:
        hosts = [_ALL_HOSTS]
    random.shuffle(hosts)
    _cached_mirrors = hosts
    return hosts


def _http_json(url_path: str) -> object:
    """One HTTPS GET (given a path+query, mirror host chosen internally)
    returning decoded JSON -- the reviewed egress site. Tries each known
    mirror in turn, per RadioBrowser's own documented failover recipe;
    raises only once every mirror has failed."""
    last_error: BaseException | None = None
    for host in _resolve_mirrors():
        url = f"https://{host}{url_path}"
        request = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
        )
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
                payload = resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
            last_error = error
            continue
        try:
            return json.loads(payload) if payload else []
        except ValueError as error:
            raise RadioBrowserError(
                "The station directory returned an unreadable reply."
            ) from error
    raise RadioBrowserError(f"Could not reach the station directory: {last_error}")


def _station_from_json(entry: dict[str, object]) -> RadioStation | None:
    name = str(entry.get("name", "")).strip()
    stream_url = str(entry.get("url_resolved") or entry.get("url") or "").strip()
    if not name or not stream_url:
        return None
    tags_raw = str(entry.get("tags", ""))
    tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())
    bitrate = _coerce_int(entry.get("bitrate"))
    votes = _coerce_int(entry.get("votes"))
    return RadioStation(
        name=name,
        stream_url=stream_url,
        station_uuid=str(entry.get("stationuuid", "")),
        homepage=str(entry.get("homepage", "")),
        favicon=str(entry.get("favicon", "")),
        country=str(entry.get("country", "")),
        language=str(entry.get("language", "")),
        tags=tags,
        codec=str(entry.get("codec", "")),
        bitrate_kbps=bitrate,
        votes=votes,
    )


def fetch_station_page(
    offset: int, limit: int = 10000, *, safe_mode: bool = False
) -> list[dict[str, object]]:
    """One raw page of the full working-station dump, for the local catalog.

    Through the same reviewed egress chokepoint as every other call here.
    Pagination is mandatory, not a nicety: the endpoint silently caps an
    unpaged request at 1,000 rows (measured 2026-08-15; the full dump is
    62,377). ``hidebroken=true`` is the catalog posture -- a station the
    directory itself marks broken is not worth shipping to anyone.
    """
    refuse_in_safe_mode(safe_mode)
    path = f"/json/stations?hidebroken=true&limit={int(limit)}&offset={int(offset)}"
    data = _http_json(path)
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


def stations_from_json(data: object) -> list[RadioStation]:
    """Parse a RadioBrowser station-list payload (pure; tolerant of junk)."""
    stations: list[RadioStation] = []
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        station = _station_from_json(entry)
        if station is not None:
            stations.append(station)
    return stations


def search_stations(
    query: str = "",
    *,
    tag: str = "",
    country: str = "",
    state: str = "",
    limit: int = _DEFAULT_LIMIT,
    offset: int = 0,
    safe_mode: bool = False,
) -> list[RadioStation]:
    """Stations matching *query* (name search), optionally narrowed by tag or
    country; ordered by community click count (most-listened first).

    *offset* skips that many results before returning *limit* of them, so a
    caller can page through a large result set (RadioBrowser caps a single
    request at 200); the stable ``clickcount`` order keeps paging consistent.
    """
    refuse_in_safe_mode(safe_mode)
    params: dict[str, object] = {
        "limit": max(1, min(limit, 200)),
        "offset": max(0, offset),
        "hidebroken": "true",
        "order": "clickcount",
        "reverse": "true",
    }
    if query:
        params["name"] = query
    if tag:
        params["tag"] = tag
    if country:
        params["country"] = country
    if state:
        params["state"] = state
    path = f"/json/stations/search?{urllib.parse.urlencode(params)}"
    return stations_from_json(_http_json(path))


def popular_stations(limit: int = 100, *, safe_mode: bool = False) -> list[RadioStation]:
    """The most-popular stations right now -- no search needed.

    Backs the "Popular Stations" browse category: RadioBrowser's ``topvote``
    endpoint returns the community's most-voted stations, so a listener can just
    open Browse Stations and see what everyone is listening to without typing a
    thing. One GET through the same reviewed egress site as search.
    """
    refuse_in_safe_mode(safe_mode)
    path = f"/json/stations/topvote/{max(1, min(limit, 200))}"
    return stations_from_json(_http_json(path))


def lookup_station(station_uuid: str, *, safe_mode: bool = False) -> RadioStation | None:
    """Fresh directory data for one station -- the stream-fallback path.

    Streams move; RadioBrowser usually knows the current URL before a saved
    favorite does. Returns None when the uuid is unknown (or blank)."""
    refuse_in_safe_mode(safe_mode)
    uuid = station_uuid.strip()
    if not uuid:
        return None
    path = f"/json/stations/byuuid?{urllib.parse.urlencode({'uuids': uuid})}"
    stations = stations_from_json(_http_json(path))
    return stations[0] if stations else None


def _names_from_json(data: object) -> list[str]:
    if not isinstance(data, list):
        return []
    return [str(entry["name"]) for entry in data if isinstance(entry, dict) and entry.get("name")]


def list_tags(limit: int = 100, *, safe_mode: bool = False) -> list[str]:
    """The most-used station tags/genres, most popular first."""
    refuse_in_safe_mode(safe_mode)
    params = {"limit": max(1, min(limit, 500)), "order": "stationcount", "reverse": "true"}
    path = f"/json/tags?{urllib.parse.urlencode(params)}"
    return _names_from_json(_http_json(path))


def list_countries(limit: int = 300, *, safe_mode: bool = False) -> list[str]:
    """Countries with at least one station, most stations first."""
    refuse_in_safe_mode(safe_mode)
    params = {"limit": max(1, min(limit, 1000)), "order": "stationcount", "reverse": "true"}
    path = f"/json/countries?{urllib.parse.urlencode(params)}"
    return _names_from_json(_http_json(path))


# -- Browse-tree "genres" protocol -------------------------------------------
# The Browse Stations tree drives a genre source through three module functions
# (fetch_genres -> genre_display -> fetch_genre_stations), the same shape Xiph
# and the Community M3U catalog implement. These thin adapters expose the
# RadioBrowser tag directory as a browsable "Radio Browser (by Genre)" node, so
# a listener can walk RadioBrowser by genre without typing a search.


def fetch_genres(*, safe_mode: bool = False) -> list[str]:
    """The most-used RadioBrowser tags, as genre slugs for the Browse tree."""
    return list_tags(safe_mode=safe_mode)


def genre_display(slug: str) -> str:
    """Human-readable label for a tag slug (e.g. ``classic hits`` -> ``Classic Hits``)."""
    return slug.replace("-", " ").replace("_", " ").strip().title() or slug


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Stations carrying the RadioBrowser tag *genre*, most-listened first."""
    return search_stations(tag=genre, safe_mode=safe_mode)


# -- The browse axes we were already paying for -------------------------------
# RadioBrowser serves far more than tags, and until now only tags and countries
# were used -- and those only to fill two dropdowns in the *search* dialog. The
# five functions below open the axes the service already had: geography (the
# most-asked-for radio browse there is), language (genuinely underserved
# elsewhere, and a first-class need for anyone whose language is not the local
# one), what people are listening to *now* as distinct from what they once voted
# for, and what changed recently. No new egress host: every one goes through the
# same mirror-resolving _http_json chokepoint as everything above.


def list_states(country: str = "", limit: int = 400, *, safe_mode: bool = False) -> list[str]:
    """States or regions, optionally within *country*, most stations first.

    The second level of a Country -> State -> stations tree. RadioBrowser's
    state list is global, so a country is passed as a path segment to scope it;
    many countries have no states at all, and an empty list is the correct,
    unremarkable answer for those -- the caller shows the country's stations
    directly rather than an empty folder.

    **The trailing slash is required and is not decorative.** The endpoint is
    ``/json/states/{country}/{searchterm}``; omitting the empty search term
    returns an empty list rather than an error, so ``/json/states/Germany``
    silently answers "Germany has no states" while ``/json/states/Germany/``
    answers correctly. Verified live on 2026-08-13.
    """
    refuse_in_safe_mode(safe_mode)
    params = {"limit": max(1, min(limit, 1000)), "order": "stationcount", "reverse": "true"}
    scope = f"/{urllib.parse.quote(country.strip())}/" if country.strip() else ""
    path = f"/json/states{scope}?{urllib.parse.urlencode(params)}"
    return _names_from_json(_http_json(path))


def list_languages(limit: int = 300, *, safe_mode: bool = False) -> list[str]:
    """Languages with at least one station, most stations first."""
    refuse_in_safe_mode(safe_mode)
    params = {"limit": max(1, min(limit, 1000)), "order": "stationcount", "reverse": "true"}
    path = f"/json/languages?{urllib.parse.urlencode(params)}"
    return _names_from_json(_http_json(path))


def stations_by_country(
    country: str, limit: int = 200, *, safe_mode: bool = False
) -> list[RadioStation]:
    """Stations licensed in *country*, most-listened first."""
    refuse_in_safe_mode(safe_mode)
    if not country.strip():
        return []
    return search_stations(country=country, limit=limit, safe_mode=safe_mode)


def stations_by_state(
    state: str, country: str = "", limit: int = 200, *, safe_mode: bool = False
) -> list[RadioStation]:
    """Stations in *state* (optionally within *country*), most-listened first."""
    refuse_in_safe_mode(safe_mode)
    if not state.strip():
        return []
    params: dict[str, object] = {
        "state": state.strip(),
        "limit": max(1, min(limit, 500)),
        "order": "clickcount",
        "reverse": "true",
        "hidebroken": "true",
    }
    if country.strip():
        params["country"] = country.strip()
    path = f"/json/stations/search?{urllib.parse.urlencode(params)}"
    return stations_from_json(_http_json(path))


def stations_by_language(
    language: str, limit: int = 200, *, safe_mode: bool = False
) -> list[RadioStation]:
    """Stations broadcasting in *language*, most-listened first."""
    refuse_in_safe_mode(safe_mode)
    if not language.strip():
        return []
    params = {
        "language": language.strip(),
        "limit": max(1, min(limit, 500)),
        "order": "clickcount",
        "reverse": "true",
        "hidebroken": "true",
    }
    path = f"/json/stations/search?{urllib.parse.urlencode(params)}"
    return stations_from_json(_http_json(path))


def trending_stations(limit: int = 100, *, safe_mode: bool = False) -> list[RadioStation]:
    """What people are tuning to *now* -- RadioBrowser's click ranking.

    Deliberately separate from :func:`popular_stations`, which is the *vote*
    ranking. They answer different questions -- "what is being listened to
    today" against "what did people once think was good" -- and a browse tree
    that offers only the second is missing the livelier half.
    """
    refuse_in_safe_mode(safe_mode)
    path = f"/json/stations/topclick/{max(1, min(limit, 200))}"
    return stations_from_json(_http_json(path))


def list_codecs(*, safe_mode: bool = False) -> list[tuple[str, int]]:
    """Audio codecs in the directory, with a station count each.

    This is vTuner's "Quality" classification -- one of the four axes a
    commercial catalogue sells -- available free from a directory we already
    query. Returned with counts because a codec is only a useful browse node if
    you can see how much is behind it: MP3 and AAC carry almost everything,
    while several of the eleven have a handful of stations apiece.
    """
    refuse_in_safe_mode(safe_mode)
    data = _http_json("/json/codecs")
    rows: list[tuple[str, int]] = []
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if name:
            rows.append((name, _coerce_int(entry.get("stationcount"))))
    rows.sort(key=lambda row: (-row[1], row[0]))
    return rows


def stations_by_codec(
    codec: str, limit: int = 200, *, min_bitrate: int = 0, safe_mode: bool = False
) -> list[RadioStation]:
    """Stations using *codec*, highest bitrate first.

    Ordered by bitrate rather than by clicks, because someone browsing by codec
    is asking a quality question, not a popularity one. *min_bitrate* (in kbps)
    narrows it further, which is the other half of what "Quality" means.
    """
    refuse_in_safe_mode(safe_mode)
    if not codec.strip():
        return []
    params: dict[str, object] = {
        "limit": max(1, min(limit, 500)),
        "order": "bitrate",
        "reverse": "true",
        "hidebroken": "true",
    }
    if min_bitrate > 0:
        params["bitrateMin"] = int(min_bitrate) * 1000
    codec_path = urllib.parse.quote(codec.strip())
    path = f"/json/stations/bycodecexact/{codec_path}?{urllib.parse.urlencode(params)}"
    return stations_from_json(_http_json(path))


def recently_changed_stations(limit: int = 100, *, safe_mode: bool = False) -> list[RadioStation]:
    """Newly added and just-fixed stations. Cheap, and it makes a directory
    feel alive rather than archival."""
    refuse_in_safe_mode(safe_mode)
    path = f"/json/stations/lastchange/{max(1, min(limit, 200))}"
    return stations_from_json(_http_json(path))


def register_click(station_uuid: str, *, safe_mode: bool = False) -> None:
    """Tell RadioBrowser the station was played (community click-count vote).

    Best-effort: called once playback actually starts, from a background
    thread; failures are swallowed by the caller (a missed vote is not worth
    interrupting playback over).
    """
    refuse_in_safe_mode(safe_mode)
    if not station_uuid:
        return
    path = f"/json/url/{urllib.parse.quote(station_uuid)}"
    _http_json(path)
