"""Reading and writing Quill Radio's history file.

Split from :mod:`quill.core.radio.history` under GATE-11, along the seam that
was already there: the record is the *shape* of what Radio remembers, and this
is the *file* it lives in. Every field added to ``RadioHistory`` needs a line
in each of the two functions below, and keeping them together makes a
half-added field -- readable but never written, or written but never read --
visible as a missing line rather than invisible in three hundred.

Both are total: an absent or broken file reads as a default record rather than
raising, because losing this file costs preferences, and refusing to start is
a worse answer than starting with the shipped ones.

Re-exported from ``history`` so no caller had to move with it.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.audio_enhance import EQ_PRESETS
from quill.core.podcasts import transcript_export
from quill.core.radio import browse_visibility
from quill.core.radio.history import (
    _FILE_NAME,
    _MAX_ENTRIES,
    RadioHistory,
    RadioOnboardingState,
    _coerce_float,
    _coerce_int,
)
from quill.core.radio.models import RadioStation
from quill.core.radio.play_queue import normalize_repeat_mode
from quill.core.radio.search_history import from_json as search_history_from_json
from quill.core.radio.search_history import to_json as search_history_to_json
from quill.core.radio.search_sources import normalize as normalize_search_sources


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
        history.show_station_details = bool(raw.get("show_station_details", True))
        history.confirm_browse_delete = bool(raw.get("confirm_browse_delete", True))
        history.explain_browse_delete = bool(raw.get("explain_browse_delete", True))
        history.winamp_playback_keys = bool(raw.get("winamp_playback_keys", True))
        history.podcast_refresh_minutes = _coerce_int(raw.get("podcast_refresh_minutes"), 0)
        history.podcast_refresh_on_launch = bool(raw.get("podcast_refresh_on_launch", False))
        history.reminder_default_lead_seconds = _coerce_int(
            raw.get("reminder_default_lead_seconds"), 900
        )
        history.reminder_sound = bool(raw.get("reminder_sound", True))
        history.skip_silence = bool(raw.get("skip_silence", False))
        history.recording_speed = _coerce_float(raw.get("recording_speed"), 1.0) or 1.0
        history.youtube_speed = _coerce_float(raw.get("youtube_speed"), 1.0) or 1.0
        history.recordings_shuffle = bool(raw.get("recordings_shuffle", False))
        history.recordings_repeat = normalize_repeat_mode(raw.get("recordings_repeat"))
        history.search_sources_enabled = normalize_search_sources(raw.get("search_sources_enabled"))
        history.search_source_facet = str(raw.get("search_source_facet", "") or "")
        history.recent_searches = search_history_from_json(raw.get("recent_searches"))
        # Present-vs-absent is load-bearing: absent stays None ("never set").
        if "browse_sources_enabled" in raw:
            stored_epoch = raw.get("browse_sources_epoch")
            epoch = int(stored_epoch) if isinstance(stored_epoch, (int, float)) else 0
            # A branch introduced since this choice was made was never rejected
            # -- it did not exist. Shown once, then stamped, so hiding it
            # afterwards sticks.
            history.browse_sources_enabled = browse_visibility.with_new_sources(
                raw.get("browse_sources_enabled"), epoch
            )
            history.browse_sources_epoch = browse_visibility.SOURCES_EPOCH
        history.show_status_bar = bool(raw.get("show_status_bar", True))
        history.ui_font_scale = min(2.0, max(1.0, _coerce_float(raw.get("ui_font_scale"), 1.0)))
        history.prevent_sleep = bool(raw.get("prevent_sleep", True))
        history.keep_awake_before_recording = bool(raw.get("keep_awake_before_recording", True))
        history.wake_for_scheduled_recording = bool(raw.get("wake_for_scheduled_recording", True))
        history.catalog_enabled = bool(raw.get("catalog_enabled", True))
        history.catalog_refresh_on_startup = bool(raw.get("catalog_refresh_on_startup", True))
        history.catalog_refresh_hours = max(
            0, min(24 * 14, _coerce_int(raw.get("catalog_refresh_hours"), 24))
        )
        history.subscription_episode_limit = max(
            0, _coerce_int(raw.get("subscription_episode_limit"), 25)
        )
        history.youtube_consented = bool(raw.get("youtube_consented", False))
        history.media_notice_signature = str(raw.get("media_notice_signature", ""))
        history.onboarding = RadioOnboardingState.from_dict(raw.get("onboarding"))
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
        history.transcript_detail = transcript_export.normalize_detail(raw.get("transcript_detail"))
        template = raw.get("now_playing_template")
        if isinstance(template, str) and template.strip():
            history.now_playing_template = template
        history.recover_from_website = bool(raw.get("recover_from_website", True))
        history.output_device = str(raw.get("output_device", ""))
        engine = str(raw.get("playback_engine", "auto"))
        history.playback_engine = engine if engine in ("auto", "wx", "mpv") else "auto"
        history.volume_boost = bool(raw.get("volume_boost", False))
        try:
            vol = int(raw.get("volume_percent", -1))
        except (TypeError, ValueError):
            vol = -1
        history.volume_percent = vol if 0 <= vol <= 100 else -1
        # channel_mode replaces the legacy mono_enabled bool; migrate an old
        # store (mono_enabled: true -> "mono") so an upgrade keeps the setting.
        raw_channel = str(raw.get("channel_mode", "") or "")
        if raw_channel in ("stereo", "mono", "left", "right"):
            history.channel_mode = raw_channel
        else:
            history.channel_mode = "mono" if bool(raw.get("mono_enabled", False)) else "stereo"
        history.night_mode_enabled = bool(raw.get("night_mode_enabled", False))
        history.optilab_enabled = bool(raw.get("optilab_enabled", False))
        raw_optilab_mode = str(raw.get("optilab_mode", "") or "")
        history.optilab_mode = (
            raw_optilab_mode
            if raw_optilab_mode in ("off", "podcast", "stream", "limiter")
            else "off"
        )
        try:
            history.optilab_input_db = float(raw.get("optilab_input_db", 0.0) or 0.0)
        except (TypeError, ValueError):
            history.optilab_input_db = 0.0
        try:
            raw_adapt = int(raw.get("optilab_auto_adapt", 0) or 0)
            history.optilab_auto_adapt = max(0, min(100, raw_adapt))
        except (TypeError, ValueError):
            history.optilab_auto_adapt = 0
        history.optilab_exact = bool(raw.get("optilab_exact", False))
        history.optilab_exact_live = bool(raw.get("optilab_exact_live", False))
        # Favorites sort order (added in 2.0.2). A store written before that
        # release has no key and kept favorites in the user's hand-arranged
        # order; defaulting an absent key to "az" silently re-sorted 30-plus
        # carefully ordered stations A-Z on upgrade (#1168, #1178). Treat a
        # missing key as "manual" so an existing order is preserved; only an
        # explicit stored value re-sorts. (The display sort is non-mutating,
        # so a user re-sorted by the old default can restore their order by
        # choosing Unsorted in Preferences.)
        if "favorites_sort" in raw:
            sort = str(raw.get("favorites_sort", "az"))
            history.favorites_sort = sort if sort in ("az", "za", "manual") else "az"
        else:
            history.favorites_sort = "manual"
        raw_folder_sorts = raw.get("folder_sort_orders", {})
        history.folder_sort_orders = (
            {
                str(path): str(order)
                for path, order in raw_folder_sorts.items()
                if str(order) in ("az", "za", "manual")
            }
            if isinstance(raw_folder_sorts, dict)
            else {}
        )
        history.alt_f4_to_tray = bool(raw.get("alt_f4_to_tray", False))
        history.open_browse_at_startup = bool(raw.get("open_browse_at_startup", False))
        from quill.core.radio import startup_window as startup

        # The choice if it has been made, else the old checkbox once -- somebody
        # who ticked "open Browse at startup" still gets Browse.
        history.startup_window = (
            startup.normalize(raw.get("startup_window"))
            if "startup_window" in raw
            else startup.migrate_from_checkbox(history.open_browse_at_startup)
        )
        history.debug_mode = bool(raw.get("debug_mode", False))
        history.last_seen = str(raw.get("last_seen", ""))
        history.log_dir = str(raw.get("log_dir", ""))
        history.use_global_volume = bool(raw.get("use_global_volume", False))
        history.song_history_enabled = bool(raw.get("song_history_enabled", True))
        resume_choice = str(raw.get("recording_resume_choice", "ask"))
        history.recording_resume_choice = (
            resume_choice if resume_choice in ("ask", "always", "never") else "ask"
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
            "show_station_details": history.show_station_details,
            "confirm_browse_delete": history.confirm_browse_delete,
            "explain_browse_delete": history.explain_browse_delete,
            "winamp_playback_keys": history.winamp_playback_keys,
            "podcast_refresh_minutes": history.podcast_refresh_minutes,
            "podcast_refresh_on_launch": history.podcast_refresh_on_launch,
            "reminder_default_lead_seconds": history.reminder_default_lead_seconds,
            "reminder_sound": history.reminder_sound,
            "skip_silence": history.skip_silence,
            "recording_speed": history.recording_speed,
            "youtube_speed": history.youtube_speed,
            "recordings_shuffle": history.recordings_shuffle,
            "recordings_repeat": history.recordings_repeat,
            "search_sources_enabled": list(history.search_sources_enabled),
            "search_source_facet": history.search_source_facet,
            "recent_searches": search_history_to_json(history.recent_searches),
            **(
                {
                    "browse_sources_enabled": list(history.browse_sources_enabled),
                    "browse_sources_epoch": history.browse_sources_epoch,
                }
                if history.browse_sources_enabled is not None
                else {}
            ),
            "show_status_bar": history.show_status_bar,
            "ui_font_scale": history.ui_font_scale,
            "prevent_sleep": history.prevent_sleep,
            "keep_awake_before_recording": history.keep_awake_before_recording,
            "wake_for_scheduled_recording": history.wake_for_scheduled_recording,
            "catalog_enabled": history.catalog_enabled,
            "catalog_refresh_on_startup": history.catalog_refresh_on_startup,
            "catalog_refresh_hours": history.catalog_refresh_hours,
            "subscription_episode_limit": history.subscription_episode_limit,
            "youtube_consented": history.youtube_consented,
            "check_updates_on_startup": history.check_updates_on_startup,
            "last_update_check": history.last_update_check,
            "eq_bass_db": history.eq_bass_db,
            "eq_mid_db": history.eq_mid_db,
            "eq_treble_db": history.eq_treble_db,
            "compressor_enabled": history.compressor_enabled,
            "close_action": history.close_action,
            "announce_dialog_transitions": history.announce_dialog_transitions,
            "transcript_detail": history.transcript_detail,
            "now_playing_template": history.now_playing_template,
            "recover_from_website": history.recover_from_website,
            "output_device": history.output_device,
            "media_notice_signature": history.media_notice_signature,
            "onboarding": history.onboarding.to_dict(),
            "playback_engine": history.playback_engine,
            "volume_boost": history.volume_boost,
            "volume_percent": history.volume_percent,
            "favorites_sort": history.favorites_sort,
            "folder_sort_orders": history.folder_sort_orders,
            "channel_mode": history.channel_mode,
            # Keep writing the legacy bool for one release so an older build can
            # still read the mono choice if the user downgrades.
            "mono_enabled": history.channel_mode == "mono",
            "night_mode_enabled": history.night_mode_enabled,
            "optilab_enabled": history.optilab_enabled,
            "optilab_mode": history.optilab_mode,
            "optilab_input_db": history.optilab_input_db,
            "optilab_auto_adapt": history.optilab_auto_adapt,
            "optilab_exact": history.optilab_exact,
            "optilab_exact_live": history.optilab_exact_live,
            "alt_f4_to_tray": history.alt_f4_to_tray,
            "open_browse_at_startup": history.open_browse_at_startup,
            "startup_window": history.startup_window,
            "debug_mode": history.debug_mode,
            "last_seen": history.last_seen,
            "log_dir": history.log_dir,
            "use_global_volume": history.use_global_volume,
            "song_history_enabled": history.song_history_enabled,
            "recording_resume_choice": history.recording_resume_choice,
            "stations": [station.to_dict() for station in history.stations],
        },
    )
