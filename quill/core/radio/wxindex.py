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


def _iso_newer(candidate: str, baseline: str) -> bool:
    """True if the ``candidate`` ISO timestamp is strictly newer than ``baseline``.

    Tolerant of trailing ``Z`` vs ``+00:00`` and of unparseable values (falls
    back to a lexicographic compare, which is correct for same-format ISO-8601).
    """
    from datetime import datetime

    def _parse(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    parsed_candidate = _parse(candidate)
    parsed_baseline = _parse(baseline)
    if parsed_candidate is not None and parsed_baseline is not None:
        return parsed_candidate > parsed_baseline
    return candidate > baseline


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


def _directory_stations(*, max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS) -> list[WxStation]:
    """Every known transmitter *with feed data*, from the full-directory tier.

    The per-state live endpoint (``/v1/states/{slug}/stations``) returns only a
    ``feed_count``, never the feed URLs -- so stations parsed from it are never
    playable. Feed URLs live only in the full ``/stations/all-known`` dump: the
    bundled snapshot, or a fresher copy in the ``directory.json`` cache written
    by :func:`refresh_directory`. This reads that full-directory tier (fresh
    cache, else bundled snapshot) so callers get real, playable feeds. No live
    call and no per-state fetch -- it is a local read.
    """
    snapshot = load_snapshot()
    cached = _read_cache("directory.json")
    if cached is not None and cached[1] <= max_age_seconds and isinstance(cached[0], dict):
        cache_generated = str(cached[0].get("generated_at", ""))
        # An in-place update ships a newer bundled snapshot but leaves the old
        # version's cache in place, still inside the 7-day age window -- so it
        # would shadow the new listings (#1207). When both carry a timestamp and
        # the bundled snapshot is newer, prefer the snapshot. A cache without a
        # timestamp (legacy/hand-written) is still honored, as before.
        snapshot_wins = bool(
            snapshot.generated_at
            and cache_generated
            and _iso_newer(snapshot.generated_at, cache_generated)
        )
        if not snapshot_wins:
            return parse_stations(cached[0].get("stations", []))
    return snapshot.stations


def playable_stations_for_state(
    slug: str, *, max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS
) -> list[WxStation]:
    """This state's transmitters that have a playable internet re-stream.

    Sourced from the full-directory tier (:func:`_directory_stations`), because
    only that tier carries feed URLs -- the per-state live endpoint does not.
    This is what the Browse tree lists, so a state's folder is never silently
    empty online while the bundled snapshot clearly has feeds for it.
    """
    return [
        s
        for s in _directory_stations(max_age_seconds=max_age_seconds)
        if s.state.lower() == slug.lower() and s.feeds
    ]


def states_with_playable_feeds(
    *, safe_mode: bool = False, max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS
) -> list[WxState]:
    """State folders for the Browse tree, counted from the SAME full-directory
    tier the station leaves come from -- so a state's "(N items)" always equals
    the transmitters that expanding it will actually show.

    The live ``/v1/states`` endpoint (:func:`list_states`) reports a
    ``stations_with_feeds`` count that can exceed what the directory tier
    (snapshot / ``directory.json`` cache) actually carries feed URLs for, which
    left states looking populated but expanding empty. This groups
    :func:`_directory_stations` by state (feeds only) for the count, and uses
    ``list_states`` only for the human state name (offline-safe fallback to the
    slug). A state with zero playable transmitters here is simply omitted.
    """
    names: dict[str, str] = {}
    try:
        for state in list_states(safe_mode=safe_mode, max_age_seconds=max_age_seconds):
            names[state.slug.lower()] = state.name
    except WxIndexError:
        pass
    counts: dict[str, int] = {}
    for station in _directory_stations(max_age_seconds=max_age_seconds):
        if station.feeds and station.state:
            key = station.state.lower()
            counts[key] = counts.get(key, 0) + 1
    folders = [
        WxState(slug=slug, name=names.get(slug, slug.upper()), stations_with_feeds=count)
        for slug, count in counts.items()
    ]
    return sorted(folders, key=lambda state: state.name.lower())


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
