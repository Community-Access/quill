"""QUILL Cast's menu bar (1.1.0).

Split out of ``quill/apps/podcasts.py`` under GATE-11 -- the menu bar is a
single 250-line method that grew with every release, and it is the part of
that module least entangled with everything else in it: it reads the frame's
own commands and binds them, and touches nothing else.

Keeping it beside the frame rather than folding it into the shared shell is
deliberate. This is QUILL Cast's *product surface* -- which commands exist,
what they are called, and which key they answer to -- and it should be
readable in one place without the tree, the transport, and the lifecycle
around it.
"""

from __future__ import annotations

import wx

#: QUILL Cast's identity. It lives beside the menu bar because that is where
#: every one of these is *displayed* -- About, Report a Bug, Check for Updates
#: -- and because the frame importing them from here avoids the circular
#: import the other direction would need.
APP_TITLE = "QUILL Cast"
APP_VERSION = "2.0.0"
APP_BUILD = 1  # this version's build (docs/release/RELEASE.md, "Build numbers")
APP_REPO = "Community-Access/quill"

_TITLE = APP_TITLE
_VERSION = APP_VERSION
_BUILD = APP_BUILD
_REPO = APP_REPO


class CastMenuBarMixin:
    """Builds QUILL Cast's menu bar. Mixed into ``PodcastsAppFrame``."""

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        subs_menu = wx.Menu()
        manager_id, add_id, import_id, export_id, settings_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        subs_menu.Append(manager_id, "Refresh All N&ow\tF5")
        subs_menu.Append(add_id, "&Add Podcast...\tCtrl+N")
        self._advanced_row(subs_menu, "import_opml", import_id, "&Import OPML...\tCtrl+Alt+I")
        self._advanced_row(subs_menu, "export_opml", export_id, "&Export OPML...\tCtrl+Alt+E")
        folder_id = wx.NewIdRef()
        subs_menu.Append(folder_id, "New &Folder...\tCtrl+Shift+F")
        # Sort Podcasts: how the library tree orders shows. Radio items so the
        # current mode is always visible; "custom" is also entered implicitly
        # by Alt+Up/Alt+Down on a show (see _on_library_move_show).
        sort_menu = wx.Menu()
        self._sort_mode_menu_ids: dict[str, object] = {}
        for mode, label in (
            ("title_az", "&Ascending (A to Z)"),
            ("title_za", "&Descending (Z to A)"),
            ("custom", "&Custom Order"),
        ):
            mode_id = wx.NewIdRef()
            self._sort_mode_menu_ids[mode] = mode_id
            sort_menu.AppendRadioItem(mode_id, label)
            self.frame.Bind(wx.EVT_MENU, lambda _e, m=mode: self._set_show_sort_mode(m), id=mode_id)
        subs_menu.AppendSubMenu(sort_menu, "So&rt Podcasts")
        local_id, watched_id, acb_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        self._area_row(subs_menu, "personal_audio", local_id, "Add &Personal Audio...\tCtrl+Alt+L")
        self._area_row(subs_menu, "watched_folders", watched_id, "&Watched Folders...\tCtrl+Alt+W")
        self._area_row(subs_menu, "acb_media", acb_id, "Follow ACB Media Podcasts (&B)\tCtrl+Alt+B")
        subs_menu.AppendSeparator()
        subs_menu.Append(settings_id, "&Settings for This Podcast...\tCtrl+Alt+,")
        # The second directory's key. Somewhere you go, not something you meet:
        # iTunes needs nothing and stays the default (core/podcasts/podcast_index).
        directory_id = wx.NewIdRef()
        self._advanced_row(
            subs_menu,
            "directory_credentials",
            directory_id,
            "Po&dcast Index Credentials...\tCtrl+Alt+Shift+I",
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_directory_credentials(), id=directory_id
        )
        # Feed Check (ear.md R2). An everyday row, not an advanced one: the
        # question it answers -- which of my podcasts is broken -- is one a
        # listener asks in their first month, and the only previous answer was to
        # re-subscribe to each one and watch.
        feed_check_id = wx.NewIdRef()
        self._area_row(subs_menu, "feed_check", feed_check_id, "Feed C&heck...\tCtrl+Shift+C")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_cast_feed_check(), id=feed_check_id)
        self._keep_menu_ids(feed_check_id)
        quick_actions_id = wx.NewIdRef()
        self._advanced_row(
            subs_menu, "quick_actions", quick_actions_id, "&Quick Actions...\tCtrl+Alt+Q"
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_quick_actions(), id=quick_actions_id
        )
        # What a row says, and in what order. An episode list is read out
        # column by column, so this is where somebody decides the sentence
        # they will hear on every row. Next to Quick Actions because the two
        # answer the same kind of question about a row: what it offers, and
        # what it says.
        from quill.ui.podcasts.list_columns_command import open_list_columns

        columns_id = wx.NewIdRef()
        self._advanced_row(
            subs_menu, "choose_columns", columns_id, "&Choose Columns...\tCtrl+Alt+Shift+C"
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: open_list_columns(self), id=columns_id)
        export_data_id, delete_data_id = wx.NewIdRef(), wx.NewIdRef()
        self._advanced_row(
            subs_menu, "export_data", export_data_id, "E&xport My Data...\tCtrl+Alt+Shift+E"
        )
        self._advanced_row(
            subs_menu,
            "delete_all_data",
            delete_data_id,
            "Clear All Podcast Data from &This Computer...\tCtrl+Alt+Shift+D",
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_export_data(), id=export_data_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_delete_all_data(), id=delete_data_id)
        # Beside Export My Data because that is where somebody looks for them,
        # and *not* the same thing: the export is a readable JSON snapshot,
        # these are an archive that goes back in (list.md 5.6). Cast's library
        # -- subscriptions, folders, playlists, positions, notes, statistics --
        # is the more painful of the two apps' to lose.
        backup_id, restore_id = wx.NewIdRef(), wx.NewIdRef()
        self._advanced_row(
            subs_menu,
            "backup",
            backup_id,
            self._menu_label("&Back Up My Podcasts...", "app.backup"),
        )
        self._advanced_row(
            subs_menu,
            "restore",
            restore_id,
            self._menu_label("Restore fro&m a Backup...", "app.restore"),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.back_up_cast_data(), id=backup_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.restore_cast_data(), id=restore_id)
        self._append_podcasts_extras(subs_menu)  # podcasts_routes.py
        subs_menu.AppendSeparator()
        self._resume_menu_item_id = wx.NewIdRef()
        subs_menu.AppendCheckItem(
            self._resume_menu_item_id, "Resume Last Episode on Lau&nch\tCtrl+Alt+Shift+L"
        )
        subs_menu.Check(self._resume_menu_item_id, self._podcast_history.resume_on_launch)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_resume_on_launch(), id=self._resume_menu_item_id
        )
        prefs_id = wx.NewIdRef()
        subs_menu.Append(prefs_id, "Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        subs_menu.AppendSeparator()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        subs_menu.Append(tray_id, "Send to Tra&y\tCtrl+W")
        subs_menu.Append(exit_id, "Exit\tCtrl+Q")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._on_check_all_feeds(), id=manager_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_add_dialog(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_import_opml(), id=import_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_export_opml(), id=export_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_show_settings_for_selection(), id=settings_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._new_library_folder(), id=folder_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_local_podcast(), id=local_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_watched_folders(), id=watched_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.subscribe_acb_media_podcasts(), id=acb_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.frame.Close(), id=exit_id)
        # Podcasts, not Subscriptions: the Follow framing (2026-09-30) makes the
        # old name wrong, and a menu named after the thing in it is the one a
        # newcomer opens first.
        menu_bar.Append(subs_menu, "&Podcasts")
        # View second, where View sits in every Microsoft application a listener
        # has used (there is no Edit menu here for it to follow).
        self._build_view_menu(menu_bar)

        episode_menu = wx.Menu()
        self._now_playing_item_id = wx.NewIdRef()
        episode_menu.Append(self._now_playing_item_id, "Podcasts: stopped")
        episode_menu.Enable(self._now_playing_item_id, False)
        episode_menu.AppendSeparator()
        play_id, stop_id, next_id, prev_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        episode_menu.Append(play_id, "&Play/Pause\tCtrl+P")
        episode_menu.Append(stop_id, "&Stop\tCtrl+.")
        mute_id = wx.NewIdRef()
        episode_menu.Append(mute_id, "&Mute/Unmute\tCtrl+Alt+M")
        vol_up_id, vol_down_id = wx.NewIdRef(), wx.NewIdRef()
        episode_menu.Append(vol_up_id, "Volume &Up\tCtrl+Up")
        episode_menu.Append(vol_down_id, "Volume &Down\tCtrl+Down")
        self._area_row(episode_menu, "transcripts", next_id, "&Next Chapter\tCtrl+Alt+Right")
        self._area_row(episode_menu, "transcripts", prev_id, "P&revious Chapter\tCtrl+Alt+Left")
        skip_fwd_id, skip_back_id = wx.NewIdRef(), wx.NewIdRef()
        self._area_row(episode_menu, "skipping", skip_fwd_id, "Skip &Forward\tCtrl+Right")
        self._area_row(episode_menu, "skipping", skip_back_id, "Skip &Back\tCtrl+Left")
        # Speed as a continuum (1.1.0): 0.5x-5.0x in tenths, from the
        # keyboard, with the scope announced -- the playing show's own speed
        # if something is playing, otherwise the shared default.
        speed_up_id, speed_down_id, speed_reset_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        self._area_row(episode_menu, "speed", speed_up_id, "Sp&eed Up\tCtrl+Shift+Up")
        self._area_row(episode_menu, "speed", speed_down_id, "Speed Do&wn\tCtrl+Shift+Down")
        self._area_row(
            episode_menu, "speed", speed_reset_id, "Reset Speed to Norma&l\tCtrl+Shift+0"
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_up(), id=speed_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_down(), id=speed_down_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_reset(), id=speed_reset_id)
        # Jump to a typed position (11.8). It existed only on a Winamp letter
        # key, which means it existed for whoever had those on and knew about
        # it, and for nobody else. Ctrl+Alt+J, the same key Quill Radio uses.
        goto_pos_id = wx.NewIdRef()
        self._keep_menu_ids(goto_pos_id)
        episode_menu.Append(
            goto_pos_id, self._menu_label("&Go to Position...", "podcasts.go_to_position")
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_go_to_position(), id=goto_pos_id)
        self._append_episode_extras(episode_menu)  # podcasts_routes.py
        stop_after_id = wx.NewIdRef()
        episode_menu.Append(stop_after_id, "Stop &After This Episode\tCtrl+Alt+Shift+A")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_toggle_stop_after_episode(), id=stop_after_id
        )
        continue_id = wx.NewIdRef()
        now_playing_id = wx.NewIdRef()
        self._area_row(
            episode_menu,
            "now_playing",
            now_playing_id,
            self._menu_label("Now Playing (&J)...", "podcasts.now_playing"),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_now_playing(), id=now_playing_id)
        about_ep_id = wx.NewIdRef()
        self._area_row(episode_menu, "notes", about_ep_id, "Ab&out This Episode...\tCtrl+Shift+A")
        note_id = wx.NewIdRef()
        self._area_row(episode_menu, "notes", note_id, "Add Ep&isode Note...\tCtrl+Alt+N")
        queue_id = wx.NewIdRef()
        self._append_queue_run_submenu(episode_menu)
        mark_all_id = wx.NewIdRef()
        episode_menu.Append(mark_all_id, "Mar&k All as Played...\tCtrl+Shift+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_mark_all_played(), id=mark_all_id)
        # Dimmed when the current show has nothing unheard (in-memory check;
        # EVT_UPDATE_UI fires far too often for a disk read).
        self.frame.Bind(
            wx.EVT_UPDATE_UI,
            lambda e: e.Enable(self.podcast_current_show_unheard() > 0),
            id=mark_all_id,
        )
        keep_id = wx.NewIdRef()
        self._area_row(episode_menu, "keep_episode", keep_id, "Keep &This Episode\tCtrl+Alt+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_keep_episode(), id=keep_id)
        stats_id = wx.NewIdRef()
        self._area_row(
            episode_menu, "statistics", stats_id, "Listening Statistics...\tCtrl+Alt+Shift+S"
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_statistics(), id=stats_id)
        episode_menu.AppendSeparator()
        self._append_podcast_recent_submenu(episode_menu)
        episode_menu.AppendSeparator()
        sleep_id = wx.NewIdRef()
        self._area_row(episode_menu, "sleep_timer", sleep_id, "Sleep Timer...\tCtrl+Alt+T")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=sleep_id)
        sleep_episode_id, sleep_extend_id = wx.NewIdRef(), wx.NewIdRef()
        self._area_row(
            episode_menu,
            "sleep_timer",
            sleep_episode_id,
            "Sleep at End of T&his Episode\tCtrl+Alt+Shift+T",
        )
        self._area_row(
            episode_menu,
            "sleep_timer",
            sleep_extend_id,
            "E&xtend Sleep Timer 5 Minutes\tCtrl+Alt+X",
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.sleep_timer_end_of_episode(), id=sleep_episode_id
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.extend_sleep_timer_command(), id=sleep_extend_id
        )
        episode_menu.AppendSeparator()
        enhance_id = wx.NewIdRef()
        self._area_row(episode_menu, "sound", enhance_id, "Sound Enhancements...\tCtrl+E")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_sound_enhancements(), id=enhance_id
        )
        # Where the audio comes out. One key cycles stereo / mono / left ear /
        # right ear, matching Quill Radio exactly (quill.core.audio.channel_mode)
        # -- someone listening with one ear, or sharing their ears with a screen
        # reader, needs this in every app and should not learn it twice.
        channel_id = wx.NewIdRef()
        self._area_row(episode_menu, "sound", channel_id, "Audio Output Mode\tCtrl+Shift+M")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_cycle_channel_mode(), id=channel_id)
        # And which sound card it comes out of. Radio can route audio itself
        # (libmpv); Cast cannot, and says so rather than opening a picker that
        # would do nothing -- see ui/media/output_device.
        device_id = wx.NewIdRef()
        self._area_row(episode_menu, "sound", device_id, "Audio Output De&vice...\tCtrl+Shift+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_choose_output_device(), id=device_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_toggle_play_pause(), id=play_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_stop(), id=stop_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_mute_toggle(), id=mute_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_volume_up(), id=vol_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_volume_down(), id=vol_down_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_next_chapter(), id=next_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_previous_chapter(), id=prev_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_skip_forward(), id=skip_fwd_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_skip_back(), id=skip_back_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_continue_listening(), id=continue_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_episode_extras(), id=about_ep_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_podcast_note(), id=note_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_play_queue(), id=queue_id)
        menu_bar.Append(episode_menu, "&Episode")

        downloads_menu = wx.Menu()
        pause_all_id, resume_all_id = wx.NewIdRef(), wx.NewIdRef()
        self._area_row(
            downloads_menu, "downloads", pause_all_id, "&Pause All Downloads\tCtrl+Alt+Shift+U"
        )
        self._area_row(
            downloads_menu, "downloads", resume_all_id, "&Resume All Downloads\tCtrl+Alt+Shift+V"
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_pause_all_downloads(), id=pause_all_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_resume_all_downloads(), id=resume_all_id
        )
        downloads_menu.AppendSeparator()
        manage_downloads_id, free_space_id, housekeeping_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        self._advanced_row(
            downloads_menu, "free_space", free_space_id, "&Free Up Space\tCtrl+Alt+F"
        )
        self._advanced_row(
            downloads_menu, "housekeeping", housekeeping_id, "Run &Housekeeping Now\tCtrl+Alt+H"
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_downloads(), id=manage_downloads_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_free_up_space(), id=free_space_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_run_maintenance(), id=housekeeping_id)
        menu_bar.Append(downloads_menu, "&Downloads")

        # No Community menu here (Jeff, 2026-09-30): the pre-release assistant it
        # carried was removed from the whole family.

        # Quillins only in Advanced mode (Jeff, 2026-09-30): an extensions menu is
        # the definition of a thing you go looking for once you know it exists.
        if self._cast_shows_row("quillins"):
            if self._cast_area_enabled("quillins"):
                menu_bar.Append(self._build_quillins_menu(), "&Quillins")

        # &Window, between Quillins and Help, the same place Radio and Weather
        # put it. See podcasts_view_menu.install_cast_window_menu.
        self.install_cast_window_menu(menu_bar)

        help_menu = wx.Menu()
        palette_id, redeem_id, updates_id, about_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        if self._cast_area_enabled("ai_features"):
            self._append_cast_ai_submenu(help_menu)  # AI Features (cast_ai_host.py)
        help_menu.Append(palette_id, self._menu_label("Command &Palette...", "app.command_palette"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_command_palette(), id=palette_id)
        # The Keyboard Shortcuts editor and the Global Hotkeys manager open the
        # same already-accessible dialogs QUILL uses (KeymapEditorMixin /
        # GlobalHotkeysMixin), scoped to this app's own commands. In both menu
        # modes: every key is the listener's (qc.md section 8).
        shortcuts_id, hotkeys_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(shortcuts_id, "&Keyboard Shortcuts...\tCtrl+Alt+Shift+W")
        help_menu.Append(hotkeys_id, "&Global Hotkeys...\tCtrl+Alt+Shift+H")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_keymap_editor(), id=shortcuts_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_global_hotkeys_manager(), id=hotkeys_id)
        # The sheet is the other half of the editor above it, and the half
        # somebody learning the app needs: the editor changes a key you can
        # already name, the sheet is how you find out which keys exist
        # (list.md 5.1). Generated from this menu bar, so it cannot go stale.
        # One key for every place in the app (list.md 5.2). In the Help menu
        # beside the sheet because both answer "how do I get to things"; the
        # popup itself teaches the direct keys, so it trains you out of itself.
        go_to_id = wx.NewIdRef()
        help_menu.Append(go_to_id, self._menu_label("G&o To...", "app.go_to"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_cast_go_to(), id=go_to_id)
        sheet_id, media_tools_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(
            sheet_id, self._menu_label("Keyboard Shortcuts S&heet...", "app.shortcut_sheet")
        )
        self._advanced_row(
            help_menu,
            "media_tools",
            media_tools_id,
            self._menu_label("&Media Tools", "app.media_tools"),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_keyboard_cheat_sheet(), id=sheet_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_media_tools_status(), id=media_tools_id
        )
        # Spotify (future.spotify) is experimental: ids always created for
        # pinning, items shown only while the feature is on and Safe Mode is off.
        spotify_connect_id, spotify_browse_id = wx.NewIdRef(), wx.NewIdRef()
        if self.features.is_enabled("future.spotify") and not self._safe_mode:
            help_menu.Append(spotify_connect_id, "Connect to Spotif&y...\tCtrl+Alt+S")
            help_menu.Append(spotify_browse_id, "&Browse Spotify Podcasts...\tCtrl+Alt+V")
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_connect(), id=spotify_connect_id
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_browse(), id=spotify_browse_id
            )
        bug_id = wx.NewIdRef()
        help_menu.Append(bug_id, "Get Help from &Support...\tCtrl+Alt+F2")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_app_bug(source_app="QUILL Cast", app_version=_VERSION),
            id=bug_id,
        )
        # Undo, Recent Problems, Quiet Hours and Export / Import My Setup:
        # four shared surfaces over shared files, wired once for both apps.
        from quill.ui.support_menu import wire_support_surfaces

        wire_support_surfaces(self, menu_bar, help_menu, wx)
        ffmpeg_id = wx.NewIdRef()
        self._advanced_row(help_menu, "get_ffmpeg", ffmpeg_id, "G&et FFmpeg...\tCtrl+Alt+Shift+F")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_ffmpeg_component(), id=ffmpeg_id)
        help_menu.AppendSeparator()
        guide_id, notes_id, prd_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        # Tutorials leads the documents: it is the door somebody new reaches
        # for, and the three below it are what you open once you know what to
        # look up. Ctrl+Alt+F1 is the family key -- the same chord opens the
        # lessons in Quill Radio, Quill Weather and QUILL.
        tutorials_id = wx.NewIdRef()
        help_menu.Append(tutorials_id, self._menu_label("&Tutorials...", "podcasts.tutorials"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_cast_tutorials(), id=tutorials_id)
        help_menu.Append(guide_id, "&User Guide\tCtrl+Alt+D")
        help_menu.Append(notes_id, "&Release Notes\tCtrl+Alt+R")
        self._advanced_row(help_menu, "prd", prd_id, "Pro&duct Requirements...\tCtrl+Alt+Y")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_podcasts_doc("userguide"), id=guide_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_podcasts_doc("release-notes-2.0"), id=notes_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_podcasts_doc("prd"), id=prd_id)
        help_menu.AppendSeparator()
        self._advanced_row(
            help_menu, "unlock_code", redeem_id, "Redeem U&nlock Code...\tCtrl+Alt+Shift+Y"
        )
        help_menu.Append(updates_id, "&Check for Updates...\tCtrl+Alt+U")
        from quill.ui.updates.shell import append_release_channel_item

        append_release_channel_item(self, help_menu, "cast", updates_id)  # Alt+H, L
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About QUILL Cast\tCtrl+Alt+O")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_redeem_unlock_code_dialog(), id=redeem_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._check_cast_updates(),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self.frame.SetMenuBar(menu_bar)
        # Pin every menu id for the frame's lifetime (see _keep_menu_ids).
        self._keep_menu_ids(
            quick_actions_id,
            columns_id,
            export_data_id,
            backup_id,
            restore_id,
            delete_data_id,
            speed_up_id,
            speed_down_id,
            speed_reset_id,
            stop_after_id,
            mark_all_id,
            keep_id,
            stats_id,
            sleep_episode_id,
            sleep_extend_id,
            manage_downloads_id,
            free_space_id,
            housekeeping_id,
            channel_id,
            spotify_connect_id,
            spotify_browse_id,
            manager_id,
            add_id,
            import_id,
            export_id,
            settings_id,
            self._resume_menu_item_id,
            prefs_id,
            folder_id,
            local_id,
            watched_id,
            acb_id,
            tray_id,
            exit_id,
            self._now_playing_item_id,
            play_id,
            stop_id,
            mute_id,
            next_id,
            prev_id,
            skip_fwd_id,
            skip_back_id,
            continue_id,
            about_ep_id,
            note_id,
            queue_id,
            sleep_id,
            enhance_id,
            pause_all_id,
            resume_all_id,
            palette_id,
            bug_id,
            ffmpeg_id,
            tutorials_id,
            guide_id,
            notes_id,
            prd_id,
            redeem_id,
            updates_id,
            about_id,
            shortcuts_id,
            hotkeys_id,
            sheet_id,
            media_tools_id,
            go_to_id,
            *self._sort_mode_menu_ids.values(),
        )
        self._refresh_sort_mode_menu()

    def _refresh_sort_mode_menu(self) -> None:
        """Keep the Sort Podcasts radio group true to the live mode -- a
        manual Move Up/Down switches to custom without touching the menu."""
        ids = getattr(self, "_sort_mode_menu_ids", None)
        menu_bar = self.frame.GetMenuBar() if ids else None
        if not ids or menu_bar is None:
            return
        item_id = ids.get(self._podcast_library.settings.show_sort_mode)
        if item_id is not None:
            menu_bar.Check(int(item_id), True)

    def _append_queue_run_submenu(self, episode_menu: object) -> None:
        """The Play Queue read as a run you step through (ear.md R2, R3).

        **A submenu, and not three more rows in the Episode menu**, for a reason
        that is not tidiness: the Episode menu already claims 22 of the 26
        available access-key letters, and not one of the four still free (G, J, Y,
        Z) appears in "Next in Queue", "Previous in Queue" or "Mark as Played and
        Next". Windows cycles focus between duplicate mnemonics instead of
        pressing, so one of a colliding pair silently cannot be reached and
        nothing announces the loss (GATE-14). A submenu is its own local, which is
        its own namespace, which is also how Windows treats it -- so these three
        get a fresh alphabet. The submenu's own label takes the Y.

        The keys were chosen against what Cast has already bound, in the menu
        literals *and* in ``APP_KEYMAPS["cast"]``: Ctrl+Alt+Up and Ctrl+Alt+Down
        are free (Ctrl+Up/Down is volume, Ctrl+Shift+Up/Down is speed,
        Ctrl+Alt+Left/Right is chapters). Mark as Played and Next is Next in
        Queue with Shift added, and its key is in ``APP_KEYMAPS["cast"]``: its
        old Ctrl+Alt+Shift+Q was QUILL's system-wide show/hide key.
        """
        queue_run = wx.Menu()
        next_id, prev_id, played_next_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        queue_run.Append(next_id, "&Next in Queue\tCtrl+Alt+Down")
        queue_run.Append(prev_id, "P&revious in Queue\tCtrl+Alt+Up")
        label = self._menu_label("Mark as Played and Ne&xt", "podcasts.mark_played_and_next")
        queue_run.Append(played_next_id, label)
        episode_menu.AppendSubMenu(queue_run, "Pla&y Queue Run")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_next_in_queue(), id=next_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_previous_in_queue(), id=prev_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_mark_played_and_next(), id=played_next_id
        )
