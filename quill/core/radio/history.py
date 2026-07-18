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
    #: Speak "Entered/Exited X dialog" around every modal dialog. Off by
    #: default, matching QUILL's own Settings.announce_dialog_transitions --
    #: the standalone apps previously never wired this policy at all, so
    #: dialog_contract.show_modal_dialog's "no policy set" fallback always
    #: spoke it, unlike full QUILL where it is opt-in.
    announce_dialog_transitions: bool = False
    #: How "What's Playing" (Ctrl+T) reads a track, as a token template over
    #: quill.core.radio.now_playing (#1068). The default cleans up the raw
    #: broadcast metadata some stations send ("YOUR SONG by Elton John"
    #: instead of a wall of key="value" noise); a listener can retune it with
    #: {title}/{artist}/{raw} tokens and [optional] segments in Preferences.
    now_playing_template: str = "{title}[ by {artist}]"
    #: When a station's stream fails, scan the station's own website for a
    #: working one (quill.core.radio.recovery Strategy C, #1065). The always-on
    #: strategies -- re-resolving a moved StreamTheWorld mount and refreshing
    #: from the directory -- run regardless; this gates only the extra
    #: website-scan step (a network fetch of the station's homepage on failure),
    #: so it is a single opt-out in Preferences. On by default; off in Safe Mode.
    recover_from_website: bool = True
    #: The mpv audio-device name radio playback routes to (#1076), e.g.
    #: "wasapi/{guid}". "" = system default. Set from the Preferences
    #: "Radio output device" dropdown; needs the mpv engine (ignored, with
    #: a spoken fallback, when libmpv is not installed).
    output_device: str = ""
    #: Which playback engine radio uses: "auto" (mpv when installed --
    #: device routing, pause/rewind live, volume boost, wider codec/HLS
    #: support -- else wx.media), "wx" (classic Windows Media, the escape
    #: hatch), or "mpv" (insist; falls back with an announcement if absent).
    playback_engine: str = "auto"
    #: Volume Boost (mpv engine): amplify up to 50% past 100 for quiet
    #: streams. No effect on the wx.media engine, which caps at 100.
    volume_boost: bool = False
    #: Sound options (listener-level, so global rather than per-station):
    #: mono downmix -- both channels blended into one, for single-sided
    #: hearing or a single earbud, where hard-panned stereo content simply
    #: disappears otherwise.
    mono_enabled: bool = False
    #: Night mode -- real-time loudness normalization (lifts quiet program
    #: material), the complement to the compressor's "tame the loud parts".
    night_mode_enabled: bool = False
    #: Alt+F4 sends the app to the system tray (still playing) instead of
    #: closing the window. Off by default -- Alt+F4 keeps its Windows-wide
    #: meaning unless the listener opts in. Separate from close_action,
    #: which governs the titlebar X and Exit: with this on, the reflexive
    #: keyboard close tucks the radio away while the deliberate exits still
    #: exit (or ask, per close_action).
    alt_f4_to_tray: bool = False
    #: Verbose radio logging (quill-radio #5). When on, the radio logger
    #: subtrees drop to DEBUG (via radio_logging.set_radio_debug) and recording
    #: runs ffmpeg at -loglevel verbose, so a hard-to-reproduce playback or
    #: recording problem leaves a full trail in quill.log. Off by default (it is
    #: chatty); one checkbox in Preferences (Ctrl+,) turns it on. Applied when
    #: history loads and whenever the checkbox changes.
    debug_mode: bool = False
    #: ISO timestamp of when the app was last running (written on close), so a
    #: startup "missed recording" report can name scheduled recordings whose
    #: time passed while it was closed (quill-radio #4). Empty = never recorded
    #: (a first run reports nothing).
    last_seen: str = ""
    #: Where the standalone writes ``quill.log`` (quill-radio #5). "" = the
    #: default ``<data_dir>/logs``. Set from the Preferences "Log folder" field;
    #: applied at startup and relocated live when changed.
    log_dir: str = ""

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
        history.announce_dialog_transitions = bool(raw.get("announce_dialog_transitions", False))
        template = raw.get("now_playing_template")
        if isinstance(template, str) and template.strip():
            history.now_playing_template = template
        history.recover_from_website = bool(raw.get("recover_from_website", True))
        history.output_device = str(raw.get("output_device", ""))
        engine = str(raw.get("playback_engine", "auto"))
        history.playback_engine = engine if engine in ("auto", "wx", "mpv") else "auto"
        history.volume_boost = bool(raw.get("volume_boost", False))
        history.mono_enabled = bool(raw.get("mono_enabled", False))
        history.night_mode_enabled = bool(raw.get("night_mode_enabled", False))
        history.alt_f4_to_tray = bool(raw.get("alt_f4_to_tray", False))
        history.debug_mode = bool(raw.get("debug_mode", False))
        history.last_seen = str(raw.get("last_seen", ""))
        history.log_dir = str(raw.get("log_dir", ""))
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
            "announce_dialog_transitions": history.announce_dialog_transitions,
            "now_playing_template": history.now_playing_template,
            "recover_from_website": history.recover_from_website,
            "output_device": history.output_device,
            "playback_engine": history.playback_engine,
            "volume_boost": history.volume_boost,
            "mono_enabled": history.mono_enabled,
            "night_mode_enabled": history.night_mode_enabled,
            "alt_f4_to_tray": history.alt_f4_to_tray,
            "debug_mode": history.debug_mode,
            "last_seen": history.last_seen,
            "log_dir": history.log_dir,
            "stations": [station.to_dict() for station in history.stations],
        },
    )
