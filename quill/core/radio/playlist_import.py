"""Parse an M3U / M3U8 playlist into radio stations for import.

:func:`parse_playlist_file` is the Import Stations entry point for every
format (M3U, PLS, XSPF, ASX); the other formats' parsers live in
``playlist_formats``.

Supports both extended M3U (``#EXTM3U`` with ``#EXTINF:<secs>,<Name>`` lines
naming each entry) and plain M3U (one stream URL per line). Only http(s) stream
URLs are taken; comments, blank lines, and non-network entries are ignored. A
URL with no ``#EXTINF`` name gets a readable fallback derived from its host.

Pure and wx-free so it is unit-tested without files or a UI.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse

from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_formats import PlaylistFormatError, parse_playlist, sniff

__all__ = [
    "IMPORT_WILDCARD",
    "PlaylistFormatError",
    "dedup_key",
    "parse_m3u",
    "parse_playlist_file",
    "read_playlist_file",
    "split_new_and_duplicates",
]


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


#: The Import Stations file-dialog filter. Until 2026-09-25 it offered only
#: M3U/M3U8 while PLS, XSPF and ASX parsers sat unused in ``playlist_formats``
#: -- and a "Listen Live" link a listener saved is as likely to be one of those.
IMPORT_WILDCARD = (
    "Playlists (*.m3u;*.m3u8;*.pls;*.xspf;*.asx;*.wax;*.wvx)"
    "|*.m3u;*.m3u8;*.pls;*.xspf;*.asx;*.wax;*.wvx"
    "|M3U playlist (*.m3u;*.m3u8)|*.m3u;*.m3u8"
    "|PLS playlist (*.pls)|*.pls"
    "|XSPF playlist (*.xspf)|*.xspf"
    "|ASX playlist (*.asx;*.wax;*.wvx)|*.asx;*.wax;*.wvx"
    "|All files (*.*)|*.*"
)


def parse_playlist_file(text: str, filename: str = "") -> list[RadioStation]:
    """Stations from an imported playlist file of any supported format (pure).

    Dispatches through ``playlist_formats.sniff`` -- body first, then the
    file's extension -- so a PLS saved as ``.m3u`` still imports. Two cases the
    sniffer would otherwise drop: a plain M3U with no ``#EXTM3U`` header and an
    unfamiliar name looks like a bare stream, so it falls back to
    :func:`parse_m3u`; an HLS manifest is never a station list and yields
    nothing. Hostile XML raises ``playlist_formats.PlaylistFormatError``.
    """
    name = PureWindowsPath(filename).name if filename else ""
    kind = sniff(text, url=name)
    if kind == "m3u8-hls":
        return []
    if kind in ("stream", "unknown"):
        return parse_m3u(text)
    return parse_playlist(text, url=name)


def read_playlist_file(path: Path) -> list[RadioStation]:
    """Read *path* and parse it with :func:`parse_playlist_file`.

    Raises ``OSError`` when the file cannot be read and
    :class:`PlaylistFormatError` for hostile XML; the importer reports both.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_playlist_file(text, path.name)


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
