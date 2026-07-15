"""Quill Radio -- Internet Radio as a standalone app.

Reuses ``RadioMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin

_TITLE = "Quill Radio"
_VERSION = "1.0.0"
_REPO = "Community-Access/quill-radio"


class RadioAppFrame(AppShellFrame, RadioMixin, AdpMixin, UnlockCodesMixin):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        self._init_radio()
        self._build_menu_bar()
        self._build_main_panel()
        self._register_radio_commands()
        self._register_adp_commands()
        self._register_unlock_code_commands()
        self._ensure_tray_icon(self._build_radio_tray_menu, tooltip=_TITLE)
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_radio_app_close)

    # -- main panel -------------------------------------------------------------
    #
    # A bare frame with only a menu bar leaves keyboard focus with nowhere to
    # land: Tab does nothing and a screen reader reads an empty client area.
    # The main panel gives the app a real, named, tabbable surface -- the
    # favorites list is the heart of the app and takes focus on launch.

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        self._now_playing_text = wx.StaticText(panel, label="Radio: stopped")
        set_accessible_name(self._now_playing_text, "Now playing")
        root.Add(self._now_playing_text, 0, wx.EXPAND | wx.ALL, 8)

        favorites_label = wx.StaticText(panel, label="&Favorite stations:")
        root.Add(favorites_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._favorites_list = wx.ListBox(panel)
        set_accessible_name(self._favorites_list, "Favorite stations")
        root.Add(self._favorites_list, 1, wx.EXPAND | wx.ALL, 8)
        self._favorites_list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._play_selected_favorite())
        self._favorites_list.Bind(wx.EVT_KEY_DOWN, self._on_favorites_key)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        # One transport button, not two: it reads Play when idle and Stop
        # while connecting/playing, so the panel never shows a dead button.
        self._play_stop_btn = wx.Button(panel, label="&Play")
        set_accessible_name(self._play_stop_btn, "Play")
        self._play_stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_play_stop_button())
        buttons.Add(self._play_stop_btn, 0, wx.RIGHT, 6)
        for label, handler in (
            ("&Record", lambda _e: self.radio_record_toggle()),
            ("&Browse Stations...", lambda _e: self.open_internet_radio()),
        ):
            button = wx.Button(panel, label=label)
            set_accessible_name(button, label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_favorites_list()
        self._favorites_list.SetFocus()

    def _on_favorites_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._play_selected_favorite()
            return
        event.Skip()

    def _on_play_stop_button(self) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        state = self._radio_controller.state.state
        if state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING):
            self.radio_stop()
        elif state is RadioPlayerState.PAUSED:
            self.radio_toggle_play_pause()
        else:
            self._play_selected_favorite()

    def _refresh_play_stop_button(self) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        state = self._radio_controller.state.state
        stopping = state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
        label = "&Stop" if stopping else "&Play"
        button = getattr(self, "_play_stop_btn", None)
        if button is not None and button.GetLabel() != label:
            button.SetLabel(label)
            set_accessible_name(button, "Stop" if stopping else "Play")
        menu_bar = self.frame.GetMenuBar()
        item_id = getattr(self, "_play_menu_item_id", None)
        if menu_bar is not None and item_id is not None:
            menu_bar.SetLabel(int(item_id), f"{label}\tCtrl+P")

    def _play_selected_favorite(self) -> None:
        index = self._favorites_list.GetSelection()
        favorites = self._radio_favorites.favorites
        if index < 0 or index >= len(favorites):
            self._announce("No station selected. Add favorites from Browse Stations.")
            return
        station = favorites[index].station
        self._radio_controller.play_station(station)
        self._announce(f"Playing {station.display_name}")

    def _reload_favorites_list(self) -> None:
        favorites = self._radio_favorites.favorites
        selected = self._favorites_list.GetSelection()
        self._favorites_list.Set([f.station.display_name for f in favorites])
        if favorites:
            self._favorites_list.SetSelection(selected if 0 <= selected < len(favorites) else 0)

    # -- menu bar -------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        station_menu = wx.Menu()
        browse_id, add_id, find_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(browse_id, "&Browse Stations...")
        station_menu.Append(add_id, "&Add Custom Station...")
        station_menu.Append(find_id, "Find &Streams from a Website...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=browse_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_add_custom(None), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_link_finder(), id=find_id)
        station_menu.AppendSeparator()
        self._append_radio_favorites_submenu(station_menu)
        menu_bar.Append(station_menu, "&Station")

        playback_menu = wx.Menu()
        self._now_playing_item_id = wx.NewIdRef()
        playback_menu.Append(self._now_playing_item_id, "Radio: stopped")
        playback_menu.Enable(self._now_playing_item_id, False)
        playback_menu.AppendSeparator()
        # One transport item mirroring the main panel's single button: it
        # reads Play when idle and Stop while connecting/playing -- no
        # separate, ambiguous Play/Pause + Stop pair.
        self._play_menu_item_id = wx.NewIdRef()
        playback_menu.Append(self._play_menu_item_id, "&Play\tCtrl+P")
        mute_id, vol_up_id, vol_down_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        playback_menu.Append(mute_id, "&Mute/Unmute\tCtrl+M")
        playback_menu.Append(vol_up_id, "Volume &Up\tCtrl+Up")
        playback_menu.Append(vol_down_id, "Volume &Down\tCtrl+Down")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._on_play_stop_button(), id=self._play_menu_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=mute_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_up(), id=vol_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_down(), id=vol_down_id)
        menu_bar.Append(playback_menu, "&Playback")

        record_menu = wx.Menu()
        record_id, schedule_id, settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        record_menu.Append(record_id, "&Record Now / Stop Recording")
        record_menu.Append(schedule_id, "&Schedule Recording...")
        record_menu.Append(settings_id, "Recording &Settings...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=record_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._radio_open_schedule_recording(), id=schedule_id
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._radio_open_recording_settings(), id=settings_id
        )
        menu_bar.Append(record_menu, "&Record")

        # Unlock-gated: a top-level Audio Description Project menu, absent
        # entirely until future.adp_assistant is unlocked (Help > Redeem
        # Unlock Code..., here or in QUILL -- they share one unlock store).
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, "A&udio Description Project")

        help_menu = wx.Menu()
        redeem_id, updates_id, about_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        help_menu.Append(redeem_id, "Redeem &Unlock Code...")
        help_menu.Append(updates_id, "Check for Up&dates...")
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About Quill Radio")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_redeem_unlock_code_dialog(), id=redeem_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self.frame.SetMenuBar(menu_bar)

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "Internet Radio from Quill, as a standalone app.\n\n"
            "Runs the same radio feature code as QUILL itself and shares its "
            "settings, favorites, and recordings.\n"
            f"https://github.com/{_REPO}",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    # -- status ---------------------------------------------------------------

    def _refresh_statusbar(self) -> None:
        text = self._radio_status_text() or "Radio: stopped"
        self._set_status(text)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing = getattr(self, "_now_playing_text", None)
        if now_playing is not None:
            now_playing.SetLabel(text)
        self._refresh_play_stop_button()
        if getattr(self, "_favorites_list", None) is not None:
            self._reload_favorites_list()

    # -- lifecycle --------------------------------------------------------------

    def _on_radio_app_close(self, event: wx.CloseEvent) -> None:
        for action in (
            getattr(self._radio_controller, "shutdown", None),
            getattr(self._radio_recorder, "shutdown", None),
            getattr(self._radio_scheduler, "shutdown", None),
        ):
            if action is None:
                continue
            try:
                action()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                pass
        self._task_manager.shutdown(wait=False)
        self._remove_tray_icon()
        event.Skip()


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    app = wx.App()
    frame = RadioAppFrame(safe_mode=safe_mode)
    frame.frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
