"""QUILL Cast -- Podcasts as a standalone app.

Reuses ``PodcastsMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.apps.podcasts_library_actions import CastLibraryActionsMixin
from quill.apps.podcasts_menu import APP_REPO, APP_TITLE, APP_VERSION, CastMenuBarMixin
from quill.ui.app_quillins import QuillinsAppMixin
from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.keymap_editor import KeymapEditorMixin
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin
from quill.ui.podcasts.winamp_mixin import CastWinampKeysMixin

# Identity lives with the menu bar that displays it; see podcasts_menu.py.
_TITLE = APP_TITLE
_VERSION = APP_VERSION
_REPO = APP_REPO
#: Shared components this app requires, for the component-refcount registry
#: (ffmpeg for playback/processing; libmpv is intentionally not used -- wx.media).
REQUIRED_COMPONENTS: tuple[str, ...] = ("ffmpeg",)


class PodcastsAppFrame(
    # AppShellFrame is listed first so its toggle_window_to_tray / _send_to_tray
    # (which the apps have) win over GlobalHotkeysMixin's send_to_tray-based copy.
    AppShellFrame,
    PodcastsMixin,
    CastLibraryActionsMixin,
    CastMenuBarMixin,
    CastWinampKeysMixin,
    MediaSleepTimerMixin,
    AdpMixin,
    UnlockCodesMixin,
    GlobalHotkeysMixin,
    KeymapEditorMixin,
    QuillinsAppMixin,
):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        # This app IS the podcast manager: the editor's release gate on
        # ``core.podcasts`` must not apply here, or the new-episode check
        # monitor and every podcast palette command silently die in a public
        # build. Safety locks still apply on top.
        self.features.grant_product_features({"core.podcasts"})
        self._init_podcasts()
        # Quillins for Quill Cast (app id "cast"): load contributions before the
        # menu bar is built so contributed items appear in the &Quillins menu.
        self._init_app_quillins("cast")
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(
            lambda: self._podcast_history.announce_dialog_transitions
        )
        self._init_media_sleep_timer()
        self._build_menu_bar()
        self._build_main_panel()
        self._register_podcasts_commands()
        self._register_podcast_session_commands()
        self._register_media_sleep_timer_commands()
        self._register_adp_commands()
        self._register_unlock_code_commands()
        self._ensure_tray_icon(self._build_podcast_tray_menu, tooltip=_TITLE)
        self._register_media_keys({
            "play_pause": self.podcast_toggle_play_pause,
            "stop": self.podcast_stop,
            "next": self.podcast_next_chapter,
            "previous": self.podcast_previous_chapter,
        })
        # Per-command system-wide hotkeys (Help > Global Hotkeys...). Register
        # the show/hide command the default table binds so its Ctrl+Alt+Shift+Q
        # actually dispatches; the transport commands (podcasts.play_pause/stop)
        # are already registered above. We do NOT call
        # _register_global_hotkey_commands -- that also adds the sticky-note /
        # editor commands the apps don't want. Then bind the message hook and
        # register whatever the user has configured.
        self.commands.try_register(
            "view.toggle_window_to_tray",
            "Show/Hide QUILL Cast to the Tray",
            self.toggle_window_to_tray,
            self._binding_for("view.toggle_window_to_tray"),
            feature_id="core.app",
        )
        self.frame.Bind(wx.EVT_HOTKEY, self._on_global_hotkey)
        self._reload_global_hotkeys()
        # Data Folder surfacing: announce a move applied at this launch, and
        # warn when a synced custom folder looks in use on another computer.
        from quill.ui.data_folder_dialog import surface_data_folder_startup

        wx.CallAfter(surface_data_folder_startup, self)
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_cast_app_close)
        # Alt+F4-to-tray (opt-in preference) is handled inside
        # _on_main_char_hook, bound with the Winamp keys in _build_main_panel:
        # two EVT_CHAR_HOOK bindings on one window would fight over which gets
        # to decide whether a key travels on.
        self._maybe_resume_last_episode()
        # Deferred (CallAfter), not inline: this touches the network, and a
        # launch is not the place to do that before the window is even up.
        wx.CallAfter(self._maybe_check_updates_on_startup)
        # Read the shared Listening Places folder once, now, while nothing is
        # playing. Deferred and off-thread: a cloud folder can take seconds to
        # materialise a file and launch must never wait on it, and a position
        # arriving mid-session would move the playhead under somebody. See
        # sync_places_command.sync_at_launch for why this is the only
        # unprompted read there is.
        from quill.ui.sync_places_command import sync_at_launch

        wx.CallAfter(sync_at_launch, self)

    # -- main panel -------------------------------------------------------------
    #
    # A bare frame with only a menu bar leaves keyboard focus with nowhere to
    # land: Tab does nothing and a screen reader reads an empty client area.
    # The main panel gives the app a real, named, tabbable surface -- the
    # same pinned views (Favorites, New Episodes, Continue Listening, Inbox)
    # and library folders the Podcast Manager shows, right on the main page,
    # matching Quill Radio's favorites tree (#1043).

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        self._now_playing_text = wx.StaticText(panel, label="Podcasts: stopped")
        set_accessible_name(self._now_playing_text, "Now playing")
        root.Add(self._now_playing_text, 0, wx.EXPAND | wx.ALL, 8)

        library_label = wx.StaticText(panel, label="&Library:")
        root.Add(library_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._shows_tree = wx.TreeCtrl(
            panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT
        )
        set_accessible_name(
            self._shows_tree,
            "Your podcast library: pinned views and folders; Enter on a show "
            "plays its next episode, Shift+F10 opens all actions",
        )
        root.Add(self._shows_tree, 1, wx.EXPAND | wx.ALL, 8)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_library_activated)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_library_context_menu)
        self._shows_tree.Bind(wx.EVT_KEY_DOWN, self._on_library_key)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_library_expanding)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        # One transport button, not two static ones: it tracks Play, Pause,
        # and Resume so it is never dead in a given state.
        self._play_pause_btn = wx.Button(panel, label="&Play")
        set_accessible_name(self._play_pause_btn, "Play")
        self._play_pause_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_transport_button())
        buttons.Add(self._play_pause_btn, 0, wx.RIGHT, 6)
        self._stop_btn = wx.Button(panel, label="&Stop")
        set_accessible_name(self._stop_btn, "Stop")
        self._stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self.podcast_stop())
        buttons.Add(self._stop_btn, 0, wx.RIGHT, 6)
        # Favorite toggle for whatever show is playing right now, same
        # pattern as Quill Radio's main-page toggle.
        self._favorite_toggle_btn = wx.Button(panel, label="Add to Fa&vorites")
        set_accessible_name(self._favorite_toggle_btn, "Add the playing show to favorites")
        self._favorite_toggle_btn.Enable(False)
        self._favorite_toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_favorite_toggle())
        buttons.Add(self._favorite_toggle_btn, 0, wx.RIGHT, 6)
        for label, handler in (
            ("Open &Manager...", lambda _e: self.open_podcast_manager()),
            ("&Add Podcast...", lambda _e: self._podcast_open_add_dialog()),
        ):
            button = wx.Button(panel, label=label)
            set_accessible_name(button, label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_library_tree()
        self._refresh_transport_controls()
        # Winamp classic transport letters on the main page, sharing Quill
        # Radio's key map (quill/ui/radio/winamp_keys.py) so the letters mean
        # the same thing in both apps.
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_main_char_hook)
        self.frame.Bind(wx.EVT_KEY_UP, self._on_main_key_up)
        # Losing the window must end a scan: a listener left at four times
        # speed because they alt-tabbed mid-hold has no way to know why.
        self.frame.Bind(wx.EVT_ACTIVATE, self._on_main_activate)
        from quill.ui.podcasts.scan_hold_control import ScanHoldController

        self._scan_hold = ScanHoldController(self, parent=self.frame)
        self._select_default_launch_view()
        self._shows_tree.SetFocus()

    # -- Winamp keys + launch view -----------------------------------------

    def _on_main_char_hook(self, event: wx.KeyEvent) -> None:
        """Alt+F4-to-tray first, then the Winamp transport letters.

        One hook rather than two: two EVT_CHAR_HOOK bindings on the same
        window means only one of them decides whether the key travels on, and
        which one wins is an implementation detail nobody should depend on.
        """
        if (
            event.GetKeyCode() == wx.WXK_F4
            and event.AltDown()
            and getattr(self._podcast_history, "alt_f4_to_tray", False)
        ):
            self._send_to_tray()
            return
        scan = getattr(self, "_scan_hold", None)
        if scan is not None and scan.handles(
            key_code=event.GetKeyCode(),
            shift=bool(event.ShiftDown()),
            ctrl=bool(event.ControlDown()),
            alt=bool(event.AltDown()),
        ):
            # Every auto-repeat comes through here, which is how the hold is
            # measured; press() is idempotent for exactly that reason.
            scan.press()
            return
        self._on_winamp_char_hook(event)

    def _on_main_key_up(self, event: wx.KeyEvent) -> None:
        """End a scan the moment the key actually comes up.

        The watchdog timer would end it anyway; this only makes the drop back
        immediate rather than up to the grace window late.
        """
        scan = getattr(self, "_scan_hold", None)
        if scan is not None and scan.is_scanning and event.GetKeyCode() == wx.WXK_RIGHT:
            scan.stop()
        event.Skip()

    def _on_main_activate(self, event: wx.ActivateEvent) -> None:
        if not event.GetActive():
            scan = getattr(self, "_scan_hold", None)
            if scan is not None:
                scan.stop()
        event.Skip()

    def _winamp_keys_enabled(self) -> bool:
        return bool(getattr(self._podcast_history, "winamp_playback_keys", True))

    def _winamp_controller(self) -> object | None:
        return self._podcast_controller

    def _winamp_rows(self) -> list[tuple[object, object]]:
        """The selected show's episodes -- what the tree is showing here."""
        selected = self._selected_tree_data()
        show = None
        if selected is not None and selected[0] == "show":
            show = self._podcast_library.find_show(selected[1])
        elif selected is not None and selected[0] == "episode":
            show_id, _, _guid = selected[1].partition("\x00")
            show = self._podcast_library.find_show(show_id)
        if show is None:
            return []
        from quill.core.podcasts.sorting import sort_episodes

        return [(show, episode) for episode in sort_episodes(show.episodes, "newest_first")]

    def _winamp_selected_index(self) -> int:
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "episode":
            return -1
        _show_id, _, guid = selected[1].partition("\x00")
        for index, (_show, episode) in enumerate(self._winamp_rows()):
            if episode.guid == guid:
                return index
        return -1

    def _winamp_select_index(self, index: int) -> None:
        rows = self._winamp_rows()
        if not (0 <= index < len(rows)):
            return
        show, episode = rows[index]
        self._reload_library_tree(keep_key=("episode", f"{show.id}\x00{episode.guid}"))

    def _winamp_play_pair(self, show: object, episode: object) -> None:
        self._play_episode_object(show, episode)

    def _select_default_launch_view(self) -> None:
        """Land on the view the listener chose, not always the tree top.

        Somebody whose routine is "open it and see what is new" should not
        have to arrow there every single time.
        """
        view_id = self._podcast_library.settings.default_launch_view
        if not view_id:
            return
        self._reload_library_tree(keep_key=("view", view_id))

    # -- library tree (pinned views + folders + shows) ---------------------

    def _reload_library_tree(self, *, keep_key: tuple[str, str] | None = None) -> None:
        from quill.core.podcasts.sorting import sort_shows, unheard_count
        from quill.core.podcasts.virtual_views import (
            VIRTUAL_VIEWS,
            favorite_shows,
            view_label,
            virtual_view_pairs,
        )

        tree = self._shows_tree
        if keep_key is None:
            keep_key = self._selected_tree_data()
        tree.DeleteAllItems()
        root = tree.AddRoot("Library")
        select_item = None

        def tag(item: object, key: tuple[str, str]) -> None:
            nonlocal select_item
            tree.SetItemData(item, key)
            if key == keep_key:
                select_item = item

        fav_count = len(favorite_shows(self._podcast_library))
        fav_label = view_label(self._podcast_library, "favorites")
        fav_item = tree.AppendItem(root, f"{fav_label} ({fav_count})" if fav_count else fav_label)
        tag(fav_item, ("view", "favorites"))
        for view_id, _default in VIRTUAL_VIEWS:
            label = view_label(self._podcast_library, view_id)
            count = len(virtual_view_pairs(self._podcast_library, view_id))
            item = tree.AppendItem(root, f"{label} ({count})" if count else label)
            tag(item, ("view", view_id))

        folder_items: dict[str | None, object] = {None: root}

        # Folder badges: how many podcasts live under each folder -- the whole
        # subtree, matching what expanding the folder actually reveals.
        direct_counts: dict[str | None, int] = {}
        for show in self._podcast_library.shows:
            direct_counts[show.folder_id] = direct_counts.get(show.folder_id, 0) + 1

        def folder_show_count(folder_id: str | None) -> int:
            total = direct_counts.get(folder_id, 0)
            for child in self._podcast_library.folders:
                if child.parent_folder_id == folder_id:
                    total += folder_show_count(child.id)
            return total

        def folder_item(folder_id: str | None) -> object:
            if folder_id in folder_items:
                return folder_items[folder_id]
            folder = self._podcast_library.find_folder(folder_id)
            if folder is None:
                return root
            count = folder_show_count(folder.id)
            label = f"{folder.name} ({count})" if count else folder.name
            item = tree.AppendItem(folder_item(folder.parent_folder_id), label)
            tag(item, ("folder", folder_id or ""))
            folder_items[folder_id] = item
            return item

        for folder in self._podcast_library.folders:
            folder_item(folder.id)

        if not self._podcast_library.shows and not self._podcast_library.folders:
            # An empty library offers the three ways in, as rows that act on
            # Enter -- and stop appearing the moment anything is subscribed.
            # The same trio Quill Radio's empty Subscriptions branch shows.
            for key, label in (
                ("add", "Add a Podcast by URL..."),
                ("import", "Import Podcasts from OPML..."),
                ("search", "Search for a Podcast..."),
            ):
                tag(tree.AppendItem(root, label), ("action", key))

        for show in sort_shows(
            self._podcast_library.shows, self._podcast_library.settings.show_sort_mode
        ):
            count = unheard_count(show)
            # Say "unheard", now that folders wear a bare "(n)" for how many
            # podcasts they hold -- two counts that read identically would
            # force the listener to remember which node kind they are on.
            label = f"{show.title} ({count} unheard)" if count else show.title
            item = tree.AppendItem(folder_item(show.folder_id), label)
            tag(item, ("show", show.id))
            # #1192: episodes hang under the show so it can be expanded in
            # place. They are filled in on demand (EVT_TREE_ITEM_EXPANDING),
            # not up front: a 1,300-show library with a refreshed catalog is
            # around 196,000 episodes, and building that many tree items on
            # every library save froze the window for minutes. A single
            # placeholder child is enough to make the show expandable, and
            # expanding one show costs one show's worth of work.
            if show.episodes:
                placeholder = tree.AppendItem(item, "Loading episodes...")
                tag(placeholder, ("placeholder", show.id))

        # Expand favorites/views/folders but leave shows COLLAPSED, so the tree
        # is not a wall of episodes -- expand a show to reveal its episodes.
        # wxMSW asserts on expanding a hidden root (TR_HIDE_ROOT), which took
        # the whole app down before its window appeared -- and the call was a
        # no-op regardless: a hidden root's children are the visible top level.
        if not (tree.GetWindowStyle() & wx.TR_HIDE_ROOT):
            tree.Expand(root)
        for fitem in folder_items.values():
            if fitem is not root:
                tree.Expand(fitem)
        first, _cookie = tree.GetFirstChild(root)
        if select_item is not None:
            tree.SelectItem(select_item)
        elif first.IsOk():
            tree.SelectItem(first)

    #: How many episodes a single expanded show lists at once. A show with a
    #: thousand-episode back catalog is a real thing, and a thousand tree
    #: items is a wall you cannot arrow through; the newest are what anyone
    #: is looking for, and the Podcast Manager has the filters and sorting
    #: for the rest. Never a silent cap -- the last node says so.
    _EPISODES_PER_SHOW_NODE = 200

    def _on_library_expanding(self, event: wx.TreeEvent) -> None:
        """Fill a show's episodes the first time it is expanded.

        The tree is built with one placeholder child per show so the expander
        exists without the episodes; this replaces that placeholder with the
        real thing, once, for the one show being opened.
        """
        item = event.GetItem()
        if not item.IsOk():
            return
        tree = self._shows_tree
        child, _cookie = tree.GetFirstChild(item)
        if not child.IsOk():
            return
        data = tree.GetItemData(child)
        if not (isinstance(data, tuple) and len(data) == 2 and data[0] == "placeholder"):
            return  # already filled
        from quill.core.podcasts.sorting import sort_episodes

        show = self._podcast_library.find_show(data[1])
        tree.DeleteChildren(item)
        if show is None:
            return
        ordered = sort_episodes(show.episodes, "newest_first")
        for episode in ordered[: self._EPISODES_PER_SHOW_NODE]:
            ep_item = tree.AppendItem(item, episode.title)
            tree.SetItemData(ep_item, ("episode", f"{show.id}\x00{episode.guid}"))
        hidden = len(ordered) - self._EPISODES_PER_SHOW_NODE
        if hidden > 0:
            more = tree.AppendItem(
                item, f"{hidden} older episode(s) -- open the Podcast Manager to see them"
            )
            tree.SetItemData(more, ("more", show.id))

    def _selected_tree_data(self) -> tuple[str, str] | None:
        tree = getattr(self, "_shows_tree", None)
        if tree is None:
            return None
        item = tree.GetSelection()
        if not item.IsOk():
            return None
        data = tree.GetItemData(item)
        return data if isinstance(data, tuple) and len(data) == 2 else None

    def _selected_show(self):
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "show":
            return None
        return self._podcast_library.find_show(selected[1])

    def _selected_episode(self):
        """(show, episode) for the selected episode row, or None."""
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "episode":
            return None
        show_id, _, guid = selected[1].partition("\x00")
        show = self._podcast_library.find_show(show_id)
        episode = show.find_episode(guid) if show is not None else None
        if show is None or episode is None:
            return None
        return show, episode

    def _on_library_activated(self, event: wx.TreeEvent) -> None:
        selected = self._selected_tree_data()
        if selected is None:
            event.Skip()
            return
        kind, key = selected
        if kind == "show":
            self._play_show_next_episode(key)
            return
        if kind == "episode":
            show_id, _, guid = key.partition("\x00")
            self._play_specific_episode(show_id, guid)
            return
        if kind == "more":
            self.open_podcast_manager()
            self._announce("Opened the Podcast Manager, where the full episode list lives.")
            return
        if kind == "action":
            # The empty-library filler rows. Add Podcast and Search open the
            # same dialog (its search box leads and its URL field sits below);
            # Import goes straight to the OPML chooser.
            if key == "import":
                self._podcast_open_import_opml()
            else:
                self._podcast_open_add_dialog()
            return
        if kind == "view":
            from quill.core.podcasts.virtual_views import view_label

            self.open_podcast_manager()
            label = view_label(self._podcast_library, key)
            self._announce(f"Opened Podcast Manager. Select {label} there.")
            return
        event.Skip()  # a folder: let the tree toggle it

    def _on_library_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_library_activated(event)
            return
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_library_remove()
            return
        if code == wx.WXK_F2:
            self._on_library_rename_key()
            return
        if code in (wx.WXK_UP, wx.WXK_DOWN) and event.AltDown():
            self._on_library_move_show(-1 if code == wx.WXK_UP else 1)
            return
        event.Skip()

    def _play_show_next_episode(self, show_id: str) -> None:
        from quill.core.podcasts.sorting import sort_episodes

        show = self._podcast_library.find_show(show_id)
        if show is None:
            return
        ordered = sort_episodes(show.episodes, "unplayed_first")
        if not ordered:
            self._announce(f"{show.title} has no episodes yet.")
            return
        episode = ordered[0]
        note = " (no unplayed episodes; playing the most recent)" if episode.played else ""
        self._play_episode_object(show, episode, note=note)

    def _play_specific_episode(self, show_id: str, guid: str) -> None:
        """Play one chosen episode -- Enter on an episode expanded under its show
        in the library tree (#1192)."""
        show = self._podcast_library.find_show(show_id)
        if show is None:
            return
        episode = next((e for e in show.episodes if e.guid == guid), None)
        if episode is not None:
            self._play_episode_object(show, episode)

    def _play_episode_object(self, show: object, episode: object, *, note: str = "") -> None:
        from quill.ui.podcasts.show_actions import start_episode_playback

        if not start_episode_playback(
            self._podcast_controller, self._podcast_library, show, episode
        ):
            return
        self._announce(f"Playing {episode.title} from {show.title}{note}")

    # -- transport & favorite controls --------------------------------------

    def _on_transport_button(self) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        state = self._podcast_controller.state.state
        if state in (PodcastPlayerState.STOPPED, PodcastPlayerState.ERROR):
            selected = self._selected_tree_data()
            if selected is not None and selected[0] == "show":
                self._play_show_next_episode(selected[1])
            else:
                self._announce("Select a show in your library first.")
            return
        self.podcast_toggle_play_pause()

    def _refresh_transport_controls(self) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        state = self._podcast_controller.state.state
        label = {
            PodcastPlayerState.PLAYING: "&Pause",
            PodcastPlayerState.LOADING: "&Pause",
            PodcastPlayerState.PAUSED: "&Resume",
        }.get(state, "&Play")
        button = getattr(self, "_play_pause_btn", None)
        if button is not None and button.GetLabel() != label:
            button.SetLabel(label)
            set_accessible_name(button, label.replace("&", ""))
        stop_btn = getattr(self, "_stop_btn", None)
        if stop_btn is not None:
            stop_btn.Enable(state != PodcastPlayerState.STOPPED)
        self._refresh_favorite_toggle()

    def _refresh_favorite_toggle(self) -> None:
        button = getattr(self, "_favorite_toggle_btn", None)
        if button is None:
            return
        show_id = self._podcast_controller.state.show_id
        show = self._podcast_library.find_show(show_id) if show_id else None
        if show is None:
            button.Enable(False)
            if button.GetLabel() != "Add to Fa&vorites":
                button.SetLabel("Add to Fa&vorites")
                set_accessible_name(button, "Add the playing show to favorites")
            return
        button.Enable(True)
        label = "Remove from Fa&vorites" if show.is_favorite else "Add to Fa&vorites"
        if button.GetLabel() != label:
            button.SetLabel(label)
            set_accessible_name(
                button,
                "Remove the playing show from favorites"
                if show.is_favorite
                else "Add the playing show to favorites",
            )

    def _on_favorite_toggle(self) -> None:
        from quill.ui.podcasts.show_actions import toggle_favorite

        show_id = self._podcast_controller.state.show_id
        show = self._podcast_library.find_show(show_id) if show_id else None
        if show is None:
            self._announce("Nothing is playing to favorite.")
            return
        toggle_favorite(self._podcast_library, show, announce=self._announce)
        self._save_podcast_library()
        self._refresh_favorite_toggle()

    def _toggle_resume_on_launch(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history

        history = self._podcast_history
        history.resume_on_launch = not history.resume_on_launch
        podcast_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        self._announce(
            "QUILL Cast will pick up where you left off at launch."
            if history.resume_on_launch
            else "Resume on launch turned off."
        )

    def _open_preferences(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history
        from quill.ui.app_preferences_dialog import (
            PreferenceAction,
            PreferenceCheckbox,
            PreferencesDialog,
        )
        from quill.ui.data_folder_dialog import open_data_folder_dialog

        history = self._podcast_history
        dialog = PreferencesDialog(
            self.frame,
            app_title=_TITLE,
            actions=[
                PreferenceAction(
                    "&Data Folder...",
                    "Where every Quill app stores settings, favorites, and "
                    "subscriptions. Choose a folder a service like Dropbox or "
                    "OneDrive keeps in sync to carry them between computers.",
                    lambda: open_data_folder_dialog(self, app_title=_TITLE),
                ),
            ],
            checkboxes=[
                PreferenceCheckbox(
                    "Resume Last Episode on &Launch",
                    "Resume Last Episode on Launch",
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
                    "Alt+F&4 minimizes to the system tray",
                    "When on, Alt+F4 sends QUILL Cast to the system tray, still "
                    "playing, instead of closing the window",
                    history.alt_f4_to_tray,
                ),
                PreferenceCheckbox(
                    "&Winamp playback keys (Z X C V B, arrows to seek)",
                    "The classic Winamp letter keys in the library and episode "
                    "lists. Turn off to use those letters for list typeahead "
                    "instead. The same keys as Quill Radio's recordings player.",
                    history.winamp_playback_keys,
                ),
            ],
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        checkbox_values, _choice_indices, _text_values = result
        (
            history.resume_on_launch,
            history.check_updates_on_startup,
            history.announce_dialog_transitions,
            history.alt_f4_to_tray,
            history.winamp_playback_keys,
        ) = checkbox_values
        podcast_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        self._announce("Preferences saved")

    def _maybe_resume_last_episode(self) -> None:
        """Podcasts as an appliance: launch, and your last episode is ready."""
        if not self._podcast_history.resume_on_launch:
            return
        last = self._podcast_history.last_played
        if last is None:
            return
        from quill.ui.podcasts.show_actions import start_episode_playback

        show = self._podcast_library.find_show(last.show_id)
        episode = show.find_episode(last.episode_guid) if show is not None else None
        if show is None or episode is None:
            return
        start_episode_playback(self._podcast_controller, self._podcast_library, show, episode)

    def _maybe_check_updates_on_startup(self) -> None:
        """Silent, throttled update check -- quiet unless a genuine update
        exists. Preferences (Ctrl+,) turns this off."""
        from datetime import UTC, datetime

        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history

        history = self._podcast_history
        if not history.check_updates_on_startup:
            return
        if not self._app_update_check_due(history.last_update_check):
            return
        history.last_update_check = datetime.now(UTC).isoformat()
        podcast_history.save_history(app_data_dir(), history)
        self.check_for_app_updates(
            repo_slug=_REPO, current_version=_VERSION, app_key="cast", silent_no_update=True
        )

    # -- menu bar -------------------------------------------------------------

    def _open_podcasts_doc(self, stem: str) -> None:
        titles = {
            "userguide": "QUILL Cast User Guide",
            "release-notes-1.1": "QUILL Cast Release Notes",
            "prd": "QUILL Cast Product Requirements",
        }
        self.open_app_document(
            self._doc_candidates("quill-cast", stem),
            title=titles.get(stem, stem),
            cache_name="app-docs",
        )

    def _new_library_folder(self) -> None:
        """Create a top-level library folder without opening the Manager --
        the same store the Manager's own New Folder button writes to."""
        dialog = wx.TextEntryDialog(self.frame, "Folder name:", "New Folder")
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name:
            return
        self._podcast_library.add_folder(name, parent_folder_id=None)
        self._save_podcast_library()
        self._announce(f"Created folder {name}. Organize shows into it from the Podcast Manager.")

    def _send_to_tray(self) -> None:
        self.frame.Hide()
        self._announce("QUILL Cast is still running in the system tray.")

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "Podcasts from Quill, as a standalone app.\n\n"
            "Runs the same podcast feature code as QUILL itself and shares "
            "its settings, subscriptions, and downloads.\n"
            f"https://github.com/{_REPO}\n\n"
            "Credits and thanks:\n"
            "- Podcast data from the Podcast Index, an open, independent "
            "podcast directory (https://podcastindex-org.github.io/docs-api/).",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    # -- show notes: no in-editor buffer standalone, so copy to clipboard ----

    def _podcast_send_show_notes_to_editor(self, plain_text: str) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(plain_text))
            finally:
                wx.TheClipboard.Close()
        self._announce("Show notes copied to clipboard")

    # -- status ---------------------------------------------------------------

    def _refresh_statusbar(self) -> None:
        text = self._podcast_status_text() or "Podcasts: stopped"
        self._set_status(text)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing = getattr(self, "_now_playing_text", None)
        if now_playing is not None:
            now_playing.SetLabel(text)
        if getattr(self, "_play_pause_btn", None) is not None:
            self._refresh_transport_controls()

    def _save_podcast_library(self) -> None:
        # Every library mutation -- folder/favorite actions, the Manager --
        # funnels through this save; refreshing here keeps the main-page
        # tree true without rebuilding it on every unrelated status change.
        #
        # The rebuild is not free. Every node's label carries a count, so one
        # reload walks every episode of every show (measured at 0.14 s over a
        # 1,300-show library with a refreshed catalog) and then builds 1,300
        # tree items. A position checkpoint fires this on every pause, stop,
        # and episode change -- which is exactly the shape of the bug that
        # made Earshot's inbox badge saturate the main thread and get the app
        # killed. So on a large library the reload rides the same coalescing
        # timer as the write, and on a normal one it stays immediate.
        super()._save_podcast_library()
        if getattr(self, "_shows_tree", None) is None:
            return
        if self._podcast_library_is_large():
            self._tree_reload_pending = True
            return
        self._reload_library_tree()

    def _flush_podcast_library(self) -> None:
        """Write, and take the deferred tree reload with it."""
        super()._flush_podcast_library()
        if getattr(self, "_tree_reload_pending", False):
            self._tree_reload_pending = False
            if getattr(self, "_shows_tree", None) is not None:
                self._reload_library_tree()

    # -- lifecycle --------------------------------------------------------------

    def _on_cast_app_close(self, event: wx.CloseEvent) -> None:
        # Cast has no "ask"/minimize confirm -- closing always exits -- but it
        # routes through the shared close flow (AppShellFrame.handle_app_close)
        # so all three companion apps share one path. protected=False means the
        # confirm is never reached; close_action="exit" closes straight away.
        self.handle_app_close(
            event,
            close_action="exit",
            protected=False,
            confirm=lambda: "exit",
            shutdown=self._cast_shutdown,
        )

    def _cast_shutdown(self) -> None:
        try:
            self._app_host.shutdown()
        except Exception:  # noqa: BLE001 - Quillin teardown must never block exit
            pass
        try:
            # Force the write rather than going through the coalescing path:
            # this is the last chance, and a pending timer will never fire.
            self._podcast_flush_stats()
            self._flush_podcast_library()
        except Exception:  # noqa: BLE001 - a failed save must never block exit
            pass
        for action in (
            getattr(getattr(self, "_scan_hold", None), "shutdown", None),
            getattr(self._podcast_controller, "shutdown", None),
            getattr(self, "_shutdown_podcast_transfers", None),
        ):
            if action is None:
                continue
            try:
                action()
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


def main() -> int:
    from quill.core.data_location import apply_pending_at_launch

    # A queued Data Folder move/import applies before a single data file is
    # read (mirrors quill.__main__.main -- the family shares one profile, so
    # whichever app launches next must be the one to apply it).
    apply_pending_at_launch()
    from quill.stability.safe_mode import should_enable_safe_mode

    safe_mode = should_enable_safe_mode(sys.argv[1:], os.environ)
    from quill.core import components
    from quill.core.podcasts.opml_cli import opml_path_from_argv

    components.register_running_app("cast", REQUIRED_COMPONENTS)
    app = wx.App()
    frame = PodcastsAppFrame(safe_mode=safe_mode)
    frame.frame.Show()
    # A subscription list opened from Explorer (the .opml association the
    # installer offers). Deferred with CallAfter rather than run here: the
    # window has to exist and be showing before a modal import appears over it,
    # or the import is the first thing on screen and the app looks like it
    # failed to start.
    opml_path = opml_path_from_argv(sys.argv[1:])
    if opml_path is not None:
        wx.CallAfter(frame.podcast_import_opml_file, opml_path)
    # A quill-cast:// link somebody opened (Share This Moment). Deferred for the
    # same reason, and refused unless it names a podcast already in the library
    # -- see ui/podcasts/share_moment.open_share_link.
    for argument in sys.argv[1:]:
        if argument.lower().startswith("quill-cast://"):
            from quill.ui.podcasts.share_moment import open_share_link

            wx.CallAfter(open_share_link, frame, argument)
            break
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
