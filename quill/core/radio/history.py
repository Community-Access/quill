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

from quill.core.audio_enhance import EQ_PRESETS
from quill.core.radio.models import RadioStation

_FILE_NAME = "radio_history.json"
_MAX_ENTRIES = 15


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
class RadioHistory:
    """Recently played stations plus the resume-on-launch preference."""

    stations: list[RadioStation] = field(default_factory=list)
    resume_on_launch: bool = False
    #: Speak "Now playing: ..." when the stream's track title changes.
    #: Off by default -- in QUILL it would interrupt writing; turning it on
    #: is one check item on the radio menus.
    announce_track_titles: bool = False
    #: Silently check GitHub releases for a newer Quill Radio on launch (the
    #: same check Help > Check for Updates runs, just quiet unless a genuine
    #: update is found); on by default, one checkbox in Preferences (Ctrl+,)
    #: turns it off.
    check_updates_on_startup: bool = True
    #: ISO timestamp of the last update check (manual or automatic), so the
    #: startup check only hits the network once a day, not on every launch.
    last_update_check: str = ""
    #: Sound Enhancements (Playback menu): three adjustable EQ bands (dB,
    #: see audio_enhance.EQ_BAND_MIN_DB/MAX_DB) and whether the compressor
    #: is on. All default to off -- normal playback never touches the
    #: ffmpeg relay unless the user opts in.
    eq_bass_db: float = 0.0
    eq_mid_db: float = 0.0
    eq_treble_db: float = 0.0
    compressor_enabled: bool = False
    #: What closing the window (titlebar X, Alt+F4, Station > Exit) does:
    #: "ask" shows a one-time-per-session-until-answered Exit/Minimize to
    #: Tray dialog (its "Don't ask me again" checkbox writes this field);
    #: "exit"/"minimize" skip straight to that action. Preferences (Ctrl+,)
    #: can always set it back to "ask".
    close_action: str = "ask"

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
        history.check_updates_on_startup = bool(raw.get("check_updates_on_startup", True))
        history.last_update_check = str(raw.get("last_update_check", ""))
        if "eq_bass_db" in raw or "eq_mid_db" in raw or "eq_treble_db" in raw:
            history.eq_bass_db = _coerce_float(raw.get("eq_bass_db"), 0.0)
            history.eq_mid_db = _coerce_float(raw.get("eq_mid_db"), 0.0)
            history.eq_treble_db = _coerce_float(raw.get("eq_treble_db"), 0.0)
        elif isinstance(raw.get("eq_preset"), str):
            # One-time migration: a file saved before the three-band sliders
            # only remembered a preset name.
            bass, mid, treble = EQ_PRESETS.get(str(raw["eq_preset"]), (0.0, 0.0, 0.0))
            history.eq_bass_db, history.eq_mid_db, history.eq_treble_db = bass, mid, treble
        history.compressor_enabled = bool(raw.get("compressor_enabled", False))
        close_action = str(raw.get("close_action", "ask"))
        history.close_action = (
            close_action if close_action in ("ask", "exit", "minimize") else "ask"
        )
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
            "check_updates_on_startup": history.check_updates_on_startup,
            "last_update_check": history.last_update_check,
            "eq_bass_db": history.eq_bass_db,
            "eq_mid_db": history.eq_mid_db,
            "eq_treble_db": history.eq_treble_db,
            "compressor_enabled": history.compressor_enabled,
            "close_action": history.close_action,
            "stations": [station.to_dict() for station in history.stations],
        },
    )
