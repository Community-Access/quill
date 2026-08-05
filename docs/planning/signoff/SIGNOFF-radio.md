# QUILL 1.0.0 Sign-off — Quill Radio (public app)

**29 commands** + **36 dialog surfaces.** Run across every §A environment (portable + system, Windows + macoS). Legend: W/S/A as in the master.

## Commands
- [ ] W  [ ] S  [ ] A  `radio.add_custom_station` — Internet Radio: Add Custom Station...
- [ ] W  [ ] S  [ ] A  `radio.browse` — Internet Radio: Browse Stations...
- [ ] W  [ ] S  [ ] A  `radio.copy_whats_playing` — Internet Radio: Copy What's Playing
- [ ] W  [ ] S  [ ] A  `radio.find_streams` — Internet Radio: Find Streams from a Website...
- [ ] W  [ ] S  [ ] A  `radio.forward` — Internet Radio: Forward 30 Seconds
- [ ] W  [ ] S  [ ] A  `radio.jump_to_live` — Internet Radio: Back to Live
- [ ] W  [ ] S  [ ] A  `radio.manage_favorites` — Internet Radio: Manage Favorites...
- [ ] W  [ ] S  [ ] A  `radio.mute_toggle` — Internet Radio: Mute/Unmute  `Ctrl+Shift+Grave, 9`
- [ ] W  [ ] S  [ ] A  `radio.play_last` — Internet Radio: Play Last Station
- [ ] W  [ ] S  [ ] A  `radio.play_pause` — Internet Radio: Play/Pause  `Ctrl+Shift+Grave, N`
- [ ] W  [ ] S  [ ] A  `radio.record_station` — Internet Radio: Record Station...
- [ ] W  [ ] S  [ ] A  `radio.record_toggle` — Internet Radio: Record Now / Stop Recording  `Ctrl+Shift+Grave, 6`
- [ ] W  [ ] S  [ ] A  `radio.recording_settings` — Internet Radio: Recording Settings...
- [ ] W  [ ] S  [ ] A  `radio.recordings` — Internet Radio: Recordings...
- [ ] W  [ ] S  [ ] A  `radio.rewind` — Internet Radio: Rewind 30 Seconds
- [ ] W  [ ] S  [ ] A  `radio.schedule_recording` — Internet Radio: Schedule Recording...
- [ ] W  [ ] S  [ ] A  `radio.sound_enhancements` — Internet Radio: Sound Enhancements...
- [ ] W  [ ] S  [ ] A  `radio.stop` — Internet Radio: Stop  `Ctrl+Shift+Grave, 0`
- [ ] W  [ ] S  [ ] A  `radio.stop_all_recordings` — Internet Radio: Stop All Recordings
- [ ] W  [ ] S  [ ] A  `radio.toggle_title_announcements` — Internet Radio: Announce Track Titles On/Off
- [ ] W  [ ] S  [ ] A  `radio.volume_boost` — Internet Radio: Volume Boost On/Off
- [ ] W  [ ] S  [ ] A  `radio.volume_down` — Internet Radio: Volume Down
- [ ] W  [ ] S  [ ] A  `radio.volume_up` — Internet Radio: Volume Up
- [ ] W  [ ] S  [ ] A  `radio.wake_timer` — Internet Radio: Wake-Up Timer...
- [ ] W  [ ] S  [ ] A  `radio.whats_playing` — Internet Radio: What's Playing?
- [ ] W  [ ] S  [ ] A  `radio.whats_playing_details` — Internet Radio: What's Playing - Review and Copy...
- [ ] W  [ ] S  [ ] A  `spotify.browse` — Spotify: Browse Spotify Podcasts...  **[GATED future.spotify]**
- [ ] W  [ ] S  [ ] A  `spotify.connect` — Spotify: Connect to Spotify...  **[GATED future.spotify]**
- [ ] W  [ ] S  [ ] A  `view.toggle_window_to_tray` — Show/Hide QUILL Cast to the Tray

## Dialog surfaces
- [ ] W  [ ] S  [ ] A  `quill/apps/radio.py::RadioAppFrame._on_sort_folder::wx.SingleChoiceDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/apps/radio.py::RadioAppFrame.import_stations_from_playlist::wx.FileDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/apps/radio.py::RadioAppFrame.import_stations_from_playlist::wx.SingleChoiceDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/add_station_dialog.py::AddStationDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/backup_ui.py::back_up_radio_data::wx.FileDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/backup_ui.py::restore_radio_data::wx.FileDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/browse_tree_dialog.py::BrowseTreeDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/close_confirm_dialog.py::RadioCloseConfirmDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::create_folder_prompt::wx.SingleChoiceDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::create_folder_prompt::wx.TextEntryDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::delete_folder_prompt::wx.MessageBox`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::move_favorite_to_folder::wx.SingleChoiceDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::move_favorite_to_folder::wx.TextEntryDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::remove_all_favorites::wx.MessageBox`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::remove_favorite::wx.MessageBox`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::rename_favorite::wx.TextEntryDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorite_actions.py::rename_folder_prompt::wx.TextEntryDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorites_manager_dialog.py::FavoritesManagerDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorites_manager_dialog.py::FavoritesManagerDialog._on_delete_folder::wx.MessageBox`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/favorites_manager_dialog.py::FavoritesManagerDialog._on_rename_folder::wx.TextEntryDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/import_stations_dialog.py::prompt_import_target::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/link_finder_dialog.py::LinkFinderDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/now_playing_dialog.py::NowPlayingDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/output_device_ui.py::choose_output_device::wx.SingleChoiceDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/playlist_export_ui.py::export_favorites_to_playlist::wx.FileDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/record_station_dialog.py::RecordStationDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/recording_settings_dialog.py::RecordingSettingsDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/recording_settings_dialog.py::RecordingSettingsDialog._on_browse::wx.DirDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/recording_settings_dialog.py::RecordingSettingsDialog._on_browse_temp::wx.DirDialog`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/recordings_manager_dialog.py::RecordingsManagerDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/recordings_manager_dialog.py::RecordingsManagerDialog._on_remove::wx.MessageBox`  _(native)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/resume_recording_dialog.py::ResumeRecordingDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/resume_recording_dialog.py::ResumeRecordingsBatchDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/schedule_recording_dialog.py::ScheduleRecordingDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/station_browser_dialog.py::StationBrowserDialog.__init__::wx.Dialog`  _(hardened_custom)_
- [ ] W  [ ] S  [ ] A  `quill/ui/radio/wake_timer_dialog.py::WakeUpTimerDialog.__init__::wx.Dialog`  _(hardened_custom)_

## Scenario checks (beyond per-command)
- [ ] W  [ ] S  [ ] A  Playback survives a dropped connection (auto-reconnect) and a crash (resume).
- [ ] W  [ ] S  [ ] A  A scheduled recording fires while the app is in the tray.
- [ ] W  [ ] S  [ ] A  Favorites manual order is preserved across restart; move up/down announces landing.
- [ ] W  [ ] S  [ ] A  Back Up / Restore stations & settings (`.qrbackup`) round-trips.
- [ ] W  [ ] S  [ ] A  Start-with-Windows autostart; missed-recording report on launch.
- [ ] W  [ ] S  [ ] A  Weather menu (embedded) works; QuillVille switcher lists only QUILL/Weather.
- [ ] W  [ ] S  [ ] A  Volume remembered across restart; media keys / tray hotkey (Ctrl+Alt+Shift+R).
