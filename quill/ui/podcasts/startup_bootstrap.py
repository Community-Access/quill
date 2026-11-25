"""Podcast controller bootstrap for QUILL's profile-gated media runtime."""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir


def initialize_podcasts(host: Any, *, defer_library_load: bool = False) -> None:
    """Build Podcasts once when enabled, otherwise keep safe passive state."""
    if getattr(host, "_podcast_runtime_initialized", False):
        return
    if getattr(host, "_podcast_runtime_initializing", False):
        return
    if getattr(host, "_podcast_controller", None) is not None:
        host._podcast_runtime_initialized = True
        return
    if not host._feature_enabled("core.podcasts"):
        _leave_passive(host)
        return
    host._podcast_runtime_initializing = True
    try:
        _build_podcasts(host, defer_library_load=defer_library_load)
        host._podcast_runtime_initialized = True
    finally:
        host._podcast_runtime_initializing = False


def _build_podcasts(host: Any, *, defer_library_load: bool) -> None:
    from quill.core.podcasts import history as podcast_history
    from quill.core.podcasts.subscriptions import PodcastLibrary, load_library
    from quill.ui.podcasts.check_monitor import PodcastCheckMonitor
    from quill.ui.podcasts.finish_bookkeeping import on_left_finished
    from quill.ui.podcasts.new_feed_check import check_start_failed
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
    host._init_podcast_transfers()
    host._podcast_check_monitor = PodcastCheckMonitor(
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
    if not defer_library_load:
        host._podcast_check_monitor.apply()
        host.podcast_run_maintenance(announce=False)


def _leave_passive(host: Any) -> None:
    host._podcast_library = None
    host._podcast_manager_dialog = None
    host._podcast_ever_active = False
    host._podcast_current_chapters = []
    host._podcast_chapters_key = None
    host._podcast_history = None
    host._podcast_history_key = ("", "")
    host._spotify_session = None
    host._podcast_controller = None
    host._podcast_check_monitor = None
    host._podcast_download_queue = None
    host._podcast_cache_queue = None
    host._podcast_quick_actions = None
    host._podcast_runtime_initialized = False
    host._podcast_runtime_initializing = False
