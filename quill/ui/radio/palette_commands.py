"""The radio command-palette registrations, in one table.

Extracted from ``main_frame_radio`` under GATE-11 (extract, never
rebaseline) when the station-catalog commands arrived. The table is pure
wiring -- command id, spoken title, handler -- and reads better as one page
than as a fifth of the mixin.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import volume_commands


def register_radio_commands(host: Any) -> None:
    for command_id, title, handler in (
        ("radio.browse", "Internet Radio: Browse Stations...", host.open_internet_radio),
        (
            "radio.browse_sources",
            "Internet Radio: Choose Browse Sources...",
            host.radio_browse_sources_visibility,
        ),
        (
            "radio.download_preferences",
            "Internet Radio: Download Preferences...",
            host.radio_download_preferences,
        ),
        (
            "radio.update_catalog",
            "Internet Radio: Update Station Catalog",
            host.radio_update_catalog,
        ),
        (
            "radio.catalog_status",
            "Internet Radio: Station Catalog Status...",
            host.radio_catalog_status,
        ),
        ("radio.play_pause", "Internet Radio: Play/Pause", host.radio_toggle_play_pause),
        ("radio.stop", "Internet Radio: Stop", host.radio_stop),
        ("radio.mute_toggle", "Internet Radio: Mute/Unmute", host.radio_mute_toggle),
        ("radio.volume_up", "Internet Radio: Volume Up", host.radio_volume_up),
        ("radio.volume_down", "Internet Radio: Volume Down", host.radio_volume_down),
        (
            "radio.add_custom_station",
            "Internet Radio: Add Custom Station...",
            lambda: host._radio_open_add_custom(None),
        ),
        (
            "radio.find_streams",
            "Internet Radio: Find Streams from a Website...",
            host._radio_open_link_finder,
        ),
        (
            "radio.manage_favorites",
            "Internet Radio: Manage Favorites...",
            host.open_manage_radio_favorites,
        ),
        (
            "radio.play_last",
            "Internet Radio: Play Last Station",
            host.radio_play_last,
        ),
        (
            "radio.whats_playing",
            "Internet Radio: What's Playing?",
            host.radio_whats_playing,
        ),
        (
            "radio.whats_playing_details",
            "Internet Radio: What's Playing - Review and Copy...",
            host.radio_whats_playing_details,
        ),
        (
            "radio.copy_whats_playing",
            "Internet Radio: Copy What's Playing",
            host.radio_copy_whats_playing,
        ),
        (
            "radio.add_youtube_link",
            "Internet Radio: Add YouTube Link...",
            host.radio_add_youtube_link,
        ),
        (
            "radio.add_youtube_playlist",
            "Internet Radio: Add from YouTube Playlist...",
            host.radio_add_youtube_playlist,
        ),
        (
            "radio.import_youtube_subscriptions",
            "Internet Radio: Import YouTube Subscriptions...",
            host.radio_import_youtube_subscriptions,
        ),
        (
            "radio.song_history",
            "Internet Radio: Song History...",
            host.radio_song_history,
        ),
        (
            "radio.toggle_global_volume",
            volume_commands.command_title(host),
            host.radio_toggle_global_volume,
        ),
        (
            "radio.forget_station_volumes",
            "Internet Radio: Forget Every Station's Own Volume...",
            host.radio_forget_station_volumes,
        ),
        (
            "radio.toggle_title_announcements",
            host._radio_title_announce_command_title(),
            host.radio_toggle_title_announcements,
        ),
        (
            "radio.rewind",
            "Internet Radio: Rewind 30 Seconds",
            host.radio_rewind,
        ),
        (
            "radio.forward",
            "Internet Radio: Forward 30 Seconds",
            host.radio_forward,
        ),
        (
            "radio.jump_to_live",
            "Internet Radio: Back to Live",
            host.radio_jump_to_live,
        ),
        (
            "radio.volume_boost",
            "Internet Radio: Volume Boost On/Off",
            host.radio_toggle_volume_boost,
        ),
        (
            "radio.sound_enhancements",
            "Internet Radio: Sound Enhancements...",
            host.open_sound_enhancements,
        ),
        (
            "media.sound_enhancements",
            "Media: Sound Enhancements...",
            host.open_media_sound_enhancements,
        ),
        (
            "radio.record_toggle",
            "Internet Radio: Record Now / Stop Recording",
            host.radio_record_toggle,
        ),
        (
            "radio.schedule_recording",
            "Internet Radio: Schedule Recording...",
            host._radio_open_schedule_recording,
        ),
        (
            "radio.recording_settings",
            "Internet Radio: Recording Settings...",
            host._radio_open_recording_settings,
        ),
        (
            "radio.recordings",
            "Internet Radio: Recordings...",
            host.open_radio_recordings,
        ),
        (
            "radio.record_station",
            "Internet Radio: Record Station...",
            host.open_record_station_dialog,
        ),
        (
            "radio.stop_all_recordings",
            "Internet Radio: Stop All Recordings",
            host.radio_stop_all_recordings,
        ),
        (
            "radio.wake_timer",
            "Internet Radio: Wake-Up Timer...",
            host.open_wake_timer_dialog,
        ),
    ):
        host.commands.try_register(
            command_id, title, handler, host._binding_for(command_id), feature_id="core.radio"
        )
    # Quick-play the first ten favorites (default Ctrl+Alt+Shift+1..0, rebindable).
    for slot in range(1, 11):
        cmd = f"radio.play_favorite_{slot}"
        host.commands.try_register(
            cmd,
            f"Internet Radio: Play Favorite {slot}",
            lambda s=slot: host._radio_play_favorite_slot(s),
            host._binding_for(cmd),
            feature_id="core.radio",
        )
    # Spotify commands live behind future.spotify (experimental), so they
    # disappear when the listener turns that feature off.
    for command_id, title, handler in (
        ("spotify.connect", "Spotify: Connect to Spotify...", host.open_spotify_connect),
        ("spotify.browse", "Spotify: Browse Spotify...", host.open_spotify_browse),
    ):
        host.commands.try_register(
            command_id,
            title,
            handler,
            host._binding_for(command_id),
            feature_id="future.spotify",
        )
