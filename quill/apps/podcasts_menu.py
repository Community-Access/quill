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
APP_VERSION = "1.1.0"
APP_REPO = "Community-Access/quill"

_TITLE = APP_TITLE
_VERSION = APP_VERSION
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
        subs_menu.Append(manager_id, "&Open Podcast Manager...\tCtrl+M")
        subs_menu.Append(add_id, "&Add Podcast...")
        subs_menu.Append(import_id, "&Import OPML...")
        subs_menu.Append(export_id, "&Export OPML...")
        folder_id = wx.NewIdRef()
        subs_menu.Append(folder_id, "New &Folder...")
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
        subs_menu.Append(local_id, "Add &Local Podcast...")
        subs_menu.Append(watched_id, "Scan &Watched Folders")
        subs_menu.Append(acb_id, "Subscribe to ACB Media &Podcasts")
        subs_menu.AppendSeparator()
        subs_menu.Append(settings_id, "Podcast &Settings...")
        # The second directory's key. Somewhere you go, not something you meet:
        # iTunes needs nothing and stays the default (core/podcasts/podcast_index).
        directory_id = wx.NewIdRef()
        subs_menu.Append(directory_id, "Podcast &Index Credentials...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_directory_credentials(), id=directory_id
        )
        quick_actions_id = wx.NewIdRef()
        subs_menu.Append(quick_actions_id, "&Quick Actions...")
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
        subs_menu.Append(columns_id, "Choose Co&lumns...\tCtrl+Alt+Shift+C")
        self.frame.Bind(wx.EVT_MENU, lambda _e: open_list_columns(self), id=columns_id)
        export_data_id, delete_data_id = wx.NewIdRef(), wx.NewIdRef()
        subs_menu.Append(export_data_id, "Ex&port My Data...")
        subs_menu.Append(delete_data_id, "Delete All Podcast &Data...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_export_data(), id=export_data_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_delete_all_data(), id=delete_data_id)
        subs_menu.AppendSeparator()
        self._resume_menu_item_id = wx.NewIdRef()
        subs_menu.AppendCheckItem(self._resume_menu_item_id, "Resume Last Episode on Lau&nch")
        subs_menu.Check(self._resume_menu_item_id, self._podcast_history.resume_on_launch)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_resume_on_launch(), id=self._resume_menu_item_id
        )
        prefs_id = wx.NewIdRef()
        subs_menu.Append(prefs_id, "&Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        subs_menu.AppendSeparator()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        subs_menu.Append(tray_id, "Send to &Tray\tCtrl+W")
        subs_menu.Append(exit_id, "E&xit")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_manager(), id=manager_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_add_dialog(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_import_opml(), id=import_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_export_opml(), id=export_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_settings(), id=settings_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._new_library_folder(), id=folder_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_local_podcast(), id=local_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.scan_watched_podcast_folders(), id=watched_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.subscribe_acb_media_podcasts(), id=acb_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.frame.Close(), id=exit_id)
        menu_bar.Append(subs_menu, "&Subscriptions")

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
        episode_menu.Append(mute_id, "&Mute/Unmute")
        vol_up_id, vol_down_id = wx.NewIdRef(), wx.NewIdRef()
        episode_menu.Append(vol_up_id, "Volume &Up\tCtrl+Up")
        episode_menu.Append(vol_down_id, "Volume &Down\tCtrl+Down")
        episode_menu.Append(next_id, "&Next Chapter")
        episode_menu.Append(prev_id, "P&revious Chapter")
        skip_fwd_id, skip_back_id = wx.NewIdRef(), wx.NewIdRef()
        episode_menu.Append(skip_fwd_id, "Skip &Forward\tCtrl+Right")
        episode_menu.Append(skip_back_id, "Skip &Back\tCtrl+Left")
        # Speed as a continuum (1.1.0): 0.5x-5.0x in tenths, from the
        # keyboard, with the scope announced -- the playing show's own speed
        # if something is playing, otherwise the shared default.
        speed_up_id, speed_down_id, speed_reset_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        episode_menu.Append(speed_up_id, "Speed U&p\tCtrl+Shift+Up")
        episode_menu.Append(speed_down_id, "Speed Do&wn\tCtrl+Shift+Down")
        episode_menu.Append(speed_reset_id, "Reset Speed to Norma&l\tCtrl+Shift+0")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_up(), id=speed_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_down(), id=speed_down_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_speed_reset(), id=speed_reset_id)
        stop_after_id = wx.NewIdRef()
        episode_menu.Append(stop_after_id, "Stop &After This Episode")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_toggle_stop_after_episode(), id=stop_after_id
        )
        continue_id = wx.NewIdRef()
        episode_menu.Append(continue_id, "&Continue Listening...")
        about_ep_id = wx.NewIdRef()
        episode_menu.Append(about_ep_id, "&About This Episode...")
        note_id = wx.NewIdRef()
        episode_menu.Append(note_id, "Add Episode &Note...")
        queue_id = wx.NewIdRef()
        episode_menu.Append(queue_id, "Play &Queue...")
        mark_all_id = wx.NewIdRef()
        episode_menu.Append(mark_all_id, "Mark All as Play&ed...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_mark_all_played(), id=mark_all_id)
        # Dimmed when the current show has nothing unheard (in-memory check;
        # EVT_UPDATE_UI fires far too often for a disk read).
        self.frame.Bind(
            wx.EVT_UPDATE_UI,
            lambda e: e.Enable(self.podcast_current_show_unheard() > 0),
            id=mark_all_id,
        )
        keep_id = wx.NewIdRef()
        episode_menu.Append(keep_id, "&Keep This Episode")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_keep_episode(), id=keep_id)
        stats_id = wx.NewIdRef()
        episode_menu.Append(stats_id, "Listening Stat&istics...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_statistics(), id=stats_id)
        episode_menu.AppendSeparator()
        self._append_podcast_recent_submenu(episode_menu)
        episode_menu.AppendSeparator()
        sleep_id = wx.NewIdRef()
        episode_menu.Append(sleep_id, "Sleep &Timer...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=sleep_id)
        sleep_episode_id, sleep_extend_id = wx.NewIdRef(), wx.NewIdRef()
        episode_menu.Append(sleep_episode_id, "Sleep at End of This E&pisode")
        episode_menu.Append(sleep_extend_id, "E&xtend Sleep Timer 5 Minutes")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.sleep_timer_end_of_episode(), id=sleep_episode_id
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.extend_sleep_timer_command(), id=sleep_extend_id
        )
        episode_menu.AppendSeparator()
        enhance_id = wx.NewIdRef()
        episode_menu.Append(enhance_id, "Sound &Enhancements...\tCtrl+E")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_sound_enhancements(), id=enhance_id
        )
        # Where the audio comes out. One key cycles stereo / mono / left ear /
        # right ear, matching Quill Radio exactly (quill.core.audio.channel_mode)
        # -- someone listening with one ear, or sharing their ears with a screen
        # reader, needs this in every app and should not learn it twice.
        channel_id = wx.NewIdRef()
        episode_menu.Append(channel_id, "Audio &Output Mode\tCtrl+Shift+M")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_cycle_channel_mode(), id=channel_id)
        # And which sound card it comes out of. Radio can route audio itself
        # (libmpv); Cast cannot, and says so rather than opening a picker that
        # would do nothing -- see ui/media/output_device.
        device_id = wx.NewIdRef()
        episode_menu.Append(device_id, "Audio Output &Device...\tCtrl+Shift+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_choose_output_device(), id=device_id)
        skip_settings_id = wx.NewIdRef()
        episode_menu.Append(skip_settings_id, "S&kip Settings...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_skip_settings(), id=skip_settings_id
        )
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
        downloads_menu.Append(pause_all_id, "&Pause All Downloads")
        downloads_menu.Append(resume_all_id, "&Resume All Downloads")
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
        downloads_menu.Append(manage_downloads_id, "&Downloads...")
        downloads_menu.Append(free_space_id, "&Free Up Space")
        downloads_menu.Append(housekeeping_id, "Run &Housekeeping Now")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_downloads(), id=manage_downloads_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_free_up_space(), id=free_space_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_run_maintenance(), id=housekeeping_id)
        menu_bar.Append(downloads_menu, "&Downloads")

        # Pre-release top-level Audio Description Project menu. The typed Ask
        # ADP assistant (future.adp_assistant) is ON by default for testing, so
        # this is present by default; _build_adp_menu returns None only if a
        # profile turns it off. The hands-free conversational mode
        # (future.adp_voice_mode) is the part that stays locked until a signed
        # unlock code is redeemed (Help > Redeem Unlock Code..., here or in
        # QUILL -- they share one unlock store). Undocumented until launch.
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, "&Community")

        menu_bar.Append(self._build_quillins_menu(), "&Quillins")

        help_menu = wx.Menu()
        palette_id, redeem_id, updates_id, about_id = (
            wx.NewIdRef(),
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
        help_menu.Append(shortcuts_id, "&Keyboard Shortcuts...")
        help_menu.Append(hotkeys_id, "&Global Hotkeys...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_keymap_editor(), id=shortcuts_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_global_hotkeys_manager(), id=hotkeys_id)
        # Spotify (future.spotify) is experimental: ids always created for
        # pinning, items shown only while the feature is on and Safe Mode is off.
        spotify_connect_id, spotify_browse_id = wx.NewIdRef(), wx.NewIdRef()
        if self.features.is_enabled("future.spotify") and not self._safe_mode:
            help_menu.Append(spotify_connect_id, "Connect to &Spotify...")
            help_menu.Append(spotify_browse_id, "&Browse Spotify Podcasts...")
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_connect(), id=spotify_connect_id
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_spotify_browse(), id=spotify_browse_id
            )
        bug_id = wx.NewIdRef()
        help_menu.Append(bug_id, "Report a &Bug...")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_app_bug(source_app="QUILL Cast", app_version=_VERSION),
            id=bug_id,
        )
        ffmpeg_id = wx.NewIdRef()
        help_menu.Append(ffmpeg_id, "&Get FFmpeg...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_ffmpeg_component(), id=ffmpeg_id)
        help_menu.AppendSeparator()
        guide_id, notes_id, prd_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(guide_id, "&User Guide")
        help_menu.Append(notes_id, "&Release Notes")
        help_menu.Append(prd_id, "&Product Requirements...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_podcasts_doc("userguide"), id=guide_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_podcasts_doc("release-notes-1.1"), id=notes_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_podcasts_doc("prd"), id=prd_id)
        help_menu.AppendSeparator()
        help_menu.Append(redeem_id, "Redeem &Unlock Code...")
        help_menu.Append(updates_id, "Check for Up&dates...")
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About QUILL Cast")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_redeem_unlock_code_dialog(), id=redeem_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="cast"
            ),
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
            skip_settings_id,
            pause_all_id,
            resume_all_id,
            palette_id,
            bug_id,
            ffmpeg_id,
            guide_id,
            notes_id,
            prd_id,
            redeem_id,
            updates_id,
            about_id,
            shortcuts_id,
            hotkeys_id,
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
