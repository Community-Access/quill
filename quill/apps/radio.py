"""Quill Radio -- Internet Radio as a standalone app.

Reuses ``RadioMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.apps import radio_now_playing as now_playing_readout
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
_VERSION = "3.0.0"
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
_FAVORITES_SORT_LABELS = (
    "Ascending (A to Z)",
    "Descending (Z to A)",
    "Unsorted (manual order)",
)
_FAVORITES_SORT_VALUES = ("az", "za", "manual")
#: View > Text Size choices: (menu label, font scale). Normal is the wx default.
_TEXT_SIZE_SCALES = (
    ("&Normal\tCtrl+Alt+1", 1.0),
    ("&Large\tCtrl+Alt+2", 1.25),
    ("La&rger\tCtrl+Alt+3", 1.5),
)
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
    # No Weather area anymore (2026-08-17): weather stands alone in the Quill
    # Weather app, reachable from the QuillVille menu. The NOAA Weather Radio
    # *streams* stay -- they are radio, under Browse Stations > Weather / NOAA.
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
        # This app IS the radio: the editor's release gate on ``core.radio``
        # (#1340) must not apply here, or the recording scheduler, wake task,
        # missed-recording reports, and every radio palette command silently
        # die in a public build. Safety locks still apply on top.
        self.features.grant_product_features({"core.radio"})
        # Radio's own menu accelerators (Ctrl+B for Browse, and the rest):
        # every menu item shows the key that reaches it.
        self._apply_app_keymap("radio")
        from quill.core.paths import app_data_dir

        self._app_features = load_app_features(app_data_dir(), "radio")
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
        # No Weather Guardian resume here anymore: the Weather menu left Quill
        # Radio (2026-08-17), so background alert monitoring belongs to the
        # Quill Weather app that owns its on/off switch.
        # Data Folder surfacing: announce a move applied at this launch, and
        # warn when a synced custom folder looks in use on another computer.
        from quill.ui.data_folder_dialog import surface_data_folder_startup

        wx.CallAfter(surface_data_folder_startup, self)
        # Media tools: say once, at launch, when this installation has lost the
        # engine that plays Ogg/Opus/HLS or the one that records. Deferred and
        # spoken rather than modal for the same reason as the line above -- a
        # launch is not the place to seize focus a screen reader has not settled
        # yet (#259). Silent on a healthy install, by design.
        from quill.ui.radio.media_preflight import surface_media_health_startup

        wx.CallAfter(surface_media_health_startup, self)
        # First run: three screens for somebody who has never used this before,
        # and nothing at all for anybody who already has favorites. Modal rather
        # than spoken, unlike the line above -- it is the whole content of a
        # first launch, and Skip leaves in one keystroke.
        from quill.ui.radio.first_run_dialog import maybe_run_first_run

        wx.CallAfter(maybe_run_first_run, self)
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

        # Read-only rather than static: a wx.StaticText cannot take focus, so the
        # one line carrying the station, the track and what the player is doing
        # could not be arrowed through, reviewed word by word, or copied. The
        # only ways to read it slowly were F6 into the status bar or Ctrl+T for
        # the full window, and neither should be required to read the line
        # already sitting at the top. No TE_PROCESS_TAB: Tab must move focus
        # onward and never be captured here.
        self._now_playing_text = wx.TextCtrl(
            panel,
            value="Radio: stopped",
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL | wx.BORDER_SIMPLE,
            size=(-1, 54),
        )
        set_accessible_name(self._now_playing_text, "Now playing")
        self._now_playing_text.SetHelpText(
            "What is playing. Ctrl+Shift+W says where you are in it; Ctrl+T opens the full details."
        )
        self._pending_now_playing: str | None = None
        self._now_playing_text.Bind(
            wx.EVT_KILL_FOCUS, lambda e: now_playing_readout.on_blur(self, e)
        )
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
        # A favorites list you play from, not a player. Play/Stop, Add to
        # Favorites, Record, the chapter buttons and Browse all left this row on
        # 2026-08-21, each keeping its menu item and key; player_panel.py had
        # already argued it -- "an always-open player is mostly furniture". Mute
        # and Volume stay, and are exactly the pair the Browse window has.
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
        # Mute sits with Volume and matches browse_tree_dialog exactly -- the
        # same control, the same label, the same key. The main window was the
        # one surface in the app without it, so the same listener met two
        # different answers to "how do I mute this?".
        self._mute_btn = wx.ToggleButton(panel, label="&Mute")
        set_accessible_name(self._mute_btn, "Mute (Ctrl+M)")
        self._mute_btn.SetValue(bool(getattr(controller, "state", None) and controller.state.muted))
        self._mute_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda _e: self.radio_mute_toggle())
        buttons.Add(self._mute_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
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
        # Space on the row you are listening to pauses it. Only that row: Space
        # everywhere else in a tree belongs to the tree, and hijacking it would
        # take away a key people use to select. A podcast paused here keeps its
        # place; the old behaviour reloaded the episode from the beginning.
        if code == wx.WXK_SPACE and not (
            event.ControlDown() or event.ShiftDown() or event.AltDown()
        ):
            favorite = self._selected_favorite()
            if favorite is not None and self._favorite_is_playing(favorite):
                self._toggle_current_playback()
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
        from quill.ui.radio.playback_state import ACTIVE_STATES

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
                and self._radio_controller.state.state in ACTIVE_STATES
            )
            entries = [
                ("&Stop" if playing else "&Play", self._on_play_stop_context),
                ("Station &Details...", self._on_favorite_details),
                ("Rena&me...\tF2", self._on_tree_rename),
                # The chord already worked; the menu now says so. A shortcut
                # only a document mentions is a shortcut most listeners never
                # hear about.
                ("Move &Up\tAlt+Shift+Up", lambda: self._move_selected_favorite(-1)),
                ("Move Dow&n\tAlt+Shift+Down", lambda: self._move_selected_favorite(1)),
                # "F&older"/"Fold&er": Move to Folder and New Folder both said
                # &o, so one of the pair silently never answered its key.
                ("Move to F&older...", self._on_tree_move_to_folder),
                ("&Remove...\tDelete", self._on_tree_remove),
                ("New Fold&er...\tCtrl+Shift+E", self._on_new_folder),
            ]
            # Mark-and-Move (#1190): pick a station up once, then drop it above
            # or below any destination in one step -- no Alt+Shift+Up/Down 30
            # times. Mirrors the Favorites Manager's Mark for Move. "Mar&k",
            # not "&Mark": Rena&me already answers M in this menu.
            marked = getattr(self, "_marked_favorite_key", None)
            entries.append(("Mar&k for Move", self._on_mark_favorite))
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
        from quill.ui.radio.playback_state import ACTIVE_STATES

        favorite = self._selected_favorite()
        if favorite is None:
            return
        state = self._radio_controller.state
        if (
            state.station is not None
            and state.station.stream_url == favorite.station.stream_url
            and state.state in ACTIVE_STATES
        ):
            self.radio_stop()
        else:
            self._radio_controller.play_station(favorite.station)
            self._announce(f"Playing {favorite.display_label}.")

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
            transport_host=self,
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
            self._announce(f"Could not read the playlist: {exc}.")
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
        from quill.ui.radio.playback_state import ACTIVE_STATES, RadioPlayerState

        state = self._radio_controller.state.state
        if state in ACTIVE_STATES:
            self.radio_stop()
        elif state is RadioPlayerState.PAUSED:
            self.radio_toggle_play_pause()
        else:
            self._play_selected_favorite()

    def _refresh_play_stop_button(self) -> None:
        from quill.ui.radio.playback_state import ACTIVE_STATES

        state = self._radio_controller.state.state
        stopping = state in ACTIVE_STATES
        # A button mnemonic on a frame competes with the MENU BAR's, which is
        # #1208: "&Record" on both meant Alt+R opened the menu and the button
        # never fired. The answer is a free letter, not no letter -- Alt+P is
        # the Playback menu, so the transport button takes Alt+L to play and
        # Alt+T to stop, and Ctrl+P still toggles from anywhere.
        button_label = "S&top" if stopping else "P&lay"
        menu_label = "&Stop" if stopping else "&Play"
        button = getattr(self, "_play_stop_btn", None)
        if button is not None and button.GetLabel() != button_label:
            button.SetLabel(button_label)
            spoken = "Stop (Alt+T, or Ctrl+P)" if stopping else "Play (Alt+L, or Ctrl+P)"
            set_accessible_name(button, spoken)
        menu_bar = self.frame.GetMenuBar()
        item_id = getattr(self, "_play_menu_item_id", None)
        if menu_bar is not None and item_id is not None:
            menu_bar.SetLabel(int(item_id), f"{menu_label}\tCtrl+P")
        self._refresh_favorite_toggle()

    def _refresh_record_button(self) -> None:
        """Keep the capture button honest about what it would capture.

        The decision lives in quill/apps/radio_capture_button.py (GATE-11);
        this is the one line that applies it.
        """
        from quill.apps.radio_capture_button import refresh

        refresh(self)

    def _on_capture_button(self) -> None:
        """Do whatever the capture button currently says it will do."""
        from quill.apps.radio_capture_button import act

        act(self)

    def _refresh_favorite_toggle(self) -> None:
        """Keep every door onto "save this station" saying the same thing."""
        from quill.apps import radio_favorite_toggle

        radio_favorite_toggle.refresh(self)

    def _on_favorite_toggle(self) -> None:
        station = self._radio_controller.state.station
        if station is None:
            self._announce("Nothing is playing to favorite.")
            return
        key = station.station_uuid or station.stream_url
        if self._radio_favorites.contains(station):
            self._radio_favorites.remove(key)
            self._announce(f"Removed {station.display_name} from favorites.")
        else:
            self._radio_favorites.add(station)
            self._announce(
                f"Added {station.display_name} to favorites.",
                sound=SoundEvent.RADIO_FAVORITE_ADDED,
            )
        self._save_radio_favorites()
        self._reload_favorites_tree()
        self._refresh_favorite_toggle()

    def _favorite_is_playing(self, favorite: object) -> bool:
        """Whether this favourite is the thing the player currently holds."""
        station = getattr(self._radio_controller.state, "station", None)
        if station is None or favorite is None:
            return False
        return str(getattr(station, "stream_url", "")) == str(
            getattr(getattr(favorite, "station", None), "stream_url", "")
        )

    def _toggle_current_playback(self) -> None:
        """Pause or resume what is playing, and say which it did."""
        from quill.ui.radio.playback_state import RadioPlayerState

        self._radio_controller.toggle_play_pause()
        state = getattr(self._radio_controller.state, "state", None)
        self._announce("Paused." if state is RadioPlayerState.PAUSED else "Resumed.")

    def _play_selected_favorite(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("No station selected. Add favorites from Browse Stations.")
            return
        if self._favorite_is_playing(favorite):
            # Already the thing playing: pause or resume it rather than loading
            # it again. Reloading a podcast episode throws away where you were
            # in it, which is the opposite of what pressing play on the row you
            # are already listening to means (reported 2026-08-18).
            self._toggle_current_playback()
            return
        self._radio_controller.play_station(favorite.station)
        self._announce(f"Playing {favorite.display_label}.")

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
        station_menu.Append(browse_id, self._menu_label("&Browse Stations...", "radio.browse"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_browse_stations(), id=browse_id)
        rrs_update_id = wx.NewIdRef()
        station_menu.Append(rrs_update_id, "Update Radio Reading &Services...\tCtrl+Alt+Shift+R")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.update_reading_services_directory(),
            id=rrs_update_id,
        )
        station_menu.Append(search_id, "&Search Stations...\tCtrl+F")
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
        # YouTube support is built in, so this is only ever needed when YouTube
        # changes how it serves audio and the bundled helper goes stale. It sits
        # next to the YouTube commands because that is where someone whose
        # YouTube links stopped working will look for it.
        yt_update_id = wx.NewIdRef()
        station_menu.Append(yt_update_id, "&Update YouTube Support...\tCtrl+Alt+Y")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_update_youtube_support(), id=yt_update_id
        )
        station_menu.Append(
            find_id, self._menu_label("Find &Streams from a Website...", "radio.find_streams")
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
            station_menu.Append(spotify_connect_id, "Connect to S&potify...\tCtrl+Alt+P")
            station_menu.Append(spotify_browse_id, "Bro&wse Spotify...\tCtrl+Alt+O")
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
            self._menu_label("Add Playing Station to &Favorites", "radio.toggle_playing_favorite"),
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
        station_menu.Append(import_id, "&Import Stations from Playlist...\tCtrl+I")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_stations_from_playlist(), id=import_id)
        # #1249: export favorites to an M3U playlist. Thin wiring lives in
        # playlist_export_ui (radio.py is at budget).
        from quill.ui.radio.playlist_export_ui import export_favorites_to_playlist

        export_id = wx.NewIdRef()
        station_menu.Append(export_id, "&Export Favorites to Playlist...\tCtrl+Shift+X")
        self.frame.Bind(wx.EVT_MENU, lambda _e: export_favorites_to_playlist(self), id=export_id)
        # #1193: move your stations/settings/recordings to a new device or recover
        # after a reinstall. Thin wiring lives in backup_ui (radio.py is at budget).
        from quill.ui.radio.backup_ui import back_up_radio_data, restore_radio_data

        backup_id, restore_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(backup_id, "Back &Up Stations and Settings...\tCtrl+Shift+U")
        station_menu.Append(restore_id, "&Restore from Backup...\tCtrl+Shift+R")
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
        station_menu.Append(prefs_id, "&Preferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_preferences(), id=prefs_id)
        station_menu.AppendSeparator()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        station_menu.Append(tray_id, "Send to &Tray\tCtrl+W")
        station_menu.Append(exit_id, "E&xit\tCtrl+Q")
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
        # Video: a finished YouTube video has a timeline, so it can be
        # scrubbed, sped up, navigated by chapter and read as a transcript --
        # none of which a live broadcast can do, and every one of which says so
        # out loud rather than doing nothing. Wiring lives in
        # quill/apps/radio_video_menu.py; radio.py is at its GATE-11 budget.
        from quill.apps.radio_playback_extras import build_playback_extras

        # Pinned as a group rather than unpacked: the helper owns which items
        # exist, and a fixed-length unpack here would break every time it grew.
        video_menu_ids = build_playback_extras(self, playback_menu, wx)
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
        playback_menu.Append(whats_playing_id, "&What's Playing?\tCtrl+T")
        # Ctrl+Shift+H is free in the standalone app; inside full QUILL the same
        # command ships unbound because there Ctrl+Shift+H is Replace All.
        song_history_id = wx.NewIdRef()
        playback_menu.Append(song_history_id, "Son&g History...\tCtrl+Shift+H")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_song_history(), id=song_history_id)
        self._global_volume_item_id = wx.NewIdRef()
        playback_menu.AppendCheckItem(
            self._global_volume_item_id,
            self._menu_label("Use One &Volume for All Stations", "radio.toggle_global_volume"),
        )
        playback_menu.Check(self._global_volume_item_id, self._radio_history.use_global_volume)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.radio_toggle_global_volume(),
            id=self._global_volume_item_id,
        )
        forget_volumes_id = wx.NewIdRef()
        playback_menu.Append(
            forget_volumes_id,
            self._menu_label(
                "Forget Every Station's Own Volu&me...", "radio.forget_station_volumes"
            ),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.radio_forget_station_volumes(), id=forget_volumes_id
        )
        self._announce_titles_item_id = wx.NewIdRef()
        playback_menu.AppendCheckItem(
            self._announce_titles_item_id,
            self._menu_label("Announce Trac&k Titles", "radio.toggle_title_announcements"),
        )
        playback_menu.Check(
            self._announce_titles_item_id, self._radio_history.announce_track_titles
        )
        sleep_id = wx.NewIdRef()
        playback_menu.Append(sleep_id, "Sleep &Timer...\tCtrl+Shift+Z")
        wake_id = wx.NewIdRef()
        playback_menu.Append(wake_id, self._menu_label("Wake-U&p Timer...", "radio.wake_timer"))
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
            settings_id, self._menu_label("Recording &Settings...", "radio.recording_settings")
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

        # Pre-release top-level Audio Description Project menu. The typed Ask
        # ADP assistant (future.adp_assistant) is ON by default for testing, so
        # this is present by default; _build_adp_menu returns None only if a
        # profile turns it off. The hands-free conversational mode
        # (future.adp_voice_mode) is the part that stays locked until a signed
        # unlock code is redeemed (Help > Redeem Unlock Code..., here or in
        # QUILL -- they share one unlock store). Undocumented until launch.
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, "A&udio Description Project\tCtrl+Alt+A")

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
        help_menu.Append(hotkeys_id, "&Global Hotkeys...\tCtrl+Alt+G")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_keymap_editor(), id=shortcuts_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_global_hotkeys_manager(), id=hotkeys_id)
        # The sheet sits beside the editor because they are the two halves of
        # one question: this one answers "what can I press?", the editor answers
        # "I want that somewhere else". Every menu item names its key since 3.0,
        # which fixed discovery *inside* a menu and left "open six menus and
        # arrow to the end of each" as the only way to see them together.
        sheet_id = wx.NewIdRef()
        help_menu.Append(sheet_id, "Keyboard Shortcuts S&heet...\tCtrl+Alt+Shift+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_keyboard_cheat_sheet(), id=sheet_id)
        bug_id = wx.NewIdRef()
        help_menu.Append(bug_id, "Report a &Bug...\tCtrl+Alt+B")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_app_bug(source_app="Quill Radio", app_version=_VERSION),
            id=bug_id,
        )
        ffmpeg_id = wx.NewIdRef()
        help_menu.Append(ffmpeg_id, "&Get FFmpeg...\tCtrl+Alt+F")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_ffmpeg_component(), id=ffmpeg_id)
        # Beside Get FFmpeg because they are the same kind of thing: the two
        # media tools every full installer bundles, and that a Lite install --
        # which downloads the base runtime and no tools at all -- has neither
        # of. Radio needs this one more than FFmpeg: mpv is the playback engine,
        # so without it Ogg, Opus and HLS stations do not play at all.
        mpv_id = wx.NewIdRef()
        help_menu.Append(mpv_id, "Get mpv Playback &Engine...\tCtrl+Alt+M")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.download_mpv_component(), id=mpv_id)
        help_menu.AppendSeparator()
        guide_id, notes_id, prd_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        # The release notes ship in two halves: the narrative, and the companion
        # that carries the reasoning. The narrative points at the companion by
        # name, so it needs a door of its own -- a document nobody can open from
        # the Help menu is a document that does not really ship.
        notes_depth_id = wx.NewIdRef()
        help_menu.Append(guide_id, "&User Guide\tF1")
        help_menu.Append(notes_id, "&Release Notes\tShift+F1")
        help_menu.Append(notes_depth_id, "Release Notes: The &Long Version\tCtrl+Shift+F1")
        help_menu.Append(prd_id, "&Product Requirements...\tCtrl+F1")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_radio_doc("userguide"), id=guide_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_radio_doc("release-notes-3.0"), id=notes_id
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._open_radio_doc("release-notes-3.0-in-depth"),
            id=notes_depth_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_radio_doc("prd"), id=prd_id)
        help_menu.AppendSeparator()
        help_menu.Append(updates_id, "Check for Up&dates...\tCtrl+Alt+U")
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About Quill Radio\tAlt+F1")
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
            sort_menu.AppendRadioItem(item_id, label + accel)
            sort_menu.Check(item_id, self._radio_history.favorites_sort == value)
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, v=value: self._set_favorites_sort(v), id=item_id
            )
        view_menu.AppendSubMenu(sort_menu, "Sort &Favorites")
        expand_id, collapse_id = wx.NewIdRef(), wx.NewIdRef()
        view_menu.Append(expand_id, "&Expand All Folders\tCtrl+Alt+E")
        view_menu.Append(collapse_id, "&Collapse All Folders\tCtrl+Alt+Shift+E")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._expand_all_folders(True), id=expand_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._expand_all_folders(False), id=collapse_id)
        view_menu.AppendSeparator()
        downloads_id = wx.NewIdRef()
        view_menu.Append(downloads_id, "&Downloads...	Ctrl+Shift+J")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_download_queue(), id=downloads_id)
        self._keep_menu_ids(downloads_id)
        from quill.apps import radio_settings_menu as menus

        catalog_status_id, audio_health_id = menus.build_catalog_status_item(self, view_menu, wx)
        self._keep_menu_ids(catalog_status_id, audio_health_id)
        self._keep_menu_ids(menus.build_choose_columns_item(self, view_menu, wx))
        features_id = wx.NewIdRef()
        view_menu.Append(features_id, "&Customize Features...\tCtrl+Alt+C")
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
        # Insert rather than Append: View belongs directly after Station, but it
        # cannot be *built* until here (its Text Size radio items need the font
        # scale that later setup resolves). Index 1 is immediately after Station.
        menu_bar.Insert(1, view_menu, "&View")
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
            sources_id,
            *video_menu_ids,
            yt_update_id,
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
            guide_id,
            notes_id,
            notes_depth_id,
            prd_id,
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

    def _open_radio_doc(self, stem: str) -> None:
        titles = {
            "userguide": "Quill Radio User Guide",
            "release-notes-3.0": "Quill Radio Release Notes",
            "release-notes-3.0-in-depth": "Quill Radio Release Notes: The Long Version",
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

    def _open_download_queue(self) -> None:
        """View > Downloads... See ``ui/radio/download_menu.py``."""
        from quill.ui.radio import download_menu

        download_menu.open_queue(self)

    def _send_to_tray(self) -> None:
        """Hide to the tray, saying what happens to any downloads still going.

        Said either way: a queue that silently keeps running is exactly as
        surprising as one that silently stops, and which happens is a
        preference somebody set once and will not remember.
        """
        from quill.ui.radio import download_menu

        self.frame.Hide()
        self._announce(download_menu.tray_message(self))

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
        self._announce(f"Sorted favorites: {labels[value]}.")

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
        self._announce(f"Text size: {names.get(scale, 'Normal')}.")

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
            self._announce("Returned to favorite stations.")
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

    def _radio_go_to_player(self) -> None:
        """Playback > Go to Player. Runs the same dispatcher every other window
        runs, so the main window cannot answer this key differently from the
        browse tree or the managers."""
        from quill.core.radio import transport_commands
        from quill.ui.radio import transport_keys

        transport_keys.perform(self, transport_commands.GO_TO_PLAYER)

    def _on_volume_boost_menu(self) -> None:
        """The Playback menu's Volume Boost check item: toggle, then pin the
        checkmark to the persisted truth."""
        self.radio_toggle_volume_boost()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._volume_boost_item_id), self._radio_history.volume_boost)

    def _open_preferences(self) -> None:
        """Station > Preferences. See :mod:`quill.apps.radio_preferences`."""
        from quill.apps.radio_preferences import open_preferences

        open_preferences(self)

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
                optilab_exact_live=history.optilab_exact_live,
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
            "Accessible internet radio, podcasts, and audio from Quill.\n\n"
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
        # Same one-way rule for Mute: Ctrl+M and the Audio menu mute too, so a
        # toggle that only ever sends and never receives ends up showing the
        # opposite of the truth.
        mute_btn = getattr(self, "_mute_btn", None)
        if mute_btn is not None:
            muted = bool(getattr(controller.state, "muted", False))
            if mute_btn.GetValue() != muted:
                mute_btn.SetValue(muted)

    def _refresh_statusbar(self) -> None:
        text = self._radio_status_text() or "Radio: stopped"
        self._set_status(text)
        self._sync_volume_slider()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing_readout.refresh(self)
        status_bar = getattr(self, "_status_bar", None)
        if status_bar is not None:
            status_bar.refresh()
        self._refresh_play_stop_button()
        self._refresh_record_button()
        from quill.apps import radio_chapter_buttons

        radio_chapter_buttons.refresh(self)

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
        from quill.ui.radio.playback_state import ACTIVE_STATES

        recording_active = bool(getattr(self._radio_recorder, "is_recording", False))
        playback_active = self._radio_controller.state.state in ACTIVE_STATES
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
    from quill.core.data_location import apply_pending_at_launch

    # A queued Data Folder move/import applies before a single data file is
    # read (mirrors quill.__main__.main -- the family shares one profile, so
    # whichever app launches next must be the one to apply it).
    apply_pending_at_launch()
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
