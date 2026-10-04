"""Your own tags on a station: "Detroit Tigers, MLB, baseball".

The directory already tags stations ("news", "talk", "sports"), but only with
what the directory knows. What a listener knows -- that this is the station that
carries the Tigers, or the one with the good Saturday folk show -- had nowhere to
live, so it could not be searched for. These tags are that place.

**Where they are kept.** A favorite carries its tags in the favorites file
itself (``FavoriteStation.user_tags``), so they travel with everything else
about it: backups, Export My Setup, a move to a new machine. A station that is
not a favorite has nowhere like that to live, so its tags go in one small
separate map, ``radio-station-tags.json``, keyed the same way favorites are (the
directory's uuid when there is one, else the stream address). The map keeps the
whole station record beside the tags, because a tagged station has to be
something a search can *return* -- a key alone is not a row anybody can play.

When a tagged station later becomes a favorite, the favorite wins and the map
entry is dropped the next time the tags are saved; until then
:func:`user_tags_for` reads either place, favorite first.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.radio.models import RadioStation
from quill.core.storage import read_json, write_json_atomic

if TYPE_CHECKING:
    from quill.core.radio.favorites import RadioFavoritesStore

__all__ = [
    "FILE_NAME",
    "MAX_TAGS",
    "MAX_TAG_CHARS",
    "StationTagStore",
    "details_with_tags",
    "format_tags",
    "load_tag_store",
    "parse_tags",
    "save_tag_store",
    "set_user_tags",
    "station_key",
    "tagged_stations",
    "tags_from_json",
    "user_tags_for",
]

FILE_NAME = "radio-station-tags.json"

#: Enough for a team, its league, its sport and a few of your own words; few
#: enough that the details panel stays one line.
MAX_TAGS = 30
MAX_TAG_CHARS = 60

#: Commas are what the dialog asks for; semicolons and new lines are what people
#: type anyway when pasting a list from somewhere else.
_SEPARATORS = re.compile(r"[,;\r\n]+")


def parse_tags(text: str) -> tuple[str, ...]:
    """Split typed text into tags: trimmed, de-duplicated ignoring case, in the
    order typed, capped at :data:`MAX_TAGS`. Empty pieces are dropped."""
    seen: set[str] = set()
    tags: list[str] = []
    for piece in _SEPARATORS.split(str(text or "")):
        tag = " ".join(piece.split())[:MAX_TAG_CHARS]
        folded = tag.casefold()
        if not tag or folded in seen:
            continue
        seen.add(folded)
        tags.append(tag)
        if len(tags) >= MAX_TAGS:
            break
    return tuple(tags)


def tags_from_json(value: object) -> tuple[str, ...]:
    """Tags read back from a file: a list of strings, anything else is none."""
    if not isinstance(value, list):
        return ()
    return parse_tags(",".join(str(tag) for tag in value))


def format_tags(tags: tuple[str, ...] | list[str]) -> str:
    """Tags as the dialog shows them: one line, comma separated."""
    return ", ".join(tags)


def station_key(station: object) -> str:
    """The same identity favorites use: directory uuid, else stream address."""
    uuid = str(getattr(station, "station_uuid", "") or "").strip()
    return uuid or str(getattr(station, "stream_url", "") or "").strip()


@dataclass(slots=True)
class StationTagStore:
    """Tags on stations that are not favorites, keyed by :func:`station_key`."""

    entries: dict[str, tuple[RadioStation, tuple[str, ...]]] = field(default_factory=dict)

    def tags_for(self, station: object) -> tuple[str, ...]:
        entry = self.entries.get(station_key(station))
        return entry[1] if entry is not None else ()

    def set(self, station: RadioStation, tags: tuple[str, ...]) -> bool:
        """Store (or with no tags, forget) *station*'s tags. Did anything change?"""
        key = station_key(station)
        if not key:
            return False
        if not tags:
            return self.entries.pop(key, None) is not None
        if self.entries.get(key, (None, ()))[1] == tags:
            return False
        self.entries[key] = (station, tags)
        return True

    def forget(self, station: object) -> bool:
        return self.entries.pop(station_key(station), None) is not None


def _path(data_dir: Path) -> Path:
    return data_dir / FILE_NAME


def load_tag_store(data_dir: Path) -> StationTagStore:
    """Read the map. A missing or broken file reads as empty; a bad entry is
    skipped rather than costing the rest."""
    store = StationTagStore()
    try:
        raw = read_json(_path(data_dir), {})
    except Exception:  # noqa: BLE001 - an unreadable map is an empty one
        return store
    entries = raw.get("stations") if isinstance(raw, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("station"), dict):
            continue
        station = RadioStation.from_dict(entry["station"])
        tags = tags_from_json(entry.get("tags"))
        if station is not None and tags and station_key(station):
            store.entries[station_key(station)] = (station, tags)
    return store


def save_tag_store(data_dir: Path, store: StationTagStore) -> None:
    """Persist the map atomically. Raises ``OSError`` when it cannot be written."""
    payload = {
        "version": 1,
        "stations": [
            {"station": station.to_dict(), "tags": list(tags)}
            for station, tags in store.entries.values()
        ],
    }
    write_json_atomic(_path(data_dir), payload)


def user_tags_for(
    station: object,
    *,
    favorites: RadioFavoritesStore | None,
    store: StationTagStore | None,
) -> tuple[str, ...]:
    """Your tags on *station*: the favorite's when it is one, else the map's."""
    key = station_key(station)
    if not key:
        return ()
    favorite = favorites.find(key) if favorites is not None else None
    if favorite is not None and favorite.user_tags:
        return favorite.user_tags
    return store.tags_for(station) if store is not None else ()


def set_user_tags(
    station: RadioStation,
    tags: tuple[str, ...],
    *,
    favorites: RadioFavoritesStore | None,
    store: StationTagStore,
) -> tuple[bool, bool]:
    """Save *tags* on *station* where they belong.

    Returns ``(favorites_changed, store_changed)`` so the caller saves only the
    file that actually changed. A favorite takes the tags and any copy in the
    map is dropped, so the two places can never disagree.
    """
    favorite = favorites.find(station_key(station)) if favorites is not None else None
    if favorite is not None:
        changed = favorite.user_tags != tags
        favorite.user_tags = tags
        return changed, store.forget(station)
    return False, store.set(station, tags)


def tagged_stations(
    *, favorites: RadioFavoritesStore | None, store: StationTagStore | None
) -> list[tuple[RadioStation, tuple[str, ...]]]:
    """Every station that carries your tags, favorites first."""
    found: list[tuple[RadioStation, tuple[str, ...]]] = []
    seen: set[str] = set()
    for favorite in favorites.favorites if favorites is not None else []:
        if favorite.user_tags:
            found.append((favorite.station, favorite.user_tags))
            seen.add(favorite.key)
    for key, (station, tags) in store.entries.items() if store is not None else []:
        if key not in seen:
            found.append((station, tags))
    return found


def details_with_tags(details: str, tags: tuple[str, ...]) -> str:
    """*details* with a "Your tags:" line, just after the directory's own tags.

    Placed beside the directory's line (or after the station's first lines when
    the directory gave none) so the two kinds of tag are read together, and
    labelled so nobody mistakes one for the other.
    """
    if not tags:
        return details
    line = f"Your tags: {format_tags(tags)}"
    lines = details.split("\n")
    at = next((i + 1 for i, text in enumerate(lines) if text.startswith("Tags: ")), 0)
    if not at:
        at = 1
        while at < len(lines) and lines[at].startswith(("Found because", "From:", "Location")):
            at += 1
    lines.insert(min(at, len(lines)), line)
    return "\n".join(lines)
