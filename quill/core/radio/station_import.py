"""Import radio stations from a JSON file into the favorites store.

Station lists travel: accessible radio apps commonly keep theirs as simple
JSON arrays of ``{"name", "category", "stream_url"}``-shaped objects,
people hand-build their own, and sharing a list with a friend is a
one-file affair. This module reads any reasonable JSON shape of that
family and merges it into
:class:`~quill.core.radio.favorites.RadioFavoritesStore`, so bringing an
existing station collection into QUILL never means retyping it.

Accepted shapes, best effort:

- a JSON array of station objects, or an object whose ``stations`` key holds
  one;
- per station: name from ``name``/``title``/``station``; URL from
  ``stream_url``/``url``/``stream``/``href``; an optional folder from
  ``category``/``folder``/``genre``/``group`` (imported stations land in
  matching favorites folders).

Only the file the user explicitly picks is read; nothing here touches the
network -- stream URLs are stored, not fetched. Deliberately ships no
third-party station list: another product's curated data is theirs (and,
in the UK, database right protects exactly this kind of curation) -- what
QUILL provides is the door, so *your own* copy of such a list, or one you
built yourself, imports in seconds. wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation

_NAME_KEYS = ("name", "title", "station")
_URL_KEYS = ("stream_url", "url", "stream", "href")
_FOLDER_KEYS = ("category", "folder", "genre", "group")


class StationImportError(CodedError):
    """The picked file could not be read as a station list."""

    code = "QUILL-RADIO-STATION-IMPORT-FAILED"


@dataclass(slots=True)
class ImportedStation:
    """One parsed entry, before merging."""

    station: RadioStation
    folder: str = ""


@dataclass(slots=True)
class ImportResult:
    """What an import actually did, for the spoken summary."""

    added: int = 0
    skipped_duplicates: int = 0
    folders: int = 0


def _first_str(entry: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_stations_json(text: str) -> list[ImportedStation]:
    """Parse *text* into stations; raises :class:`StationImportError` when
    the file is not JSON or holds no usable station at all. Entries missing
    a name or a plausible URL are skipped, not fatal."""
    try:
        data = json.loads(text)
    except ValueError as error:
        raise StationImportError(f"That file is not valid JSON: {error}") from error
    if isinstance(data, dict):
        data = data.get("stations", data.get("Stations"))
    if not isinstance(data, list):
        raise StationImportError(
            "That JSON file does not look like a station list (expected an "
            "array of stations, or an object with a 'stations' array)."
        )
    out: list[ImportedStation] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = _first_str(entry, _NAME_KEYS)
        url = _first_str(entry, _URL_KEYS)
        if not name or not url.lower().startswith(("http://", "https://")):
            continue
        out.append(
            ImportedStation(
                station=RadioStation(name=name, stream_url=url),
                folder=_first_str(entry, _FOLDER_KEYS),
            )
        )
    if not out:
        raise StationImportError(
            "No stations with a name and a stream address were found in that file."
        )
    return out


def merge_stations(store: RadioFavoritesStore, stations: list[ImportedStation]) -> ImportResult:
    """Merge parsed *stations* into *store* (caller saves).

    A station whose URL (or uuid) is already a favorite is skipped, never
    duplicated or overwritten -- an import must not disturb the collection
    someone already curated. Folder names come along, so a categorized list
    arrives organized."""
    result = ImportResult()
    new_folders: set[str] = set()
    for imported in stations:
        key = imported.station.station_uuid or imported.station.stream_url
        if store.find(key) is not None:
            result.skipped_duplicates += 1
            continue
        store.add(imported.station, folder=imported.folder, custom=True)
        result.added += 1
        if imported.folder:
            new_folders.add(imported.folder)
    result.folders = len(new_folders)
    return result
