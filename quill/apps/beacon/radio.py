"""Radio depth: stream validation, alternates, program metadata (PRD 9.1, 44.3).

A radio station is fragile: a stream URL goes dark, a station moves hosts, a
playlist pointer rots. This module gives Beacon the radio-specific handling the
generic capture path lacks:

- ``validate_stream`` checks whether a stream URL is currently reachable. It
  never makes a network call unless the caller passes a ``fetcher``; with no
  fetcher it returns "not checked" so the feature is fail-safe and unit-
  testable offline. No project data is sent -- only a request to a public
  stream URL the user already saved.
- ``alternate_streams`` proposes fallback URLs for a station (https/http
  variants, playlist -> direct-stream guesses) so a dead primary does not lose
  the station.
- ``capture_program`` builds a radioProgram Resource + Beacon from schedule or
  now-playing metadata, the thing a generic capture cannot infer.

Pure logic over inputs; wx-free and unit-testable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse, urlunparse

from quill.apps.beacon import uld
from quill.apps.beacon.model import (
    TYPE_RADIO_PROGRAM,
    TYPE_RADIO_STATION,
    Beacon,
    Resource,
)

# MIME types that indicate a reachable audio stream (PRD 9.1).
_STREAM_MIME_PREFIXES = (
    "audio/",
    "application/ogg",
    "application/x-mpegurl",
    "application/vnd.apple.mpegurl",
)
_PLAYLIST_EXT = (".m3u", ".m3u8", ".pls", ".asx", ".ram")


def validate_stream(
    url: str,
    *,
    fetcher: Callable[[str, int], tuple[int, str] | None] | None = None,
    timeout: int = 5,
) -> dict[str, Any]:
    """Check whether a stream URL is reachable.

    ``fetcher(url, timeout)`` should return ``(status_code, content_type)`` or
    ``None`` if the request failed. When ``fetcher`` is None (the default) no
    network call is made and ``reachable`` is ``None`` ("not checked"), so the
    UI can run offline and tests need no sockets.
    """
    out: dict[str, Any] = {
        "url": url,
        "reachable": None,
        "status": None,
        "mime": "",
        "message": "not checked",
    }
    if not url or not url.strip():
        out["message"] = "empty URL"
        return out
    if fetcher is None:
        return out
    try:
        result = fetcher(url, timeout)
    except Exception as ex:  # never let a network error crash the caller
        out["reachable"] = False
        out["message"] = f"check failed: {ex}"
        return out
    if result is None:
        out["reachable"] = False
        out["message"] = "unreachable"
        return out
    status, mime = result
    out["status"] = status
    out["mime"] = mime or ""
    ok = status is not None and 200 <= int(status) < 400
    out["reachable"] = ok
    if ok:
        out["message"] = "reachable"
    else:
        out["message"] = f"HTTP {status}"
    return out


def alternate_streams(url: str) -> list[str]:
    """Propose fallback stream URLs for a station (PRD 17.4 recovery).

    Generates https<->http variants and, for playlist URLs, a best-guess
    direct-stream URL. The original URL is never included in the result. No
    network is used; these are candidate strings for the user to try.
    """
    if not url or not url.strip():
        return []
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        return []
    alts: list[str] = []
    # Scheme flip.
    other = "https" if p.scheme == "http" else "http"
    alts.append(urlunparse((other, p.netloc, p.path, p.params, p.query, "")))
    # Playlist -> guess a direct stream path on the same host.
    low = p.path.lower()
    if any(low.endswith(ext) for ext in _PLAYLIST_EXT):
        base = urlunparse((p.scheme, p.netloc, "/", "", "", ""))
        alts.append(base + "stream")
        alts.append(base + "live")
        alts.append(base + "listen")
    # Dedupe, drop the original, preserve order.
    seen: set[str] = set()
    out: list[str] = []
    for a in alts:
        if a and a != url and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def capture_program(
    *,
    station: str,
    program: str,
    host: str = "",
    start_ms: int | None = None,
    end_ms: int | None = None,
    url: str = "",
    description: str = "",
    note: str = "",
    tags: list[str] | None = None,
    collections: list[str] | None = None,
    favorite: bool = False,
    capture_source: str = "manual",
) -> tuple[Beacon, Resource]:
    """Build a radioProgram Beacon + Resource from schedule/now-playing data.

    A program is a time-bound broadcast on a station: "Morning Edition on
    KQED, 06:00-09:00, hosted by A Martinez." Capturing it as its own Beacon
    lets the user save the show, not just the stream, and find it by host or
    time later. The station name is carried as a tag so it groups naturally.
    """
    title = program or station or "Radio program"
    tags = list(tags or [])
    if station and station not in tags:
        tags.insert(0, station)
    canon = url or f"radio://{station}/{program}".replace(" ", "-")
    res = Resource(
        type=TYPE_RADIO_PROGRAM,
        canonical_id=canon,
        title=title,
        creator=host,
        primary_uri=url,
        metadata={
            "station": station,
            "program": program,
            "host": host,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "description": description,
        },
    )
    loc = uld.build_uld(
        resource_id=res.resource_id,
        location_type="media",
        media_start_ms=start_ms,
        media_end_ms=end_ms,
        display_summary=f"{program} on {station}" if station and program else title,
    )
    beacon = Beacon(
        title=title,
        note=note,
        favorite=favorite,
        in_inbox=True,
        tags=tags,
        collections=list(collections or []),
        capture_source=capture_source,
    )
    beacon.locations = [loc]
    return beacon, res


def station_from_stream(url: str, *, title: str = "") -> tuple[Beacon, Resource]:
    """Build a radioStation Beacon from a stream URL with alternates stored.

    The primary stream is the resource URI; proposed alternates are stored on
    the resource metadata so a dead primary can be repaired without losing the
    station (PRD 17.4).
    """
    alts = alternate_streams(url)
    res = Resource(
        type=TYPE_RADIO_STATION,
        canonical_id=url,
        title=title or url,
        primary_uri=url,
        metadata={"alternates": alts},
    )
    loc = uld.build_uld(
        resource_id=res.resource_id,
        location_type="native",
        display_summary=title or url,
    )
    beacon = Beacon(title=title or url, in_inbox=True, tags=[], capture_source="manual")
    beacon.locations = [loc]
    return beacon, res
