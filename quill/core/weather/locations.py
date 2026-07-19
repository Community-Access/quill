"""Saved weather locations -- a small JSON store, atomic like every other QUILL
store (temp file + os.replace via write_json_atomic). Holds any number of
places and remembers which is primary (the one Weather Now opens to). wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.weather.models import WeatherLocation

_STORE_NAME = "weather_locations.json"


def _store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


@dataclass(slots=True)
class WeatherLocationStore:
    locations: list[WeatherLocation] = field(default_factory=list)
    primary_id: str = ""

    def find(self, location_id: str) -> WeatherLocation | None:
        return next((loc for loc in self.locations if loc.id == location_id), None)

    def primary(self) -> WeatherLocation | None:
        return self.find(self.primary_id) or (self.locations[0] if self.locations else None)

    def contains_point(self, latitude: float, longitude: float) -> bool:
        return any(
            abs(loc.latitude - latitude) < 1e-4 and abs(loc.longitude - longitude) < 1e-4
            for loc in self.locations
        )

    def add(self, location: WeatherLocation, *, make_primary: bool = False) -> WeatherLocation:
        """Append a location (assigning an id if it lacks one). The first
        location added always becomes primary; others only on request."""
        if not location.id:
            location.id = _next_id(self.locations)
        self.locations.append(location)
        if make_primary or not self.primary_id:
            self.primary_id = location.id
        return location

    def remove(self, location_id: str) -> bool:
        before = len(self.locations)
        self.locations = [loc for loc in self.locations if loc.id != location_id]
        if self.primary_id == location_id:
            self.primary_id = self.locations[0].id if self.locations else ""
        return len(self.locations) != before

    def set_primary(self, location_id: str) -> bool:
        if self.find(location_id) is None:
            return False
        self.primary_id = location_id
        return True

    def move(self, location_id: str, *, delta: int) -> bool:
        """Reorder a location within the list by +/-1 (for keyboard reordering)."""
        index = next((i for i, loc in enumerate(self.locations) if loc.id == location_id), None)
        if index is None:
            return False
        target = index + delta
        if not (0 <= target < len(self.locations)):
            return False
        self.locations.insert(target, self.locations.pop(index))
        return True


def _next_id(existing: list[WeatherLocation]) -> str:
    used = {loc.id for loc in existing}
    n = 1
    while f"loc_{n}" in used:
        n += 1
    return f"loc_{n}"


def load_locations(data_dir: Path) -> WeatherLocationStore:
    """Read saved locations (an absent or broken file reads as empty)."""
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return WeatherLocationStore()
    if not isinstance(raw, dict):
        return WeatherLocationStore()
    store = WeatherLocationStore(primary_id=str(raw.get("primary_id", "")))
    raw_locations = raw.get("locations")
    for entry in raw_locations if isinstance(raw_locations, list) else []:
        loc = _location_from_dict(entry)
        if loc is not None:
            store.locations.append(loc)
    if store.find(store.primary_id) is None:
        store.primary_id = store.locations[0].id if store.locations else ""
    return store


def save_locations(data_dir: Path, store: WeatherLocationStore) -> None:
    """Persist locations atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "primary_id": store.primary_id,
            "locations": [
                {
                    "id": loc.id,
                    "display_name": loc.display_name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "resolved_name": loc.resolved_name,
                    "state": loc.state,
                    "query": loc.query,
                }
                for loc in store.locations
            ],
        },
    )


def _location_from_dict(entry: object) -> WeatherLocation | None:
    if not isinstance(entry, dict):
        return None
    try:
        lat = float(entry["latitude"])
        lon = float(entry["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return WeatherLocation(
        display_name=str(entry.get("display_name", "")),
        latitude=lat,
        longitude=lon,
        resolved_name=str(entry.get("resolved_name", "")),
        state=str(entry.get("state", "")),
        query=str(entry.get("query", "")),
        id=str(entry.get("id", "")),
    )
