"""Quill Radio -- Internet Radio as a standalone app.

Reuses ``RadioMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.core import http_client
from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin

_TITLE = "Quill Radio"
_VERSION = "1.1.0"
_REPO = "Community-Access/quill-radio"
http_client.set_product_identity(_TITLE, _VERSION)  # radio User-Agent identity (#6)

#: RadioHistory.close_action's Preferences combo box (see also
#: RadioCloseConfirmDialog, which writes this same field via "Don't ask me
#: again").
_CLOSE_ACTION_LABELS = ("Ask every time", "Exit", "Minimize to Tray")
_CLOSE_ACTION_VALUES = ("ask", "exit", "minimize")

#: The What's Playing (Ctrl+T) announcement template and its accessible help,
#: shown as a text field in Preferences (#1068). Blank restores the default.
_DEFAULT_NOW_PLAYING_TEMPLATE = "{title}[ by {artist}]"
_NOW_PLAYING_HELP = (
    "How What's Playing (Ctrl+T) reads a track. Use {title} and {artist}; "
    "put optional wording in [square brackets] to hide it when that field is "
    "empty (the default {title}[ by {artist}] drops the ' by' when there is no "
    "artist). {raw} is the stream's exact original text. Leave blank to restore "
    "the default."
)

#: The Preferences "Radio output device" dropdown (#1076): "" (System
#: default) plays to the default device; a device name routes just the
#: radio there (needs the mpv engine). Earcons and your screen reader stay
#: on the system default device.
_OUTPUT_DEVICE_HELP = (
    "The sound card radio playback comes out of. System default keeps "
    "everything as it is today; choosing a device sends just the radio "
    "there -- your screen reader and Quill Radio's own sounds stay on the "
    "system default device."
)

#: RadioHistory.playback_engine's Preferences combo box. Automatic = mpv
#: when installed (device routing, pause/rewind live, Volume Boost, more
#: station formats), else Windows Media; the explicit entries are the
#: escape hatch / insist options.
_ENGINE_LABELS = ("Automatic (recommended)", "Windows Media (classic)", "mpv")
_ENGINE_VALUES = ("auto", "wx", "mpv")
_ENGINE_HELP = (
    "Which audio engine plays the radio. Automatic uses mpv when it is "
    "installed -- that is what enables the output device choice, pausing "
    "and rewinding live radio, Volume Boost, and stations in more formats "
    "-- and Windows Media otherwise. Windows Media (classic) is exactly "
    "the pre-1.1 behavior."
)


class RadioAppFrame(AppShellFrame, RadioMixin, MediaSleepTimerMixin, AdpMixin, UnlockCodesMixin):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        self._init_radio()
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(lambda: self._radio_history.announce_dialog_transitions)
        self._init_media_sleep_timer()
        self._build_menu_bar()
        self._build_main_panel()
        self._register_radio_commands()
        self._register_media_sleep_timer_commands()
        self._register_adp_commands()
        self._register_unlock_code_commands()
        self._ensure_tray_icon(self._build_radio_tray_menu, tooltip=_TITLE)
        self._register_media_keys({
            "play_pause": self._on_play_stop_button,
            "stop": self.radio_stop,
        })
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_radio_app_close)
        # Alt+F4-to-tray (opt-in preference): intercepted at the char hook,
        # before Windows turns it into a close, so the window tucks away with
        # playback running. The titlebar X and Exit keep close_action.
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_radio_char_hook)
        self._maybe_resume_last_station()
        # Deferred (CallAfter), not inline: this touches the network, and a
        # launch is not the place to do that before the window is even up.
        wx.CallAfter(self._maybe_check_updates_on_startup)

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
        # The same nested folder tree the Favorites Manager shows -- the
        # structure you build is right on the main page, not behind a dialog.
        self._favorites_tree = wx.TreeCtrl(
            panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT
        )
        set_accessible_name(
            self._favorites_tree,
            "Favorite stations, organized in your folders; Enter plays, Delete "
            "removes, F2 renames, Shift+F10 opens all actions",
        )
        # Low-vision legibility (#3): pin the tree to the theme-resolved system
        # colours so it is never near-invisible on a mismatched default.
        from quill.ui.radio.favorites_manager_dialog import apply_readable_tree_colours

        apply_readable_tree_colours(self._favorites_tree)
        root.Add(self._favorites_tree, 1, wx.EXPAND | wx.ALL, 8)
        self._favorites_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_favorites_activated)
        self._favorites_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_favorites_context_menu)
        self._favorites_tree.Bind(wx.EVT_KEY_DOWN, self._on_favorites_key)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        # One transport button, not two: it reads Play when idle and Stop
        # while connecting/playing, so the panel never shows a dead button.
        self._play_stop_btn = wx.Button(panel, label="&Play")
        set_accessible_name(self._play_stop_btn, "Play")
        self._play_stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_play_stop_button())
        buttons.Add(self._play_stop_btn, 0, wx.RIGHT, 6)
        # Favorite toggle for whatever is on right now: Add while listening
        # to something new (from ACB Media, Recently Played, a test...),
        # Remove when the playing station is already saved.
        self._favorite_toggle_btn = wx.Button(panel, label="Add to Fa&vorites")
        set_accessible_name(self._favorite_toggle_btn, "Add the playing station to favorites")
        self._favorite_toggle_btn.Enable(False)
        self._favorite_toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_favorite_toggle())
        buttons.Add(self._favorite_toggle_btn, 0, wx.RIGHT, 6)
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
        self._reload_favorites_tree()
        self._favorites_tree.SetFocus()

    # -- favorites tree ---------------------------------------------------------

    def _reload_favorites_tree(self, keep_key: str | None = None) -> None:
        tree = self._favorites_tree
        if keep_key is None:
            selected = self._selected_tree_data()
            if selected is not None and selected[0] == "station":
                keep_key = selected[1]
        tree.DeleteAllItems()
        root = tree.AddRoot("Favorites")
        folder_items: dict[str, wx.TreeItemId] = {}
        select_item = None

        def folder_item(path: str) -> wx.TreeItemId:
            if not path:
                return root
            existing = folder_items.get(path)
            if existing is not None:
                return existing
            parent_path, _, name = path.rpartition("/")
            item = tree.AppendItem(folder_item(parent_path), name)
            tree.SetItemData(item, ("folder", path))
            folder_items[path] = item
            return item

        store = self._radio_favorites
        for path in store.folder_names():
            folder_item(path)
        for favorite in store.favorites:
            item = tree.AppendItem(folder_item(favorite.folder), favorite.display_label)
            tree.SetItemData(item, ("station", favorite.key))
            if favorite.key == keep_key:
                select_item = item
        tree.ExpandAll()
        first, _cookie = tree.GetFirstChild(root)
        if select_item is not None:
            tree.SelectItem(select_item)
        elif first.IsOk():
            tree.SelectItem(first)

    def _selected_tree_data(self) -> tuple[str, str] | None:
        tree = getattr(self, "_favorites_tree", None)
        if tree is None:
            return None
        item = tree.GetSelection()
        if not item.IsOk():
            return None
        data = tree.GetItemData(item)
        return data if isinstance(data, tuple) and len(data) == 2 else None

    def _selected_favorite(self):
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "station":
            return None
        return self._radio_favorites.find(selected[1])

    def _on_favorites_activated(self, event: wx.CommandEvent) -> None:
        selected = self._selected_tree_data()
        if selected is not None and selected[0] == "station":
            self._play_selected_favorite()
            return
        event.Skip()  # a folder: let the tree toggle it

    def _on_favorites_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_favorites_activated(event)
            return
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_tree_remove()
            return
        if code == wx.WXK_F2:
            self._on_tree_rename()
            return
        # The tree wants arrow keys for its own navigation (Win32 grants a
        # focused TreeCtrl first claim on WM_KEYDOWN for Up/Down), so the
        # Playback menu's Ctrl+Up/Ctrl+Down accelerator never reaches the
        # frame while focus is here -- the tree just moves its selection
        # cursor instead. Handle the volume chord directly, same as Enter/
        # Delete/F2 above, so it works from the tree (the default focus on
        # launch) and not only when focus happens to be elsewhere.
        if event.ControlDown() and not event.ShiftDown() and not event.AltDown():
            if code == wx.WXK_UP:
                self.radio_volume_up()
                return
            if code == wx.WXK_DOWN:
                self.radio_volume_down()
                return
        event.Skip()

    def _on_favorites_context_menu(self, _event: object) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        selected = self._selected_tree_data()
        if selected is None:
            return
        menu = wx.Menu()
        entries: list[tuple[str, object]] = []
        if selected[0] == "station":
            favorite = self._selected_favorite()
            playing = (
                favorite is not None
                and self._radio_controller.state.station is not None
                and self._radio_controller.state.station.stream_url == favorite.station.stream_url
                and self._radio_controller.state.state
                in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
            )
            entries = [
                ("&Stop" if playing else "&Play", self._on_play_stop_context),
                ("Rena&me...\tF2", self._on_tree_rename),
                ("Move to F&older...", self._on_tree_move_to_folder),
                ("&Remove...\tDelete", self._on_tree_remove),
                ("New F&older...\tCtrl+Shift+E", self._on_new_folder),
                ("Manage Fa&vorites...", self.open_manage_radio_favorites),
            ]
        else:
            entries = [
                ("Rena&me Folder...\tF2", self._on_tree_rename),
                ("&Delete Folder...", self._on_tree_remove),
                ("New F&older...\tCtrl+Shift+E", self._on_new_folder),
                ("Manage Fa&vorites...", self.open_manage_radio_favorites),
            ]
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._keep_menu_ids(*id_refs)
        self._favorites_tree.PopupMenu(menu)
        menu.Destroy()

    def _on_play_stop_context(self) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        favorite = self._selected_favorite()
        if favorite is None:
            return
        state = self._radio_controller.state
        if (
            state.station is not None
            and state.station.stream_url == favorite.station.stream_url
            and state.state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
        ):
            self.radio_stop()
        else:
            self._radio_controller.play_station(favorite.station)
            self._announce(f"Playing {favorite.display_label}")

    def _on_tree_rename(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        if selected is None:
            return
        if selected[0] == "station":
            favorite = self._selected_favorite()
            if favorite is not None and favorite_actions.rename_favorite(
                self.frame, self._radio_favorites, favorite, announce=self._announce
            ):
                self._save_radio_favorites()
                self._reload_favorites_tree(keep_key=favorite.key)
        elif favorite_actions.rename_folder_prompt(
            self.frame, self._radio_favorites, selected[1], announce=self._announce
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_tree_remove(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        if selected is None:
            return
        if selected[0] == "station":
            favorite = self._selected_favorite()
            if favorite is not None and favorite_actions.remove_favorite(
                self.frame, self._radio_favorites, favorite, announce=self._announce
            ):
                self._save_radio_favorites()
                self._reload_favorites_tree()
        elif favorite_actions.delete_folder_prompt(
            self.frame, self._radio_favorites, selected[1], announce=self._announce
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_new_folder(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        initial_parent = selected[1] if selected is not None and selected[0] == "folder" else ""
        if favorite_actions.create_folder_prompt(
            self.frame,
            self._radio_favorites,
            announce=self._announce,
            initial_parent=initial_parent,
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_tree_move_to_folder(self) -> None:
        from quill.ui.radio import favorite_actions

        favorite = self._selected_favorite()
        if favorite is None:
            return
        if favorite_actions.move_favorite_to_folder(
            self.frame, self._radio_favorites, favorite, announce=self._announce
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree(keep_key=favorite.key)

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
        self._refresh_favorite_toggle()

    def _refresh_favorite_toggle(self) -> None:
        button = getattr(self, "_favorite_toggle_btn", None)
        if button is None:
            return
        station = self._radio_controller.state.station
        if station is None:
            button.Enable(False)
            if button.GetLabel() != "Add to Fa&vorites":
                button.SetLabel("Add to Fa&vorites")
                set_accessible_name(button, "Add the playing station to favorites")
            return
        button.Enable(True)
        saved = self._radio_favorites.contains(station)
        label = "Remove from Fa&vorites" if saved else "Add to Fa&vorites"
        if button.GetLabel() != label:
            button.SetLabel(label)
            set_accessible_name(
                button,
                "Remove the playing station from favorites"
                if saved
                else "Add the playing station to favorites",
            )

    def _on_favorite_toggle(self) -> None:
        station = self._radio_controller.state.station
        if station is None:
            self._announce("Nothing is playing to favorite.")
            return
        key = station.station_uuid or station.stream_url
        if self._radio_favorites.contains(station):
            self._radio_favorites.remove(key)
            self._announce(f"Removed {station.display_name} from favorites")
        else:
            self._radio_favorites.add(station)
            self._announce(f"Added {station.display_name} to favorites")
        self._save_radio_favorites()
        self._reload_favorites_tree()
        self._refresh_favorite_toggle()

    def _play_selected_favorite(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("No station selected. Add favorites from Browse Stations.")
            return
        self._radio_controller.play_station(favorite.station)
        self._announce(f"Playing {favorite.display_label}")

    # -- menu bar -------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        station_menu = wx.Menu()
        browse_id, add_id, find_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(browse_id, "&Browse Stations...")
        station_menu.Append(add_id, "&Add Custom Station...")
        station_menu.Append(find_id, "Find &Streams from a Website...")
        manage_id = wx.NewIdRef()
        station_menu.Append(manage_id, "&Manage Favorites...")
        new_folder_id = wx.NewIdRef()
        station_menu.Append(new_folder_id, "New F&older...\tCtrl+Shift+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._on_new_folder(), id=new_folder_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=browse_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_add_custom(None), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_link_finder(), id=find_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_manage_radio_favorites(), id=manage_id)
        station_menu.AppendSeparator()
        play_last_id = wx.NewIdRef()
        station_menu.Append(play_last_id, "Play &Last Station\tCtrl+L")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_play_last(), id=play_last_id)
        self._append_radio_recent_submenu(station_menu)
        self._append_radio_favorites_submenu(station_menu)
        self._append_acb_media_submenu(station_menu)
        self._resume_menu_item_id = wx.NewIdRef()
        station_menu.AppendCheckItem(self._resume_menu_item_id, "Resume Last Station on Lau&nch")
        station_menu.Check(self._resume_menu_item_id, self._radio_history.resume_on_launch)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_resume_on_launch(), id=self._resume_menu_item_id
        )
        prefs_id = wx.NewIdRef()
        station_menu.Append(prefs_id, "&Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        station_menu.AppendSeparator()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(tray_id, "Send to &Tray\tCtrl+W")
        station_menu.Append(exit_id, "E&xit")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.frame.Close(), id=exit_id)
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
        self._volume_boost_item_id = wx.NewIdRef()
        playback_menu.AppendCheckItem(self._volume_boost_item_id, "Volume &Boost\tCtrl+Shift+B")
        playback_menu.Check(self._volume_boost_item_id, self._radio_history.volume_boost)
        playback_menu.AppendSeparator()
        # Live DVR (mpv engine): pause is the Play/Stop item; these move
        # within the buffered live window.
        rewind_id, forward_id, live_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        playback_menu.Append(rewind_id, "Re&wind 30 Seconds\tCtrl+Shift+Left")
        playback_menu.Append(forward_id, "&Forward 30 Seconds\tCtrl+Shift+Right")
        playback_menu.Append(live_id, "Back to &Live\tCtrl+Shift+L")
        playback_menu.AppendSeparator()
        whats_playing_id = wx.NewIdRef()
        playback_menu.Append(whats_playing_id, "&What's Playing?\tCtrl+T")
        self._announce_titles_item_id = wx.NewIdRef()
        playback_menu.AppendCheckItem(self._announce_titles_item_id, "Announce Trac&k Titles")
        playback_menu.Check(
            self._announce_titles_item_id, self._radio_history.announce_track_titles
        )
        sleep_id = wx.NewIdRef()
        playback_menu.Append(sleep_id, "Sleep &Timer...")
        wake_id = wx.NewIdRef()
        playback_menu.Append(wake_id, "Wake-U&p Timer...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_wake_timer_dialog(), id=wake_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._on_play_stop_button(), id=self._play_menu_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=mute_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_up(), id=vol_up_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_down(), id=vol_down_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._on_volume_boost_menu(), id=self._volume_boost_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_rewind(), id=rewind_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_forward(), id=forward_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_jump_to_live(), id=live_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_whats_playing(), id=whats_playing_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.radio_toggle_title_announcements(),
            id=self._announce_titles_item_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=sleep_id)
        playback_menu.AppendSeparator()
        enhance_id = wx.NewIdRef()
        playback_menu.Append(enhance_id, "Sound &Enhancements...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sound_enhancements(), id=enhance_id)
        menu_bar.Append(playback_menu, "&Playback")

        record_menu = wx.Menu()
        record_id, schedule_id, settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        recordings_id = wx.NewIdRef()
        record_menu.Append(record_id, "&Record Now / Stop Recording")
        record_station_id = wx.NewIdRef()
        record_menu.Append(record_station_id, "Record Statio&n...")
        record_menu.Append(schedule_id, "&Schedule Recording...")
        record_menu.Append(recordings_id, "Recordin&gs...")
        record_menu.Append(settings_id, "Recording &Settings...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=record_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_record_station_dialog(), id=record_station_id
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._radio_open_schedule_recording(), id=schedule_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_radio_recordings(), id=recordings_id)
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
        palette_id, redeem_id, updates_id, about_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        help_menu.Append(palette_id, "Command &Palette...\tCtrl+Shift+P")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_command_palette(), id=palette_id)
        bug_id = wx.NewIdRef()
        help_menu.Append(bug_id, "Report a &Bug...")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_app_bug(source_app="Quill Radio", app_version=_VERSION),
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
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_radio_doc("userguide"), id=guide_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_radio_doc("release-notes-1.0"), id=notes_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_radio_doc("prd"), id=prd_id)
        help_menu.AppendSeparator()
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
        # Pin every menu id for the frame's lifetime (see _keep_menu_ids).
        self._keep_menu_ids(
            browse_id,
            add_id,
            find_id,
            manage_id,
            new_folder_id,
            play_last_id,
            self._resume_menu_item_id,
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
            guide_id,
            notes_id,
            prd_id,
            redeem_id,
            updates_id,
            about_id,
        )

    def _open_radio_doc(self, stem: str) -> None:
        titles = {
            "userguide": "Quill Radio User Guide",
            "release-notes-1.0": "Quill Radio Release Notes",
            "prd": "Quill Radio Product Requirements",
        }
        self.open_app_document(
            self._doc_candidates("quill-radio", stem),
            title=titles.get(stem, stem),
            cache_name="app-docs",
        )

    def _radio_no_ffmpeg_message(self) -> str:
        return (
            "Recording needs FFmpeg, which normally ships inside Quill Radio. "
            "It looks like it's missing -- choose Help > Get FFmpeg... to "
            "download the official build, then try again."
        )

    def _send_to_tray(self) -> None:
        self.frame.Hide()
        self._announce("Quill Radio is still running in the system tray.")

    def _toggle_resume_on_launch(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        history.resume_on_launch = not history.resume_on_launch
        radio_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        self._announce(
            "Quill Radio will pick up where you left off at launch."
            if history.resume_on_launch
            else "Resume on launch turned off."
        )

    def _on_radio_char_hook(self, event: wx.KeyEvent) -> None:
        """Alt+F4 -> system tray when the preference is on (still playing);
        every other key -- and Alt+F4 with the preference off -- flows
        through untouched."""
        if (
            event.GetKeyCode() == wx.WXK_F4
            and event.AltDown()
            and getattr(self._radio_history, "alt_f4_to_tray", False)
        ):
            self._send_to_tray()
            return
        event.Skip()

    def _on_volume_boost_menu(self) -> None:
        """The Playback menu's Volume Boost check item: toggle, then pin the
        checkmark to the persisted truth."""
        self.radio_toggle_volume_boost()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._volume_boost_item_id), self._radio_history.volume_boost)

    def _open_preferences(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history
        from quill.ui.app_preferences_dialog import (
            PreferenceAction,
            PreferenceCheckbox,
            PreferenceChoice,
            PreferencesDialog,
            PreferenceText,
        )
        from quill.ui.radio.mpv_radio_engine import list_audio_devices, output_device_choices

        history = self._radio_history
        close_action_index = _CLOSE_ACTION_VALUES.index(history.close_action)
        device_labels, device_names, device_index = output_device_choices(
            list_audio_devices(), history.output_device
        )
        dialog = PreferencesDialog(
            self.frame,
            app_title=_TITLE,
            checkboxes=[
                PreferenceCheckbox(
                    "Resume Last Station on &Launch",
                    "Resume Last Station on Launch",
                    history.resume_on_launch,
                ),
                PreferenceCheckbox(
                    "&Check for updates automatically on launch",
                    "Check for updates automatically on launch",
                    history.check_updates_on_startup,
                ),
                PreferenceCheckbox(
                    "&Announce dialog transitions (more spoken detail)",
                    "Announce dialog transitions -- off by default to reduce alert noise",
                    history.announce_dialog_transitions,
                ),
                PreferenceCheckbox(
                    "&Recover failed streams from the station's website",
                    "When a station's stream won't play, scan the station's own "
                    "website for a working one -- on by default",
                    history.recover_from_website,
                ),
                PreferenceCheckbox(
                    "Alt+F&4 minimizes to the system tray",
                    "When on, Alt+F4 sends Quill Radio to the system tray, still "
                    "playing, instead of closing the window. The titlebar X and "
                    "Exit keep the 'When closing the window' behavior",
                    history.alt_f4_to_tray,
                ),
            ],
            choices=[
                PreferenceChoice(
                    "When &closing the window:",
                    "When closing the window",
                    list(_CLOSE_ACTION_LABELS),
                    close_action_index,
                ),
                PreferenceChoice(
                    "Playback &engine:",
                    _ENGINE_HELP,
                    list(_ENGINE_LABELS),
                    _ENGINE_VALUES.index(history.playback_engine),
                ),
                PreferenceChoice(
                    "Radio &output device:",
                    _OUTPUT_DEVICE_HELP,
                    device_labels,
                    device_index,
                ),
            ],
            texts=[
                PreferenceText(
                    "&What's Playing announcement:",
                    _NOW_PLAYING_HELP,
                    history.now_playing_template,
                ),
            ],
            actions=[
                PreferenceAction(
                    "Reset &All Stations' Sound Enhancements...",
                    "Reset all stations' Sound Enhancements to the shared default",
                    self._reset_all_sound_enhancements,
                ),
            ],
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        checkbox_values, choice_indices, text_values = result
        (
            history.resume_on_launch,
            history.check_updates_on_startup,
            history.announce_dialog_transitions,
            history.recover_from_website,
            history.alt_f4_to_tray,
        ) = checkbox_values
        history.close_action = _CLOSE_ACTION_VALUES[choice_indices[0]]
        chosen_engine = _ENGINE_VALUES[choice_indices[1]]
        if chosen_engine != history.playback_engine:
            history.playback_engine = chosen_engine
            # A playing station reconnects through the newly chosen backend.
            self._radio_controller.set_playback_engine(chosen_engine)
        chosen_device = device_names[choice_indices[2]]
        if chosen_device != history.output_device:
            history.output_device = chosen_device
            # Reconnects a playing station through the right engine; a
            # station already on air moves to the new device immediately.
            self._radio_controller.set_output_device(chosen_device)
        new_template = text_values[0].strip()
        history.now_playing_template = new_template or _DEFAULT_NOW_PLAYING_TEMPLATE
        radio_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        self._announce("Preferences saved")

    def _reset_all_sound_enhancements(self) -> None:
        """Preferences > Reset All Stations' Sound Enhancements...: clear
        every favorite's override in one pass, the bulk counterpart to the
        Sound Enhancements dialog's own per-station Reset to Default."""
        overridden = [
            favorite
            for favorite in self._radio_favorites.favorites
            if favorite.has_sound_enhancement_override
        ]
        if not overridden:
            self._announce("No stations have their own Sound Enhancements to reset.")
            return
        count = len(overridden)
        plural = "" if count == 1 else "s"
        answer = self._show_message_box(
            f"{count} station{plural} have their own Sound Enhancements. "
            "Reset all of them to the shared default?",
            "Reset All Stations' Sound Enhancements",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        if answer != wx.YES:
            return
        history = self._radio_history
        playing_station = self._radio_controller.state.station
        playing_key = (
            (playing_station.station_uuid or playing_station.stream_url)
            if playing_station is not None
            else None
        )
        reset_playing = False
        for favorite in overridden:
            self._radio_favorites.clear_enhancement_override(favorite.key)
            if favorite.key == playing_key:
                reset_playing = True
        self._save_radio_favorites()
        if reset_playing:
            self._radio_controller.set_enhancement(
                bass_db=history.eq_bass_db,
                mid_db=history.eq_mid_db,
                treble_db=history.eq_treble_db,
                compressor_enabled=history.compressor_enabled,
            )
        self._announce(f"Reset {count} station{plural} to the shared default.")

    def _maybe_resume_last_station(self) -> None:
        """Radio as an appliance: launch, and your station is already on."""
        if not self._radio_history.resume_on_launch:
            return
        station = self._radio_history.last_station
        if station is not None:
            self._radio_controller.play_station(station)

    def _maybe_check_updates_on_startup(self) -> None:
        """Silent, throttled update check -- quiet unless a genuine update
        exists. Preferences (Ctrl+,) turns this off."""
        from datetime import UTC, datetime

        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        if not history.check_updates_on_startup:
            return
        if not self._app_update_check_due(history.last_update_check):
            return
        history.last_update_check = datetime.now(UTC).isoformat()
        radio_history.save_history(app_data_dir(), history)
        self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION, silent_no_update=True)

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

    def _save_radio_favorites(self) -> None:
        # Every favorites mutation -- the toggle button, tree actions, the
        # Favorites Manager -- funnels through this save; refreshing here
        # keeps the main-page tree true without rebuilding it on every
        # unrelated status change.
        super()._save_radio_favorites()
        if getattr(self, "_favorites_tree", None) is not None:
            self._reload_favorites_tree()

    # -- lifecycle --------------------------------------------------------------

    def _on_radio_app_close(self, event: wx.CloseEvent) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        # Alt+F4 / titlebar X / Exit all raise EVT_CLOSE, and a keyboard or
        # screen-reader user who hears nothing right away tends to press
        # Alt+F4 again. wx's modal loop still pumps events while the first
        # RadioCloseConfirmDialog.ShowModal() is running, so that second
        # close event used to re-enter this method and open a *second*
        # confirm dialog on top of the first -- which corrupted the Windows
        # modal stack so badly that both dialogs stayed invisible and the
        # whole app stopped responding to Alt+F4, Exit, everything. Ignore a
        # close event that arrives while one is already being confirmed.
        if getattr(self, "_closing_in_progress", False):
            event.Veto()
            return
        history = self._radio_history
        action = history.close_action
        if action == "ask":
            from quill.ui.radio.player_controller import RadioPlayerState

            recording_active = bool(getattr(self._radio_recorder, "is_recording", False))
            playback_active = self._radio_controller.state.state in (
                RadioPlayerState.PLAYING,
                RadioPlayerState.CONNECTING,
            )
            # "Ask every time" exists to protect an in-progress recording (and,
            # secondarily, to offer Minimize to Tray) from a silent Alt+F4 --
            # not to interrupt an idle app with a prompt. Nothing playing or
            # recording means there's nothing the dialog is protecting, so
            # close the same as if action were "exit"; this doesn't persist
            # (no dialog was shown, so no choice was made to remember).
            if not recording_active and not playback_active:
                action = "exit"
            else:
                from quill.ui.radio.close_confirm_dialog import RadioCloseConfirmDialog

                self._closing_in_progress = True
                try:
                    result = RadioCloseConfirmDialog(
                        self.frame, recording_active=recording_active, announce_cb=self._announce
                    ).show()
                finally:
                    self._closing_in_progress = False
                if result is None:
                    event.Veto()
                    return
                action, dont_ask_again = result
                if dont_ask_again:
                    history.close_action = action
                    radio_history.save_history(app_data_dir(), history)
        if action == "minimize":
            event.Veto()
            self._send_to_tray()
            return
        for shutdown_fn in (
            getattr(self._radio_controller, "shutdown", None),
            getattr(self._radio_recorder, "shutdown", None),
            getattr(self._radio_scheduler, "shutdown", None),
        ):
            if shutdown_fn is None:
                continue
            try:
                shutdown_fn()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                pass
        self._task_manager.shutdown(wait=False)
        self._unregister_media_keys()
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
