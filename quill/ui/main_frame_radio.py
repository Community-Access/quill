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
from quill.core.radio import radio_browser
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
        self._radio_ever_played = False
        self._radio_controller = RadioPlayerController(
            self.frame,
            on_state_changed=self._on_radio_state_changed,
            on_register_click=self._radio_register_click,
        )
        self._radio_recording_settings = load_recording_settings(app_data_dir())
        self._radio_recorder = RadioRecorder(on_state_changed=self._on_radio_recording_changed)
        self._radio_scheduler = RecordingScheduler(
            data_dir=app_data_dir(),
            recorder=self._radio_recorder,
            recording_settings=self._radio_recording_settings,
            on_fired=self._on_radio_scheduled_recording_fired,
        )

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

        if state.station is not None and not self._radio_ever_played:
            self._radio_ever_played = True
            hidden = list(getattr(self.settings, "status_bar_hidden", []))
            if "radio_player" in hidden:
                hidden.remove("radio_player")
                self.settings.status_bar_hidden = hidden
                save_settings(self.settings)
        self._refresh_statusbar()
        self._refresh_radio_tray_tooltip()

    def _refresh_radio_tray_tooltip(self) -> None:
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        wx = self._wx
        controller = getattr(self, "_radio_controller", None)
        text = controller.state.status_text if controller is not None else ""
        tooltip = f"Quill - {text}" if text and "stopped" not in text.lower() else "Quill"
        try:
            icon = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
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

    def _append_radio_favorites_submenu(self, menu: object) -> None:
        wx = self._wx
        favorites = getattr(self, "_radio_favorites", None)
        if favorites is None or not favorites.favorites:
            return
        sub = wx.Menu()
        for favorite in favorites.favorites:
            station = favorite.station
            item_id = wx.NewIdRef()
            sub.Append(item_id, station.display_name)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
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
        ):
            self.commands.try_register(
                command_id, title, handler, self._binding_for(command_id), feature_id="core.radio"
            )
