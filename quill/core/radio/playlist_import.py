"""Parse an M3U / M3U8 playlist into radio stations for import.

Supports both extended M3U (``#EXTM3U`` with ``#EXTINF:<secs>,<Name>`` lines
naming each entry) and plain M3U (one stream URL per line). Only http(s) stream
URLs are taken; comments, blank lines, and non-network entries are ignored. A
URL with no ``#EXTINF`` name gets a readable fallback derived from its host.

Pure and wx-free so it is unit-tested without files or a UI.
"""

from __future__ import annotations

from urllib.parse import urlparse

from quill.core.radio.models import RadioStation


def _name_from_url(url: str) -> str:
    """A readable fallback station name from a stream URL (its host)."""
    host = urlparse(url).hostname or url
    return host[4:] if host.startswith("www.") else host


def parse_m3u(text: str) -> list[RadioStation]:
    """Parse M3U/M3U8 *text* into a list of :class:`RadioStation`.

    Extended-M3U ``#EXTINF:...,Name`` lines name the following URL; a bare URL
    line with no preceding ``#EXTINF`` is named after its host. Duplicate stream
    URLs are collapsed (first name wins). Non-http(s) lines are skipped.
    """
    stations: list[RadioStation] = []
    seen: set[str] = set()
    pending_name = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("#EXTINF"):
            # "#EXTINF:<duration>,<Name>" -- the name is everything after the
            # first comma; duration/attributes before it are ignored.
            _, _, after_colon = line.partition(":")
            pending_name = after_colon.split(",", 1)[1].strip() if "," in after_colon else ""
            continue
        if line.startswith("#"):
            continue  # other directives / comments
        if not line.lower().startswith(("http://", "https://")):
            pending_name = ""
            continue
        if line in seen:
            pending_name = ""
            continue
        seen.add(line)
        stations.append(RadioStation(name=pending_name or _name_from_url(line), stream_url=line))
        pending_name = ""
    return stations


def dedup_key(station: RadioStation) -> str:
    """The identity a favorite is matched on: its uuid, else its stream URL."""
    return station.station_uuid or station.stream_url


def split_new_and_duplicates(
    stations: list[RadioStation], existing_keys: set[str]
) -> tuple[list[RadioStation], list[RadioStation]]:
    """Partition parsed *stations* into (new, duplicates) against the set of
    keys already in the favorites (``dedup_key`` of every current favorite), so
    the importer can ask the listener how to handle the overlap."""
    new: list[RadioStation] = []
    duplicates: list[RadioStation] = []
    for station in stations:
        (duplicates if dedup_key(station) in existing_keys else new).append(station)
    return new, duplicates
