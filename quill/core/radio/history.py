"""Recently played internet-radio stations, persisted as atomic JSON.

Backs the Station menu's Recently Played submenu, the Play Last Station
command, and the standalone app's optional resume-on-launch behavior.
Most recent first, capped, de-duplicated by the same key favorites use.
wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.models import RadioStation

_FILE_NAME = "radio_history.json"
_MAX_ENTRIES = 15


@dataclass(slots=True)
class RadioHistory:
    """Recently played stations plus the resume-on-launch preference."""

    stations: list[RadioStation] = field(default_factory=list)
    resume_on_launch: bool = False
    #: Speak "Now playing: ..." when the stream's track title changes.
    #: Off by default -- in QUILL it would interrupt writing; turning it on
    #: is one check item on the radio menus.
    announce_track_titles: bool = False

    def record(self, station: RadioStation) -> None:
        """Note that *station* just played; it moves to the front."""
        key = station.station_uuid or station.stream_url
        self.stations = [s for s in self.stations if (s.station_uuid or s.stream_url) != key]
        self.stations.insert(0, station)
        del self.stations[_MAX_ENTRIES:]

    @property
    def last_station(self) -> RadioStation | None:
        return self.stations[0] if self.stations else None


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_history(data_dir: Path) -> RadioHistory:
    """Read history (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return RadioHistory()
    history = RadioHistory()
    if isinstance(raw, dict):
        history.resume_on_launch = bool(raw.get("resume_on_launch", False))
        history.announce_track_titles = bool(raw.get("announce_track_titles", False))
        entries = raw.get("stations")
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            station = RadioStation.from_dict(entry)
            if station is not None:
                history.stations.append(station)
        del history.stations[_MAX_ENTRIES:]
    return history


def save_history(data_dir: Path, history: RadioHistory) -> None:
    """Persist history atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "resume_on_launch": history.resume_on_launch,
            "announce_track_titles": history.announce_track_titles,
            "stations": [station.to_dict() for station in history.stations],
        },
    )
