"""Public NOAA Weather Radio facade: three-tier resolver over WeatherIndex.

Resolution order for reads: fresh cache (younger than ``max_age_seconds``)
-> live fetch (then write cache) -> stale cache -> bundled snapshot. Every
tier is wx-free; the only network egress is the reviewed site in
``wxindex_http``.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from quill.core.paths import app_data_dir
from quill.core.radio.wxindex_http import Fetcher, WxIndexError, http_json, refuse_in_safe_mode
from quill.core.radio.wxindex_models import (
    WxState,
    WxStation,
    parse_states,
    parse_station,
    parse_stations,
)
from quill.core.radio.wxindex_snapshot import load_snapshot

_DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days

_SAME = re.compile(r"^\d{6}$")
_CALLSIGN = re.compile(r"^[A-Z]{2,3}\d{2,3}$", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class RefreshResult:
    station_count: int
    state_count: int
    generated_at: str


def _cache_dir() -> Path:
    path = app_data_dir() / "radio" / "wxindex-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(name: str) -> Path:
    return _cache_dir() / name


def _read_cache(name: str) -> tuple[object, float] | None:
    """Return ``(data, age_seconds)`` for a cache file, or None if missing/corrupt."""
    path = _cache_path(name)
    try:
        text = path.read_text(encoding="utf-8")
        age_seconds = time.time() - path.stat().st_mtime
    except OSError:
        return None
    try:
        data: object = json.loads(text)
    except ValueError:
        return None
    return data, age_seconds


def _write_cache(name: str, data: object) -> None:
    path = _cache_path(name)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(path)


def _live_or_cache(
    path: str,
    cache_name: str,
    *,
    safe_mode: bool,
    fetcher: Fetcher | None,
    max_age_seconds: float,
) -> object:
    cached = _read_cache(cache_name)
    if cached is not None and cached[1] <= max_age_seconds:
        return cached[0]
    try:
        refuse_in_safe_mode(safe_mode)
        fresh = http_json(path, fetcher=fetcher)
    except WxIndexError:
        if cached is not None:
            return cached[0]  # stale cache beats a live failure
        raise
    _write_cache(cache_name, fresh)
    return fresh


def list_states(
    *,
    safe_mode: bool = False,
    fetcher: Fetcher | None = None,
    max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS,
) -> list[WxState]:
    try:
        data = _live_or_cache(
            "/v1/states",
            "states.json",
            safe_mode=safe_mode,
            fetcher=fetcher,
            max_age_seconds=max_age_seconds,
        )
    except WxIndexError:
        return load_snapshot().states
    return parse_states(data)


def stations_for_state(
    slug: str,
    *,
    safe_mode: bool = False,
    fetcher: Fetcher | None = None,
    max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS,
) -> list[WxStation]:
    try:
        data = _live_or_cache(
            f"/v1/states/{slug}/stations",
            f"state-{slug}.json",
            safe_mode=safe_mode,
            fetcher=fetcher,
            max_age_seconds=max_age_seconds,
        )
    except WxIndexError:
        return [s for s in load_snapshot().stations if s.state.lower() == slug.lower()]
    return parse_stations(data)


def refresh_directory(
    *,
    safe_mode: bool = False,
    fetcher: Fetcher | None = None,
) -> RefreshResult:
    """Force a live pull of the whole directory and cache it. No fallback tiers.

    Unlike the read paths, a manual refresh is meant to report success or
    failure honestly, so Safe Mode and network errors both raise rather than
    silently degrading to a stale cache or the bundled snapshot.
    """
    refuse_in_safe_mode(safe_mode)
    states_data = http_json("/v1/states", fetcher=fetcher)
    stations_data = http_json("/v1/stations/all-known", fetcher=fetcher)
    _write_cache("states.json", states_data)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc = {"generated_at": generated_at, "states": states_data, "stations": stations_data}
    _write_cache("directory.json", doc)
    state_count = len(states_data) if isinstance(states_data, list) else 0
    station_count = len(stations_data) if isinstance(stations_data, list) else 0
    return RefreshResult(
        station_count=station_count,
        state_count=state_count,
        generated_at=generated_at,
    )


def station_detail(
    callsign: str, *, safe_mode: bool = False, fetcher: Fetcher | None = None
) -> WxStation | None:
    try:
        refuse_in_safe_mode(safe_mode)
        return parse_station(http_json(f"/v1/stations/{quote(callsign)}", fetcher=fetcher))
    except WxIndexError:
        for s in load_snapshot().stations:
            if s.callsign.lower() == callsign.lower():
                return s
        return None


def search_stations(
    query: str, *, safe_mode: bool = False, fetcher: Fetcher | None = None
) -> list[WxStation]:
    """Route a query to the right WeatherIndex search endpoint.

    A 6-digit query is treated as a SAME code (``?same=``); a callsign-shaped
    query (``ABC123``) hits the station-detail endpoint; ``"County, ST"``
    routes to ``?c=&s=``; anything else is treated as free-text state/name
    search (``?s=``). Falls back to a substring match over the bundled
    snapshot when the live request is refused or fails.
    """
    q = query.strip()
    if not q:
        return []
    try:
        refuse_in_safe_mode(safe_mode)
        if _SAME.match(q):
            return parse_stations(http_json(f"/v1/station_search?same={quote(q)}", fetcher=fetcher))
        if _CALLSIGN.match(q):
            s = station_detail(q, safe_mode=safe_mode, fetcher=fetcher)
            return [s] if s else []
        if "," in q:  # "County, ST"
            county, _, st = q.partition(",")
            return parse_stations(
                http_json(
                    f"/v1/station_search?c={quote(county.strip())}&s={quote(st.strip())}",
                    fetcher=fetcher,
                )
            )
        return parse_stations(http_json(f"/v1/station_search?s={quote(q)}", fetcher=fetcher))
    except WxIndexError:
        ql = q.lower()
        return [
            s
            for s in load_snapshot().stations
            if ql in s.callsign.lower()
            or ql in s.state.lower()
            or any(ql in c.lower() for c in s.counties)
            or q in s.same_codes
        ]


def local_stations(
    latitude: float,
    longitude: float,
    *,
    county: str = "",
    safe_mode: bool = False,
    fetcher: Fetcher | None = None,
) -> list[WxStation]:
    """Resolve nearby stations: county/SAME match first, else nearest-by-coordinate."""
    if county:
        hits = search_stations(county, safe_mode=safe_mode, fetcher=fetcher)
        if hits:
            return hits
    stations = load_snapshot().stations

    def dist(s: WxStation) -> float:
        return math.hypot(s.latitude - latitude, s.longitude - longitude)

    return sorted((s for s in stations if s.latitude or s.longitude), key=dist)[:5]
