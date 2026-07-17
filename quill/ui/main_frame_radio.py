"""Tools > Media > Internet Radio -- menu, commands, hotkeys, status bar
mini-player, and the system tray radio section.

RadioBrowser search, the bundled ACB Media category, custom stations, and
the website link finder all funnel through the one shared
``RadioPlayerController`` created here, so playback survives closing any of
the dialogs. See PRD §5.84f for the feature plan and
``quill/ui/radio/player_controller.py`` for why this always uses the
wx.media backend.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.radio import favorites as radio_favorites
from quill.core.radio import history as radio_history
from quill.core.radio import radio_browser, wake_timer
from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import (
    RadioRecorder,
    RecordingError,
    load_recording_settings,
    save_recording_settings,
)
from quill.core.radio.recording_schedule import RecordingScheduler
from quill.core.speech.ffmpeg import ffmpeg_available
from quill.ui.radio.add_station_dialog import AddStationDialog
from quill.ui.radio.link_finder_dialog import LinkFinderDialog
from quill.ui.radio.player_controller import RadioPlaybackState, RadioPlayerController
from quill.ui.radio.recording_settings_dialog import RecordingSettingsDialog
from quill.ui.radio.schedule_recording_dialog import ScheduleRecordingDialog
from quill.ui.radio.station_browser_dialog import StationBrowserDialog

_SAFE_MODE_MESSAGE = "Internet Radio is disabled in Safe Mode. Restart QUILL normally to use it."
_NO_FFMPEG_MESSAGE = (
    "Recording needs the FFmpeg optional component. Install it from "
    "Help > Download Optional Components (Audio: export, playback & chapters), "
    "then try again."
)


class RadioMixin:
    """Adds Internet Radio to ``MainFrame``."""

    # -- setup --------------------------------------------------------------

    def _init_radio(self) -> None:
        # Parents the player controller on self.frame: MainFrame.__init__ must
        # only call this (and _init_podcasts) after the frame is constructed,
        # or startup dies with AttributeError('frame').
        self._radio_favorites = radio_favorites.load_favorites(app_data_dir())
        self._radio_history = radio_history.load_history(app_data_dir())
        self._radio_history_key = ""
        self._radio_track_title = ""
        self._radio_fallback_tried = ""
        self._radio_ever_played = False
        # Track-title poller: fires only while a stream plays; each tick reads
        # one ICY metadata block from the playing stream, off-thread.
        self._radio_title_timer = self._wx.Timer(self.frame)
        self.frame.Bind(
            self._wx.EVT_TIMER,
            lambda _e: self._radio_fetch_track_title(),
            self._radio_title_timer,
        )
        self._radio_controller = RadioPlayerController(
            self.frame,
            on_state_changed=self._on_radio_state_changed,
            on_register_click=self._radio_register_click,
            before_play=self._stop_podcast_before_radio,
            on_enhance_error=self._on_radio_enhance_error,
            resolve_enhancement=self._radio_resolve_enhancement,
            resolve_volume=self._radio_resolve_volume,
            output_device=self._radio_history.output_device,
            on_output_device_error=self._on_radio_output_device_error,
            playback_engine=self._radio_history.playback_engine,
            on_buffering=lambda: self._wx.CallAfter(self._announce, "Buffering..."),
        )
        self._radio_controller.set_enhancement(
            bass_db=self._radio_history.eq_bass_db,
            mid_db=self._radio_history.eq_mid_db,
            treble_db=self._radio_history.eq_treble_db,
            compressor_enabled=self._radio_history.compressor_enabled,
        )
        self._radio_controller.set_sound_options(
            mono_enabled=self._radio_history.mono_enabled,
            night_mode_enabled=self._radio_history.night_mode_enabled,
        )
        self._radio_controller.set_volume_boost(self._radio_history.volume_boost)
        self._radio_recording_settings = load_recording_settings(app_data_dir())
        self._radio_recorder = RadioRecorder(
            on_state_changed=self._on_radio_recording_changed,
            on_reconnect=self._on_radio_recording_reconnect,
        )
        self._radio_scheduler = RecordingScheduler(
            data_dir=app_data_dir(),
            recorder=self._radio_recorder,
            recording_settings=self._radio_recording_settings,
            on_fired=self._on_radio_scheduled_recording_fired,
            filter_graph_provider=self._radio_recording_filter_graph,
        )
        self._radio_wake_watcher = wake_timer.WakeUpWatcher(
            app_data_dir(), on_wake=self._on_radio_wake_up
        )

    def _stop_podcast_before_radio(self) -> None:
        """Never double-play: starting a radio stream silences a playing
        podcast episode first (position is checkpointed by its stop path).
        Works in MainFrame (both players live) and is a no-op in standalone
        Quill Radio, which has no podcast controller."""
        podcast = getattr(self, "_podcast_controller", None)
        if podcast is not None:
            podcast.stop()

    def _radio_register_click(self, station_uuid: str) -> None:
        try:
            radio_browser.register_click(station_uuid, safe_mode=self._safe_mode)
        except Exception:  # noqa: BLE001 - a missed click-vote must never surface
            pass

    def _save_radio_favorites(self) -> None:
        radio_favorites.save_favorites(app_data_dir(), self._radio_favorites)

    # -- recording --------------------------------------------------------

    def _on_radio_recording_changed(self, is_recording: bool, destination: Path | None) -> None:
        self._wx.CallAfter(self._apply_radio_recording_changed, is_recording, destination)

    def _apply_radio_recording_changed(self, is_recording: bool, destination: Path | None) -> None:
        self._refresh_statusbar()
        self._refresh_radio_tray_tooltip()
        if not is_recording and destination is not None:
            self._announce(f"Recording saved: {destination.name}")

    def _on_radio_recording_reconnect(self, attempt: int, maximum: int) -> None:
        self._wx.CallAfter(
            self._announce,
            f"Recording lost its stream; reconnecting, attempt {attempt} of {maximum}. "
            "The recording continues in a new part file.",
        )

    def _on_radio_scheduled_recording_fired(self, entry: object, error: str) -> None:
        self._wx.CallAfter(self._apply_radio_scheduled_recording_fired, entry, error)

    def _apply_radio_scheduled_recording_fired(self, entry: object, error: str) -> None:
        station_name = getattr(entry, "station_name", "")
        if error:
            self._announce(f"Scheduled recording of {station_name} could not start: {error}")
        else:
            self._announce(f"Scheduled recording started: {station_name}")
        self._refresh_statusbar()

    def _radio_no_ffmpeg_message(self) -> str:
        """Where to get ffmpeg, phrased for the hosting app: QUILL points at
        its components hub; the standalone apps override this to point at
        their own Help > Get FFmpeg... item."""
        return _NO_FFMPEG_MESSAGE

    def radio_record_toggle(self) -> None:
        if not ffmpeg_available():
            self._show_message_box(
                self._radio_no_ffmpeg_message(),
                "Internet Radio",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        if self._radio_recorder.is_recording:
            self._radio_recorder.stop()
            self._announce("Stopping recording...")
            return
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None:
            self._announce("Nothing is playing to record. Start a station first.")
            return
        try:
            self._radio_recorder.start(
                station_name=station.name,
                stream_url=station.stream_url,
                settings=self._radio_recording_settings,
                filter_graph=self._radio_recording_filter_graph(),
            )
        except RecordingError as error:
            self._announce(str(error))
            return
        self._announce(f"Recording {station.name}")
        self._refresh_statusbar()

    def _radio_recording_filter_graph(self) -> str:
        """The current Sound Enhancements filter graph, or "" if Recording
        Settings' "Apply Sound Enhancements to recordings" is off."""
        if not self._radio_recording_settings.apply_sound_enhancements:
            return ""
        from quill.core.audio_enhance import build_filter_graph

        history = self._radio_history
        return build_filter_graph(
            history.eq_bass_db,
            history.eq_mid_db,
            history.eq_treble_db,
            compressor_enabled=history.compressor_enabled,
            mono_enabled=history.mono_enabled,
            night_mode_enabled=history.night_mode_enabled,
        )

    def _radio_open_recording_settings(self) -> None:
        dialog = RecordingSettingsDialog(
            self.frame, settings=self._radio_recording_settings, announce_cb=self._announce
        )
        updated = dialog.show()
        if updated is None:
            return
        self._radio_recording_settings = updated
        self._radio_scheduler.set_recording_settings(updated)
        save_recording_settings(app_data_dir(), updated)
        self._announce("Recording settings saved")

    def _radio_open_schedule_recording(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        dialog = ScheduleRecordingDialog(
            self.frame,
            entries=self._radio_scheduler.entries,
            default_station_name=station.name if station is not None else "",
            default_stream_url=station.stream_url if station is not None else "",
            on_add=self._radio_scheduler.add,
            on_remove=self._radio_scheduler.remove,
            on_update=self._radio_scheduler.update,
            favorites=self._radio_favorites,
            announce_cb=self._announce,
        )
        dialog.show()

    def _on_radio_state_changed(self, state: RadioPlaybackState) -> None:
        from quill.core.settings import save_settings

        self._radio_track_history_and_volume(state)
        self._radio_track_titles_follow_playback(state)
        self._radio_maybe_try_fallback_url(state)
        if state.station is not None and not self._radio_ever_played:
            self._radio_ever_played = True
            hidden = list(getattr(self.settings, "status_bar_hidden", []))
            if "radio_player" in hidden:
                hidden.remove("radio_player")
                self.settings.status_bar_hidden = hidden
                save_settings(self.settings)
        self._refresh_statusbar()
        self._refresh_radio_tray_tooltip()

    def _radio_track_history_and_volume(self, state: RadioPlaybackState) -> None:
        """Two memories, updated on every playback state change: the
        recently-played history (a newly started station moves to its front)
        and the per-station volume (a favorite remembers the volume you set
        while it plays -- restoring it on the way back in is
        RadioPlayerController's own job, via resolve_volume)."""
        station = state.station
        if station is None:
            self._radio_history_key = ""
            return
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if key != self._radio_history_key:
            # A different station just started.
            self._radio_history_key = key
            self._radio_history.record(station)
            radio_history.save_history(app_data_dir(), self._radio_history)
            return
        if (
            favorite is not None
            and not state.muted
            and state.volume_percent != favorite.volume_percent
        ):
            self._radio_favorites.set_volume(key, state.volume_percent)
            self._save_radio_favorites()

    # -- track titles (What's Playing) -----------------------------------------

    _TITLE_POLL_MS = 30000

    def _radio_track_titles_follow_playback(self, state: RadioPlaybackState) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        timer = getattr(self, "_radio_title_timer", None)
        if timer is None:
            return
        if state.state is RadioPlayerState.PLAYING and state.station is not None:
            # A good connection also re-arms the one-shot stream fallback.
            self._radio_fallback_tried = ""
            if not timer.IsRunning():
                timer.Start(self._TITLE_POLL_MS)
                self._radio_fetch_track_title()
        else:
            timer.Stop()
            self._radio_track_title = ""

    def _radio_fetch_track_title(self, *, announce_result: bool = False) -> None:
        """Read the playing stream's current title off-thread; announce a
        change when the user opted in, or unconditionally for an explicit
        What's Playing request."""
        from quill.core.radio.icy import read_stream_title

        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None or self._safe_mode:
            if announce_result:
                self._announce("Nothing is playing.")
            return
        url = station.stream_url

        def _fetch(**_kwargs: object) -> str:
            return read_stream_title(url)

        def _done(_op: str, title: object) -> None:
            resolved = str(title or "")
            if not resolved and controller is not None:
                # Engine-native fallback (mpv media-title): some hosts
                # reject the out-of-band ICY tap, and HLS has no ICY at all.
                resolved = controller.engine_track_title()
            self._wx.CallAfter(self._radio_apply_track_title, resolved, announce_result)

        self._task_manager.submit(
            "radio-track-title",
            _fetch,
            on_success=_done,
            on_failure=lambda *_a: None,
        )

    def _radio_now_playing_phrase(self, title: str) -> str:
        """Render a raw stream title into the spoken announcement (#1068).

        Cleans up the raw broadcast metadata some stations send and applies the
        user's ``now_playing_template`` (see quill.core.radio.now_playing), so
        a wall of ``key="value"`` noise becomes "Now playing: YOUR SONG by
        Elton John"."""
        from quill.core.radio.now_playing import render_now_playing

        template = getattr(self._radio_history, "now_playing_template", "") or None
        phrase = render_now_playing(title, template) if template else render_now_playing(title)
        return f"Now playing: {phrase}"

    def _radio_apply_track_title(self, title: str, announce_result: bool) -> None:
        changed = bool(title) and title != self._radio_track_title
        if title:
            self._radio_track_title = title
        if announce_result:
            self._announce(
                self._radio_now_playing_phrase(title)
                if title
                else "This stream doesn't share track titles."
            )
            return
        if changed and self._radio_history.announce_track_titles:
            self._announce(self._radio_now_playing_phrase(title))

    def radio_whats_playing(self) -> None:
        """Speak the current track title on demand."""
        if self._radio_track_title:
            self._announce(self._radio_now_playing_phrase(self._radio_track_title))
            return
        self._radio_fetch_track_title(announce_result=True)

    # -- live DVR (mpv engine): rewind / forward / back to live -----------------

    def radio_rewind(self) -> None:
        """Jump back 30 seconds within the live buffer."""
        behind = self._radio_controller.rewind(30)
        if behind is None:
            self._announce(self._radio_dvr_unavailable_message())
            return
        self._announce(f"Rewound 30 seconds. {self._radio_behind_live_phrase(behind)}")

    def radio_forward(self) -> None:
        """Jump forward 30 seconds, back toward the live edge."""
        behind = self._radio_controller.forward(30)
        if behind is None:
            self._announce(self._radio_dvr_unavailable_message())
            return
        self._announce(f"Forward 30 seconds. {self._radio_behind_live_phrase(behind)}")

    def radio_jump_to_live(self) -> None:
        """Return to the live edge of the stream."""
        if self._radio_controller.jump_to_live():
            self._announce("Back to live.")
        else:
            self._announce("Nothing is playing.")

    def _radio_dvr_unavailable_message(self) -> str:
        if self._radio_controller.state.station is None:
            return "Nothing is playing."
        return (
            "Rewinding live radio needs the mpv playback engine -- check "
            "Preferences > Playback engine."
        )

    @staticmethod
    def _radio_behind_live_phrase(behind: float) -> str:
        """A spoken 'how far behind live' fragment: 'Live.' under 5 seconds,
        else 'N seconds behind live.' / 'M minutes N seconds behind live.'"""
        seconds = int(round(behind))
        if seconds < 5:
            return "Live."
        if seconds < 60:
            return f"{seconds} seconds behind live."
        minutes, remainder = divmod(seconds, 60)
        plural = "" if minutes == 1 else "s"
        if remainder:
            return f"{minutes} minute{plural} {remainder} seconds behind live."
        return f"{minutes} minute{plural} behind live."

    def radio_toggle_volume_boost(self) -> None:
        """Volume Boost: amplify up to 50% past 100 for quiet streams
        (mpv engine). The 0-100 volume scale everywhere else is untouched."""
        history = self._radio_history
        history.volume_boost = not history.volume_boost
        radio_history.save_history(app_data_dir(), history)
        effective = self._radio_controller.set_volume_boost(history.volume_boost)
        if not history.volume_boost:
            self._announce("Volume Boost off.")
        elif effective:
            self._announce("Volume Boost on: up to 50 percent louder.")
        else:
            self._announce(
                "Volume Boost on. It takes effect on the mpv playback engine -- "
                "check Preferences > Playback engine."
            )

    def radio_toggle_title_announcements(self) -> None:
        history = self._radio_history
        history.announce_track_titles = not history.announce_track_titles
        radio_history.save_history(app_data_dir(), history)
        self._announce(
            "Track titles will be announced as they change."
            if history.announce_track_titles
            else "Track title announcements turned off."
        )

    # -- self-healing stream recovery (#1065) -----------------------------------

    def _radio_maybe_try_fallback_url(self, state: RadioPlaybackState) -> None:
        """A station whose stream fails heals itself (#1065).

        On a playback error, run the recovery ladder off-thread: re-resolve a
        moved StreamTheWorld mount, refresh from the directory, and -- unless
        the user turned it off -- scan the station's own website (Triton players
        and "Listen Live" links included). A confident hit is played
        automatically; anything ambiguous is announced so the user can pick it
        up in Find Streams. One attempt per station per session, so a truly dead
        station never loops."""
        from quill.ui.radio.player_controller import RadioPlayerState

        station = state.station
        if state.state is not RadioPlayerState.ERROR or station is None or self._safe_mode:
            return
        key = station.station_uuid or station.stream_url
        if self._radio_fallback_tried == key:
            return
        self._radio_fallback_tried = key
        allow_website = bool(getattr(self._radio_history, "recover_from_website", True))

        def _recover(**_kwargs: object) -> object:
            from quill.core.radio.recovery import recover_stream

            return recover_stream(station, allow_website=allow_website, safe_mode=self._safe_mode)

        def _done(_op: str, result: object) -> None:
            self._wx.CallAfter(self._radio_apply_recovery, result)

        self._task_manager.submit(
            "radio-stream-recovery",
            _recover,
            on_success=_done,
            on_failure=lambda *_a: None,
        )

    def _radio_apply_recovery(self, result: object) -> None:
        from quill.core.radio.recovery import RecoveryResult

        if not isinstance(result, RecoveryResult):
            return
        if result.station is not None:
            self._announce(result.message)
            # Self-heal the saved favorite so the next play starts from the good
            # URL, then play the healed station.
            favorite = self._radio_favorites.find(
                result.station.station_uuid or result.station.stream_url
            )
            if favorite is not None:
                favorite.station = result.station
                self._save_radio_favorites()
            self._radio_controller.play_station(result.station)
            return
        # No confident stream -- announce whatever we learned (candidates to
        # try via Find Streams, or simply that nothing was found).
        if result.message:
            self._announce(result.message)

    # -- wake-up timer ------------------------------------------------------------

    def _on_radio_wake_up(self, station: RadioStation) -> None:
        self._wx.CallAfter(self._apply_radio_wake_up, station)

    def _apply_radio_wake_up(self, station: RadioStation) -> None:
        self._radio_controller.play_station(station)
        self._announce(f"Good morning. {station.display_name} is coming on.")

    def open_wake_timer_dialog(self) -> None:
        """Wake-Up Timer...: the sleep timer's twin."""
        from quill.core.radio.wake_timer import load_wake_setting, save_wake_setting
        from quill.ui.radio.wake_timer_dialog import WakeUpTimerDialog

        controller = getattr(self, "_radio_controller", None)
        dialog = WakeUpTimerDialog(
            self.frame,
            setting=load_wake_setting(app_data_dir()),
            favorites=self._radio_favorites,
            now_playing=controller.state.station if controller is not None else None,
            announce_cb=self._announce,
        )
        updated = dialog.show()
        if updated is None:
            return
        save_wake_setting(app_data_dir(), updated)
        self._announce(updated.spoken_summary() if updated.enabled else "Wake-up timer turned off.")

    # -- record a different station ---------------------------------------------

    def open_record_station_dialog(self) -> None:
        """Record Station...: record B while listening to A (or to nothing)."""
        from quill.ui.radio.record_station_dialog import RecordStationDialog

        if not ffmpeg_available():
            self._show_message_box(
                self._radio_no_ffmpeg_message(),
                "Internet Radio",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        if self._radio_recorder.is_recording:
            self._announce(
                "A recording is already running; stop it first from the Recordings list."
            )
            return
        controller = getattr(self, "_radio_controller", None)
        dialog = RecordStationDialog(
            self.frame,
            favorites=self._radio_favorites,
            now_playing=controller.state.station if controller is not None else None,
            default_duration_minutes=min(60, self._radio_recording_settings.max_duration_minutes),
            announce_cb=self._announce,
        )
        choice = dialog.show()
        if choice is None:
            return
        station, minutes = choice
        try:
            self._radio_recorder.start(
                station_name=station.name,
                stream_url=station.stream_url,
                settings=self._radio_recording_settings,
                duration_minutes=minutes,
                filter_graph=self._radio_recording_filter_graph(),
            )
        except RecordingError as error:
            self._announce(str(error))
            return
        self._announce(f"Recording {station.display_name} for {minutes} minutes.")
        self._refresh_statusbar()

    def radio_play_last(self) -> None:
        """Play whatever was on last -- radio as an appliance."""
        station = self._radio_history.last_station
        if station is None:
            self._announce("Nothing in the radio history yet. Play a station first.")
            return
        self._radio_controller.play_station(station)
        self._announce(f"Playing {station.display_name}")

    def _append_radio_recent_submenu(self, menu: object) -> None:
        """A Recently Played submenu: the last stations, newest first.

        Replaying a station never adds a second row -- the store moves the
        existing entry to the front (de-duplicated by uuid/stream URL). When
        a recent station is also a favorite, it speaks the favorite's own
        display name so the two menus never read like different stations."""
        wx = self._wx
        stations = list(self._radio_history.stations)
        if not stations:
            return
        sub = wx.Menu()
        for station in stations:
            item_id = wx.NewIdRef()
            favorite = self._radio_favorites.find(station.station_uuid or station.stream_url)
            label = favorite.display_label if favorite is not None else station.display_name
            sub.Append(item_id, label)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
            self._retain_radio_menu_ids(item_id)
        menu.AppendSubMenu(sub, "Recently &Played")

    def _refresh_radio_tray_tooltip(self) -> None:
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        wx = self._wx
        controller = getattr(self, "_radio_controller", None)
        text = controller.state.status_text if controller is not None else ""
        # The tray icon's tooltip is also its accessible name: brand it with
        # the hosting app's own title ("Quill Radio" standalone, "Quill"
        # embedded) so tray navigation never reads the wrong product.
        app_name = self.frame.GetTitle() or "Quill"
        tooltip = f"{app_name} - {text}" if text and "stopped" not in text.lower() else app_name
        try:
            icon = getattr(self, "_app_icon", None) or wx.ArtProvider.GetIcon(
                wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
            )
            tray_icon.SetIcon(icon, tooltip)
        except Exception:  # noqa: BLE001 - tray tooltip refresh must never crash
            pass

    # -- status bar -----------------------------------------------------------

    def _radio_status_text(self) -> str:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return ""
        text = controller.state.status_text
        recorder = getattr(self, "_radio_recorder", None)
        if recorder is not None and recorder.is_recording:
            text += " (recording)"
        return text

    def radio_play_stop_toggle(self) -> None:
        """One transport action for menus rebuilt per popup: Stop while
        connecting/playing, resume when paused, replay the current station
        when stopped (live streams have no meaningful pause)."""
        from quill.ui.radio.player_controller import RadioPlayerState

        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        state = controller.state.state
        if state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING):
            self.radio_stop()
        else:
            self.radio_toggle_play_pause()

    def _build_radio_status_bar_menu(self, menu: object) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        wx = self._wx
        play_id, mute_id = wx.NewIdRef(), wx.NewIdRef()
        controller = getattr(self, "_radio_controller", None)
        playing = controller is not None and controller.state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
        )
        # One transport item (this menu is rebuilt on every popup, so the
        # label is always current): Stop while playing, Play otherwise --
        # the same single-button rule as the main panel and Playback menu.
        menu.Append(play_id, "Stop" if playing else "Play")
        menu.Append(mute_id, "Mute/Unmute")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_play_stop_toggle(), id=play_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=mute_id)
        self._append_radio_favorites_submenu(menu)
        self._append_radio_recent_submenu(menu)
        menu.AppendSeparator()
        recorder = getattr(self, "_radio_recorder", None)
        record_id, schedule_id, rec_settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        record_label = (
            "Stop Recording" if recorder is not None and recorder.is_recording else "Record Now"
        )
        menu.Append(record_id, record_label)
        menu.Append(schedule_id, "Schedule Recording...")
        menu.Append(rec_settings_id, "Recording Settings...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=record_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._radio_open_schedule_recording(), id=schedule_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._radio_open_recording_settings(), id=rec_settings_id)
        menu.AppendSeparator()
        browse_id = wx.NewIdRef()
        menu.Append(browse_id, "Browse Stations...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=browse_id)
        self._retain_radio_menu_ids(
            play_id, mute_id, record_id, schedule_id, rec_settings_id, browse_id
        )

    def _retain_radio_menu_ids(self, *refs: object) -> None:
        """Keep popup/submenu wx.NewIdRef objects alive while their menu can
        still fire. A dropped ref unreserves the id, and the next NewIdRef
        anywhere (another popup, an app-shell menu) can receive the same id --
        cross-wiring EVT_MENU bindings. Refs accumulate per host; rebuilt
        popups simply extend the list, which is bounded in practice."""
        refs_list = getattr(self, "_radio_menu_id_refs", None)
        if refs_list is None:
            refs_list = []
            self._radio_menu_id_refs = refs_list
        refs_list.extend(refs)

    def _append_acb_media_submenu(self, menu: object) -> None:
        """An ACB Media submenu: every stream in the built-in directory,
        playable inline -- no dialog hunt. Local data, no network."""
        from quill.core.radio import acb_media

        wx = self._wx
        stations = acb_media.acb_media_stations()
        if not stations:
            return
        sub = wx.Menu()
        for station in stations:
            item_id = wx.NewIdRef()
            sub.Append(item_id, station.display_name)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
            self._retain_radio_menu_ids(item_id)
        menu.AppendSubMenu(sub, "ACB &Media")

    def _append_radio_favorites_submenu(self, menu: object) -> None:
        wx = self._wx
        favorites = getattr(self, "_radio_favorites", None)
        if favorites is None or not favorites.favorites:
            return
        sub = wx.Menu()
        # Mirror the Favorites Manager's nested folders: each folder path
        # ("News/Morning") becomes a nested submenu, stations appended to
        # their folder's menu in store order.
        folder_menus: dict[str, object] = {"": sub}

        def folder_menu(path: str) -> object:
            existing = folder_menus.get(path)
            if existing is not None:
                return existing
            parent_path, _, name = path.rpartition("/")
            parent = folder_menu(parent_path)
            child = wx.Menu()
            parent.AppendSubMenu(child, name)
            folder_menus[path] = child
            return child

        for favorite in favorites.favorites:
            station = favorite.station
            item_id = wx.NewIdRef()
            folder_menu(favorite.folder).Append(item_id, favorite.display_label)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
            self._retain_radio_menu_ids(item_id)
        menu.AppendSubMenu(sub, "Favorite Stations")

    # -- system tray ----------------------------------------------------------

    def _build_radio_tray_menu(self, menu: object) -> None:
        wx = self._wx
        controller = getattr(self, "_radio_controller", None)
        now_playing_id = wx.NewIdRef()
        menu.Append(
            now_playing_id, controller.state.status_text if controller else "Radio: stopped"
        )
        menu.Enable(now_playing_id, False)
        self._retain_radio_menu_ids(now_playing_id)
        self._build_radio_status_bar_menu(menu)

    # -- commands ---------------------------------------------------------

    def radio_toggle_play_pause(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.toggle_play_pause()
        self._announce(controller.state.status_text)

    def radio_stop(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.stop()
        self._announce("Radio stopped")

    def radio_mute_toggle(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.toggle_mute()
        self._announce("Radio muted" if controller.state.muted else "Radio unmuted")

    def radio_volume_up(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.volume_up()
        self._announce(f"Radio volume {controller.state.volume_percent}")

    def radio_volume_down(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.volume_down()
        self._announce(f"Radio volume {controller.state.volume_percent}")

    def _on_radio_enhance_error(self, message: str) -> None:
        """Sound Enhancements couldn't start (ffmpeg missing, relay failed);
        playback still proceeds unenhanced, so this is an announcement, not a
        blocking dialog."""
        self._announce(f"Sound Enhancements: {message} Playing without it.")

    def _on_radio_output_device_error(self, message: str) -> None:
        """The chosen output device couldn't be used (libmpv missing or the
        engine failed); playback still proceeds on the system default, so
        this is an announcement, not a blocking dialog (#1076)."""
        self._announce(message)

    def _radio_resolve_enhancement(self, station: RadioStation) -> tuple[float, float, float, bool]:
        """(bass_db, mid_db, treble_db, compressor_enabled) for *station*:
        its own remembered Sound Enhancements if it's a favorite with an
        override, else the shared default -- called by RadioPlayerController
        on every play_station."""
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if favorite is not None and favorite.has_sound_enhancement_override:
            return (
                favorite.eq_bass_db,
                favorite.eq_mid_db,
                favorite.eq_treble_db,
                favorite.compressor_enabled,
            )
        history = self._radio_history
        return (
            history.eq_bass_db,
            history.eq_mid_db,
            history.eq_treble_db,
            history.compressor_enabled,
        )

    def _radio_resolve_volume(self, station: RadioStation) -> int:
        """The memorized volume (0-100) for *station*, or -1 when it's not a
        favorite or has none recorded yet -- called by RadioPlayerController
        on every play_station. A -1 tells the controller to leave the
        current volume alone rather than force a default."""
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if favorite is not None and favorite.volume_percent >= 0:
            return favorite.volume_percent
        return -1

    def _radio_enhance_context_favorite(self) -> FavoriteStation | None:
        """The favorite Sound Enhancements edits right now: the currently
        playing station, if it's a favorite -- None means edit the shared
        default instead (mirrors PodcastManagerDialog._sort_context_show)."""
        station = self._radio_controller.state.station
        if station is None:
            return None
        key = station.station_uuid or station.stream_url
        return self._radio_favorites.find(key)

    # -- dialogs ------------------------------------------------------------

    def open_sound_enhancements(self) -> None:
        """Playback > Sound Enhancements...: a three-band EQ + a compressor.
        Edits the currently-playing station's own override if it's a
        favorite, otherwise the shared default -- see
        RadioFavoritesStore.set_enhancement."""
        from quill.core.radio import history as radio_history
        from quill.ui.sound_enhance_dialog import SoundEnhanceDialog

        history = self._radio_history
        favorite = self._radio_enhance_context_favorite()
        if favorite is not None and favorite.has_sound_enhancement_override:
            bass, mid, treble, compressor = (
                favorite.eq_bass_db,
                favorite.eq_mid_db,
                favorite.eq_treble_db,
                favorite.compressor_enabled,
            )
        else:
            bass, mid, treble, compressor = (
                history.eq_bass_db,
                history.eq_mid_db,
                history.eq_treble_db,
                history.compressor_enabled,
            )
        on_reset = None
        if favorite is not None and favorite.has_sound_enhancement_override:

            def on_reset(favorite: FavoriteStation = favorite) -> None:
                self._radio_favorites.clear_enhancement_override(favorite.key)
                self._save_radio_favorites()
                state = self._radio_controller.state
                if (
                    state.station is not None
                    and (state.station.station_uuid or state.station.stream_url) == favorite.key
                ):
                    self._radio_controller.set_enhancement(
                        bass_db=history.eq_bass_db,
                        mid_db=history.eq_mid_db,
                        treble_db=history.eq_treble_db,
                        compressor_enabled=history.compressor_enabled,
                    )
                self._announce(
                    f"Sound Enhancements for {favorite.display_label}: back to the shared default."
                )

        dialog = SoundEnhanceDialog(
            self.frame,
            bass_db=bass,
            mid_db=mid,
            treble_db=treble,
            compressor_enabled=compressor,
            subject=favorite.display_label if favorite is not None else "station",
            show_sound_options=True,
            mono_enabled=history.mono_enabled,
            night_mode_enabled=history.night_mode_enabled,
            announce_cb=self._announce,
            on_reset=on_reset,
        )
        result = dialog.show()
        if result is None:
            return
        bass_db, mid_db, treble_db, compressor_enabled, _smart_speed_not_applicable = result
        # Listener-level sound options: always shared (they describe the
        # listener, not a station), regardless of a per-station EQ override.
        mono_enabled, night_mode_enabled = dialog.sound_options
        if (mono_enabled, night_mode_enabled) != (history.mono_enabled, history.night_mode_enabled):
            history.mono_enabled = mono_enabled
            history.night_mode_enabled = night_mode_enabled
            radio_history.save_history(app_data_dir(), history)
            self._radio_controller.set_sound_options(
                mono_enabled=mono_enabled, night_mode_enabled=night_mode_enabled
            )
        if favorite is not None:
            self._radio_favorites.set_enhancement(
                favorite.key,
                bass_db=bass_db,
                mid_db=mid_db,
                treble_db=treble_db,
                compressor_enabled=compressor_enabled,
            )
            self._save_radio_favorites()
            target = favorite.display_label
        else:
            history.eq_bass_db = bass_db
            history.eq_mid_db = mid_db
            history.eq_treble_db = treble_db
            history.compressor_enabled = compressor_enabled
            radio_history.save_history(app_data_dir(), history)
            target = "the shared default"
        self._radio_controller.set_enhancement(
            bass_db=bass_db,
            mid_db=mid_db,
            treble_db=treble_db,
            compressor_enabled=compressor_enabled,
        )
        self._announce(
            f"Sound Enhancements for {target}: Bass {bass_db:+.0f}, Mid {mid_db:+.0f}, "
            f"Treble {treble_db:+.0f}" + (", Even Out Volume on" if compressor_enabled else "")
        )

    def open_manage_radio_favorites(self) -> None:
        """Manage Favorites...: search, play, remove, reorder, nested folders.

        Shared verbatim by embedded QUILL and standalone Quill Radio; every
        change persists immediately through the same store both read."""
        from quill.ui.radio.favorites_manager_dialog import FavoritesManagerDialog

        dlg = FavoritesManagerDialog(
            self.frame,
            favorites=self._radio_favorites,
            controller=self._radio_controller,
            announce_cb=self._announce,
            on_changed=self._save_radio_favorites,
        )
        dlg.show()
        self._refresh_statusbar()

    def open_radio_recordings(self) -> None:
        """Recordings...: made, in-progress (live status), and scheduled."""
        from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog

        dlg = RecordingsManagerDialog(
            self.frame,
            recorder=self._radio_recorder,
            settings=self._radio_recording_settings,
            scheduler=self._radio_scheduler,
            controller=self._radio_controller,
            announce_cb=self._announce,
        )
        dlg.show()
        self._refresh_statusbar()

    def open_internet_radio(self) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        dlg = StationBrowserDialog(
            self.frame,
            controller=self._radio_controller,
            favorites_store=self._radio_favorites,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_favorites_changed=self._save_radio_favorites,
            on_open_add_custom=self._radio_open_add_custom,
            on_open_link_finder=self._radio_open_link_finder,
        )
        dlg.show()
        self._refresh_statusbar()

    def _radio_open_add_custom(self, prefill: RadioStation | None) -> None:
        dlg = AddStationDialog(
            self.frame,
            controller=self._radio_controller,
            prefill=prefill,
            announce_cb=self._announce,
        )
        station = dlg.show()
        if station is None:
            return
        self._radio_favorites.add(station, custom=True)
        self._save_radio_favorites()
        self._announce(f"Added {station.name} to Favorites")

    def _radio_open_link_finder(self) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        dlg = LinkFinderDialog(
            self.frame,
            controller=self._radio_controller,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_use_link=self._radio_open_add_custom,
        )
        dlg.show()

    # -- command palette registration ----------------------------------------

    def _register_radio_commands(self) -> None:
        for command_id, title, handler in (
            ("radio.browse", "Internet Radio: Browse Stations...", self.open_internet_radio),
            ("radio.play_pause", "Internet Radio: Play/Pause", self.radio_toggle_play_pause),
            ("radio.stop", "Internet Radio: Stop", self.radio_stop),
            ("radio.mute_toggle", "Internet Radio: Mute/Unmute", self.radio_mute_toggle),
            ("radio.volume_up", "Internet Radio: Volume Up", self.radio_volume_up),
            ("radio.volume_down", "Internet Radio: Volume Down", self.radio_volume_down),
            (
                "radio.add_custom_station",
                "Internet Radio: Add Custom Station...",
                lambda: self._radio_open_add_custom(None),
            ),
            (
                "radio.find_streams",
                "Internet Radio: Find Streams from a Website...",
                self._radio_open_link_finder,
            ),
            (
                "radio.manage_favorites",
                "Internet Radio: Manage Favorites...",
                self.open_manage_radio_favorites,
            ),
            (
                "radio.play_last",
                "Internet Radio: Play Last Station",
                self.radio_play_last,
            ),
            (
                "radio.whats_playing",
                "Internet Radio: What's Playing?",
                self.radio_whats_playing,
            ),
            (
                "radio.toggle_title_announcements",
                "Internet Radio: Announce Track Titles On/Off",
                self.radio_toggle_title_announcements,
            ),
            (
                "radio.rewind",
                "Internet Radio: Rewind 30 Seconds",
                self.radio_rewind,
            ),
            (
                "radio.forward",
                "Internet Radio: Forward 30 Seconds",
                self.radio_forward,
            ),
            (
                "radio.jump_to_live",
                "Internet Radio: Back to Live",
                self.radio_jump_to_live,
            ),
            (
                "radio.volume_boost",
                "Internet Radio: Volume Boost On/Off",
                self.radio_toggle_volume_boost,
            ),
            (
                "radio.sound_enhancements",
                "Internet Radio: Sound Enhancements...",
                self.open_sound_enhancements,
            ),
            (
                "radio.record_toggle",
                "Internet Radio: Record Now / Stop Recording",
                self.radio_record_toggle,
            ),
            (
                "radio.schedule_recording",
                "Internet Radio: Schedule Recording...",
                self._radio_open_schedule_recording,
            ),
            (
                "radio.recording_settings",
                "Internet Radio: Recording Settings...",
                self._radio_open_recording_settings,
            ),
            (
                "radio.recordings",
                "Internet Radio: Recordings...",
                self.open_radio_recordings,
            ),
            (
                "radio.record_station",
                "Internet Radio: Record Station...",
                self.open_record_station_dialog,
            ),
            (
                "radio.wake_timer",
                "Internet Radio: Wake-Up Timer...",
                self.open_wake_timer_dialog,
            ),
        ):
            self.commands.try_register(
                command_id, title, handler, self._binding_for(command_id), feature_id="core.radio"
            )
