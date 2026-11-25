"""Radio controller bootstrap, kept outside the frame mixin's module budget."""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir


def initialize_radio(host: Any) -> None:
    """Build Radio once, or leave a disabled host safely passive."""
    if getattr(host, "_radio_runtime_initialized", False):
        return
    if getattr(host, "_radio_runtime_initializing", False):
        return
    if getattr(host, "_radio_controller", None) is not None:
        host._radio_runtime_initialized = True
        return
    if not host._feature_enabled("core.radio"):
        _leave_passive(host)
        return
    host._radio_runtime_initializing = True
    try:
        _build_radio(host)
        host._radio_runtime_initialized = True
    finally:
        host._radio_runtime_initializing = False


def _build_radio(host: Any) -> None:
    """Construct Radio's controller, scheduler, persistence and timers once."""

    from quill.core.radio import favorites as radio_favorites
    from quill.core.radio import history as radio_history
    from quill.core.radio import wake_timer
    from quill.core.radio.recording import RadioRecorder, load_recording_settings
    from quill.core.radio.recording_schedule import RecordingScheduler
    from quill.ui.outcome_report import say_recording_finished
    from quill.ui.radio.player_controller import RadioPlayerController

    host._radio_favorites = radio_favorites.load_favorites(app_data_dir())
    host._radio_history = radio_history.load_history(app_data_dir())
    from quill.core.radio.radio_logging import set_radio_debug

    set_radio_debug(host._radio_history.debug_mode)
    host._radio_history_key = ""
    host._radio_track_title = ""
    host._radio_track_source = ""
    host._radio_fallback_tried = ""
    host._radio_ever_played = False
    host._radio_title_timer = host._wx.Timer(host.frame)
    host.frame.Bind(
        host._wx.EVT_TIMER,
        lambda _e: host._radio_fetch_track_title(),
        host._radio_title_timer,
    )
    from quill.core.spotify.session import SpotifySession

    host._spotify_session = SpotifySession()
    host._radio_controller = RadioPlayerController(
        host.frame,
        on_state_changed=host._on_radio_state_changed,
        on_register_click=host._radio_register_click,
        before_play=host._stop_podcast_before_radio,
        on_enhance_error=host._on_radio_enhance_error,
        resolve_enhancement=host._radio_resolve_enhancement,
        resolve_volume=host._radio_resolve_volume,
        output_device=host._radio_history.output_device,
        on_output_device_error=host._on_radio_output_device_error,
        playback_engine=host._radio_history.playback_engine,
        on_buffering=lambda: host._wx.CallAfter(host._radio_announce_buffering),
        spotify_token_provider=host._spotify_session.access_token,
        resolve_youtube=host._radio_resolve_youtube,
        youtube_consent=host._radio_youtube_consent,
    )
    host._radio_controller.on_output_device_reverted = host._on_radio_output_device_reverted
    from quill.ui.radio.song_marks_ui import resolve_timeshift_minutes

    host._radio_controller._resolve_timeshift_minutes = lambda station: resolve_timeshift_minutes(
        host, station
    )
    host._radio_controller.set_enhancement(
        bass_db=host._radio_history.eq_bass_db,
        mid_db=host._radio_history.eq_mid_db,
        treble_db=host._radio_history.eq_treble_db,
        compressor_enabled=host._radio_history.compressor_enabled,
    )
    host._radio_controller.set_sound_options(
        channel_mode=host._radio_history.channel_mode,
        night_mode_enabled=host._radio_history.night_mode_enabled,
        optilab_enabled=host._radio_history.optilab_enabled,
        optilab_mode=host._radio_history.optilab_mode,
        optilab_input_db=host._radio_history.optilab_input_db,
        optilab_auto_adapt=host._radio_history.optilab_auto_adapt,
        optilab_exact_live=host._radio_history.optilab_exact_live,
    )
    host._radio_controller.set_volume_boost(host._radio_history.volume_boost)
    host._radio_controller._radio_history = host._radio_history
    host._radio_controller._skip_silence = bool(host._radio_history.skip_silence)
    host._radio_recording_settings = load_recording_settings(app_data_dir())
    host._radio_recorder = RadioRecorder(
        on_state_changed=host._on_radio_recording_changed,
        on_reconnect=host._on_radio_recording_reconnect,
        on_parts_joined=lambda note: host._wx.CallAfter(host._announce, note),
        on_exact_processed=lambda note: host._wx.CallAfter(host._announce, note),
        on_capture_failed=lambda station, reason: host._wx.CallAfter(
            host._radio_announce_capture_failed, station, reason
        ),
        on_finished=lambda report: host._wx.CallAfter(say_recording_finished, host, report),
    )
    host._radio_scheduler = RecordingScheduler(
        data_dir=app_data_dir(),
        recorder=host._radio_recorder,
        recording_settings=host._radio_recording_settings,
        on_fired=host._on_radio_scheduled_recording_fired,
        on_busy=host._on_radio_scheduled_recording_busy,
        filter_graph_provider=host._radio_recording_filter_graph,
    )
    host._radio_wake_watcher = wake_timer.WakeUpWatcher(
        app_data_dir(), on_wake=host._on_radio_wake_up
    )
    host._wx.CallAfter(host._report_missed_recordings)
    host._wx.CallAfter(host._reconcile_and_offer_radio_resume)
    host._radio_last_seen_timer = host._wx.Timer(host.frame)
    host.frame.Bind(
        host._wx.EVT_TIMER,
        lambda _e: host._radio_minute_tick(),
        host._radio_last_seen_timer,
    )
    host._radio_last_seen_timer.Start(60_000)
    host._wx.CallAfter(host._refresh_radio_wake_task)
    from quill.ui.radio import catalog_ui

    host._wx.CallAfter(catalog_ui.refresh_on_startup, host)


def _leave_passive(host: Any) -> None:
    """Keep shutdown/status probes safe without constructing optional players."""
    for name in (
        "_radio_favorites",
        "_radio_history",
        "_radio_title_timer",
        "_spotify_session",
        "_radio_controller",
        "_radio_recording_settings",
        "_radio_recorder",
        "_radio_scheduler",
        "_radio_wake_watcher",
        "_radio_last_seen_timer",
    ):
        setattr(host, name, None)
    host._radio_history_key = ""
    host._radio_track_title = ""
    host._radio_track_source = ""
    host._radio_fallback_tried = ""
    host._radio_ever_played = False
    host._radio_runtime_initialized = False
    host._radio_runtime_initializing = False
