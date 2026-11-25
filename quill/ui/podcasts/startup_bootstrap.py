"""Podcast controller bootstrap for QUILL's profile-gated media runtime."""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir

_RUNTIME_ATTRS = (
    "_podcast_library",
    "_podcast_manager_dialog",
    "_podcast_ever_active",
    "_podcast_current_chapters",
    "_podcast_chapters_key",
    "_podcast_history",
    "_podcast_history_key",
    "_spotify_session",
    "_podcast_quick_actions",
    "_podcast_stop_after_episode",
    "_podcast_stats_key",
    "_podcast_stats_seconds",
    "_podcast_stats_speed",
    "_podcast_chapter_skip",
    "_podcast_controller",
    "_podcast_check_monitor",
    "_podcast_download_queue",
    "_podcast_cache_queue",
    "_podcast_cache_item_id",
    "_podcast_cache_key",
    "_podcast_runtime_initialized",
    "_podcast_runtime_initializing",
    "_podcast_runtime_failed",
    "_podcast_automatic_generation",
    "_podcast_automatic_start_queued",
    "_podcast_automatic_started",
    "_podcast_automatic_paused",
)


def initialize_podcasts(host: Any, *, defer_library_load: bool = False) -> None:
    """Build Podcasts once when enabled, otherwise keep safe passive state."""
    if getattr(host, "_podcast_runtime_initializing", False):
        return
    requested = podcast_feature_requested(host)
    if not requested:
        if getattr(host, "_podcast_controller", None) is None:
            _leave_passive(host)
        else:
            pause_podcast_automatic(host)
        return
    if getattr(host, "_podcast_controller", None) is not None:
        host._podcast_runtime_initializing = True
        try:
            resume_podcast_automatic(host)
        except Exception:
            host._podcast_runtime_initialized = False
            host._podcast_runtime_failed = True
            raise
        else:
            host._podcast_runtime_initialized = True
            host._podcast_runtime_failed = False
        finally:
            host._podcast_runtime_initializing = False
        return
    snapshot = _snapshot(host)
    host._podcast_runtime_initializing = True
    try:
        _build_podcasts(host, defer_library_load=defer_library_load)
        resume_podcast_automatic(host)
    except Exception:
        rollback_podcasts(host, snapshot)
        host._podcast_runtime_failed = True
        raise
    else:
        host._podcast_runtime_initialized = True
        host._podcast_runtime_failed = False
    finally:
        host._podcast_runtime_initializing = False


def podcast_feature_requested(host: Any) -> bool:
    """Feature/profile state, independent of an earlier runtime failure."""
    locks = getattr(host, "_feature_locks", None)
    if locks is not None and locks.is_locked("core.podcasts"):
        return False
    features = getattr(host, "features", None)
    return True if features is None else bool(features.is_enabled("core.podcasts"))


def _build_podcasts(host: Any, *, defer_library_load: bool) -> None:
    from quill.core.podcasts import history as podcast_history
    from quill.core.podcasts.subscriptions import PodcastLibrary, load_library
    from quill.ui.podcasts.finish_bookkeeping import on_left_finished
    from quill.ui.podcasts.player_controller import PodcastPlayerController

    host._podcast_library = PodcastLibrary() if defer_library_load else load_library(app_data_dir())
    from quill.ui.podcasts.launch_catchup import catch_up_with_radio

    if not defer_library_load:
        try:
            catch_up_with_radio(host._podcast_library)
        except Exception:
            host._wx.CallAfter(
                host._announce,
                "The Quill Radio listening handoff could not be applied. "
                "Your podcast library is still available.",
            )
    host._podcast_manager_dialog = None
    host._podcast_ever_active = False
    host._podcast_current_chapters = []
    host._podcast_chapters_key = None
    host._podcast_history = podcast_history.load_history(app_data_dir())
    host._podcast_history_key = ("", "")
    from quill.core.spotify.session import SpotifySession

    host._spotify_session = SpotifySession()
    host._init_podcast_session()
    host._podcast_controller = PodcastPlayerController(
        host.frame,
        on_state_changed=host._on_podcast_state_changed,
        on_episode_finished=host._on_podcast_episode_finished,
        on_position_checkpoint=host._on_podcast_position_checkpoint,
        on_left_finished=lambda show_id, guid: on_left_finished(host, show_id, guid),
        before_play=host._stop_radio_before_podcast,
        on_enhance_error=host._on_podcast_enhance_error,
        spotify_token_provider=host._spotify_session.access_token,
        on_second_tick=host._podcast_second_tick,
        local_fallback=host._podcast_local_fallback,
        output_device=host._podcast_library.settings.output_device,
    )
    settings = host._podcast_library.settings
    host._podcast_controller.set_enhancement(
        bass_db=settings.eq_bass_db,
        mid_db=settings.eq_mid_db,
        treble_db=settings.eq_treble_db,
        compressor_enabled=settings.compressor(),
        smart_speed_enabled=settings.smart_speed_enabled,
        channel_mode=settings.channel_mode,
    )
    host._podcast_check_monitor = _new_check_monitor(host)
    host._init_podcast_transfers()


def _new_check_monitor(host: Any) -> Any:
    from quill.ui.podcasts.check_monitor import PodcastCheckMonitor
    from quill.ui.podcasts.new_feed_check import check_start_failed

    return PodcastCheckMonitor(
        host.frame,
        settings_provider=lambda: (
            getattr(host, "settings", None) or getattr(host, "_podcast_history", None)
        ),
        library_provider=lambda: host._podcast_library,
        refresh_show=host.refresh_podcast_feed,
        safe_mode=host._safe_mode,
        feature_enabled=lambda: host._feature_enabled("core.podcasts"),
        on_refresh_error=lambda show_id, _error: check_start_failed(host, show_id),
        library_changed=host._save_podcast_library,
    )


def resume_podcast_automatic(host: Any) -> None:
    """Resume only stopped automatic Podcast pieces after TLS is ready."""
    from quill.ui.startup_launch import defer_after_ssl_trust

    if not podcast_feature_requested(host):
        pause_podcast_automatic(host)
        return
    if getattr(host, "_podcast_library_loading", False):
        return
    if getattr(host, "_podcast_check_monitor", None) is None:
        host._podcast_check_monitor = _new_check_monitor(host)
    host._podcast_automatic_paused = False
    if getattr(host, "_podcast_automatic_start_queued", False) or getattr(
        host, "_podcast_automatic_started", False
    ):
        return
    generation = int(getattr(host, "_podcast_automatic_generation", 0))
    host._podcast_automatic_start_queued = True

    def failed(label: str) -> None:
        if generation == int(getattr(host, "_podcast_automatic_generation", 0)):
            host._podcast_automatic_start_queued = False
            host._podcast_automatic_started = False
            host._podcast_runtime_initialized = False
            host._podcast_runtime_failed = True
        report = getattr(host, "_report_startup_task_failure", None)
        if callable(report):
            report(label)

    try:
        defer_after_ssl_trust(
            host._wx,
            (
                (
                    "podcast automatic startup",
                    lambda: _start_podcast_automatic(host, generation),
                ),
            ),
            on_failure=failed,
        )
    except Exception:
        host._podcast_automatic_start_queued = False
        raise


def _start_podcast_automatic(host: Any, generation: int) -> None:
    if generation != int(getattr(host, "_podcast_automatic_generation", 0)):
        return
    host._podcast_automatic_start_queued = False
    if not podcast_feature_requested(host):
        return
    if getattr(host, "_podcast_automatic_started", False):
        return
    try:
        monitor = host._podcast_check_monitor
        monitor.apply()
        host.podcast_run_maintenance(announce=False)
    except Exception:
        monitor = getattr(host, "_podcast_check_monitor", None)
        shutdown = getattr(monitor, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:  # noqa: BLE001 - preserve the startup failure
                pass
        from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

        try:
            shutdown_feed_checks(host)
        except Exception:  # noqa: BLE001 - preserve the startup failure
            pass
        host._podcast_automatic_started = False
        raise
    host._podcast_automatic_started = True
    host._podcast_automatic_paused = False


def pause_podcast_automatic(host: Any) -> None:
    """Stop future feed checks while preserving the live player and library."""
    if getattr(host, "_podcast_automatic_paused", False):
        return
    host._podcast_automatic_paused = True
    host._podcast_automatic_started = False
    host._podcast_automatic_start_queued = False
    host._podcast_automatic_generation = int(getattr(host, "_podcast_automatic_generation", 0)) + 1
    monitor = getattr(host, "_podcast_check_monitor", None)
    cancel = getattr(monitor, "cancel_all", None)
    if callable(cancel):
        try:
            cancel()
        except Exception:  # noqa: BLE001 - feed generation still blocks delivery
            pass
    stop = getattr(monitor, "stop", None)
    if callable(stop):
        try:
            stop()
        except Exception:  # noqa: BLE001 - the feature gate prevents another tick
            pass
    from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

    try:
        shutdown_feed_checks(host)
    except Exception:  # noqa: BLE001 - generation cancellation still protects delivery
        pass


def _snapshot(host: Any) -> dict[str, tuple[bool, Any]]:
    return {name: (hasattr(host, name), getattr(host, name, None)) for name in _RUNTIME_ATTRS}


def rollback_podcasts(host: Any, snapshot: dict[str, tuple[bool, Any]]) -> None:
    """Stop and discard everything created by a failed first Podcast build."""
    from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

    try:
        shutdown_feed_checks(host)
    except Exception:  # noqa: BLE001 - rollback must still restore every reference
        pass
    for name in (
        "_podcast_check_monitor",
        "_podcast_controller",
        "_podcast_download_queue",
        "_podcast_cache_queue",
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
    created_download = not snapshot.get("_podcast_download_queue", (False, None))[0]
    created_cache = not snapshot.get("_podcast_cache_queue", (False, None))[0]
    created_queues = created_download and created_cache
    if created_queues and (
        getattr(host, "_podcast_download_queue", None) is not None
        or getattr(host, "_podcast_cache_queue", None) is not None
    ):
        from quill.core.podcasts import queue_events

        queue_events.set_listener(None)
    for name, (existed, value) in snapshot.items():
        if existed:
            setattr(host, name, value)
        elif hasattr(host, name):
            delattr(host, name)
    host._podcast_runtime_initialized = False
    host._podcast_runtime_initializing = False


def _leave_passive(host: Any) -> None:
    host._podcast_library = None
    host._podcast_manager_dialog = None
    host._podcast_ever_active = False
    host._podcast_current_chapters = []
    host._podcast_chapters_key = None
    host._podcast_history = None
    host._podcast_history_key = ("", "")
    if getattr(host, "_radio_controller", None) is None:
        host._spotify_session = None
    host._podcast_controller = None
    host._podcast_check_monitor = None
    host._podcast_download_queue = None
    host._podcast_cache_queue = None
    host._podcast_quick_actions = None
    host._podcast_runtime_initialized = False
    host._podcast_runtime_initializing = False
    host._podcast_runtime_failed = False
    host._podcast_automatic_generation = 0
    host._podcast_automatic_start_queued = False
    host._podcast_automatic_started = False
    host._podcast_automatic_paused = True
