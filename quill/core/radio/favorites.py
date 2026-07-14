"""Saved internet-radio stations: favorites (from RadioBrowser or user-added
custom links) persisted as atomic JSON, the standard QUILL settings-surface
pattern (see ``core/publish/destinations.py`` for the sibling example).

Every favorite carries an optional ``folder`` name. Radio itself only ever
uses the default (unfoldered) list today. Podcasts (`quill/core/podcasts/`)
shipped its own atomic-JSON store (`subscriptions.py`) with a real nested
folder tree rather than reusing this shape -- a show's folder placement
needed arbitrary nesting, which this flat `folder` field doesn't support.
wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.models import RadioStation

_FILE_NAME = "radio_favorites.json"


@dataclass(slots=True)
class FavoriteStation:
    """A saved station plus the metadata favorites need beyond the model."""

    station: RadioStation
    #: "" is the default (unfoldered) list; reserved for future organization.
    folder: str = ""
    #: True for a station the user typed in themselves (not from RadioBrowser
    #: search) -- shown as "Custom" in the browser so its provenance is clear.
    custom: bool = False

    @property
    def key(self) -> str:
        """A stable identity for de-duplication: RadioBrowser uuid when known,
        else the stream URL itself (custom stations have no uuid)."""
        return self.station.station_uuid or self.station.stream_url


@dataclass(slots=True)
class RadioFavoritesStore:
    """All saved favorites, in display order."""

    favorites: list[FavoriteStation] = field(default_factory=list)

    def find(self, key: str) -> FavoriteStation | None:
        for favorite in self.favorites:
            if favorite.key == key:
                return favorite
        return None

    def contains(self, station: RadioStation) -> bool:
        key = station.station_uuid or station.stream_url
        return self.find(key) is not None

    def add(self, station: RadioStation, *, folder: str = "", custom: bool = False) -> None:
        if self.contains(station):
            return
        self.favorites.append(FavoriteStation(station=station, folder=folder, custom=custom))

    def remove(self, key: str) -> bool:
        before = len(self.favorites)
        self.favorites = [f for f in self.favorites if f.key != key]
        return len(self.favorites) != before

    def move(self, key: str, *, delta: int) -> bool:
        """Shift the favorite identified by *key* up (-1) or down (+1)."""
        index = next((i for i, f in enumerate(self.favorites) if f.key == key), -1)
        if index < 0:
            return False
        target = index + delta
        if target < 0 or target >= len(self.favorites):
            return False
        self.favorites[index], self.favorites[target] = (
            self.favorites[target],
            self.favorites[index],
        )
        return True


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_favorites(data_dir: Path) -> RadioFavoritesStore:
    """Read saved favorites (an absent or broken file reads as empty)."""
    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return RadioFavoritesStore()
    entries = raw.get("favorites") if isinstance(raw, dict) else None
    store = RadioFavoritesStore()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        station_data = entry.get("station")
        if not isinstance(station_data, dict):
            continue
        station = RadioStation.from_dict(station_data)
        if station is None:
            continue
        store.favorites.append(
            FavoriteStation(
                station=station,
                folder=str(entry.get("folder", "")),
                custom=bool(entry.get("custom", False)),
            )
        )
    return store


def save_favorites(data_dir: Path, store: RadioFavoritesStore) -> None:
    """Persist favorites atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "favorites": [
                {
                    "station": favorite.station.to_dict(),
                    "folder": favorite.folder,
                    "custom": favorite.custom,
                }
                for favorite in store.favorites
            ]
        },
    )
