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
from quill.core.app_features import AppArea, load_app_features
from quill.core.radio import reading_services
from quill.core.radio.radio_browser import RadioBrowserError
from quill.core.sound_events import SoundEvent
from quill.ui.app_quillins import QuillinsAppMixin
from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.keymap_editor import KeymapEditorMixin
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin
from quill.ui.main_frame_weather import WeatherMixin

_TITLE = "Quill Radio"
_VERSION = "2.2.0"
_REPO = "Community-Access/quill"
#: Shared components this app requires, for the component-refcount registry
#: (ffmpeg for recording; mpv/libmpv is the playback engine).
REQUIRED_COMPONENTS: tuple[str, ...] = ("ffmpeg", "mpv")
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
_FAVORITES_SORT_LABELS = ("Ascending (A to Z)", "Descending (Z to A)", "Unsorted (manual order)")
_FAVORITES_SORT_VALUES = ("az", "za", "manual")
#: View > Text Size choices: (menu label, font scale). Normal is the wx default.
_TEXT_SIZE_SCALES = (("&Normal", 1.0), ("&Large", 1.25), ("La&rger", 1.5))
_ENGINE_HELP = (
    "Which audio engine plays the radio. Automatic uses mpv when it is "
    "installed -- that is what enables the output device choice, pausing "
    "and rewinding live radio, Volume Boost, and stations in more formats "
    "-- and Windows Media otherwise. Windows Media (classic) is exactly "
    "the pre-1.1 behavior."
)

#: Station > Update Radio Reading Services... Safe Mode refusal (mirrors
#: WeatherMixin's _SAFE_MODE_WEATHER wording for Update NOAA Weather Radio
#: Directory).
_SAFE_MODE_RRS = (
    "Radio Reading Services is a network service and is turned off in Safe Mode. "
    "Restart without Safe Mode to use it."
)


def reading_services_refresh_summary(*, safe_mode: bool = False) -> str:
    """Live-refresh the Radio Reading Services directory and summarize the
    result as a plain string (pure, no wx) -- so the text
    ``RadioAppFrame.update_reading_services_directory`` announces is
    unit-testable without wx. Mirrors ``main_frame_weather``'s
    ``update_noaa_radio_directory``: a Safe Mode refusal or RadioBrowser
    error comes back as a clear failure string instead of raising.
    """
    try:
        reading_services.refresh_reading_services(safe_mode=safe_mode)
    except RadioBrowserError as exc:
        return f"Could not update Radio Reading Services. {exc}"
    # Report the total the user will actually see -- the curated bundled list
    # plus anything the live refresh discovered -- not just the live count.
    total = len(reading_services.list_reading_services(safe_mode=safe_mode))
    return f"Radio Reading Services updated: {total} services."


#: The switchable areas of Quill Radio (View > Customize Features...). Turning
#: one off omits its whole menu on the next launch. Core areas -- Station,
#: Playback, View, Help -- are always present and not listed here.
RADIO_AREAS: tuple[AppArea, ...] = (
    AppArea(
        "recording",
        "Recording",
        "The Record menu: record now, record a station, scheduled recordings, "
        "and the recordings library.",
    ),
    AppArea(
        "weather",
        "Weather",
        "The Weather menu: forecasts, alerts, background alert monitoring, and "
        "NOAA Weather Radio. (Weather is also available as its own Quill Weather app.)",
    ),
)


class RadioAppFrame(
    # AppShellFrame is listed first so its toggle_window_to_tray / _send_to_tray
    # (which the apps have) win over GlobalHotkeysMixin's send_to_tray-based copy.
    AppShellFrame,
    RadioMixin,
    MediaSleepTimerMixin,
    AdpMixin,
    UnlockCodesMixin,
    WeatherMixin,
    GlobalHotkeysMixin,
    KeymapEditorMixin,
    QuillinsAppMixin,
):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        from quill.core.paths import app_data_dir

        self._app_features = load_app_features(app_data_dir(), "radio")
        # Radio hands weather off to its own app: the Weather menu offers "Open
        # the Quill Weather App", and the two run side by side, each in its own
        # window and tray, reachable from the other.
        self._weather_offers_app_launch = True
        self._init_radio()
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(lambda: self._radio_history.announce_dialog_transitions)
        self._init_media_sleep_timer()
        from quill.ui.window_menu import WindowManager

        # Shared &Window menu + Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 traversal
        # across the main window and the modeless radio surfaces. RadioMixin's
        # open_* methods pass this to each surface, which becomes a modeless
        # frame in the standalone app; embedded QUILL passes no manager, so the
        # same surfaces stay modal there.
        self._windows = WindowManager(wx)
        # Quillins for Quill Radio (app id "radio"): load contributions before
        # the menu bar is built so contributed items appear in the &Quillins menu.
        self._init_app_quillins("radio")
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
        self._register_tray_hotkey("Ctrl+Alt+Shift+R")  # show/hide Radio to the tray
        # Per-command system-wide hotkeys (Help > Global Hotkeys...). Register
        # the show/hide command the default table binds so its Ctrl+Alt+Shift+Q
        # actually dispatches; the transport commands (radio.play_pause/stop/...)
        # are already registered above. We do NOT call
        # _register_global_hotkey_commands -- that also adds the sticky-note /
        # editor commands the apps don't want. Then bind the message hook and
        # register whatever the user has configured.
        self.commands.try_register(
            "view.toggle_window_to_tray",
            "Show/Hide Quill Radio to the Tray",
            self.toggle_window_to_tray,
            self._binding_for("view.toggle_window_to_tray"),
            feature_id="core.app",
        )
        self.frame.Bind(wx.EVT_HOTKEY, self._on_global_hotkey)
        self._reload_global_hotkeys()
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_radio_app_close)
        # Alt+F4-to-tray (opt-in preference): intercepted at the char hook,
        # before Windows turns it into a close, so the window tucks away with
        # playback running. The titlebar X and Exit keep close_action.
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_radio_char_hook)
        self._maybe_resume_last_station()
        # Watch for a second launch asking us to come forward (#1152): a
        # re-launched Quill Radio enqueues a "show" request and exits; this
        # timer drains it and un-hides/raises this window, even from the tray.
        self._start_ipc_poll()
        # Deferred (CallAfter), not inline: this touches the network, and a
        # launch is not the place to do that before the window is even up.
        wx.CallAfter(self._maybe_check_updates_on_startup)
        # Resume Weather Guardian's alert watch if the user left it on (also
        # deferred: it polls the NWS off-thread).
        wx.CallAfter(self.start_weather_monitoring_if_enabled)
        # Missed-recording reporting + startup reconcile/resume live in
        # RadioMixin._init_radio now (R2/11.6 + R3), so both hosts get them once.

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
        # Keep the spoken name short -- a screen reader reads it on every focus,
        # and the old tutorial-style name ("...; Enter plays, Delete removes, F2
        # renames, Shift+F10 opens all actions") was read aloud constantly. The
        # role ("tree view") already conveys what it is; the key hints move to
        # help text, discoverable but not spoken on entry.
        set_accessible_name(self._favorites_tree, "Favorite stations")
        self._favorites_tree.SetHelpText(
            "Enter plays, Delete removes, F2 renames, Shift+F10 opens all actions."
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
        # No "&" mnemonic on the transport button: "&Stop"/"&Play" would claim
        # Alt+S / Alt+P, which collide with the Station / Playback menu-bar
        # mnemonics (the menu bar wins, so the button never fired) -- #1208. The
        # reliable transport key is the menu accelerator Ctrl+P, which the
        # accessible name now advertises so it is reported correctly.
        self._play_stop_btn = wx.Button(panel, label="Play")
        set_accessible_name(self._play_stop_btn, "Play (Ctrl+P)")
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
        # The Record button doubles as the stop control: while a recording is
        # running it reads "Stop Recording" so it is obvious you are recording
        # (#1152 feedback), mirroring the single Play/Stop button above.
        self._record_btn = wx.Button(panel, label="&Record")
        set_accessible_name(self._record_btn, "Record")
        self._record_btn.Bind(wx.EVT_BUTTON, lambda _e: self.radio_record_toggle())
        buttons.Add(self._record_btn, 0, wx.RIGHT, 6)
        browse_btn = wx.Button(panel, label="&Browse Stations...")
        set_accessible_name(browse_btn, "Browse Stations...")
        browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_browse_stations())
        buttons.Add(browse_btn, 0, wx.RIGHT, 6)
        # A volume control right in the Tab order, so the volume can be adjusted
        # by arrowing a focused slider while listening -- not only via Ctrl+Up/
        # Down or the status bar (#1214). Kept in step with the real volume by
        # _refresh_statusbar (which also reflects Ctrl+Up/Down and per-station
        # memory), so the two paths never disagree.
        buttons.Add(
            wx.StaticText(panel, label="Vol&ume:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        start_volume = 100
        controller = getattr(self, "_radio_controller", None)
        if controller is not None:
            start_volume = controller.state.volume_percent
        self._volume_slider = wx.Slider(
            panel, value=start_volume, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL
        )
        set_accessible_name(self._volume_slider, "Volume, percent")
        self._volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_slider)
        buttons.Add(self._volume_slider, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        # The arrow-navigable status bar lives along the bottom (F6 to reach it,
        # View > Show Status Bar to hide it). Its cells and behaviour live in
        # RadioStatusBar; the panel keeps radio.py's own footprint small.
        from quill.ui.radio.status_bar import RadioStatusBar

        self._status_bar = RadioStatusBar(self)
        status_panel = self._status_bar.build(panel)
        root.Add(status_panel, 0, wx.EXPAND | wx.ALL, 2)
        self._status_bar.set_visible(self._radio_history.show_status_bar)

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_favorites_tree()
        self._status_bar.refresh()
        self._apply_text_size()
        self._favorites_tree.SetFocus()

    def _focus_initial_control(self) -> None:
        """Land keyboard focus on the favorites tree after the window is shown so
        the menu bar is reachable straight away (#1193): a pre-show SetFocus does
        not stick, which left the window opening with no control focused -- the
        first Alt then opened the window's system menu instead of the app menu."""
        tree = getattr(self, "_favorites_tree", None)
        if tree is not None:
            try:
                tree.SetFocus()
            except Exception:  # noqa: BLE001 - initial focus is best-effort
                pass

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
        sort = self._radio_history.favorites_sort
        folder_sorts = self._radio_history.folder_sort_orders
        for path in store.folders_in_display_order(sort):
            folder_item(path)
        for favorite in store.favorites_in_display_order(sort, folder_sorts):
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
        # Alt+Shift+Up/Down reordering is handled in the frame char hook
        # (_on_radio_char_hook) -- Windows steals Alt+arrow for the menu before
        # a focused TreeCtrl's EVT_KEY_DOWN can see it.
        event.Skip()

    def _move_selected_favorite(self, delta: int) -> None:
        """Move the selected favorite up (-1) or down (+1) within its folder,
        only when that folder is in manual order, and speak where it landed."""
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("Select a station to move it.")
            return
        folder_sort = self._radio_history.folder_sort_orders.get(
            favorite.folder, self._radio_history.favorites_sort
        )
        switched = False
        if folder_sort != "manual":
            # Reordering is a clear intent to reorder: switch to manual order
            # (revealing the preserved hand-arranged order, announced below) and
            # move within it. No longer bakes the sorted view over the stored
            # order, which used to destroy it (#1186).
            self._force_favorites_manual_order()
            switched = True
        from quill.ui.radio.favorites_manager_dialog import move_announcement

        if not self._radio_favorites.move(favorite.key, delta=delta):
            self._announce("Already at the edge of its folder.")
            if switched:
                self._reload_favorites_tree(keep_key=favorite.key)
            return
        # Speak the new position before the tree reload re-announces the item, so
        # "Moved down, now above X" is what the listener hears.
        prefix = "Switched to manual order. " if switched else ""
        self._announce(prefix + move_announcement(self._radio_favorites, favorite.key, delta))
        self._save_radio_favorites()
        self._reload_favorites_tree(keep_key=favorite.key)

    def _force_favorites_manual_order(self) -> None:
        """Switch favorites to manual sort WITHOUT rewriting the stored order.

        Reordering from a sorted (A-Z/Z-A) view is a clear intent to hand-arrange,
        so flip the sort to manual -- which reveals the preserved stored order (the
        caller reloads the tree and announces "Switched to manual order") -- and
        then the move happens within that now-visible order. Crucially this does
        NOT bake the sorted display over the stored list: doing so silently
        destroyed a listener's hand-arranged order the first time they reordered
        from an A-Z view, with no way to recover it (#1186). The stored list is
        left untouched; only the sort setting changes.
        """
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        self._radio_history.favorites_sort = "manual"
        self._radio_history.folder_sort_orders = {}
        radio_history.save_history(app_data_dir(), self._radio_history)
        self._save_radio_favorites()

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
                ("Station &Details...", self._on_favorite_details),
                ("Rena&me...\tF2", self._on_tree_rename),
                ("Move to F&older...", self._on_tree_move_to_folder),
                ("&Remove...\tDelete", self._on_tree_remove),
                ("New F&older...\tCtrl+Shift+E", self._on_new_folder),
            ]
            # Mark-and-Move (#1190): pick a station up once, then drop it above
            # or below any destination in one step -- no Alt+Shift+Up/Down 30
            # times. Mirrors the Favorites Manager's Mark for Move.
            marked = getattr(self, "_marked_favorite_key", None)
            entries.append(("&Mark for Move", self._on_mark_favorite))
            if marked is not None and (favorite is None or marked != favorite.key):
                entries.append(("Move Marked A&bove", lambda: self._on_move_marked_favorite(True)))
                entries.append(("Move Marked Belo&w", lambda: self._on_move_marked_favorite(False)))
            entries.append(("Manage Fa&vorites...", self.open_manage_radio_favorites))
        else:
            entries = [
                ("Rena&me Folder...\tF2", self._on_tree_rename),
                ("&Sort This Folder...", self._on_sort_folder),
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

    def _on_favorite_details(self) -> None:
        """Show the selected favorite's details (name, source, stream, format,
        country) in the same reviewable, copyable window the search results use,
        so a listener can arrow through them and copy -- reachable per favorite."""
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("Select a station to see its details.")
            return
        from quill.ui.radio.now_playing_dialog import NowPlayingDialog

        NowPlayingDialog(
            self.frame,
            favorite.station.details_text,
            self._show_modal_dialog,
            self._copy_to_clipboard,
            self._announce,
            title=f"Details: {favorite.display_name}",
        ).show()

    def _on_mark_favorite(self) -> None:
        """Mark-and-Move step 1 (#1190): remember the selected station so a
        single Move Marked Above/Below drops it, instead of nudging one step at
        a time with Alt+Shift+Up/Down."""
        favorite = self._selected_favorite()
        if favorite is None:
            return
        self._marked_favorite_key = favorite.key
        self._announce(
            f"Marked {favorite.display_label}. Select a destination, then choose "
            "Move Marked Above or Move Marked Below from this menu."
        )

    def _on_move_marked_favorite(self, before: bool) -> None:
        """Mark-and-Move step 2 (#1190): drop the marked station directly above
        or below the currently selected one (adopting its folder)."""
        target = self._selected_favorite()
        marked_key = getattr(self, "_marked_favorite_key", None)
        if target is None or marked_key is None:
            return
        if marked_key == target.key:
            self._announce("Select a different station as the destination.")
            return
        # Reordering only makes sense in manual order; switch to it first. This
        # reveals your preserved hand-arranged order -- it never overwrites it.
        folder_sort = self._radio_history.folder_sort_orders.get(
            target.folder, self._radio_history.favorites_sort
        )
        if folder_sort != "manual":
            self._force_favorites_manual_order()
        if self._radio_favorites.move_relative_to(marked_key, target.key, before=before):
            self._marked_favorite_key = None
            self._save_radio_favorites()
            self._reload_favorites_tree(keep_key=marked_key)
            where = "above" if before else "below"
            self._announce(f"Moved {where} {target.display_label}.")
        else:
            self._announce("Could not move the marked station there.")

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

    def _on_sort_folder(self) -> None:
        """Give the selected folder its own sort order -- A to Z, Z to A,
        Unsorted, or follow the global default -- applied to its stations and
        remembered (per-folder override of Favorites sort order)."""
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "folder":
            return
        path = selected[1]
        labels = [
            "Follow the default",
            "Ascending (A to Z)",
            "Descending (Z to A)",
            "Unsorted (manual order)",
        ]
        values: list[str | None] = [None, "az", "za", "manual"]
        current = self._radio_history.folder_sort_orders.get(path)
        with wx.SingleChoiceDialog(
            self.frame, f'Sort order for the folder "{path}":', "Sort Folder", labels
        ) as dlg:
            dlg.SetSelection(values.index(current) if current in values else 0)
            if dlg.ShowModal() != wx.ID_OK:
                return
            chosen = values[dlg.GetSelection()]
        orders = dict(self._radio_history.folder_sort_orders)
        if chosen is None:
            orders.pop(path, None)
        else:
            orders[path] = chosen
        self._radio_history.folder_sort_orders = orders
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        radio_history.save_history(app_data_dir(), self._radio_history)
        self._reload_favorites_tree()
        self._announce(f"{path}: {dict(zip(values, labels, strict=True))[chosen]}.")

    def import_stations_from_playlist(self) -> None:
        """Station > Import Stations from Playlist...: read an M3U/M3U8 file,
        pick (or create) a target folder at any depth, handle any duplicates
        against the current favorites, and add the rest."""
        from pathlib import Path

        from quill.core.radio.playlist_import import parse_m3u, split_new_and_duplicates
        from quill.ui.radio.import_stations_dialog import prompt_import_target

        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Choose a playlist to import",
            wildcard="Playlists (*.m3u;*.m3u8)|*.m3u;*.m3u8|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return
            source = Path(file_dialog.GetPath())
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._announce(f"Could not read the playlist: {exc}")
            return
        stations = parse_m3u(text)
        if not stations:
            self._show_message_box(
                "No radio stations were found in that playlist.",
                "Import Stations",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        folder = prompt_import_target(
            self.frame, self._radio_favorites.folder_names(), len(stations)
        )
        if folder is None:
            return
        existing = {favorite.key for favorite in self._radio_favorites.favorites}
        new, duplicates = split_new_and_duplicates(stations, existing)
        to_import = stations
        if duplicates:
            labels = [
                f"Skip the {len(duplicates)} already in your favorites -- "
                f"import the {len(new)} new one(s)",
                f"Import everything, including the {len(duplicates)} duplicate(s)",
            ]
            with wx.SingleChoiceDialog(
                self.frame,
                f"{len(duplicates)} of the {len(stations)} stations are already in "
                "your favorites. How should I handle them?",
                "Import Stations -- Duplicates Found",
                labels,
            ) as dup_dialog:
                if dup_dialog.ShowModal() != wx.ID_OK:
                    return
                to_import = stations if dup_dialog.GetSelection() == 1 else new
        if not to_import:
            self._announce("Nothing to import -- every station was already a favorite.")
            return
        for station in to_import:
            self._radio_favorites.add(station, folder=folder)
        self._save_radio_favorites()
        self._reload_favorites_tree()
        where = f'the "{folder}" folder' if folder else "your favorites"
        plural = "station" if len(to_import) == 1 else "stations"
        self._announce(f"Imported {len(to_import)} {plural} into {where}.")

    # -- Radio Reading Services -------------------------------------------------

    def update_reading_services_directory(self) -> None:
        """Station > Update Radio Reading Services...: force a live pull of
        the Radio Reading Services directory off-thread, then announce the
        refreshed count. Mirrors Weather > Update NOAA Weather Radio
        Directory (``main_frame_weather.WeatherMixin.update_noaa_radio_directory``)."""
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_RRS, "Radio Reading Services", wx.ICON_INFORMATION | wx.OK
            )
            return
        self._announce("Updating Radio Reading Services...")

        def _work(**_kwargs: object) -> str:
            return reading_services_refresh_summary(safe_mode=self._safe_mode)

        def _done(_op: str, result: object) -> None:
            self._wx.CallAfter(self._announce, str(result))

        self._task_manager.submit(
            "radio-reading-services-update", _work, on_success=_done, on_failure=None
        )

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
        # Button label carries no "&" (see #1208); the Playback menu item keeps
        # its in-menu mnemonic (safe -- submenu mnemonics don't collide with the
        # menu bar) plus the working Ctrl+P accelerator.
        button_label = "Stop" if stopping else "Play"
        menu_label = "&Stop" if stopping else "&Play"
        button = getattr(self, "_play_stop_btn", None)
        if button is not None and button.GetLabel() != button_label:
            button.SetLabel(button_label)
            set_accessible_name(button, f"{button_label} (Ctrl+P)")
        menu_bar = self.frame.GetMenuBar()
        item_id = getattr(self, "_play_menu_item_id", None)
        if menu_bar is not None and item_id is not None:
            menu_bar.SetLabel(int(item_id), f"{menu_label}\tCtrl+P")
        self._refresh_favorite_toggle()

    def _refresh_record_button(self) -> None:
        """Reflect recording state on the Record button: it becomes "Stop
        Recording" while any recording is active so it is obvious you are
        recording, and toggles back to "Record" when they all stop."""
        button = getattr(self, "_record_btn", None)
        if button is None:
            return
        recording = bool(getattr(self._radio_recorder, "is_recording", False))
        label = "Stop &Recording" if recording else "&Record"
        if button.GetLabel() != label:
            button.SetLabel(label)
            set_accessible_name(button, "Stop Recording" if recording else "Record")

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
            self._announce(
                f"Added {station.display_name} to favorites",
                sound=SoundEvent.RADIO_FAVORITE_ADDED,
            )
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
        # Browse and Search are distinct: Browse Stations opens the unified
        # source tree (a delightful, search-free "wander the sources" view);
        # Search Stations opens the field-based dialog focused on the box.
        browse_id, search_id, add_id, find_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        station_menu.Append(browse_id, "&Browse Stations...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_browse_stations(), id=browse_id)
        rrs_update_id = wx.NewIdRef()
        station_menu.Append(rrs_update_id, "Update Radio Reading &Services...")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.update_reading_services_directory(),
            id=rrs_update_id,
        )
        station_menu.Append(search_id, "&Search Stations...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_internet_radio(focus_search=True), id=search_id
        )
        station_menu.Append(add_id, "&Add Custom Station...")
        station_menu.Append(find_id, "Find &Streams from a Website...")
        manage_id = wx.NewIdRef()
        station_menu.Append(manage_id, "&Manage Favorites...")
        new_folder_id = wx.NewIdRef()
        station_menu.Append(new_folder_id, "New F&older...\tCtrl+Shift+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._on_new_folder(), id=new_folder_id)
        import_id = wx.NewIdRef()
        station_menu.Append(import_id, "&Import Stations from Playlist...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_stations_from_playlist(), id=import_id)
        # #1249: export favorites to an M3U playlist. Thin wiring lives in
        # playlist_export_ui (radio.py is at budget).
        from quill.ui.radio.playlist_export_ui import export_favorites_to_playlist

        export_id = wx.NewIdRef()
        station_menu.Append(export_id, "&Export Favorites to Playlist...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: export_favorites_to_playlist(self), id=export_id)
        # #1193: move your stations/settings/recordings to a new device or recover
        # after a reinstall. Thin wiring lives in backup_ui (radio.py is at budget).
        from quill.ui.radio.backup_ui import back_up_radio_data, restore_radio_data

        backup_id, restore_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(backup_id, "Back &Up Stations and Settings...")
        station_menu.Append(restore_id, "&Restore from Backup...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: back_up_radio_data(self), id=backup_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: restore_radio_data(self), id=restore_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_add_custom(None), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._radio_open_link_finder(), id=find_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_manage_radio_favorites(), id=manage_id)
        station_menu.AppendSeparator()
        play_last_id = wx.NewIdRef()
        station_menu.Append(play_last_id, "Play &Last Station\tCtrl+L")
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
        station_menu.AppendCheckItem(self._resume_menu_item_id, "Resume Last Station on Lau&nch")
        station_menu.Check(self._resume_menu_item_id, self._radio_history.resume_on_launch)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_resume_on_launch(), id=self._resume_menu_item_id
        )
        from quill.platform.windows import radio_startup

        self._startup_menu_item_id = wx.NewIdRef()
        station_menu.AppendCheckItem(self._startup_menu_item_id, "Start Quill Radio with &Windows")
        station_menu.Check(self._startup_menu_item_id, radio_startup.is_launch_at_startup_enabled())
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_launch_at_startup(), id=self._startup_menu_item_id
        )
        prefs_id = wx.NewIdRef()
        station_menu.Append(prefs_id, "&Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        station_menu.AppendSeparator()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(tray_id, "Send to &Tray\tCtrl+W")
        station_menu.Append(exit_id, "E&xit")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        # Explicit Exit must quit for real, not minimize-to-tray (#1193).
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
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
        # #1253: pick the audio output device (sound card) with a shortcut, without
        # opening full Preferences. Thin wiring lives in output_device_ui.
        from quill.ui.radio.output_device_ui import choose_output_device

        output_device_id = wx.NewIdRef()
        playback_menu.Append(output_device_id, "&Output Device...\tCtrl+Shift+D")
        self.frame.Bind(wx.EVT_MENU, lambda _e: choose_output_device(self), id=output_device_id)
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
        # Ctrl+Shift+H is free in the standalone app; inside full QUILL the same
        # command ships unbound because there Ctrl+Shift+H is Replace All.
        song_history_id = wx.NewIdRef()
        playback_menu.Append(song_history_id, "Son&g History...\tCtrl+Shift+H")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_song_history(), id=song_history_id)
        self._global_volume_item_id = wx.NewIdRef()
        playback_menu.AppendCheckItem(
            self._global_volume_item_id, "Use One &Volume for All Stations"
        )
        playback_menu.Check(self._global_volume_item_id, self._radio_history.use_global_volume)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.radio_toggle_global_volume(),
            id=self._global_volume_item_id,
        )
        forget_volumes_id = wx.NewIdRef()
        playback_menu.Append(forget_volumes_id, "Forget Every Station's Own Volu&me...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_forget_station_volumes(), id=forget_volumes_id
        )
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
        playback_menu.Append(enhance_id, "Sound &Enhancements...\tCtrl+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sound_enhancements(), id=enhance_id)
        menu_bar.Append(playback_menu, "&Playback")

        record_menu = wx.Menu()
        record_id, schedule_id, settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        recordings_id = wx.NewIdRef()
        record_menu.Append(record_id, "&Record Now / Stop Recording")
        record_station_id = wx.NewIdRef()
        record_menu.Append(record_station_id, "Record Statio&n...")
        stop_all_id = wx.NewIdRef()
        record_menu.Append(stop_all_id, "Stop A&ll Recordings")
        record_menu.Append(schedule_id, "&Schedule Recording...")
        record_menu.Append(recordings_id, "Recordin&gs...")
        record_menu.Append(settings_id, "Recording &Settings...")
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
        # Recording and Weather are user-switchable areas (View > Customize
        # Features...): when turned off, the whole menu is not built at all.
        if self._app_area_enabled("recording"):
            menu_bar.Append(record_menu, "&Record")

        if self._app_area_enabled("weather"):
            self._append_weather_menu(menu_bar)

        # Pre-release top-level Audio Description Project menu. The typed Ask
        # ADP assistant (future.adp_assistant) is ON by default for testing, so
        # this is present by default; _build_adp_menu returns None only if a
        # profile turns it off. The hands-free conversational mode
        # (future.adp_voice_mode) is the part that stays locked until a signed
        # unlock code is redeemed (Help > Redeem Unlock Code..., here or in
        # QUILL -- they share one unlock store). Undocumented until launch.
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
        # Spotify (future.spotify) is experimental: the ids are always created
        # (so _keep_menu_ids can pin them) but the items appear only while the
        # feature is on and Safe Mode is off.
        spotify_connect_id, spotify_browse_id = wx.NewIdRef(), wx.NewIdRef()
        if self.features.is_enabled("future.spotify") and not self._safe_mode:
            help_menu.Append(spotify_connect_id, "Connect to &Spotify...")
            help_menu.Append(spotify_browse_id, "&Browse Spotify...")
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
            wx.EVT_MENU, lambda _e: self._open_radio_doc("release-notes-2.2"), id=notes_id
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
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="radio"
            ),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)

        # &View: show/hide the read-only Station Details pane, honored by every
        # surface that has one (Browse Stations, Search Stations).
        view_menu = wx.Menu()
        show_details_id = wx.NewIdRef()
        view_menu.AppendCheckItem(show_details_id, "Show Station &Details")
        view_menu.Check(show_details_id, self._radio_history.show_station_details)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_show_station_details(), id=show_details_id
        )
        self._status_bar_item_id = wx.NewIdRef()
        view_menu.AppendCheckItem(self._status_bar_item_id, "Show Status &Bar")
        view_menu.Check(self._status_bar_item_id, self._radio_history.show_status_bar)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_show_status_bar(), id=self._status_bar_item_id
        )
        view_menu.AppendSeparator()
        # Sort Favorites: the same setting Preferences carries, surfaced here as
        # radio items so it is one keystroke away and its current value is visible.
        sort_menu = wx.Menu()
        self._sort_item_ids = [wx.NewIdRef() for _ in _FAVORITES_SORT_VALUES]
        sort_accels = ("\tCtrl+Shift+A", "\tCtrl+Shift+Z", "")
        for item_id, label, value, accel in zip(
            self._sort_item_ids,
            _FAVORITES_SORT_LABELS,
            _FAVORITES_SORT_VALUES,
            sort_accels,
            strict=True,
        ):
            sort_menu.AppendRadioItem(item_id, label + accel)
            sort_menu.Check(item_id, self._radio_history.favorites_sort == value)
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, v=value: self._set_favorites_sort(v), id=item_id
            )
        view_menu.AppendSubMenu(sort_menu, "Sort &Favorites")
        expand_id, collapse_id = wx.NewIdRef(), wx.NewIdRef()
        view_menu.Append(expand_id, "&Expand All Folders")
        view_menu.Append(collapse_id, "&Collapse All Folders")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._expand_all_folders(True), id=expand_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._expand_all_folders(False), id=collapse_id)
        view_menu.AppendSeparator()
        features_id = wx.NewIdRef()
        view_menu.Append(features_id, "&Customize Features...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_app_features(), id=features_id)
        self._keep_menu_ids(features_id)
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
        menu_bar.Append(view_menu, "&View")
        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx,
                self.frame,
                self._launch_sibling,
                exclude="radio",
                retain=self._keep_menu_ids,
            ),
            "&QuillVille",
        )
        menu_bar.Append(self._build_quillins_menu(), "&Quillins")
        menu_bar.Append(help_menu, "&Help")

        # Persistent &Window menu + Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 on the
        # main window; each modeless surface installs the same on its own bar so
        # the numbered traversal reaches every open radio window.
        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)
        # Pin every menu id for the frame's lifetime (see _keep_menu_ids).
        self._keep_menu_ids(
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
            guide_id,
            notes_id,
            prd_id,
            redeem_id,
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
        )

    def _open_radio_doc(self, stem: str) -> None:
        titles = {
            "userguide": "Quill Radio User Guide",
            "release-notes-2.2": "Quill Radio Release Notes",
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

    def _on_station_menu_open(self, event: object) -> None:
        """Rebuild Recently Played just before the Station menu opens, so it
        reflects everything played since launch (the menu bar itself is built
        once at startup). Mirrors the Window menu's just-in-time refresh. Always
        skips so other EVT_MENU_OPEN handlers (the Window menu's) still run."""
        get_menu = getattr(event, "GetMenu", None)
        menu = get_menu() if callable(get_menu) else None
        if menu is getattr(self, "_station_menu", None):
            self._rebuild_recent_submenu()
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _send_to_tray(self) -> None:
        self.frame.Hide()
        self._announce("Quill Radio is still running in the system tray.")

    # -- single instance (#1152) ------------------------------------------------

    def _start_ipc_poll(self) -> None:
        """Poll the radio IPC queue for a foreground request from a 2nd launch."""
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, timer)
        timer.Start(800)
        self._ipc_timer = timer

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        # Any queued request is a "come to the foreground" from a second launch
        # (the radio slot only ever enqueues show requests). Drain and surface.
        if drain_open_requests(slot=_IPC_SLOT):
            self._foreground_window()

    def _foreground_window(self) -> None:
        """Bring the window forward, un-hiding it from the tray and de-iconizing."""
        frame = self.frame
        if not frame.IsShown():
            frame.Show(True)
        if frame.IsIconized():
            frame.Iconize(False)
        frame.Raise()
        frame.RequestUserAttention()

    def _toggle_show_station_details(self) -> None:
        """Flip Show Station Details and persist it. The Browse and Search Stations
        surfaces read it when they open, so the change takes effect next time you
        open one."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        history.show_station_details = not history.show_station_details
        radio_history.save_history(app_data_dir(), history)
        self._announce(
            "Station details will be shown."
            if history.show_station_details
            else "Station details will be hidden."
        )

    def _toggle_show_status_bar(self) -> None:
        """Flip Show Status Bar, persist it, and show/hide the bar right away."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        history.show_status_bar = not history.show_status_bar
        radio_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._status_bar_item_id), history.show_status_bar)
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is not None:
            status_bar.set_visible(history.show_status_bar)
            if history.show_status_bar:
                status_bar.refresh()
        self._announce("Status bar shown." if history.show_status_bar else "Status bar hidden.")

    def _set_favorites_sort(self, value: str) -> None:
        """View > Sort Favorites: change the favorites sort order and reload the
        tree. Same setting Preferences carries; announced so the change is heard."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        if history.favorites_sort == value:
            return
        history.favorites_sort = value
        radio_history.save_history(app_data_dir(), history)
        self._reload_favorites_tree()
        labels = dict(zip(_FAVORITES_SORT_VALUES, _FAVORITES_SORT_LABELS, strict=True))
        self._announce(f"Sorted favorites: {labels[value]}")

    def _expand_all_folders(self, expand: bool) -> None:
        """View > Expand/Collapse All Folders on the favorites tree."""
        tree = getattr(self, "_favorites_tree", None)
        if tree is None:
            return
        if expand:
            tree.ExpandAll()
            self._announce("Expanded all folders.")
        else:
            tree.CollapseAll()
            self._announce("Collapsed all folders.")

    def _set_text_size(self, scale: float) -> None:
        """View > Text Size: persist the font scale and apply it right away."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        if abs(history.ui_font_scale - scale) < 0.01:
            return
        history.ui_font_scale = scale
        radio_history.save_history(app_data_dir(), history)
        self._apply_text_size()
        names = {1.0: "Normal", 1.25: "Large", 1.5: "Larger"}
        self._announce(f"Text size: {names.get(scale, 'Normal')}")

    def _apply_text_size(self) -> None:
        """Scale the main window's fonts (tree, buttons, now-playing line, status
        bar) to the saved ui_font_scale. A no-op at 1.0 beyond restoring the base
        font, so toggling back to Normal returns to the system default."""
        scale = float(getattr(self._radio_history, "ui_font_scale", 1.0) or 1.0)
        panel = getattr(self, "_main_panel", None)
        if panel is None:
            return
        base = self._wx.SystemSettings.GetFont(self._wx.SYS_DEFAULT_GUI_FONT)
        font = base.Scaled(scale) if scale != 1.0 else base
        for name in (
            "_now_playing_text",
            "_favorites_tree",
            "_play_stop_btn",
            "_favorite_toggle_btn",
            "_record_btn",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.SetFont(font)
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is not None:
            status_bar.set_font(font)
        panel.Layout()

    def _focus_status_bar(self) -> None:
        """F6: move focus into the status bar, or back out of it if already there.

        Does nothing (beyond a nudge) when the bar is hidden -- there is nowhere
        to land, so the key is a no-op the way an empty region would be."""
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is None or not status_bar.is_shown():
            return
        if status_bar.has_focus():
            self._focus_initial_control()
            self._announce("Returned to favorite stations")
            return
        status_bar.refresh()
        status_bar.focus_bar(return_focus=getattr(self, "_favorites_tree", None))

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

    def _toggle_launch_at_startup(self) -> None:
        """Station > Start Quill Radio with Windows: add or remove the per-user
        autostart entry, then reflect what actually took (a locked-down registry
        may refuse silently)."""
        from quill.platform.windows import radio_startup

        if not radio_startup.is_windows():
            self._announce("Starting with Windows is only available on Windows.")
            return
        radio_startup.set_launch_at_startup(not radio_startup.is_launch_at_startup_enabled())
        actual = radio_startup.is_launch_at_startup_enabled()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._startup_menu_item_id), actual)
        self._announce(
            "Quill Radio will start with Windows."
            if actual
            else "Quill Radio will not start with Windows."
        )

    # -- switchable feature areas ----------------------------------------------

    def _app_area_enabled(self, area_id: str) -> bool:
        features = getattr(self, "_app_features", None)
        return True if features is None else features.is_enabled(area_id)

    def _open_app_features(self) -> None:
        """View > Customize Features...: turn whole areas of Quill Radio on or
        off. Menu changes take effect at the next launch."""
        from quill.core.app_features import save_app_features
        from quill.core.paths import app_data_dir
        from quill.ui.app_features_dialog import AppFeaturesDialog

        dlg = AppFeaturesDialog(
            self.frame,
            app_title=_TITLE,
            areas=RADIO_AREAS,
            settings=self._app_features,
            announce_cb=self._announce,
        )
        if dlg.show():
            save_app_features(app_data_dir(), self._app_features)
            self._announce(
                "Feature settings saved. Menu changes take effect the next time "
                "you open Quill Radio."
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
        # Alt+Shift+Up / Alt+Shift+Down reorder the selected favorite (manual
        # order), Teams-style. Caught here in the frame's char hook rather than
        # the tree's EVT_KEY_DOWN because Windows routes Alt+arrow to the menu
        # system before a focused TreeCtrl ever sees it. Only acts when the
        # favorites tree actually has focus.
        code = event.GetKeyCode()
        # F6 jumps focus into the status bar (and a second F6 hands it back),
        # the same region key the QUILL editor uses.
        if code == wx.WXK_F6 and not event.AltDown() and not event.ControlDown():
            self._focus_status_bar()
            return
        if (
            event.AltDown()
            and event.ShiftDown()
            and not event.ControlDown()
            and code in (wx.WXK_UP, wx.WXK_DOWN)
            and wx.Window.FindFocus() is getattr(self, "_favorites_tree", None)
        ):
            self._move_selected_favorite(-1 if code == wx.WXK_UP else 1)
            return
        # Ctrl+Shift+E: New Folder, as an app-wide hotkey (#1211). The Station
        # menu carries the same accelerator, but a focused favorites TreeCtrl can
        # swallow the chord before the menu accelerator fires, so handle it here
        # too -- the same reason the reorder chord above is caught in the hook.
        if event.ControlDown() and event.ShiftDown() and not event.AltDown() and code == ord("E"):
            self._on_new_folder()
            return
        # Ctrl+Up / Ctrl+Down adjust volume from anywhere (#1263). The Playback
        # menu carries the same accelerator, but a bare Ctrl+arrow menu
        # accelerator is unreliable on Win32 and a focused control (the favorites
        # tree, a button) can swallow the chord before it fires. The frame char
        # hook runs before the focused control, so this makes the volume keys
        # work regardless of focus -- except inside a text field, where Ctrl+arrow
        # must stay available for editing.
        if (
            event.ControlDown()
            and not event.ShiftDown()
            and not event.AltDown()
            and code in (wx.WXK_UP, wx.WXK_DOWN)
            and not isinstance(wx.Window.FindFocus(), (wx.TextCtrl, wx.ComboBox))
        ):
            if code == wx.WXK_UP:
                self.radio_volume_up()
            else:
                self.radio_volume_down()
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
                PreferenceCheckbox(
                    "Verbose logging (&debug mode)",
                    "Write detailed radio diagnostics -- playback, recording, and "
                    "stream recovery -- to quill.log, for tracking down a "
                    "hard-to-reproduce problem. Off by default (it is chatty)",
                    history.debug_mode,
                ),
                PreferenceCheckbox(
                    "&Keep the computer awake while playing or recording",
                    "Stop Windows from going to sleep while a station is playing "
                    "or a recording is running, so the audio does not cut off. "
                    "On by default. (The screen may still turn off.)",
                    history.prevent_sleep,
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
                PreferenceChoice(
                    "&Favorites sort order:",
                    "How your favorites are ordered in the list. Ascending (A to "
                    "Z) and Descending (Z to A) sort folders and stations by name "
                    "and re-sort when you add one; Unsorted keeps your "
                    "hand-arranged Move Up/Down order. A folder can override this "
                    "for its own stations from its context menu.",
                    list(_FAVORITES_SORT_LABELS),
                    _FAVORITES_SORT_VALUES.index(history.favorites_sort),
                ),
            ],
            texts=[
                PreferenceText(
                    "&What's Playing announcement:",
                    _NOW_PLAYING_HELP,
                    history.now_playing_template,
                ),
                PreferenceText(
                    "&Log folder:",
                    "Where quill.log is written; leave blank for the default. "
                    "Changing it moves the log immediately.",
                    history.log_dir,
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
            history.debug_mode,
            history.prevent_sleep,
        ) = checkbox_values
        # Apply verbose logging immediately (quill-radio #5) so it takes effect
        # this session, not just the next launch.
        from quill.core.radio.radio_logging import set_radio_debug

        set_radio_debug(history.debug_mode)
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
        chosen_sort = _FAVORITES_SORT_VALUES[choice_indices[3]]
        if chosen_sort != history.favorites_sort:
            history.favorites_sort = chosen_sort
            self._reload_favorites_tree()
        new_template = text_values[0].strip()
        history.now_playing_template = new_template or _DEFAULT_NOW_PLAYING_TEMPLATE
        new_log_dir = text_values[1].strip()
        if new_log_dir != history.log_dir:
            history.log_dir = new_log_dir
            # Relocate the live log so new records land in the chosen folder now
            # (quill-radio #5), not just next launch.
            listener = getattr(self, "_log_listener", None)
            if listener is not None:
                from pathlib import Path

                from quill.stability.logging_config import relocate_log

                target = Path(new_log_dir) if new_log_dir else app_data_dir() / "logs"
                relocate_log(listener, target)
        radio_history.save_history(app_data_dir(), history)
        # Apply the Prevent Sleep choice now: acquire the keep-awake lock if a
        # station is already playing, or release it if the user just turned it off.
        self._update_sleep_inhibitor()
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
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
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
            # Every setting is per-stream now, so the playing station's channel,
            # night mode, and OptiLab also revert to the shared default live.
            self._radio_controller.set_sound_options(
                channel_mode=history.channel_mode,
                night_mode_enabled=history.night_mode_enabled,
                optilab_enabled=history.optilab_enabled,
                optilab_mode=history.optilab_mode,
                optilab_input_db=history.optilab_input_db,
                optilab_auto_adapt=history.optilab_auto_adapt,
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
        self.check_for_app_updates(
            repo_slug=_REPO, current_version=_VERSION, app_key="radio", silent_no_update=True
        )

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "Internet Radio from Quill, as a standalone app.\n\n"
            "Runs the same radio feature code as QUILL itself and shares its "
            "settings, favorites, and recordings.\n"
            f"https://github.com/{_REPO}\n\n"
            "Credits and thanks:\n"
            "- Broadcast polish adapted from OptiLab Core by dgl1984 "
            "(https://github.com/dgl1984/optilab, Apache-2.0).",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    # -- status ---------------------------------------------------------------

    def _on_volume_slider(self, _event: object) -> None:
        """Arrowing the focused Volume slider sets the radio volume (#1214).

        No explicit announcement here: the slider has keyboard focus while it is
        being arrowed, so the screen reader already speaks the new value on each
        press. Adding our own _announce on top made every keystroke double-speak
        (the native "55" plus "Radio volume 55") -- verbose. Let the focused
        slider carry the percentage; we only keep the live state in sync.
        """
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        percent = self._volume_slider.GetValue()
        controller.set_volume(percent)
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is not None:
            status_bar.refresh()

    def _sync_volume_slider(self) -> None:
        """Reflect the true volume on the slider without firing its event.

        SetValue does not emit EVT_SLIDER, so this stays a one-way sync (no loop)
        and keeps the slider honest after Ctrl+Up/Down or per-station volume
        memory changes the level elsewhere.
        """
        slider = getattr(self, "_volume_slider", None)
        controller = getattr(self, "_radio_controller", None)
        if slider is None or controller is None:
            return
        current = controller.state.volume_percent
        if slider.GetValue() != current:
            slider.SetValue(current)

    def _refresh_statusbar(self) -> None:
        text = self._radio_status_text() or "Radio: stopped"
        self._set_status(text)
        self._sync_volume_slider()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing = getattr(self, "_now_playing_text", None)
        if now_playing is not None:
            now_playing.SetLabel(text)
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is not None:
            status_bar.refresh()
        self._refresh_play_stop_button()
        self._refresh_record_button()

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
        # Thin wrapper over the shared close flow (AppShellFrame.handle_app_close),
        # which never ShowModals from inside EVT_CLOSE -- it vetoes and defers the
        # confirm dialog so Alt+F4 works while a station plays. "Ask" only prompts
        # when there's something to protect (live playback or a recording).
        from quill.ui.radio.player_controller import RadioPlayerState

        recording_active = bool(getattr(self._radio_recorder, "is_recording", False))
        playback_active = self._radio_controller.state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
        )
        self.handle_app_close(
            event,
            close_action=self._radio_history.close_action,
            protected=recording_active or playback_active,
            confirm=self._radio_close_confirm,
            shutdown=self._radio_shutdown,
        )

    def _radio_close_confirm(self) -> str | None:
        """Show Quill Radio's Exit / Minimize to Tray / Cancel dialog and return
        the choice ("exit"/"minimize"/None), persisting "Don't ask me again" to
        close_action. Run deferred by the shared close flow, never from inside
        EVT_CLOSE (see AppShellFrame.handle_app_close)."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history
        from quill.ui.radio.close_confirm_dialog import RadioCloseConfirmDialog

        recording_active = bool(getattr(self._radio_recorder, "is_recording", False))
        result = RadioCloseConfirmDialog(
            self.frame, recording_active=recording_active, announce_cb=self._announce
        ).show()
        if result is None:
            return None  # Cancel: stay open, nothing to remember.
        action, dont_ask_again = result
        if dont_ask_again:
            self._radio_history.close_action = action
            radio_history.save_history(app_data_dir(), self._radio_history)
        return action

    def _radio_shutdown(self) -> None:
        """Teardown just before the Radio window closes. Stamp when the app was
        last running so the next launch can report scheduled recordings missed
        while it was closed (#4; shared with embedded QUILL via RadioMixin,
        R2/11.6), stop the periodic timers and clear the active-recording marker
        (R3, so a clean close is not mistaken for a crash), then shut the
        controller, recorder, scheduler, task manager, media keys, and tray down
        (all non-blocking)."""
        try:
            self._app_host.shutdown()
        except Exception:  # noqa: BLE001 - Quillin teardown must never block exit
            pass
        self._stamp_radio_last_seen()
        # Stop Weather Guardian's timer without flipping its persisted on state,
        # so a clean exit resumes monitoring on the next launch.
        self.stop_weather_monitoring(announce=False, persist=False)
        for timer_attr in ("_radio_last_seen_timer", "_ipc_timer"):
            timer = getattr(self, timer_attr, None)
            if timer is not None:
                try:
                    timer.Stop()
                except Exception:  # noqa: BLE001
                    pass
        self._clear_radio_recording_marker()
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
        # Guarded like MainFrame's teardown: a hotkey unregister failure must
        # never block the window from closing.
        try:
            self._unregister_global_hotkeys()
        except Exception:  # noqa: BLE001 - shutdown must never block exit
            pass
        self._remove_tray_icon()


#: Single-instance slot for Quill Radio's IPC lock/queue -- distinct from
#: QUILL's own ("") and Quill Cast's, so the three sibling apps that share one
#: data dir each guard themselves without blocking each other (#1152).
_IPC_SLOT = "radio"


def main() -> int:
    from quill.stability.safe_mode import should_enable_safe_mode

    safe_mode = should_enable_safe_mode(sys.argv[1:], os.environ)
    from quill.core.ipc import (
        enqueue_open_request,
        release_primary_instance,
        try_claim_primary_instance,
    )

    # Single instance (#1152): if a Quill Radio is already running -- including
    # one sitting in the system tray -- do not open a second window. Ask the
    # running copy to come to the foreground, then exit. Cheap, before any UI or
    # logging setup, so a re-launch is near-instant.
    if not try_claim_primary_instance(slot=_IPC_SLOT):
        enqueue_open_request(None, slot=_IPC_SLOT)
        return 0

    from quill.core import components

    components.register_running_app("radio", REQUIRED_COMPONENTS)

    # Configure file logging before the app comes up so startup records -- and
    # everything radio debug mode raises to DEBUG -- land in quill.log
    # (quill-radio #5). The folder is the log-location preference, or the
    # default <data_dir>/logs.
    from pathlib import Path

    from quill.core.paths import app_data_dir
    from quill.core.radio import history as radio_history
    from quill.stability.logging_config import configure_logging

    history = radio_history.load_history(app_data_dir())
    log_dir = Path(history.log_dir) if history.log_dir else app_data_dir() / "logs"
    log_listener = configure_logging(log_dir)
    app = wx.App()
    frame = RadioAppFrame(safe_mode=safe_mode)
    frame._log_listener = log_listener
    frame.frame.Show()
    frame.frame.Raise()
    wx.CallAfter(frame._focus_initial_control)  # #1193: menu bar reachable on launch
    try:
        app.MainLoop()
    finally:
        release_primary_instance(slot=_IPC_SLOT)
        log_listener.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
