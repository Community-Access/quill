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
        )
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

    def radio_record_toggle(self) -> None:
        if not ffmpeg_available():
            self._show_message_box(
                _NO_FFMPEG_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
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
            )
        except RecordingError as error:
            self._announce(str(error))
            return
        self._announce(f"Recording {station.name}")
        self._refresh_statusbar()

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
        while it plays, and gets it back the next time it starts)."""
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
            if favorite is not None and favorite.volume_percent >= 0:
                controller = self._radio_controller
                if state.volume_percent != favorite.volume_percent:
                    controller.set_volume(favorite.volume_percent)
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
            self._wx.CallAfter(self._radio_apply_track_title, str(title or ""), announce_result)

        self._task_manager.submit(
            "radio-track-title",
            _fetch,
            on_success=_done,
            on_failure=lambda *_a: None,
        )

    def _radio_apply_track_title(self, title: str, announce_result: bool) -> None:
        changed = bool(title) and title != self._radio_track_title
        if title:
            self._radio_track_title = title
        if announce_result:
            self._announce(
                f"Now playing: {title}" if title else "This stream doesn't share track titles."
            )
            return
        if changed and self._radio_history.announce_track_titles:
            self._announce(f"Now playing: {title}")

    def radio_whats_playing(self) -> None:
        """Speak the current track title on demand."""
        if self._radio_track_title:
            self._announce(f"Now playing: {self._radio_track_title}")
            return
        self._radio_fetch_track_title(announce_result=True)

    def radio_toggle_title_announcements(self) -> None:
        history = self._radio_history
        history.announce_track_titles = not history.announce_track_titles
        radio_history.save_history(app_data_dir(), history)
        self._announce(
            "Track titles will be announced as they change."
            if history.announce_track_titles
            else "Track title announcements turned off."
        )

    # -- stream fallback --------------------------------------------------------

    def _radio_maybe_try_fallback_url(self, state: RadioPlaybackState) -> None:
        """A dead favorite heals itself: on a playback error for a station the
        RadioBrowser directory knows, fetch its current URL and retry once."""
        from quill.ui.radio.player_controller import RadioPlayerState

        station = state.station
        if state.state is not RadioPlayerState.ERROR or station is None:
            return
        uuid = station.station_uuid
        key = uuid or station.stream_url
        if not uuid or self._safe_mode or self._radio_fallback_tried == key:
            return
        self._radio_fallback_tried = key
        old_url = station.stream_url

        def _fetch(**_kwargs: object) -> object:
            return radio_browser.lookup_station(uuid, safe_mode=self._safe_mode)

        def _done(_op: str, fresh: object) -> None:
            self._wx.CallAfter(self._radio_apply_fallback, fresh, old_url)

        self._task_manager.submit(
            "radio-stream-fallback",
            _fetch,
            on_success=_done,
            on_failure=lambda *_a: None,
        )

    def _radio_apply_fallback(self, fresh: object, old_url: str) -> None:
        station = fresh if isinstance(fresh, RadioStation) else None
        if station is None or station.stream_url == old_url:
            return
        self._announce("That stream has moved; trying its current address.")
        # Self-heal the saved favorite so the next play starts from the good URL.
        favorite = self._radio_favorites.find(station.station_uuid)
        if favorite is not None:
            favorite.station = station
            self._save_radio_favorites()
        self._radio_controller.play_station(station)

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
                _NO_FFMPEG_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
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

    def _build_radio_status_bar_menu(self, menu: object) -> None:
        wx = self._wx
        play_id, stop_id, mute_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        menu.Append(play_id, "Play/Pause")
        menu.Append(stop_id, "Stop")
        menu.Append(mute_id, "Mute/Unmute")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_toggle_play_pause(), id=play_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_stop(), id=stop_id)
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
        menu.Append(browse_id, "Open Internet Radio...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=browse_id)
        self._retain_radio_menu_ids(
            play_id, stop_id, mute_id, record_id, schedule_id, rec_settings_id, browse_id
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

    # -- dialogs ------------------------------------------------------------

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
