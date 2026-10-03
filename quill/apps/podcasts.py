"""QUILL Cast -- Podcasts as a standalone app.

Reuses ``PodcastsMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.apps.podcasts_close import (
    CastCloseMixin,
)
from quill.apps.podcasts_go_to import CastGoToMixin
from quill.apps.podcasts_help_surfaces import CastHelpSurfacesMixin
from quill.apps.podcasts_library_actions import CastLibraryActionsMixin
from quill.apps.podcasts_menu import APP_REPO, APP_TITLE, APP_VERSION, CastMenuBarMixin
from quill.apps.podcasts_now_playing import CastNowPlayingMixin
from quill.apps.podcasts_preferences import CastPreferencesMixin
from quill.apps.podcasts_routes import CastPlaceRoutesMixin
from quill.apps.podcasts_view_menu import CastViewMenuMixin
from quill.ui.app_quillins import QuillinsAppMixin
from quill.ui.app_shell import AppShellFrame
from quill.ui.app_support import ListeningAppSupportMixin
from quill.ui.keymap_editor import KeymapEditorMixin
from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin
from quill.ui.podcasts.cast_ai_host import CastAiMixin
from quill.ui.podcasts.episode_list import CastEpisodeListMixin
from quill.ui.podcasts.main_panel import CastMainPanelMixin
from quill.ui.podcasts.manager_actions import ManagerActionsMixin
from quill.ui.podcasts.manager_downloads import ManagerDownloadsMixin
from quill.ui.podcasts.manager_expired import ManagerExpiredMixin
from quill.ui.podcasts.manager_row_view import ManagerRowViewMixin
from quill.ui.podcasts.manager_verbs import ManagerVerbsMixin
from quill.ui.podcasts.places import CastPlacesMixin
from quill.ui.podcasts.places_host import CastPlacesHostMixin
from quill.ui.podcasts.quick_play_commands import CastQuickPlayMixin
from quill.ui.podcasts.winamp_mixin import CastWinampKeysMixin
from quill.ui.podcasts.window_title import CastWindowTitleMixin

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
    CastPlaceRoutesMixin,  # the one window's doors, before the shared mixins
    PodcastsMixin,
    CastLibraryActionsMixin,
    CastCloseMixin,
    CastGoToMixin,
    CastHelpSurfacesMixin,
    CastMenuBarMixin,
    CastMainPanelMixin,
    CastNowPlayingMixin,
    CastAiMixin,  # the shared hosted AI, through an adapter (ear.md A1)
    CastPlacesMixin,
    CastPlacesHostMixin,
    CastEpisodeListMixin,
    CastPreferencesMixin,
    CastQuickPlayMixin,
    CastViewMenuMixin,
    CastWindowTitleMixin,
    CastWinampKeysMixin,
    # The Podcast Manager's mixins, re-homed on the frame (qc.md Phase 2):
    # one implementation of every episode and podcast verb for QUILL's
    # Manager and Cast's one window. Last, so the frame's own names win.
    ManagerVerbsMixin,
    ManagerActionsMixin,
    ManagerDownloadsMixin,
    ManagerRowViewMixin,
    ManagerExpiredMixin,
    MediaSleepTimerMixin,
    UnlockCodesMixin,
    GlobalHotkeysMixin,
    KeymapEditorMixin,
    QuillinsAppMixin,
    ListeningAppSupportMixin,
):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360), app_id="cast")
        self._apply_app_keymap("cast")
        self.commands.set_availability_probe(self._cast_command_unavailable_reason)
        # Undo, Recent Problems, Quiet Hours and setup transfer: the shared
        # slots, claimed before any window can offer them.
        self._init_app_support()
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
        # F1 context help with Cast's authored purpose catalogue. The app
        # shell already activated the shared engine (provider + dialog-contract
        # hook + main-frame F1); this re-activation swaps in Cast's
        from quill.ui.podcasts import context_help

        context_help.activate()
        self._init_media_sleep_timer()
        from quill.ui.window_menu import WindowManager

        self._windows = WindowManager(wx)
        self._build_menu_bar()
        self._build_main_panel()
        self._init_now_playing()  # window 2 (qc.md 5)
        self._register_podcasts_commands()
        self._register_podcast_session_commands()
        self._register_media_sleep_timer_commands()
        self._register_unlock_code_commands()
        from quill.ui.podcasts import problem_retries

        self._register_app_support_commands(problem_retries)
        # Bookmarks (4.5): the anchor Cast builds for an episode is the one
        # Quill Radio builds, which is what makes the list shared.
        from quill.ui.podcasts import bookmarks_wiring

        bookmarks_wiring.register(self)
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
        wx.CallAfter(self._say_launch_digest)  # qc.md 5b: one sentence, if anything arrived
        wx.CallAfter(self._check_at_launch)  # qc.md 5e: on launch, and missed checks
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
        # First run: three screens for somebody who has never used this before,
        # and nothing at all for anybody who already has podcasts -- however
        # they got there. The dialog has existed since 1.1 with no caller,
        # which is exactly the failure Quill Radio's equivalent carries a
        # docstring about; this is that caller. Scheduled last so it opens over
        # a window everything else has already finished with.
        from quill.ui.podcasts.first_run_dialog import maybe_run_first_run

        wx.CallAfter(maybe_run_first_run, self)
        # What this installation cannot do, said once. Every Cast feature that
        # needs FFmpeg fails by producing a plausible result -- an untrimmed
        # download, an analysis that finds no chapters -- so without this the
        # loss is invisible (list.md 5.3). Silent on a healthy install.
        wx.CallAfter(self._cast_launch_notices)  # media health, then F-06's notice

    # -- main panel -------------------------------------------------------------
    #
    # A bare frame with only a menu bar leaves keyboard focus with nowhere to
    # land: Tab does nothing and a screen reader reads an empty client area.
    # The main panel gives the app a real, named, tabbable surface -- the
    # same pinned views (Favorites, New Episodes, Continue Listening, Inbox)
    # and library folders the Podcast Manager shows, right on the main page,
    # matching Quill Radio's favorites tree (#1043).

    def _winamp_keys_enabled(self) -> bool:
        return bool(getattr(self._podcast_history, "winamp_playback_keys", True))

    def _winamp_controller(self) -> object | None:
        return self._podcast_controller

    def _winamp_rows(self) -> list[tuple[object, object]]:
        """The list on screen: the content list's rows, or the selected show's."""
        if self._content_is_list():
            return self._list_winamp_rows()
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
        if self._content_is_list():
            return self._episodes.GetFirstSelected()
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "episode":
            return -1
        _show_id, _, guid = selected[1].partition("\x00")
        for index, (_show, episode) in enumerate(self._winamp_rows()):
            if episode.guid == guid:
                return index
        return -1

    def _winamp_select_index(self, index: int) -> None:
        if self._content_is_list():
            self._select_list_row(index)
            return
        rows = self._winamp_rows()
        if not (0 <= index < len(rows)):
            return
        show, episode = rows[index]
        self._reload_library_tree(keep_key=("episode", f"{show.id}\x00{episode.guid}"))

    def _winamp_play_pair(self, show: object, episode: object) -> None:
        self._play_episode_object(show, episode)

    # -- library tree (pinned views + folders + shows) ---------------------

    def _reload_library_tree(self, *, keep_key: tuple[str, str] | None = None) -> None:
        from quill.core.podcasts.sorting import sort_shows, unheard_count

        if self._library_find_active():  # Find shows matches: refresh those
            self._refresh_library_find()
            return
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

        # The pinned views are places now (qc.md 4.3); this tree is the
        # Podcasts place: folders and podcasts only.
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
                ("search", "Find a Podcast..."),
            ):
                tag(tree.AppendItem(root, label), ("action", key))

        # Hide Caught-Up Podcasts (R1) filters at the one place the tree is
        # built, so two answers about which podcasts exist cannot coexist.
        for show in sort_shows(
            self._visible_library_shows(), self._podcast_library.settings.show_sort_mode
        ):
            count = unheard_count(show)
            label = f"{show.title} ({count} unheard)" if count else show.title
            item = tree.AppendItem(folder_item(show.folder_id), label)
            tag(item, ("show", show.id))
            if show.episodes:
                placeholder = tree.AppendItem(item, "Loading episodes...")
                tag(placeholder, ("placeholder", show.id))

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
        from quill.ui.podcasts import library_tree

        item = event.GetItem()
        if not item.IsOk():
            return
        tree = self._shows_tree
        child, _cookie = tree.GetFirstChild(item)
        if not child.IsOk():
            return
        data = tree.GetItemData(child)
        if not (isinstance(data, tuple) and len(data) == 2):
            return  # already filled
        if data[0] == library_tree.PLACEHOLDER_VIEW:
            library_tree.fill_view_children(self, item, data[1])
            return
        if data[0] != "placeholder":
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

    def _content_is_list(self) -> bool:
        pane = getattr(self, "_content", None)
        return pane is not None and pane.showing == pane.LIST

    def _selected_tree_data(self) -> tuple[str, str] | None:
        if self._content_is_list():
            return self._list_selected_data()
        tree = getattr(self, "_shows_tree", None)
        if tree is None:
            return None
        try:
            item = tree.GetSelection()
            if not item.IsOk():
                return None
            data = tree.GetItemData(item)
        except RuntimeError:  # the tree is mid-teardown
            return None
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
            show = self._podcast_library.find_show(key)
            if show is not None:
                self._open_show_in_place(show)
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
            self.show_place(key)
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
        if code == wx.WXK_LEFT and not self._library_find_active():
            tree = self._shows_tree
            item = tree.GetSelection()
            if item.IsOk() and tree.GetItemParent(item) == tree.GetRootItem():
                self._places.focus()
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
        note = " (no unheard episodes; playing the most recent)" if episode.played else ""
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
            # Play acts on whatever the cursor is on: a podcast, an episode, or a
            # view. It used to understand podcasts only and answer "select a show"
            # to an episode -- a refusal dressed as help, on the row somebody had
            # just arrowed to on purpose (Jeff, 2026-09-30).
            self._play_selection_or_say_why()
            return
        self.podcast_toggle_play_pause()

    def _refresh_transport_controls(self) -> None:
        from quill.core.podcasts import transport_intent
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        state = self._podcast_controller.state.state
        intent = {
            PodcastPlayerState.PLAYING: transport_intent.PLAYING,
            PodcastPlayerState.LOADING: transport_intent.PLAYING,
            PodcastPlayerState.PAUSED: transport_intent.PAUSED,
        }.get(state, transport_intent.STOPPED)
        # The label carries the object (qc.md 4.5), so it depends on the
        # selection as well as the player state and is re-read on both.
        label = self._transport_button_face(intent).label
        button = getattr(self, "_play_pause_btn", None)
        if button is not None and button.GetLabel() != label:
            button.SetLabel(label)
        stop_btn = getattr(self, "_stop_btn", None)
        if stop_btn is not None:
            stop_btn.Enable(state != PodcastPlayerState.STOPPED)
        self._refresh_favorite_toggle()
        # The status bar carries the same facts as this row, so it refreshes here
        # rather than on a timer: a readout on a timer is wrong for up to one tick,
        # and a listener sitting on the cell hears the stale value.
        self._refresh_cast_status_bar()

    def _refresh_favorite_toggle(self) -> None:
        button = getattr(self, "_favorite_toggle_btn", None)
        if button is None:
            return
        show_id = self._podcast_controller.state.show_id
        show = self._podcast_library.find_show(show_id) if show_id else None
        if show is None:
            button.Enable(False)
            if button.GetLabel() != "Add to &Favorites":
                button.SetLabel("Add to &Favorites")
            return
        button.Enable(True)
        label = "Remove from &Favorites" if show.is_favorite else "Add to &Favorites"
        if button.GetLabel() != label:
            button.SetLabel(label)

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
        start_episode_playback(
            self._podcast_controller,
            self._podcast_library,
            show,
            episode,
            announce=self._announce,
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
        self.check_for_app_updates(
            repo_slug=_REPO, current_version=_VERSION, app_key="cast", silent_no_update=True
        )

    # -- menu bar -------------------------------------------------------------

    def open_cast_tutorials(self, slug: str = "") -> None:
        """Help > Tutorials...: the guided lessons, in their own peer window."""
        from quill.ui.podcasts.tutorials import open_tutorials

        open_tutorials(self, slug=slug)

    def _open_podcasts_doc(self, stem: str) -> None:
        titles = {
            "userguide": "QUILL Cast User Guide",
            "release-notes-2.0": "QUILL Cast Release Notes",
            "prd": "QUILL Cast Product Requirements",
            "tutorials": "QUILL Cast Tutorials",
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
            "its settings, podcasts, and downloads.\n"
            f"https://github.com/{_REPO}\n\n"
            "Credits and thanks:\n"
            "- Podcast data from the Podcast Index, an open, independent "
            "podcast directory (https://podcastindex-org.github.io/docs-api/)."
            "\n\nSupport: support@community-access.org",
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
        self._refresh_window_title()  # R15: the Inbox count, free for the reader
        text = self._podcast_status_text() or "Podcasts: stopped"
        self._set_status(text)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing = getattr(self, "_now_playing_text", None)
        if now_playing is not None:
            setter = getattr(now_playing, "ChangeValue", None) or now_playing.SetLabel
            if (getattr(now_playing, "GetValue", None) or now_playing.GetLabel)() != text:
                setter(text)
        if getattr(self, "_play_pause_btn", None) is not None:
            self._refresh_transport_controls()

    def _save_podcast_library(self) -> None:
        super()._save_podcast_library()
        if getattr(self, "_shows_tree", None) is None:
            return
        if self._podcast_library_is_large():
            self._tree_reload_pending = True
            return
        self._reload_library_tree()
        self._refresh_place(keep=True)

    def _flush_podcast_library(self) -> None:
        """Write, and take the deferred tree reload with it."""
        super()._flush_podcast_library()
        if getattr(self, "_tree_reload_pending", False):
            self._tree_reload_pending = False
            if getattr(self, "_shows_tree", None) is not None:
                self._reload_library_tree()


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
