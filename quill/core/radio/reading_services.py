"""Radio Reading Services: bundled snapshot plus a three-tier live resolver.

Reads ``quill/data/reading_services.json`` -- a curated, hand-vetted list of
radio reading services for people who are blind or have print disabilities --
so the app can surface them without a live directory lookup. Missing or
corrupt snapshots are never fatal: they log and return an empty list.

On top of that bundled tier, :func:`list_reading_services` mirrors
:mod:`quill.core.radio.wxindex`'s three-tier resolver: fresh cache (younger
than ``_DEFAULT_MAX_AGE_SECONDS``) -> live refresh via RadioBrowser (then
cached) -> stale cache -> the bundled snapshot. :func:`refresh_reading_services`
does the live pull: it re-queries RadioBrowser's directory (the free, keyless
station directory already used by :mod:`quill.core.radio.radio_browser`) for
each reading-service keyword, keeps only stations that look like a reading
service, de-dupes by stream URL, and writes the result to the app-data cache.

wx-free, strict-typed.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.radio import radio_browser
from quill.core.radio.models import RadioStation
from quill.core.radio.radio_browser import RadioBrowserError, refuse_in_safe_mode

_LOG = logging.getLogger(__name__)

_DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days -- mirrors wxindex's cache window

#: Terms that mark a RadioBrowser station as a radio reading service (audio
#: description / talking newspaper service for blind and print-disabled
#: listeners), as opposed to a general-interest station that happens to share
#: a word. Matched against both the station name and its tags.
_READING_KEYWORDS = (
    "radio reading",
    "reading service",
    "audio information",
    "reading radio",
    "blind radio",
)

Searcher = Callable[..., list[RadioStation]]


@dataclass(slots=True, frozen=True)
class RrsRefreshResult:
    count: int
    generated_at: str


def _is_reading_service(station: RadioStation) -> bool:
    """True if *station* looks like a radio reading service and is playable.

    A keyword match in the name or tags is required, plus a non-empty
    ``stream_url`` -- a matching name with nothing to play is useless here.
    """
    if not station.stream_url:
        return False
    name = station.name.lower()
    tags = [tag.lower() for tag in station.tags]
    for keyword in _READING_KEYWORDS:
        if keyword in name:
            return True
        if any(keyword in tag for tag in tags):
            return True
    return False


def _cache_dir() -> Path:
    path = app_data_dir() / "radio" / "reading-services-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path() -> Path:
    return _cache_dir() / "directory.json"


def _station_to_cache_dict(station: RadioStation) -> dict[str, object]:
    data = station.to_dict()
    data["source"] = station.source
    return data


def _station_from_cache_dict(data: dict[str, object]) -> RadioStation | None:
    station = RadioStation.from_dict(data)
    if station is None:
        return None
    return dataclasses.replace(station, source=str(data.get("source", "")))


def _stations_from_doc(doc: object) -> list[RadioStation]:
    if not isinstance(doc, dict):
        return []
    raw = doc.get("stations", [])
    if not isinstance(raw, list):
        return []
    stations: list[RadioStation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        station = _station_from_cache_dict(item)
        if station is not None:
            stations.append(station)
    return stations


def _read_cache() -> tuple[list[RadioStation], float] | None:
    """Return ``(stations, age_seconds)`` for the cache file, or None if missing/corrupt."""
    path = _cache_path()
    try:
        text = path.read_text(encoding="utf-8")
        age_seconds = time.time() - path.stat().st_mtime
    except OSError:
        return None
    try:
        doc: object = json.loads(text)
    except ValueError:
        return None
    return _stations_from_doc(doc), age_seconds


def _write_cache(stations: list[RadioStation], generated_at: str) -> None:
    path = _cache_path()
    tmp = path.with_suffix(path.suffix + ".tmp")
    doc = {
        "generated_at": generated_at,
        "stations": [_station_to_cache_dict(s) for s in stations],
    }
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    tmp.replace(path)


def reading_services_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "reading_services.json"


def load_reading_services() -> list[RadioStation]:
    path = reading_services_path()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _LOG.warning("Radio Reading Services snapshot unavailable (%s): %s", path, error)
        return []
    if not isinstance(doc, dict):
        return []
    services = doc.get("services", [])
    if not isinstance(services, list):
        return []

    stations: list[RadioStation] = []
    for svc in services:
        if not isinstance(svc, dict):
            continue
        name = str(svc.get("name", "")).strip()
        stream_url = str(svc.get("stream_url", "")).strip()
        if not name or not stream_url:
            continue
        state = str(svc.get("state", "")).strip()
        tags = ("reading service", "blind") + ((state,) if state else ())
        stations.append(
            RadioStation(
                name=name,
                stream_url=stream_url,
                station_uuid=str(svc.get("station_uuid", "")),
                homepage=str(svc.get("homepage", "")),
                country="United States",
                tags=tags,
                source="Radio Reading Service",
            )
        )
    return stations


def refresh_reading_services(
    *, safe_mode: bool = False, searcher: Searcher | None = None
) -> RrsRefreshResult:
    """Live-query RadioBrowser for reading services and cache the result.

    Unlike :func:`list_reading_services`, a manual refresh is meant to report
    success or failure honestly, so Safe Mode raises rather than silently
    degrading to a cache or the bundled snapshot -- the same contract as
    :func:`quill.core.radio.wxindex.refresh_directory`.
    """
    refuse_in_safe_mode(safe_mode)
    search = searcher if searcher is not None else radio_browser.search_stations
    seen_urls: set[str] = set()
    stations: list[RadioStation] = []
    for keyword in _READING_KEYWORDS:
        for station in search(keyword, safe_mode=safe_mode):
            if not _is_reading_service(station):
                continue
            if station.stream_url in seen_urls:
                continue
            seen_urls.add(station.stream_url)
            stations.append(dataclasses.replace(station, source="Radio Reading Service"))
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_cache(stations, generated_at)
    return RrsRefreshResult(count=len(stations), generated_at=generated_at)


def list_reading_services(
    *, safe_mode: bool = False, searcher: Searcher | None = None
) -> list[RadioStation]:
    """Resolve reading services: fresh cache -> live refresh (then cache) ->
    stale cache -> bundled snapshot. Never raises -- every tier degrades to
    the next rather than surfacing a network or Safe Mode error to a reader.
    """
    cached = _read_cache()
    if cached is not None and cached[1] <= _DEFAULT_MAX_AGE_SECONDS:
        return cached[0]
    try:
        refresh_reading_services(safe_mode=safe_mode, searcher=searcher)
    except RadioBrowserError:
        pass
    else:
        fresh = _read_cache()
        if fresh is not None:
            return fresh[0]
    if cached is not None:
        return cached[0]  # stale cache beats a live failure
    return load_reading_services()
