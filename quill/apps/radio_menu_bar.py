"""Quill Radio's menu bar, built in one place.

Command registration and menu rendering, one lifetime: the bar is built at
start-up and rebuilt when a mode or feature changes. Moved whole out of
``RadioAppFrame`` under qc.md F-08 (2026-10-03); the host contract is
unchanged.
"""

from __future__ import annotations

import wx

from quill.apps import radio_audio_menu, radio_go_to


class RadioMenuBarMixin:
    """Radio's menu bar; mixed into ``RadioAppFrame``."""

    def _build_menu_bar(self) -> None:
        # Module constants stay in radio.py (the app version is GATE-APPVER's).
        from quill.apps.radio import (
            _FAVORITES_SORT_LABELS,
            _FAVORITES_SORT_VALUES,
            _MATCH_EDITION,
            _REPO,
            _TEXT_SIZE_SCALES,
            _TITLE,
            _VERSION,
        )

        menu_bar = wx.MenuBar()

        station_menu = wx.Menu()
        # Browse and Search are distinct: Browse Stations opens the unified
        # source tree (a delightful, search-free "wander the sources" view);
        # Search Stations opens the field-based dialog focused on the box.
        browse_id, search_id, add_id, find_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        station_menu.Append(browse_id, self._menu_label("&Browse Stations...", "radio.browse"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_browse_stations(), id=browse_id)
        local_id = wx.NewIdRef()  # no access letter: D is Download Preferences' (GATE-14)
        station_menu.Append(local_id, self._menu_label("Local Media...", "radio.local_media"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_local_media(), id=local_id)
        rrs_update_id = wx.NewIdRef()
        station_menu.Append(rrs_update_id, "Update Radio Reading &Services...\tCtrl+Alt+F10")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.update_reading_services_directory(),
            id=rrs_update_id,
        )
        station_menu.Append(search_id, "S&earch Stations...\tCtrl+F")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_internet_radio(focus_search=True), id=search_id
        )
        station_menu.Append(
            add_id, self._menu_label("&Add Custom Station...", "radio.add_custom_station")
        )
        yt_link_id = wx.NewIdRef()
        station_menu.Append(
            yt_link_id, self._menu_label("Add YouTube Lin&k...", "radio.add_youtube_link")
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_add_youtube_link(), id=yt_link_id)
        yt_playlist_id = wx.NewIdRef()
        station_menu.Append(
            yt_playlist_id,
            self._menu_label("Add from &YouTube Playlist...", "radio.add_youtube_playlist"),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_add_youtube_playlist(), id=yt_playlist_id
        )
        yt_subs_id = wx.NewIdRef()
        station_menu.Append(
            yt_subs_id,
            self._menu_label(
                "&Import YouTube Subscriptions...", "radio.import_youtube_subscriptions"
            ),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_import_youtube_subscriptions(), id=yt_subs_id
        )
        # Real-time OAuth sign-in (future.youtube_oauth, locked off in public
        # builds): extracted so this menu build does not grow past GATE-11.
        from quill.apps.radio_youtube_oauth_menu import add_youtube_oauth_menu_items

        add_youtube_oauth_menu_items(self, station_menu, wx)
        # Search YouTube... and Repair YouTube Support... (GATE-11 extraction).
        from quill.apps.radio_youtube_menu import add_youtube_menu_items

        add_youtube_menu_items(self, station_menu, wx)
        station_menu.Append(
            find_id, self._menu_label("&Find Streams from a Website...", "radio.find_streams")
        )
        # Remembered-choice items live in radio_settings_menu (GATE-11); the
        # ids come back for pinning.
        from quill.apps.radio_settings_menu import build_download_prefs_item, build_settings_items

        sources_id, browse_sources_id, update_catalog_id = build_settings_items(
            self, station_menu, wx
        )
        self._keep_menu_ids(browse_sources_id, update_catalog_id)
        # Spotify (future.spotify) is experimental: the ids are always created
        # (so _keep_menu_ids can pin them) but the items appear only while the
        # feature is on and Safe Mode is off. They live on Station, not Help,
        # because Spotify is somewhere you get stations from -- the same kind of
        # thing as Browse and Search, which is where someone looks for it.
        spotify_connect_id, spotify_browse_id = wx.NewIdRef(), wx.NewIdRef()
        if self.features.is_enabled("future.spotify") and not self._safe_mode:
            station_menu.AppendSeparator()
            station_menu.Append(spotify_connect_id, "Connect to Spotify...\tCtrl+Alt+P")
            station_menu.Append(spotify_browse_id, "Browse Spotify...\tCtrl+Alt+O")
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_connect(), id=spotify_connect_id
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_browse(), id=spotify_browse_id
            )
        manage_id = wx.NewIdRef()
        station_menu.Append(
            manage_id, self._menu_label("&Manage Favorites...", "radio.manage_favorites")
        )
        # Saving what is playing, which until now existed only as a button
        # on the main window. It cannot live in the favorites tree context
        # menu instead: the station it acts on is usually one you found in
        # Browse and that is not in the tree at all.
        self._fav_toggle_menu_id = wx.NewIdRef()
        station_menu.Append(
            self._fav_toggle_menu_id,
            self._menu_label("A&dd Playing Station to Favorites", "radio.toggle_playing_favorite"),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._on_favorite_toggle(), id=self._fav_toggle_menu_id
        )
        # Put the actions you use at the top of every row menu, and choose what
        # Enter does. Wiring lives in ui/radio/quick_actions_command (at budget).
        from quill.ui.radio.quick_actions_command import open_quick_actions

        quick_id = wx.NewIdRef()
        station_menu.Append(quick_id, "&Quick Actions...\tCtrl+Alt+Q")
        self.frame.Bind(wx.EVT_MENU, lambda _e: open_quick_actions(self), id=quick_id)
        new_folder_id = wx.NewIdRef()
        station_menu.Append(new_folder_id, "New F&older...\tCtrl+Shift+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._on_new_folder(), id=new_folder_id)
        import_id = wx.NewIdRef()
        station_menu.Append(import_id, "Im&port Stations from Playlist...\tCtrl+I")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_stations_from_playlist(), id=import_id)
        # #1249: export favorites to an M3U playlist. Thin wiring lives in
        # playlist_export_ui (radio.py is at budget).
        from quill.ui.radio.playlist_export_ui import export_favorites_to_playlist

        export_id = wx.NewIdRef()
        station_menu.Append(export_id, "E&xport Favorites to Playlist...\tCtrl+Shift+X")
        self.frame.Bind(wx.EVT_MENU, lambda _e: export_favorites_to_playlist(self), id=export_id)
        # #1193: move your stations/settings/recordings to a new device or recover
        # after a reinstall. Thin wiring lives in backup_ui (radio.py is at budget).
        from quill.ui.radio.backup_ui import back_up_radio_data, restore_radio_data

        backup_id, restore_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(backup_id, "Ba&ck Up Stations and Settings...\tCtrl+Shift+U")
        # Ctrl+Shift+R went to Recordings on 2026-08-21 (which gave up Ctrl+G to
        # Go To): frequency wins the shorter chord, and nobody restores a backup
        # by muscle memory.
        station_menu.Append(restore_id, "&Restore from Backup...\tCtrl+Alt+Shift+W")
        self.frame.Bind(wx.EVT_MENU, lambda _e: back_up_radio_data(self), id=backup_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: restore_radio_data(self), id=restore_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_add_custom(None), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_link_finder(), id=find_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_manage_radio_favorites(), id=manage_id)
        station_menu.AppendSeparator()
        play_last_id = wx.NewIdRef()
        station_menu.Append(play_last_id, self._menu_label("Play &Last Station", "radio.play_last"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_play_last(), id=play_last_id)
        # ACB Media and NFB Radio no longer nest here: both are bundled source
        # categories in Browse Stations already, so the flat menu copies only
        # duplicated them -- and drifted out of date. They live in Browse now.
        # Recently Played and Favorites stay; Recently Played refreshes each
        # time the Station menu opens (see _on_station_menu_open) so a station
        # you just played shows without relaunching.
        self._station_menu = station_menu
        self._append_radio_recent_submenu(station_menu)
        self._append_radio_favorites_submenu(station_menu)
        # Bind the just-in-time Recently-Played refresh once: _build_menu_bar is
        # re-callable (a keymap edit rebuilds it), and EVT_MENU_OPEN is a
        # frame-level bind that would otherwise stack a new handler each rebuild.
        if not getattr(self, "_station_menu_open_bound", False):
            self.frame.Bind(wx.EVT_MENU_OPEN, self._on_station_menu_open)
            self._station_menu_open_bound = True
        self._resume_menu_item_id = wx.NewIdRef()
        station_menu.AppendCheckItem(
            self._resume_menu_item_id, "Resume Last Station on Lau&nch\tCtrl+Alt+L"
        )
        station_menu.Check(self._resume_menu_item_id, self._radio_history.resume_on_launch)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_resume_on_launch(), id=self._resume_menu_item_id
        )
        from quill.platform.windows import radio_startup

        self._startup_menu_item_id = wx.NewIdRef()
        station_menu.AppendCheckItem(
            self._startup_menu_item_id, "Start Quill Radio with &Windows\tCtrl+Alt+W"
        )
        station_menu.Check(self._startup_menu_item_id, radio_startup.is_launch_at_startup_enabled())
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_launch_at_startup(), id=self._startup_menu_item_id
        )
        (download_prefs_id,) = build_download_prefs_item(self, station_menu, wx)
        self._keep_menu_ids(download_prefs_id)
        prefs_id = wx.NewIdRef()
        station_menu.Append(prefs_id, "Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(tray_id, "Send to &Tray\tCtrl+W")
        station_menu.Append(exit_id, "Exit\tCtrl+Q")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        # Explicit Exit must quit for real, not minimize-to-tray (#1193).
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
        menu_bar.Append(station_menu, "&Station")

        playback_menu = wx.Menu()
        # 39 items answering three unrelated questions -- what the transport is
        # doing, how the audio sounds, what to do with video -- split 2026-08-21
        # into 17 / 11 / 8. No key changes: the accelerator gate enforces
        # uniqueness across the whole menu bar, not per menu, so moving an item
        # costs relearning where to look and nothing in muscle memory. View is
        # built here and inserted further down, because Listening Statistics is
        # a report about past listening rather than a control over present
        # listening and belongs there with the other reports.
        audio_menu = wx.Menu()
        video_menu = wx.Menu()
        view_menu = wx.Menu()
        self._now_playing_item_id = wx.NewIdRef()
        playback_menu.Append(self._now_playing_item_id, "Radio: stopped")
        playback_menu.Enable(self._now_playing_item_id, False)
        playback_menu.AppendSeparator()
        # Two rows, adjacent: one that starts and ends (Play, then Stop) and
        # one that pauses. Built and relabelled in radio_transport_menu.
        from quill.apps import radio_transport_menu

        radio_transport_menu.append_items(self, playback_menu, wx)
        mute_id, vol_up_id, vol_down_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        audio_menu.Append(mute_id, self._menu_label("&Mute/Unmute", "radio.mute_toggle"))
        audio_menu.Append(vol_up_id, self._menu_label("Volume &Up", "radio.volume_up"))
        audio_menu.Append(vol_down_id, self._menu_label("Volume &Down", "radio.volume_down"))
        self._volume_boost_item_id = wx.NewIdRef()
        audio_menu.AppendCheckItem(self._volume_boost_item_id, "Volume &Boost\tCtrl+Shift+B")
        audio_menu.Check(self._volume_boost_item_id, self._radio_history.volume_boost)
        # #1253: pick the audio output device (sound card) with a shortcut, without
        # opening full Preferences. Thin wiring lives in output_device_ui.
        from quill.ui.radio.output_device_ui import choose_output_device

        output_device_id = wx.NewIdRef()
        audio_menu.Append(output_device_id, "&Output Device...\tCtrl+Shift+D")
        self.frame.Bind(wx.EVT_MENU, lambda _e: choose_output_device(self), id=output_device_id)
        playback_menu.AppendSeparator()
        # Live DVR (mpv engine): pause is the Play/Stop item; these move
        # within the buffered live window.
        rewind_id, forward_id, live_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        playback_menu.Append(rewind_id, self._menu_label("Re&wind 30 Seconds", "radio.rewind"))
        playback_menu.Append(forward_id, self._menu_label("&Forward 30 Seconds", "radio.forward"))
        playback_menu.Append(live_id, self._menu_label("Back to &Live", "radio.jump_to_live"))
        # Video: a finished YouTube video has a timeline, so it can be
        # scrubbed, sped up, navigated by chapter and read as a transcript --
        # none of which a live broadcast can do, and every one of which says so
        # out loud rather than doing nothing. Wiring lives in
        # quill/apps/radio_video_menu.py; radio.py is at its GATE-11 budget.
        from quill.apps.radio_playback_extras import build_playback_extras

        # Pinned as a group rather than unpacked: the helper owns which items
        # exist, and a fixed-length unpack here would break every time it grew.
        video_menu_ids = build_playback_extras(
            self, playback_menu, wx, audio_menu, video_menu, view_menu
        )
        playback_menu.AppendSeparator()
        whats_playing_id = wx.NewIdRef()
        # Go to Player summons the player panel over whatever window you are
        # in. transport_keys.install() carries it into the browse tree, the
        # managers and the rest; the main window has no transport install, so
        # until 2026-08-21 Ctrl+Shift+G worked in every window EXCEPT this
        # one -- the one most people try first. A menu item is the right home
        # for it here: it binds the accelerator on the frame and puts the key
        # in a label, which is how every other key in this app is found.
        go_to_player_id = wx.NewIdRef()
        playback_menu.Append(go_to_player_id, "&Go to Player	Ctrl+Shift+G")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_go_to_player(), id=go_to_player_id)
        playback_menu.Append(whats_playing_id, "W&hat's Playing?\tCtrl+T")
        # Ctrl+Shift+H is free in the standalone app; inside full QUILL the same
        # command ships unbound because there Ctrl+Shift+H is Replace All.
        song_history_id = wx.NewIdRef()
        playback_menu.Append(
            song_history_id, self._menu_label("&Song History...", "radio.song_history")
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_song_history(), id=song_history_id)
        forget_volumes_id = radio_audio_menu.build_preferences(self, audio_menu, wx)
        sleep_id = wx.NewIdRef()
        playback_menu.Append(sleep_id, "Sleep &Timer...\tCtrl+Shift+Z")
        wake_id = wx.NewIdRef()
        playback_menu.Append(wake_id, self._menu_label("Wake-U&p Timer...", "radio.wake_timer"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_wake_timer_dialog(), id=wake_id)
        from quill.ui.radio import bookmarks_wiring as bookmarks

        bookmarks.append_menu_item(self, playback_menu, wx)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=mute_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_up(), id=vol_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_down(), id=vol_down_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._on_volume_boost_menu(), id=self._volume_boost_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_rewind(), id=rewind_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_forward(), id=forward_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_jump_to_live(), id=live_id)
        # Ctrl+T opens the reviewable Now Playing window (fetch-and-speak fallback).
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_whats_playing_details(), id=whats_playing_id
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.radio_toggle_title_announcements(),
            id=self._announce_titles_item_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=sleep_id)
        playback_menu.AppendSeparator()
        enhance_id = wx.NewIdRef()
        audio_menu.Append(
            enhance_id, self._menu_label("Sound &Enhancements...", "radio.sound_enhancements")
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sound_enhancements(), id=enhance_id)
        menu_bar.Append(playback_menu, "&Playback")
        menu_bar.Append(audio_menu, "&Audio")
        # Video is always present, greyed out with nothing to show: a menu that
        # comes and goes changes the shape of a bar navigated by position.
        menu_bar.Append(video_menu, "Vi&deo")

        record_menu = wx.Menu()
        record_id, schedule_id, settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        recordings_id = wx.NewIdRef()
        record_menu.Append(
            record_id, self._menu_label("&Record Now / Stop Recording", "radio.record_toggle")
        )
        record_station_id = wx.NewIdRef()
        record_menu.Append(
            record_station_id, self._menu_label("Record Statio&n...", "radio.record_station")
        )
        stop_all_id = wx.NewIdRef()
        record_menu.Append(
            stop_all_id, self._menu_label("Stop A&ll Recordings", "radio.stop_all_recordings")
        )
        record_menu.Append(
            schedule_id, self._menu_label("&Schedule Recording...", "radio.schedule_recording")
        )
        record_menu.Append(recordings_id, self._menu_label("Recordin&gs...", "radio.recordings"))
        record_menu.Append(
            settings_id, self._menu_label("R&ecording Settings...", "radio.recording_settings")
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=record_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_record_station_dialog(), id=record_station_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_stop_all_recordings(), id=stop_all_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._radio_open_schedule_recording(), id=schedule_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_radio_recordings(), id=recordings_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._radio_open_recording_settings(), id=settings_id
        )
        # Recording is a user-switchable area (View > Customize Features...):
        # when turned off, the whole menu is not built at all. (The Weather
        # menu is gone entirely -- weather lives in the Quill Weather app.)
        if self._app_area_enabled("recording"):
            menu_bar.Append(record_menu, "&Record")

        # The top-level Community menu: "places this community already goes,
        # brought inside the app". The rows it started with are gone (removed
        # from the whole family on 2026-09-30), and the menu
        # now carries only the community surfaces it was renamed for in
        # 2026-08-23 -- Ask QUILL Radio and Use My ChatGPT Subscription, the ACB
        # Media schedule and podcasts, and Community Picks, all appended by
        # radio_launch_tasks.append_calendar_menu. It starts empty here so that
        # helper's leading separator is skipped and the menu opens on a row
        # rather than on a rule.
        from quill.apps.radio_launch_tasks import append_calendar_menu

        community_menu = wx.Menu()
        append_calendar_menu(self, community_menu, wx)
        # No chord in the title (2026-08-25): Alt+C already opens this menu, and
        # the Ctrl+Alt+A it used to advertise is Bookmark This Moment.
        menu_bar.Append(community_menu, "&Community")

        help_menu = wx.Menu()
        palette_id, updates_id, about_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        help_menu.Append(palette_id, self._menu_label("Command &Palette...", "app.command_palette"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_command_palette(), id=palette_id)
        # The Keyboard Shortcuts editor and the Global Hotkeys manager open the
        # same already-accessible dialogs QUILL uses (KeymapEditorMixin /
        # GlobalHotkeysMixin), scoped to this app's own commands.
        shortcuts_id, hotkeys_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(shortcuts_id, "&Keyboard Shortcuts...\tCtrl+Alt+K")
        help_menu.Append(hotkeys_id, "G&lobal Hotkeys...\tCtrl+Alt+G")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_keymap_editor(), id=shortcuts_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_global_hotkeys_manager(), id=hotkeys_id)
        # Undo, Recent Problems, Quiet Hours and Export / Import My Setup:
        # four shared surfaces over shared files, wired once for both apps.
        from quill.ui.support_menu import wire_support_surfaces

        wire_support_surfaces(self, menu_bar, help_menu, wx)
        # The sheet sits beside the editor because they are the two halves of
        # one question: this one answers "what can I press?", the editor answers
        # "I want that somewhere else". Every menu item names its key since 3.0,
        # which fixed discovery *inside* a menu and left "open six menus and
        # arrow to the end of each" as the only way to see them together.
        sheet_id = wx.NewIdRef()
        help_menu.Append(sheet_id, "Keyboard Shortcuts S&heet...\tCtrl+Alt+Shift+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_keyboard_cheat_sheet(), id=sheet_id)
        bug_id = wx.NewIdRef()
        help_menu.Append(bug_id, "&Get Help from Support...\tCtrl+Alt+F2")  # as QUILL Lite
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_app_bug(source_app="Quill Radio", app_version=_VERSION),
            id=bug_id,
        )
        ffmpeg_id = wx.NewIdRef()
        help_menu.Append(ffmpeg_id, "R&epair FFmpeg...\tCtrl+Alt+F")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_ffmpeg_component(), id=ffmpeg_id)
        # Beside Repair FFmpeg: the two media tools both downloads bundle, so
        # these are emergency repair only (named so in 3.0.1). A copy from the
        # thin installer retired in 3.0.0 has neither
        # until upgraded, and a runtime another app laid down can lack them.
        # mpv matters more than FFmpeg -- it is the playback engine, so without
        # it Ogg, Opus and HLS stations do not play at all.
        mpv_id = wx.NewIdRef()
        help_menu.Append(mpv_id, "Repair &mpv Playback Engine...\tCtrl+Alt+M")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_mpv_component(), id=mpv_id)
        from quill.apps import radio_help_docs

        help_menu.AppendSeparator()
        # What Is This?, the tutorials and the four documents: one block, built
        # in apps/radio_help_docs so the keys and the reasoning behind them live
        # next to the code that opens what they open.
        doc_ids = radio_help_docs.install_help_items(self, help_menu, wx)
        help_menu.AppendSeparator()
        help_menu.Append(updates_id, "Check for Up&dates...\tCtrl+Alt+U")
        from quill.ui.updates.shell import append_release_channel_item, installed_app_version

        append_release_channel_item(self, help_menu, "radio", updates_id)  # Alt+H, N
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About Quill Radio\tAlt+F1")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO,
                current_version=installed_app_version("radio"),
                app_key="radio",
                match_edition=_MATCH_EDITION,
            ),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)

        # &View: show/hide the read-only Station Details pane, honored by every
        # surface that has one (Browse Stations, Search Stations).
        show_details_id = wx.NewIdRef()
        view_menu.AppendCheckItem(show_details_id, "Show Station &Details\tCtrl+D")
        view_menu.Check(show_details_id, self._radio_history.show_station_details)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_show_station_details(), id=show_details_id
        )
        self._status_bar_item_id = wx.NewIdRef()
        view_menu.AppendCheckItem(self._status_bar_item_id, "Show Status &Bar\tCtrl+Shift+Alt+B")
        view_menu.Check(self._status_bar_item_id, self._radio_history.show_status_bar)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_show_status_bar(), id=self._status_bar_item_id
        )
        view_menu.AppendSeparator()
        # Sort Favorites: the same setting Preferences carries, surfaced here as
        # radio items so it is one keystroke away and its current value is visible.
        sort_menu = wx.Menu()
        self._sort_item_ids = [wx.NewIdRef() for _ in _FAVORITES_SORT_VALUES]
        # F-keys, not digits (2026-08-17): Ctrl+Alt+Shift+4/5/6 are the
        # quick-play favorites' chords (radio.play_favorite_4..6), which these
        # literals were silently fighting — see SIBLING_APP_ACCELERATORS for
        # the twin conflict and how it was found.
        sort_accels = (
            "\tCtrl+Alt+Shift+F4",
            "\tCtrl+Alt+Shift+F5",
            "\tCtrl+Alt+Shift+F6",
        )
        for item_id, label, value, accel in zip(
            self._sort_item_ids,
            _FAVORITES_SORT_LABELS,
            _FAVORITES_SORT_VALUES,
            sort_accels,
            strict=True,
        ):
            sort_menu.AppendRadioItem(item_id, f"&{label}{accel}")  # A, D, U
            sort_menu.Check(item_id, self._radio_history.favorites_sort == value)
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, v=value: self._set_favorites_sort(v), id=item_id
            )
        view_menu.AppendSubMenu(sort_menu, "Sort &Favorites")
        expand_id, collapse_id = wx.NewIdRef(), wx.NewIdRef()
        view_menu.Append(expand_id, "&Expand All Folders\tCtrl+Alt+E")
        view_menu.Append(collapse_id, "&Collapse All Folders\tCtrl+Alt+Shift+E")
        from quill.apps.radio_favorite_toggle import expand_all_folders as expand_all

        self.frame.Bind(wx.EVT_MENU, lambda _e: expand_all(self, True), id=expand_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: expand_all(self, False), id=collapse_id)
        view_menu.AppendSeparator()
        downloads_id = wx.NewIdRef()
        view_menu.Append(downloads_id, "D&ownloads...	Ctrl+Shift+J")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_download_queue(), id=downloads_id)
        self._keep_menu_ids(downloads_id)
        from quill.apps import radio_settings_menu as menus

        go_to_id = wx.NewIdRef()
        view_menu.Append(go_to_id, self._menu_label("&Go To...", "radio.go_to"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: radio_go_to.open_go_to(self), id=go_to_id)
        catalog_status_id, audio_health_id = menus.build_catalog_status_item(self, view_menu, wx)
        self._keep_menu_ids(go_to_id, catalog_status_id, audio_health_id)
        self._keep_menu_ids(menus.build_choose_columns_item(self, view_menu, wx))
        features_id = wx.NewIdRef()
        view_menu.Append(features_id, "C&ustomize Features...\tCtrl+Alt+C")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_app_features(), id=features_id)
        self._keep_menu_ids(features_id)
        # What the main window shows (main_view): radio items, because it is a
        # choice of exactly one and a checkmark is how a menu says which.
        from quill.ui.radio import main_view_menu

        self._keep_menu_ids(*main_view_menu.append(self, view_menu, wx))
        view_menu.AppendSeparator()
        # Text Size: scale the main window's fonts for low-vision listeners.
        text_menu = wx.Menu()
        self._text_size_item_ids = [wx.NewIdRef() for _ in _TEXT_SIZE_SCALES]
        for item_id, (label, scale) in zip(
            self._text_size_item_ids, _TEXT_SIZE_SCALES, strict=True
        ):
            text_menu.AppendRadioItem(item_id, label)
            text_menu.Check(item_id, abs(self._radio_history.ui_font_scale - scale) < 0.01)
            self.frame.Bind(wx.EVT_MENU, lambda _e, s=scale: self._set_text_size(s), id=item_id)
        view_menu.AppendSubMenu(text_menu, "&Text Size")
        # Insert, not Append: View cannot be *built* until here (Text Size needs the
        # font scale later setup resolves). Index 2: &Edit is already at 1.
        menu_bar.Insert(2, view_menu, "&View")
        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx,
                self.frame,
                self._launch_sibling,
                exclude="radio",
                retain=self._keep_menu_ids,
                # Quill Inkwell is deliberately off Quill Radio's menu for 3.0.
                # It is released elsewhere in the family; a listener opening a
                # radio app has no reason to be offered a text expander, and a
                # menu item that opens one is a promise this release did not
                # mean to make.
                also_exclude=("inkwell",),
            ),
            "&QuillVille",
        )
        # Quillins is held back from the public build for now: the menu appears
        # only in a developer build (QUILL_DEV_BUILD=1), via the unreleased
        # future.quillins_menu flag. The Quillin host itself is untouched --
        # bundled Quillins still load and still contribute -- this hides only the
        # top-level menu, so nothing a Quillin provides stops working.
        if self.features.is_enabled("future.quillins_menu"):
            menu_bar.Append(self._build_quillins_menu(), "Quilli&ns")  # Alt+Q is QuillVille
        menu_bar.Append(help_menu, "&Help")

        # Persistent &Window menu + Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 on the
        # main window; each modeless surface installs the same on its own bar so
        # the numbered traversal reaches every open radio window.
        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        # focus= so Ctrl+Tab into the main window lands on the favorites tree
        # (its default control), not on the bare frame.
        self._windows.register(self.frame, _TITLE, focus=self._focus_initial_control)
        # Pin every menu id for the frame's lifetime (see _keep_menu_ids).
        self._keep_menu_ids(
            sources_id,
            *video_menu_ids,
            yt_subs_id,
            yt_link_id,
            spotify_connect_id,
            spotify_browse_id,
            browse_id,
            rrs_update_id,
            search_id,
            add_id,
            find_id,
            manage_id,
            new_folder_id,
            play_last_id,
            self._resume_menu_item_id,
            self._startup_menu_item_id,
            prefs_id,
            tray_id,
            exit_id,
            self._now_playing_item_id,
            self._play_menu_item_id,
            mute_id,
            vol_up_id,
            vol_down_id,
            self._volume_boost_item_id,
            rewind_id,
            forward_id,
            live_id,
            whats_playing_id,
            song_history_id,
            self._global_volume_item_id,
            forget_volumes_id,
            self._announce_titles_item_id,
            sleep_id,
            wake_id,
            enhance_id,
            record_id,
            record_station_id,
            schedule_id,
            recordings_id,
            settings_id,
            palette_id,
            bug_id,
            ffmpeg_id,
            *doc_ids,
            updates_id,
            about_id,
            show_details_id,
            self._status_bar_item_id,
            expand_id,
            collapse_id,
            *self._sort_item_ids,
            *self._text_size_item_ids,
            shortcuts_id,
            hotkeys_id,
            sheet_id,
        )
