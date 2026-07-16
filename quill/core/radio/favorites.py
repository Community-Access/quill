"""Saved internet-radio stations: favorites (from RadioBrowser or user-added
custom links) persisted as atomic JSON, the standard QUILL settings-surface
pattern (see ``core/publish/destinations.py`` for the sibling example).

Every favorite carries a ``folder`` path ("" = top level; "News/Morning"
nests Morning inside News), giving the Favorites Manager arbitrary-depth
folders on the same flat field every existing favorites file already has.
Podcasts (`quill/core/podcasts/`) keeps its own id-based folder tree in
`subscriptions.py`; stations don't need ids, so paths stay simpler here.
wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.audio_enhance import clamp_eq_gain
from quill.core.radio.models import RadioStation

_FILE_NAME = "radio_favorites.json"


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value) if value.strip() else default
        except ValueError:
            return default
    return default


@dataclass(slots=True)
class FavoriteStation:
    """A saved station plus the metadata favorites need beyond the model."""

    station: RadioStation
    #: "" is the top level. Folders nest by path: "News/Morning" is the
    #: Morning folder inside News -- arbitrary depth on the same flat field
    #: every existing favorites file already has, so old data loads as-is.
    folder: str = ""
    #: True for a station the user typed in themselves (not from RadioBrowser
    #: search) -- shown as "Custom" in the browser so its provenance is clear.
    custom: bool = False
    #: A user-chosen display name overriding the (often noisy) directory
    #: name in lists, menus, and announcements; "" keeps the station's own.
    custom_name: str = ""
    #: Remembered per-station volume (stations are mastered wildly
    #: differently); -1 means "no preference recorded yet".
    volume_percent: int = -1
    #: Sound Enhancements (Playback > Sound Enhancements...), remembered per
    #: station the same way volume is: a whole-record override, on only when
    #: has_sound_enhancement_override is True (mirrors PodcastSettings'
    #: whole-record show override -- see PodcastLibrary.apply_show_override).
    #: While False the fields below are unused; the station follows
    #: RadioHistory's shared eq_bass_db/mid/treble/compressor_enabled.
    has_sound_enhancement_override: bool = False
    eq_bass_db: float = 0.0
    eq_mid_db: float = 0.0
    eq_treble_db: float = 0.0
    compressor_enabled: bool = False

    @property
    def key(self) -> str:
        """A stable identity for de-duplication: RadioBrowser uuid when known,
        else the stream URL itself (custom stations have no uuid)."""
        return self.station.station_uuid or self.station.stream_url

    @property
    def display_label(self) -> str:
        """What lists, menus, and announcements call this favorite."""
        return self.custom_name or self.station.display_name


@dataclass(slots=True)
class RadioFavoritesStore:
    """All saved favorites, in display order."""

    favorites: list[FavoriteStation] = field(default_factory=list)
    #: Explicitly created folders (New Folder...), so a folder can exist and
    #: show in the tree before any station is filed into it. Entry folders
    #: (paths carried by favorites) are merged in by :meth:`folder_names`.
    folders: list[str] = field(default_factory=list)

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
        """Shift the favorite identified by *key* up (-1) or down (+1),
        staying inside its own folder group: the swap partner is the nearest
        favorite in that direction with the same ``folder`` value, so display
        order inside a folder changes without tearing the entry out of it."""
        index = next((i for i, f in enumerate(self.favorites) if f.key == key), -1)
        if index < 0 or delta == 0:
            return False
        step = 1 if delta > 0 else -1
        folder = self.favorites[index].folder
        target = index + step
        while 0 <= target < len(self.favorites):
            if self.favorites[target].folder == folder:
                self.favorites[index], self.favorites[target] = (
                    self.favorites[target],
                    self.favorites[index],
                )
                return True
            target += step
        return False

    def move_relative_to(self, key: str, target_key: str, *, before: bool) -> bool:
        """Place *key* directly above (*before*) or below the target favorite.

        The moved entry adopts the target's folder, so Move Above/Move Below
        across a folder boundary also files the station there -- the same
        semantics as reordering into a podcast Play Queue position.
        """
        if key == target_key:
            return False
        source = next((i for i, f in enumerate(self.favorites) if f.key == key), -1)
        if source < 0:
            return False
        entry = self.favorites.pop(source)
        target = next((i for i, f in enumerate(self.favorites) if f.key == target_key), -1)
        if target < 0:
            self.favorites.insert(source, entry)
            return False
        entry.folder = self.favorites[target].folder
        self.favorites.insert(target if before else target + 1, entry)
        return True

    def set_folder(self, key: str, folder: str) -> bool:
        """File the favorite under *folder* ("" returns it to the top level)."""
        favorite = self.find(key)
        if favorite is None:
            return False
        favorite.folder = folder.strip()
        return True

    def rename(self, key: str, custom_name: str) -> bool:
        """Give the favorite a user-chosen display name ("" restores the
        station's own directory name)."""
        favorite = self.find(key)
        if favorite is None:
            return False
        favorite.custom_name = custom_name.strip()
        return True

    def set_volume(self, key: str, volume_percent: int) -> bool:
        """Remember the preferred volume for this station (0-100)."""
        favorite = self.find(key)
        if favorite is None:
            return False
        favorite.volume_percent = max(0, min(100, int(volume_percent)))
        return True

    def set_enhancement(
        self,
        key: str,
        *,
        bass_db: float,
        mid_db: float,
        treble_db: float,
        compressor_enabled: bool,
    ) -> bool:
        """Give this station its own Sound Enhancements, overriding the
        shared default (RadioHistory.eq_bass_db/mid/treble/compressor_enabled)
        for this station only."""
        favorite = self.find(key)
        if favorite is None:
            return False
        favorite.has_sound_enhancement_override = True
        favorite.eq_bass_db = bass_db
        favorite.eq_mid_db = mid_db
        favorite.eq_treble_db = treble_db
        favorite.compressor_enabled = compressor_enabled
        return True

    def clear_enhancement_override(self, key: str) -> bool:
        """Go back to following the shared default for this station."""
        favorite = self.find(key)
        if favorite is None or not favorite.has_sound_enhancement_override:
            return False
        favorite.has_sound_enhancement_override = False
        return True

    def add_folder(self, path: str) -> bool:
        """Register a folder explicitly (it may hold no stations yet)."""
        cleaned = path.strip().strip("/")
        if not cleaned or cleaned in self.folder_names():
            return False
        self.folders.append(cleaned)
        return True

    def folder_names(self) -> list[str]:
        """Every folder path in display order: explicitly created folders
        first, then folders implied by the favorites that live in them."""
        seen: list[str] = []
        for path in self.folders:
            if path and path not in seen:
                seen.append(path)
        for favorite in self.favorites:
            if favorite.folder and favorite.folder not in seen:
                seen.append(favorite.folder)
        return seen

    def rename_folder(self, old: str, new: str) -> int:
        """Rename a folder everywhere it appears; returns entries touched.

        Folders nest by path ("News/Morning" is Morning inside News), so the
        rename also carries every descendant folder along by rewriting the
        path prefix.
        """
        new = new.strip().strip("/")
        if not old or not new or old == new:
            return 0
        prefix = old + "/"
        count = 0
        for favorite in self.favorites:
            if favorite.folder == old:
                favorite.folder = new
                count += 1
            elif favorite.folder.startswith(prefix):
                favorite.folder = new + "/" + favorite.folder[len(prefix) :]
                count += 1
        self.folders = [
            new
            if path == old
            else (new + "/" + path[len(prefix) :] if path.startswith(prefix) else path)
            for path in self.folders
        ]
        return count

    def delete_folder(self, name: str) -> int:
        """Dissolve a folder and everything nested inside it: the stations
        move to the top level of the list (they are never deleted with the
        folder); returns entries touched."""
        prefix = name + "/"
        count = 0
        for favorite in self.favorites:
            if favorite.folder == name or favorite.folder.startswith(prefix):
                favorite.folder = ""
                count += 1
        self.folders = [
            path for path in self.folders if path != name and not path.startswith(prefix)
        ]
        return count

    def search(self, query: str) -> list[FavoriteStation]:
        """Favorites matching *query*, case-insensitive, in display order.

        Matches the station name, country, language, tags, folder name, and
        homepage -- rich enough to find one stream among hundreds. An empty
        query returns everything.
        """
        needle = query.strip().lower()
        if not needle:
            return list(self.favorites)
        out: list[FavoriteStation] = []
        for favorite in self.favorites:
            station = favorite.station
            haystack = " ".join((
                station.name,
                favorite.custom_name,
                station.country,
                getattr(station, "language", ""),
                " ".join(station.tags),
                favorite.folder,
                getattr(station, "homepage", ""),
            )).lower()
            if needle in haystack:
                out.append(favorite)
        return out


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
    if isinstance(raw, dict):
        raw_folders = raw.get("folders")
        for path in raw_folders if isinstance(raw_folders, list) else []:
            if isinstance(path, str) and path.strip():
                store.folders.append(path.strip().strip("/"))
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        station_data = entry.get("station")
        if not isinstance(station_data, dict):
            continue
        station = RadioStation.from_dict(station_data)
        if station is None:
            continue
        volume_raw = entry.get("volume_percent", -1)
        volume = int(volume_raw) if isinstance(volume_raw, (int, float)) else -1
        store.favorites.append(
            FavoriteStation(
                station=station,
                folder=str(entry.get("folder", "")),
                custom=bool(entry.get("custom", False)),
                custom_name=str(entry.get("custom_name", "")),
                volume_percent=volume if 0 <= volume <= 100 else -1,
                has_sound_enhancement_override=bool(
                    entry.get("has_sound_enhancement_override", False)
                ),
                eq_bass_db=clamp_eq_gain(_coerce_float(entry.get("eq_bass_db"), 0.0)),
                eq_mid_db=clamp_eq_gain(_coerce_float(entry.get("eq_mid_db"), 0.0)),
                eq_treble_db=clamp_eq_gain(_coerce_float(entry.get("eq_treble_db"), 0.0)),
                compressor_enabled=bool(entry.get("compressor_enabled", False)),
            )
        )
    return store


def save_favorites(data_dir: Path, store: RadioFavoritesStore) -> None:
    """Persist favorites atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "folders": list(store.folders),
            "favorites": [
                {
                    "station": favorite.station.to_dict(),
                    "folder": favorite.folder,
                    "custom": favorite.custom,
                    "custom_name": favorite.custom_name,
                    "volume_percent": favorite.volume_percent,
                    "has_sound_enhancement_override": favorite.has_sound_enhancement_override,
                    "eq_bass_db": favorite.eq_bass_db,
                    "eq_mid_db": favorite.eq_mid_db,
                    "eq_treble_db": favorite.eq_treble_db,
                    "compressor_enabled": favorite.compressor_enabled,
                }
                for favorite in store.favorites
            ],
        },
    )
