"""The radio command-palette registrations, in one table.

Extracted from ``main_frame_radio`` under GATE-11 (extract, never
rebaseline) when the station-catalog commands arrived. The table is pure
wiring -- command id, spoken title, handler -- and reads better as one page
than as a fifth of the mixin.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import browse_door, volume_commands


def _open_statistics(host: Any) -> None:
    """How long, on what, in what network -- see ui/radio/stats_dialog."""
    from quill.ui.radio.stats_dialog import open_for_host

    open_for_host(host)


def _folder_step(host: Any, *, forward: bool) -> None:
    """Walk the folder queue Play All in Folder left behind."""
    from quill.ui.radio import favorite_folder_actions

    controller = getattr(host, "_radio_controller", None)
    if forward:
        favorite_folder_actions.next_in_folder(host, controller)
    else:
        favorite_folder_actions.previous_in_folder(host, controller)


def _youtube(host: Any, verb: str) -> None:
    """Search YouTube... or Read Comments... for what is playing."""
    if verb == "search":
        from quill.ui.radio import youtube_search_ui

        youtube_search_ui.search_youtube(host)
        return
    from quill.ui.radio import youtube_comments_ui

    youtube_comments_ui.open_for_playing(host)


def _youtube_more(host: Any, verb: str) -> None:
    """Video > YouTube's four commands (radio_youtube_video_menu)."""
    from quill.ui.radio import (
        youtube_live_chat_ui,
        youtube_search_filters_ui,
        youtube_sponsorblock_ui,
        youtube_video_window,
    )

    {
        "chat": youtube_live_chat_ui.open_for_playing,
        "video": youtube_video_window.open_for_playing,
        "sponsorblock": youtube_sponsorblock_ui.open_settings,
        "filters": youtube_search_filters_ui.search_with_filters,
    }[verb](host)


def _edit_playing_tags(host: Any) -> None:
    """Edit Station Tags... for the station on air -- see station_tags_dialog."""
    from quill.ui.radio.station_tags_dialog import edit_playing

    edit_playing(host)


def register_radio_commands(host: Any) -> None:
    for command_id, title, handler in (
        (
            "radio.browse",
            "Internet Radio: Browse Stations...",
            lambda: browse_door.open_browse(host),
        ),
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
        # Playing a favorites folder leaves a queue behind, and a queue with no
        # way to step through it is a queue nobody can use. Palette commands
        # rather than menu items on purpose: every letter and Shift+letter of
        # the shared radio chord is already assigned, and an item advertising a
        # key that does nothing is worse than one with no key at all.
        (
            "radio.statistics",
            "Internet Radio: Listening Statistics...",
            lambda: _open_statistics(host),
        ),
        (
            "radio.folder_next",
            "Internet Radio: Next Station in Folder",
            lambda: _folder_step(host, forward=True),
        ),
        (
            "radio.folder_previous",
            "Internet Radio: Previous Station in Folder",
            lambda: _folder_step(host, forward=False),
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
            "radio.search_youtube",
            "Internet Radio: Search YouTube...",
            lambda: _youtube(host, "search"),
        ),
        (
            "radio.youtube_comments",
            "Internet Radio: Read YouTube Comments...",
            lambda: _youtube(host, "comments"),
        ),
        (
            "radio.youtube_live_chat",
            "Internet Radio: YouTube Live Chat...",
            lambda: _youtube_more(host, "chat"),
        ),
        (
            "radio.youtube_video",
            "Internet Radio: YouTube Video Details...",
            lambda: _youtube_more(host, "video"),
        ),
        (
            "radio.youtube_sponsorblock",
            "Internet Radio: Skip Sponsor Segments in YouTube Videos...",
            lambda: _youtube_more(host, "sponsorblock"),
        ),
        (
            "radio.youtube_search_filters",
            "Internet Radio: Search YouTube with Filters...",
            lambda: _youtube_more(host, "filters"),
        ),
        (
            "radio.song_history",
            "Internet Radio: Song History...",
            host.radio_song_history,
        ),
        (
            # Your own searchable tags on what is on air (station_tags_dialog).
            "radio.edit_station_tags",
            "Internet Radio: Edit Tags for the Playing Station...",
            lambda: _edit_playing_tags(host),
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
        (
            "radio.tutorials",
            "Internet Radio: Tutorials...",
            host.open_radio_tutorials,
        ),
    ):
        host.commands.try_register(
            command_id, title, handler, host._binding_for(command_id), feature_id="core.radio"
        )
    # Quick-play the first ten favorites. No editor chord since 2026-09-16 --
    # numbered tray paste took Ctrl+Alt+Shift+digit, and in Quill Radio the ten
    # keys live on Alt+1..0 (APP_KEYMAPS). They stay registered so the palette
    # reaches them and anybody can bind them back.
    for slot in range(1, 11):
        cmd = f"radio.play_favorite_{slot}"
        host.commands.try_register(
            cmd,
            f"Internet Radio: Play Favorite {slot}",
            lambda s=slot: host._radio_play_favorite_slot(s),
            host._binding_for(cmd),
            feature_id="core.radio",
        )
    host.commands.try_register(
        "radio.play_favorite",
        "Internet Radio: Play Favorite...",
        host.open_radio_favorite_chooser,
        host._binding_for("radio.play_favorite"),
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

    # ...then the shared transport table, filling only the gaps this app left:
    # the palette could change a setting and could not pause what was playing
    # (2026-08-18). Last on purpose -- register_commands skips any verb this
    # app already listed, so it has to see the table above first.
    # Local Media: the window, adding files, and the playing playlist's steps.
    from quill.ui.radio import local_media_commands, transport_keys

    local_media_commands.register(host)
    transport_keys.register_commands(host, prefix="radio")
