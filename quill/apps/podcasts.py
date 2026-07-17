"""QUILL Cast -- Podcasts as a standalone app.

Reuses ``PodcastsMixin`` (the exact same class ``MainFrame`` uses) unchanged:
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
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin

_TITLE = "QUILL Cast"
_VERSION = "1.0.5"
_REPO = "Community-Access/quill-cast"


class PodcastsAppFrame(
    AppShellFrame, PodcastsMixin, MediaSleepTimerMixin, AdpMixin, UnlockCodesMixin
):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        self._init_podcasts()
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(
            lambda: self._podcast_history.announce_dialog_transitions
        )
        self._init_media_sleep_timer()
        self._build_menu_bar()
        self._build_main_panel()
        self._register_podcasts_commands()
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
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_cast_app_close)
        self._maybe_resume_last_episode()
        # Deferred (CallAfter), not inline: this touches the network, and a
        # launch is not the place to do that before the window is even up.
        wx.CallAfter(self._maybe_check_updates_on_startup)

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
        self._shows_tree.SetFocus()

    # -- library tree (pinned views + folders + shows) ---------------------

    def _reload_library_tree(self, *, keep_key: tuple[str, str] | None = None) -> None:
        from quill.core.podcasts.sorting import sort_shows, unheard_count
        from quill.core.podcasts.virtual_views import (
            VIRTUAL_VIEWS,
            favorite_shows,
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
        fav_item = tree.AppendItem(root, f"Favorites ({fav_count})" if fav_count else "Favorites")
        tag(fav_item, ("view", "favorites"))
        for view_id, label in VIRTUAL_VIEWS:
            count = len(virtual_view_pairs(self._podcast_library, view_id))
            item = tree.AppendItem(root, f"{label} ({count})" if count else label)
            tag(item, ("view", view_id))

        folder_items: dict[str | None, object] = {None: root}

        def folder_item(folder_id: str | None) -> object:
            if folder_id in folder_items:
                return folder_items[folder_id]
            folder = self._podcast_library.find_folder(folder_id)
            if folder is None:
                return root
            item = tree.AppendItem(folder_item(folder.parent_folder_id), folder.name)
            tag(item, ("folder", folder_id or ""))
            folder_items[folder_id] = item
            return item

        for folder in self._podcast_library.folders:
            folder_item(folder.id)
        for show in sort_shows(self._podcast_library.shows, "title_az"):
            count = unheard_count(show)
            label = f"{show.title} ({count})" if count else show.title
            item = tree.AppendItem(folder_item(show.folder_id), label)
            tag(item, ("show", show.id))

        tree.ExpandAll()
        first, _cookie = tree.GetFirstChild(root)
        if select_item is not None:
            tree.SelectItem(select_item)
        elif first.IsOk():
            tree.SelectItem(first)

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

    def _on_library_activated(self, event: wx.TreeEvent) -> None:
        selected = self._selected_tree_data()
        if selected is None:
            event.Skip()
            return
        kind, key = selected
        if kind == "show":
            self._play_show_next_episode(key)
            return
        if kind == "view":
            self.open_podcast_manager()
            label = key.replace("_", " ").title() if key != "favorites" else "Favorites"
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
        event.Skip()

    def _on_library_context_menu(self, _event: object) -> None:
        selected = self._selected_tree_data()
        if selected is None:
            return
        kind, key = selected
        entries: list[tuple[str, object]] = []
        if kind == "show":
            show = self._podcast_library.find_show(key)
            if show is None:
                return
            playing = self._podcast_controller.state.show_id == show.id and (
                self._podcast_controller.state.state.name not in ("STOPPED", "ERROR")
            )
            fav_label = "Remove from Fa&vorites" if show.is_favorite else "Add to Fa&vorites"
            entries = [
                ("&Stop" if playing else "&Play Next Episode", self._on_library_play_stop_context),
                (fav_label, self._on_library_favorite_toggle_context),
                ("&Move to Folder...", self._on_library_move_to_folder),
                ("Download &All Episodes", self._on_library_download_all_episodes),
                ("&Remove All Episodes...", self._on_library_remove_all_episodes),
                ("&Unsubscribe...\tDelete", self._on_library_remove),
                ("New F&older...", self._on_library_new_folder),
                ("Open &Manager...", lambda: self.open_podcast_manager()),
            ]
        elif kind == "folder":
            entries = [
                ("Rena&me Folder...", self._on_library_rename_folder),
                ("&Delete Folder...\tDelete", self._on_library_remove),
                ("New F&older...", self._on_library_new_folder),
                ("Open &Manager...", lambda: self.open_podcast_manager()),
            ]
        else:
            entries = [("Open &Manager...", lambda: self.open_podcast_manager())]
        menu = wx.Menu()
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._keep_menu_ids(*id_refs)
        self._shows_tree.PopupMenu(menu)
        menu.Destroy()

    def _on_library_play_stop_context(self) -> None:
        show = self._selected_show()
        if show is None:
            return
        state = self._podcast_controller.state
        if state.show_id == show.id and state.state.name not in ("STOPPED", "ERROR"):
            self.podcast_stop()
        else:
            self._play_show_next_episode(show.id)

    def _on_library_favorite_toggle_context(self) -> None:
        from quill.ui.podcasts.show_actions import toggle_favorite

        show = self._selected_show()
        if show is None:
            return
        toggle_favorite(self._podcast_library, show, announce=self._announce)
        self._save_podcast_library()
        self._refresh_transport_controls()

    def _on_library_download_all_episodes(self) -> None:
        from quill.ui.podcasts.show_actions import download_all_episodes

        show = self._selected_show()
        if show is None:
            return
        download_all_episodes(
            self._podcast_download_queue,
            self._podcast_download_root(),
            show,
            announce=self._announce,
        )

    def _on_library_remove_all_episodes(self) -> None:
        from quill.ui.podcasts.show_actions import remove_all_episodes_prompt

        show = self._selected_show()
        if show is None:
            return
        if remove_all_episodes_prompt(
            self.frame, self._podcast_download_queue, show, announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_move_to_folder(self) -> None:
        from quill.ui.podcasts.show_actions import move_show_to_folder

        show = self._selected_show()
        if show is None:
            return
        if move_show_to_folder(self.frame, self._podcast_library, show, announce=self._announce):
            self._save_podcast_library()

    def _on_library_rename_folder(self) -> None:
        from quill.ui.podcasts.show_actions import rename_folder_prompt

        selected = self._selected_tree_data()
        if selected is None or selected[0] != "folder":
            return
        if rename_folder_prompt(
            self.frame, self._podcast_library, selected[1], announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_new_folder(self) -> None:
        from quill.ui.podcasts.show_actions import create_folder_prompt

        selected = self._selected_tree_data()
        initial_parent = selected[1] if selected is not None and selected[0] == "folder" else None
        if create_folder_prompt(
            self.frame,
            self._podcast_library,
            announce=self._announce,
            initial_parent_id=initial_parent,
        ):
            self._save_podcast_library()

    def _on_library_remove(self) -> None:
        from quill.ui.podcasts.show_actions import delete_folder_prompt, unsubscribe_show_prompt

        selected = self._selected_tree_data()
        if selected is None:
            return
        kind, key = selected
        if kind == "show":
            show = self._podcast_library.find_show(key)
            if show is not None and unsubscribe_show_prompt(
                self.frame, self._podcast_library, show, announce=self._announce
            ):
                self._save_podcast_library()
        elif kind == "folder":
            if delete_folder_prompt(
                self.frame, self._podcast_library, key, announce=self._announce
            ):
                self._save_podcast_library()

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
        played_note = ""
        if episode.played:
            played_note = " (no unplayed episodes; playing the most recent)"
        settings = self._podcast_library.effective_settings(show)
        self._podcast_controller.play_episode(
            show_id=show.id,
            episode_guid=episode.guid,
            title=episode.title,
            source=episode.downloaded_path or episode.audio_url,
            resume_ms=episode.position_ms,
            rate=settings.speed,
            bass_db=settings.eq_bass_db,
            mid_db=settings.eq_mid_db,
            treble_db=settings.eq_treble_db,
            compressor_enabled=settings.compressor_enabled,
            smart_speed_enabled=settings.smart_speed_enabled,
            auto_skip_intro_ms=settings.auto_skip_intro_seconds * 1000,
            auto_skip_outro_ms=settings.auto_skip_outro_seconds * 1000,
        )
        self._announce(f"Playing {episode.title} from {show.title}{played_note}")

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
        from quill.ui.app_preferences_dialog import PreferenceCheckbox, PreferencesDialog

        history = self._podcast_history
        dialog = PreferencesDialog(
            self.frame,
            app_title=_TITLE,
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
        show = self._podcast_library.find_show(last.show_id)
        episode = show.find_episode(last.episode_guid) if show is not None else None
        if show is None or episode is None:
            return
        settings = self._podcast_library.effective_settings(show)
        self._podcast_controller.play_episode(
            show_id=show.id,
            episode_guid=episode.guid,
            title=episode.title,
            source=episode.downloaded_path or episode.audio_url,
            resume_ms=episode.position_ms,
            rate=settings.speed,
            bass_db=settings.eq_bass_db,
            mid_db=settings.eq_mid_db,
            treble_db=settings.eq_treble_db,
            compressor_enabled=settings.compressor_enabled,
            smart_speed_enabled=settings.smart_speed_enabled,
            auto_skip_intro_ms=settings.auto_skip_intro_seconds * 1000,
            auto_skip_outro_ms=settings.auto_skip_outro_seconds * 1000,
        )

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
        self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION, silent_no_update=True)

    # -- menu bar -------------------------------------------------------------

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
        local_id, watched_id, acb_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        subs_menu.Append(local_id, "Add &Local Podcast...")
        subs_menu.Append(watched_id, "Scan &Watched Folders")
        subs_menu.Append(acb_id, "Subscribe to ACB Media &Podcasts")
        subs_menu.AppendSeparator()
        subs_menu.Append(settings_id, "Podcast &Settings...")
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
        episode_menu.Append(stop_id, "&Stop")
        mute_id = wx.NewIdRef()
        episode_menu.Append(mute_id, "&Mute/Unmute")
        episode_menu.Append(next_id, "&Next Chapter")
        episode_menu.Append(prev_id, "P&revious Chapter")
        skip_fwd_id, skip_back_id = wx.NewIdRef(), wx.NewIdRef()
        episode_menu.Append(skip_fwd_id, "Skip &Forward")
        episode_menu.Append(skip_back_id, "Skip &Back")
        note_id = wx.NewIdRef()
        episode_menu.Append(note_id, "Add Episode &Note...")
        queue_id = wx.NewIdRef()
        episode_menu.Append(queue_id, "Play &Queue...")
        episode_menu.AppendSeparator()
        self._append_podcast_recent_submenu(episode_menu)
        episode_menu.AppendSeparator()
        sleep_id = wx.NewIdRef()
        episode_menu.Append(sleep_id, "Sleep &Timer...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=sleep_id)
        episode_menu.AppendSeparator()
        enhance_id = wx.NewIdRef()
        episode_menu.Append(enhance_id, "Sound &Enhancements...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_sound_enhancements(), id=enhance_id
        )
        skip_settings_id = wx.NewIdRef()
        episode_menu.Append(skip_settings_id, "S&kip Settings...")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_podcast_skip_settings(), id=skip_settings_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_toggle_play_pause(), id=play_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_stop(), id=stop_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_mute_toggle(), id=mute_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_next_chapter(), id=next_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_previous_chapter(), id=prev_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_skip_forward(), id=skip_fwd_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_skip_back(), id=skip_back_id)
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
        menu_bar.Append(downloads_menu, "&Downloads")

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
            wx.EVT_MENU, lambda _e: self._open_podcasts_doc("release-notes-1.0"), id=notes_id
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
            lambda _e: self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self.frame.SetMenuBar(menu_bar)
        # Pin every menu id for the frame's lifetime (see _keep_menu_ids).
        self._keep_menu_ids(
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
        )

    def _open_podcasts_doc(self, stem: str) -> None:
        titles = {
            "userguide": "QUILL Cast User Guide",
            "release-notes-1.0": "QUILL Cast Release Notes",
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
            f"https://github.com/{_REPO}",
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
        super()._save_podcast_library()
        if getattr(self, "_shows_tree", None) is not None:
            self._reload_library_tree()

    # -- lifecycle --------------------------------------------------------------

    def _on_cast_app_close(self, event: wx.CloseEvent) -> None:
        try:
            self._save_podcast_library()
        except Exception:  # noqa: BLE001 - a failed save must never block exit
            pass
        for action in (
            getattr(self._podcast_controller, "shutdown", None),
            getattr(self._podcast_download_queue, "shutdown", None),
        ):
            if action is None:
                continue
            try:
                action()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                pass
        self._task_manager.shutdown(wait=False)
        self._unregister_media_keys()
        self._remove_tray_icon()
        event.Skip()


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    app = wx.App()
    frame = PodcastsAppFrame(safe_mode=safe_mode)
    frame.frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
