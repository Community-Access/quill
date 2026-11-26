"""Radio controller bootstrap, kept outside the frame mixin's module budget."""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir

_RUNTIME_ATTRS = (
    "_radio_favorites",
    "_radio_history",
    "_radio_history_key",
    "_radio_track_title",
    "_radio_track_source",
    "_radio_fallback_tried",
    "_radio_ever_played",
    "_radio_title_timer",
    "_spotify_session",
    "_radio_controller",
    "_radio_recording_settings",
    "_radio_recorder",
    "_radio_scheduler",
    "_radio_wake_watcher",
    "_radio_last_seen_timer",
    "_radio_runtime_initialized",
    "_radio_runtime_initializing",
    "_radio_runtime_failed",
    "_radio_automatic_generation",
    "_radio_automatic_start_queued",
    "_radio_automatic_started",
    "_radio_automatic_paused",
)


def initialize_radio(host: Any) -> None:
    """Build Radio once, or leave a disabled host safely passive."""
    if getattr(host, "_radio_runtime_initializing", False):
        return
    requested = radio_feature_requested(host)
    if not requested:
        if getattr(host, "_radio_controller", None) is None:
            _leave_passive(host)
        else:
            pause_radio_automatic(host)
        return
    controller = getattr(host, "_radio_controller", None)
    if controller is not None:
        host._radio_runtime_initializing = True
        try:
            resume_radio_automatic(host)
        except Exception:
            host._radio_runtime_initialized = False
            host._radio_runtime_failed = True
            raise
        else:
            host._radio_runtime_initialized = True
            host._radio_runtime_failed = False
        finally:
            host._radio_runtime_initializing = False
        return
    snapshot = _snapshot(host)
    host._radio_runtime_initializing = True
    try:
        _build_radio(host)
        resume_radio_automatic(host)
    except Exception:
        rollback_radio(host, snapshot)
        host._radio_runtime_failed = True
        raise
    else:
        host._radio_runtime_initialized = True
        host._radio_runtime_failed = False
    finally:
        host._radio_runtime_initializing = False


def radio_feature_requested(host: Any) -> bool:
    """Feature/profile state, independent of a prior runtime failure."""
    locks = getattr(host, "_feature_locks", None)
    if locks is not None and locks.is_locked("core.radio"):
        return False
    features = getattr(host, "features", None)
    return True if features is None else bool(features.is_enabled("core.radio"))


def radio_automatic_enabled(host: Any) -> bool:
    """Whether automatic radio side effects may start right now."""
    from quill.ui.startup_launch import ssl_trust_ready

    return (
        radio_feature_requested(host)
        and not getattr(host, "_radio_runtime_initializing", False)
        and not getattr(host, "_radio_runtime_failed", False)
        and ssl_trust_ready()
    )


def _build_radio(host: Any) -> None:
    """Construct Radio's controller, scheduler, persistence and timers once."""

    from quill.core.radio import favorites as radio_favorites
    from quill.core.radio import history as radio_history
    from quill.core.radio.recording import RadioRecorder, load_recording_settings
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
    host._radio_scheduler = None
    host._radio_wake_watcher = None
    host._radio_last_seen_timer = None


def resume_radio_automatic(host: Any) -> None:
    """Start only missing automatic Radio pieces; keep the live player alone."""
    from quill.core.radio import wake_timer
    from quill.core.radio.recording_schedule import RecordingScheduler
    from quill.ui.startup_launch import defer_after_ssl_trust

    if not radio_feature_requested(host):
        pause_radio_automatic(host)
        return
    automatic_attrs = (
        "_radio_scheduler",
        "_radio_wake_watcher",
        "_radio_last_seen_timer",
        "_radio_automatic_start_queued",
        "_radio_automatic_started",
        "_radio_automatic_paused",
    )
    before = {name: getattr(host, name, None) for name in automatic_attrs}
    try:
        if getattr(host, "_radio_scheduler", None) is None:
            host._radio_scheduler = RecordingScheduler(
                data_dir=app_data_dir(),
                recorder=host._radio_recorder,
                recording_settings=host._radio_recording_settings,
                on_fired=host._on_radio_scheduled_recording_fired,
                on_busy=host._on_radio_scheduled_recording_busy,
                filter_graph_provider=host._radio_recording_filter_graph,
                can_run=lambda: radio_automatic_enabled(host),
            )
        if getattr(host, "_radio_wake_watcher", None) is None:
            host._radio_wake_watcher = wake_timer.WakeUpWatcher(
                app_data_dir(),
                on_wake=host._on_radio_wake_up,
                can_run=lambda: radio_automatic_enabled(host),
            )
        timer = getattr(host, "_radio_last_seen_timer", None)
        if timer is None:
            timer = host._wx.Timer(host.frame)
            host.frame.Bind(
                host._wx.EVT_TIMER,
                lambda _e: host._radio_minute_tick(),
                timer,
            )
            host._radio_last_seen_timer = timer
        is_running = getattr(timer, "IsRunning", None)
        if not callable(is_running) or not is_running():
            timer.Start(60_000)
        host._radio_automatic_paused = False
        if not getattr(host, "_radio_automatic_start_queued", False) and not getattr(
            host, "_radio_automatic_started", False
        ):
            generation = int(getattr(host, "_radio_automatic_generation", 0))
            host._radio_automatic_start_queued = True

            def failed(label: str) -> None:
                if generation == int(getattr(host, "_radio_automatic_generation", 0)):
                    host._radio_automatic_start_queued = False
                    host._radio_automatic_started = False
                    host._radio_runtime_initialized = False
                    host._radio_runtime_failed = True
                report = getattr(host, "_report_startup_task_failure", None)
                if callable(report):
                    report(label)

            defer_after_ssl_trust(
                host._wx,
                (
                    (
                        "radio automatic startup",
                        lambda: _start_radio_automatic(host, generation),
                    ),
                ),
                on_failure=failed,
            )
    except Exception:
        _rollback_automatic(host, before)
        raise


def _start_radio_automatic(host: Any, generation: int) -> None:
    if generation != int(getattr(host, "_radio_automatic_generation", 0)):
        return
    host._radio_automatic_start_queued = False
    if not radio_feature_requested(host):
        return
    if getattr(host, "_radio_automatic_started", False):
        return
    try:
        host._report_missed_recordings()
        host._reconcile_and_offer_radio_resume()
        host._refresh_radio_wake_task()
        controller = getattr(host, "_radio_controller", None)
        if controller is not None:
            host._radio_track_titles_follow_playback(controller.state)
        from quill.ui.radio import catalog_ui

        catalog_ui.refresh_on_startup(host)
    except Exception:
        host._radio_automatic_started = False
        raise
    host._radio_automatic_started = True
    host._radio_automatic_paused = False


def pause_radio_automatic(host: Any) -> None:
    """Stop future automatic Radio work without touching playback/recordings."""
    if getattr(host, "_radio_automatic_paused", False):
        return
    host._radio_automatic_paused = True
    host._radio_automatic_started = False
    host._radio_automatic_start_queued = False
    host._radio_automatic_generation = int(getattr(host, "_radio_automatic_generation", 0)) + 1
    from quill.ui.radio import catalog_ui

    try:
        catalog_ui.pause(host)
    except Exception:  # noqa: BLE001 - the scheduler guard still blocks work
        pass
    for name in ("_radio_scheduler", "_radio_wake_watcher"):
        automatic = getattr(host, name, None)
        shutdown = getattr(automatic, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:  # noqa: BLE001 - the feature gate still blocks callbacks
                pass
        setattr(host, name, None)
    for name in ("_radio_last_seen_timer", "_radio_title_timer"):
        timer = getattr(host, name, None)
        stop = getattr(timer, "Stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - shutdown must continue
                pass


def _rollback_automatic(host: Any, before: dict[str, Any]) -> None:
    for name, previous in before.items():
        current = getattr(host, name, None)
        if current is previous:
            continue
        shutdown = getattr(current, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:  # noqa: BLE001 - restore the original failure
                pass
        stop = getattr(current, "Stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - restore the original failure
                pass
        setattr(host, name, previous)


def _snapshot(host: Any) -> dict[str, tuple[bool, Any]]:
    return {name: (hasattr(host, name), getattr(host, name, None)) for name in _RUNTIME_ATTRS}


def rollback_radio(host: Any, snapshot: dict[str, tuple[bool, Any]]) -> None:
    """Stop and discard everything made by a failed first Radio build."""
    automatic = ("_radio_scheduler", "_radio_wake_watcher")
    for name in automatic + (
        "_radio_last_seen_timer",
        "_radio_title_timer",
        "_radio_controller",
        "_radio_recorder",
    ):
        existed, previous = snapshot.get(name, (False, None))
        current = getattr(host, name, None)
        if existed and current is previous:
            continue
        shutdown = getattr(current, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:  # noqa: BLE001 - rollback must finish
                pass
        stop = getattr(current, "Stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - rollback must finish
                pass
    for name, (existed, value) in snapshot.items():
        if existed:
            setattr(host, name, value)
        elif hasattr(host, name):
            delattr(host, name)
    host._radio_runtime_initialized = False
    host._radio_runtime_initializing = False
    host._radio_runtime_failed = False


def _leave_passive(host: Any) -> None:
    """Keep shutdown/status probes safe without constructing optional players."""
    for name in (
        "_radio_favorites",
        "_radio_history",
        "_radio_title_timer",
        "_radio_controller",
        "_radio_recording_settings",
        "_radio_recorder",
        "_radio_scheduler",
        "_radio_wake_watcher",
        "_radio_last_seen_timer",
    ):
        setattr(host, name, None)
    if getattr(host, "_podcast_controller", None) is None:
        host._spotify_session = None
    host._radio_history_key = ""
    host._radio_track_title = ""
    host._radio_track_source = ""
    host._radio_fallback_tried = ""
    host._radio_ever_played = False
    host._radio_runtime_initialized = False
    host._radio_runtime_initializing = False
    host._radio_runtime_failed = False
    host._radio_automatic_generation = 0
    host._radio_automatic_start_queued = False
    host._radio_automatic_started = False
    host._radio_automatic_paused = True
