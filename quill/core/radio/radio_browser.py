"""RadioBrowser client: free, keyless internet-radio station directory.

RadioBrowser (radio-browser.info) is a community-run, open-data directory of
internet radio streams with no API key and no commercial terms to violate --
the one FastPlay backend (of its three: RadioBrowser, TuneIn, iHeartRadio)
that is fully documented and safe to depend on long-term. See
``docs/planning/radio.md`` for why the other two were deliberately left out.

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
    limit: int = _DEFAULT_LIMIT,
    safe_mode: bool = False,
) -> list[RadioStation]:
    """Stations matching *query* (name search), optionally narrowed by tag or
    country; ordered by community click count (most-listened first)."""
    refuse_in_safe_mode(safe_mode)
    params: dict[str, object] = {
        "limit": max(1, min(limit, 200)),
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
    path = f"/json/stations/search?{urllib.parse.urlencode(params)}"
    return stations_from_json(_http_json(path))


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
