"""Tools > Media > Podcasts... -- the Podcast Manager.

A folder `wx.TreeCtrl` on the left (folders genuinely nest, so this is the
one place in the Podcasts feature a real tree fits, unlike the flat
category lists Radio's dialogs use) and an episode list on the right. This
dialog does not own playback -- it drives the single shared
``PodcastPlayerController`` passed in (the same one the status bar and tray
drive), so closing it never stops the episode that's playing, and picking a
different episode always replaces whatever was playing rather than layering
two streams.

Controls are parented directly on the dialog, not an intermediate panel (the
NVDA-virtual-buffer rule documented in ``dialog_button_contract.py``).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts import feed_auth, position_sync
from quill.core.podcasts.chapter_sources import (
    episode_has_possible_chapters,
)
from quill.core.podcasts.download_queue import PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.sorting import (
    EPISODE_SORT_MODES,
    SHOW_SORT_MODES,
    sort_episodes,
    sort_shows,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids, show_message_box
from quill.ui.media.list_columns_view import fill_row
from quill.ui.podcasts.manager_actions import ManagerActionsMixin
from quill.ui.podcasts.manager_downloads import ManagerDownloadsMixin
from quill.ui.podcasts.manager_phase4 import ManagerPhase4Mixin
from quill.ui.podcasts.manager_reveal import ManagerRevealMixin
from quill.ui.podcasts.manager_row_view import ManagerRowViewMixin
from quill.ui.podcasts.player_controller import PodcastPlayerController
from quill.ui.podcasts.winamp_mixin import CastWinampKeysMixin

_FOLDER_ROOT_LABEL = "All Podcasts"
_SPEED_CHOICES = ("0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x")
_EPISODE_SORT_LABELS = (
    "Newest first",
    "Oldest first",
    "Title A-Z",
    "Longest first",
    "Shortest first",
    "Unplayed first",
)
_SHOW_SORT_LABELS = (
    "Title A-Z",
    "Title Z-A",
    "Most unheard first",
    "Recently updated first",
    "Your custom order",
)
_VIEW_MODE_LABELS = ("Flat list", "Grouped in list", "Folders per podcast")
_VIEW_MODE_MODES = ("flat", "grouped", "folders")


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "show"


def episode_destination(download_root: Path, show: PodcastShow, episode: PodcastEpisode) -> Path:
    """Where a downloaded episode's file lands: ``<root>/<show-slug>/<episode-slug><ext>``."""
    suffix = Path(episode.audio_url.split("?", 1)[0]).suffix or ".mp3"
    return download_root / _slug(show.title) / f"{_slug(episode.title)}{suffix}"


def _shows_in_folder_subtree(library: PodcastLibrary, folder_id: str) -> list[PodcastShow]:
    """Every show in *folder_id* or any folder nested under it, tree order.

    Powers the per-folder bulk actions (set the whole folder's shows to
    stream/download) where "the folder" always means the whole subtree a
    user sees under that node, never just its direct children.
    """
    shows = [show for show in library.shows if show.folder_id == folder_id]
    for folder in library.folders:
        if folder.parent_folder_id == folder_id:
            shows.extend(_shows_in_folder_subtree(library, folder.id))
    return shows


def _item_key(item: object) -> int:
    """Stable, hashable identity for a wx.TreeItemId.

    ``GetID()`` returns a fresh ``sip.voidptr`` wrapper on every call; two
    wrappers for the SAME tree item never compare equal, so keying the
    item->show / item->folder dicts by the wrapper silently missed every lookup
    -- ``_selected_show_id`` always returned None, so selecting a podcast showed
    no episodes (#1189). ``int()`` of the voidptr is the raw pointer value:
    stable, equal, hashable.
    """
    get_id = getattr(item, "GetID", None)
    if callable(get_id):
        try:
            return int(get_id())
        except (TypeError, ValueError):
            pass
    return id(item)


def _shows_episodes(library: PodcastLibrary, folder_id: str) -> list[PodcastEpisode]:
    """Every episode belonging to a show directly in *folder_id* (not
    subfolders -- the caller recurses those separately)."""
    episodes: list[PodcastEpisode] = []
    for show in library.shows:
        if show.folder_id == folder_id:
            episodes.extend(show.episodes)
    return episodes


class PodcastManagerDialog(
    ManagerRevealMixin,
    ManagerPhase4Mixin,
    ManagerActionsMixin,
    ManagerDownloadsMixin,
    ManagerRowViewMixin,
    CastWinampKeysMixin,
):
    """Browse/subscribe/download/play podcasts."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        download_queue: PodcastDownloadQueue,
        controller: PodcastPlayerController,
        download_root: Path,
        safe_mode: bool,
        task_manager: object = None,
        announce_cb: Callable[[str], None] | None = None,
        winamp_keys_enabled: Callable[[], bool] | None = None,
        quick_actions: object = None,
        on_library_changed: Callable[[], None] | None = None,
        on_open_add_podcast: Callable[[], None] | None = None,
        on_open_import_opml: Callable[[], None] | None = None,
        on_export_opml: Callable[[], None] | None = None,
        on_refresh_feed: Callable[[str], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
        on_send_show_notes: Callable[[str], None] | None = None,
        chapter_skip_state: Callable[[], object] | None = None,
        transport_host: object = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._download_queue = download_queue
        self._controller = controller
        self._download_root = download_root
        self._safe_mode = safe_mode
        self._task_manager = task_manager
        self._announce = announce_cb or (lambda _m: None)
        #: Preferences checkbox, default on -- see CastWinampKeysMixin.
        self._winamp_keys_enabled_cb = winamp_keys_enabled or (lambda: True)
        #: The live Quick Actions order, so context menus and the Ctrl+N keys
        #: reflect what the listener arranged. Falls back to the shipped
        #: default, which is exactly the pre-1.1.0 menu order.
        if quick_actions is None:
            from quill.core.podcasts.quick_actions import QuickActionOrders

            quick_actions = QuickActionOrders()
        self._quick_actions = quick_actions
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_open_add_podcast = on_open_add_podcast
        self._on_open_import_opml = on_open_import_opml
        self._on_export_opml = on_export_opml
        self._refresh_feed_cb = on_refresh_feed
        self._on_open_settings = on_open_settings
        self._on_send_show_notes = on_send_show_notes
        self._chapter_skip_state = chapter_skip_state or (lambda: None)
        #: The app frame, for the shared transport keyboard (transport_keys).
        self._transport_host = transport_host

        self._current_show: PodcastShow | None = None
        self._current_episodes: list[PodcastEpisode] = []
        self._tree_item_show: dict[int, str] = {}
        self._tree_item_folder: dict[int, str] = {}

        self.dialog = wx.Dialog(
            parent, title="Podcasts", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((820, 600))
        self.dialog.SetSize((960, 680))
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        self._build_phase4_row(root_sizer)

        body = wx.BoxSizer(wx.HORIZONTAL)

        tree_col = wx.BoxSizer(wx.VERTICAL)
        tree_col.Add(wx.StaticText(self.dialog, label="&Folders and Podcasts"), 0, wx.BOTTOM, 4)
        show_sort_row = wx.BoxSizer(wx.HORIZONTAL)
        show_sort_row.Add(
            wx.StaticText(self.dialog, label="Sort sho&ws:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._show_sort_choice = wx.Choice(self.dialog, choices=list(_SHOW_SORT_LABELS))
        self._show_sort_choice.SetName("How podcasts are ordered within each folder")
        # Open on the library's own mode (Subscriptions > Sort Podcasts /
        # Alt+Up custom moves), so the Manager and the main tree agree.
        library_mode = self._library.settings.show_sort_mode
        self._show_sort_choice.SetSelection(
            SHOW_SORT_MODES.index(library_mode) if library_mode in SHOW_SORT_MODES else 0
        )
        show_sort_row.Add(self._show_sort_choice, 1, wx.EXPAND)
        tree_col.Add(show_sort_row, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._tree = wx.TreeCtrl(
            self.dialog,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE | wx.BORDER_SIMPLE,
        )
        self._tree.SetName(
            "Podcast folders and subscriptions; select a folder to see its "
            "contents, a show to see its episodes"
        )
        tree_col.Add(self._tree, 1, wx.EXPAND)
        body.Add(tree_col, 1, wx.EXPAND | wx.RIGHT, 10)

        episode_col = wx.BoxSizer(wx.VERTICAL)
        episode_col.Add(wx.StaticText(self.dialog, label="&Episodes"), 0, wx.BOTTOM, 4)
        episode_sort_row = wx.BoxSizer(wx.HORIZONTAL)
        episode_sort_row.Add(
            wx.StaticText(self.dialog, label="Sort &episodes:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._episode_sort_choice = wx.Choice(self.dialog, choices=list(_EPISODE_SORT_LABELS))
        self._episode_sort_choice.SetName(
            "How episodes are ordered -- for the selected podcast, or the "
            "shared default when no single podcast is selected"
        )
        self._episode_sort_choice.SetSelection(0)
        episode_sort_row.Add(self._episode_sort_choice, 1, wx.EXPAND)
        episode_col.Add(episode_sort_row, 0, wx.EXPAND | wx.BOTTOM, 4)
        view_mode_row = wx.BoxSizer(wx.HORIZONTAL)
        view_mode_row.Add(
            wx.StaticText(self.dialog, label="&View cross-show lists as:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._view_mode_choice = wx.Choice(self.dialog, choices=list(_VIEW_MODE_LABELS))
        self._view_mode_choice.SetName(
            "How the Inbox, New Episodes, Continue Listening, and Favorites "
            "present episodes from more than one show at once"
        )
        self._view_mode_choice.SetSelection(
            _VIEW_MODE_MODES.index(self._library.settings.episode_list_view_mode)
            if self._library.settings.episode_list_view_mode in _VIEW_MODE_MODES
            else 1
        )
        view_mode_row.Add(self._view_mode_choice, 1, wx.EXPAND)
        episode_col.Add(view_mode_row, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._episodes = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._episodes.SetName("Episodes of the selected show; arrow through for details")
        self._build_episode_columns()
        episode_col.Add(self._episodes, 1, wx.EXPAND)
        body.Add(episode_col, 2, wx.EXPAND)

        root_sizer.Add(body, 2, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root_sizer.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        player_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_pause_btn = wx.Button(self.dialog, label="&Play/Pause")
        self._play_pause_btn.SetName("Play or pause the current episode")
        self._stop_btn = wx.Button(self.dialog, label="&Stop")
        speed_label = wx.StaticText(self.dialog, label="S&peed:")
        self._speed_choice = wx.Choice(self.dialog, choices=list(_SPEED_CHOICES))
        self._speed_choice.SetName("Playback speed for this podcast")
        self._speed_choice.SetSelection(_SPEED_CHOICES.index("1.0x"))
        self._now_playing = wx.StaticText(self.dialog, label="Nothing playing.")
        self._now_playing.SetName("Now playing")
        player_row.Add(self._play_pause_btn, 0, wx.RIGHT, 6)
        player_row.Add(self._stop_btn, 0, wx.RIGHT, 12)
        player_row.Add(speed_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        player_row.Add(self._speed_choice, 0, wx.RIGHT, 12)
        player_row.Add(self._now_playing, 1, wx.ALIGN_CENTER_VERTICAL)
        root_sizer.Add(player_row, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        add_podcast_btn = wx.Button(self.dialog, label="&Add Podcast...")
        add_podcast_btn.SetName("Search, add by feed URL, or import OPML")
        new_folder_btn = wx.Button(self.dialog, label="&New Folder...")
        new_folder_btn.SetName("Create a new folder, nested under the selected folder if any")
        import_opml_btn = wx.Button(self.dialog, label="&Import OPML...")
        export_opml_btn = wx.Button(self.dialog, label="&Export OPML...")
        settings_btn = wx.Button(self.dialog, label="Podcast &Settings...")
        settings_btn.SetName("Global defaults for playback mode, retention, speed, and downloads")
        self._download_btn = wx.Button(self.dialog, label="&Download")
        self._download_btn.SetName("Download the selected episode")
        self._download_btn.Enable(False)
        self._pause_btn = wx.Button(self.dialog, label="&Pause Download")
        self._pause_btn.SetName("Pause or resume this episode's download")
        self._pause_btn.Enable(False)
        self._remove_download_btn = wx.Button(self.dialog, label="&Remove Download")
        self._remove_download_btn.Enable(False)
        self._chapters_btn = wx.Button(self.dialog, label="C&hapters...")
        self._chapters_btn.SetName("Browse and jump to this episode's chapter markers")
        self._chapters_btn.Enable(False)
        unsubscribe_btn = wx.Button(self.dialog, label="&Unsubscribe")
        unsubscribe_btn.SetName("Unsubscribe from the selected show (Delete key also works)")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        for widget in (
            add_podcast_btn,
            new_folder_btn,
            import_opml_btn,
            export_opml_btn,
            settings_btn,
            self._download_btn,
            self._pause_btn,
            self._remove_download_btn,
            self._chapters_btn,
            unsubscribe_btn,
        ):
            btn_row.Add(widget, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root_sizer)

        # The whole transport on this window -- play/pause, stop, skip, speed,
        # chapters, volume -- reaching Cast's own verbs, instead of only the
        # main window's menu bar reaching them.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(self.dialog, self._transport_host, wx=wx)

        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)
        self._tree.Bind(wx.EVT_TREE_KEY_DOWN, self._on_tree_key_down)
        self._tree.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._show_tree_context_menu())
        self._episodes.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_episode_selected)
        self._episodes.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_episode_activate)
        self._episodes.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._show_episode_context_menu())
        self._episodes.Bind(wx.EVT_KEY_DOWN, self._on_episode_key_down)
        add_podcast_btn.Bind(wx.EVT_BUTTON, self._on_add_podcast)
        new_folder_btn.Bind(wx.EVT_BUTTON, self._on_new_folder)
        import_opml_btn.Bind(wx.EVT_BUTTON, self._on_import_opml)
        export_opml_btn.Bind(wx.EVT_BUTTON, self._on_export_opml_click)
        settings_btn.Bind(wx.EVT_BUTTON, self._on_open_settings_click)
        self._download_btn.Bind(wx.EVT_BUTTON, self._on_download)
        self._pause_btn.Bind(wx.EVT_BUTTON, self._on_pause_resume_download)
        self._remove_download_btn.Bind(wx.EVT_BUTTON, self._on_remove_download)
        self._chapters_btn.Bind(wx.EVT_BUTTON, self._on_chapters_click)
        unsubscribe_btn.Bind(wx.EVT_BUTTON, self._on_unsubscribe)
        self._play_pause_btn.Bind(wx.EVT_BUTTON, self._on_play_pause)
        self._stop_btn.Bind(wx.EVT_BUTTON, self._on_stop)
        self._speed_choice.Bind(wx.EVT_CHOICE, self._on_speed_choice)
        self._show_sort_choice.Bind(wx.EVT_CHOICE, lambda _e: self.refresh_tree())
        self._episode_sort_choice.Bind(wx.EVT_CHOICE, self._on_episode_sort_choice)
        self._view_mode_choice.Bind(wx.EVT_CHOICE, self._on_view_mode_choice)

        from quill.ui.podcasts.scan_hold_control import ScanHoldController

        self._scan_hold = ScanHoldController(self, parent=self.dialog)
        from quill.ui.podcasts import manager_keys

        self.dialog.Bind(wx.EVT_CHAR_HOOK, lambda e: manager_keys.on_char_hook(self, e))
        self.dialog.Bind(wx.EVT_KEY_UP, lambda e: manager_keys.on_key_up(self, e))

        self.refresh_tree()
        self._update_now_playing()
        self._sync_speed_choice()

    # -- Winamp classic keys (CastWinampKeysMixin hooks) -------------------

    def _winamp_keys_enabled(self) -> bool:
        return bool(self._winamp_keys_enabled_cb())

    def _winamp_rows(self) -> list[tuple[object, object]]:
        """Whatever the episode list is showing, paired with its show."""
        pair_shows = getattr(self, "_pair_shows", [])
        rows: list[tuple[object, object]] = []
        for index, episode in enumerate(self._current_episodes):
            show = self._current_show
            if show is None and index < len(pair_shows):
                show = pair_shows[index]
            if show is not None:
                rows.append((show, episode))
        return rows

    def _winamp_selected_index(self) -> int:
        return self._episodes.GetFirstSelected()

    def _winamp_select_index(self, index: int) -> None:
        if 0 <= index < self._episodes.GetItemCount():
            self._episodes.Select(index)
            self._episodes.Focus(index)
            self._episodes.EnsureVisible(index)

    def _winamp_play_pair(self, show: object, episode: object) -> None:
        self._play_episode(show, episode, resume_ms=episode.position_ms)

    # ------------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Podcasts", announce=self._announce)
        finally:
            # The controller keeps playing after this dialog closes -- only
            # the dialog itself is torn down.
            self.dialog.Destroy()

    def _update_now_playing(self) -> None:
        self._now_playing.SetLabel(self._controller.state.status_text)

    # ------------------------------------------------------------------
    # Tree

    def _selected_show_sort_mode(self) -> str:
        index = self._show_sort_choice.GetSelection()
        return SHOW_SORT_MODES[index] if index >= 0 else "title_az"

    def _selected_episode_sort_mode(self) -> str:
        index = self._episode_sort_choice.GetSelection()
        return EPISODE_SORT_MODES[index] if index >= 0 else "date_newest"

    def _sort_context_show(self) -> PodcastShow | None:
        """The show whose sort order the Sort dropdown edits right now --
        the selected single show, or the selected per-podcast Folders node
        inside a virtual view; None means the dropdown edits the shared
        default instead (every show without its own override follows it)."""
        if self._current_show is not None:
            return self._current_show
        return self._selected_virtual_show()

    def _sync_episode_sort_choice(self) -> None:
        show = self._sort_context_show()
        mode = (
            self._library.effective_settings(show).episode_sort_mode
            if show is not None
            else self._library.settings.episode_sort_mode
        )
        index = EPISODE_SORT_MODES.index(mode) if mode in EPISODE_SORT_MODES else 0
        self._episode_sort_choice.SetSelection(index)

    def _on_episode_sort_choice(self, _event: object) -> None:
        mode = self._selected_episode_sort_mode()
        label = self._episode_sort_choice.GetStringSelection()
        show = self._sort_context_show()
        if show is not None:
            self._library.apply_show_override(show, episode_sort_mode=mode)
            self._announce(f"Sort order for {show.title} set to {label}")
        else:
            self._library.settings.episode_sort_mode = mode
            self._announce(f"Sort order set to {label} (the shared default)")
        self._on_library_changed()
        self._refresh_episode_list()

    def _on_view_mode_choice(self, _event: object) -> None:
        index = self._view_mode_choice.GetSelection()
        mode = _VIEW_MODE_MODES[index] if index >= 0 else "grouped"
        self._library.settings.episode_list_view_mode = mode
        self._on_library_changed()
        label = self._view_mode_choice.GetStringSelection()
        self._announce(f"Cross-show lists now shown as {label}")
        # "Folders" adds/removes per-podcast tree nodes; every mode still
        # needs the episode list (and, if the selection landed on a show
        # node that no longer exists, the sort choice) refreshed.
        self.refresh_tree()
        self._refresh_episode_list()

    def _refresh_episode_list(self) -> None:
        """Re-fill whatever's currently shown -- a virtual view / Inbox
        folder / per-podcast Folders node, or a single show -- after the
        sort mode or view mode changes."""
        if not self._maybe_fill_virtual_selection():
            self._fill_episodes(self._current_show)
        self._sync_episode_sort_choice()

    def _unheard_count_for_folder(self, folder_id: str) -> int:
        # One shared implementation with Radio's Subscriptions branch, so the
        # two apps can never disagree about what a folder's number means.
        from quill.core.podcasts.sorting import unheard_count_for_folder

        return unheard_count_for_folder(self._library, folder_id)

    def refresh_tree(self) -> None:
        self._tree.DeleteAllItems()
        self._tree_item_show.clear()
        self._tree_item_folder.clear()
        root = self._tree.AddRoot(_FOLDER_ROOT_LABEL)
        self._add_virtual_view_nodes(root)
        show_sort_mode = self._selected_show_sort_mode()

        def add_folder_children(parent_item: object, folder_id: str | None) -> None:
            child_folders = sorted(
                (f for f in self._library.folders if f.parent_folder_id == folder_id),
                key=lambda f: f.name.casefold(),
            )
            for folder in child_folders:
                unheard = self._unheard_count_for_folder(folder.id)
                label = f"{folder.name} ({unheard} unheard)" if unheard else folder.name
                item = self._tree.AppendItem(parent_item, label)
                self._tree_item_folder[_item_key(item)] = folder.id
                add_folder_children(item, folder.id)
                add_shows(item, folder.id)
            add_shows(parent_item, folder_id)

        def add_shows(parent_item: object, folder_id: str | None) -> None:
            matching = self._apply_show_filter([
                s for s in self._library.shows if s.folder_id == folder_id
            ])
            for show in sort_shows(matching, show_sort_mode):
                unheard = sum(1 for e in show.episodes if not e.played)
                label = f"{show.title} ({unheard} unheard)" if unheard else show.title
                item = self._tree.AppendItem(parent_item, label)
                self._tree_item_show[_item_key(item)] = show.id

        add_folder_children(root, None)
        self._tree.ExpandAll()
        if not self._library.shows:
            self._status.SetLabel(
                "No podcasts yet. Press Add Podcast to search, add by feed URL, or import OPML."
            )

    def _selected_show_id(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = _item_key(item)
        return self._tree_item_show.get(key)

    def _selected_folder_id(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = _item_key(item)
        return self._tree_item_folder.get(key)

    def _on_tree_selection(self, _event: object) -> None:
        if self._maybe_fill_virtual_selection():
            self._sync_episode_sort_choice()
            return
        show_id = self._selected_show_id()
        show = self._library.find_show(show_id) if show_id else None
        self._current_show = show
        self._fill_episodes(show)
        self._sync_speed_choice()
        self._sync_episode_sort_choice()

    def _sync_speed_choice(self) -> None:
        if self._current_show is None:
            self._speed_choice.SetSelection(_SPEED_CHOICES.index("1.0x"))
            return
        speed = self._library.effective_settings(self._current_show).speed
        label = f"{speed:g}x"
        if label not in _SPEED_CHOICES:
            label = "1.0x"
        self._speed_choice.SetSelection(_SPEED_CHOICES.index(label))

    def _on_speed_choice(self, _event: object) -> None:
        show = self._current_show
        if show is None:
            return
        speed = float(self._speed_choice.GetStringSelection().rstrip("x"))
        self._library.apply_show_override(show, speed=speed)
        self._on_library_changed()
        if self._controller.state.show_id == show.id:
            self._controller.set_rate(speed)
        self._announce(f"Playback speed set to {speed:g}x for {show.title}")

    def _on_tree_key_down(self, event: object) -> None:
        if event.GetKeyCode() == self._wx.WXK_DELETE:
            self._on_unsubscribe(event)
            return
        if event.GetKeyCode() == self._wx.WXK_F2:
            # F2 renames whatever is selected: a folder, a show, or a playlist.
            folder_id = self._selected_folder_id()
            if folder_id:
                folder = self._library.find_folder(folder_id)
                if folder is not None:
                    self._on_rename_folder(folder)
                    return
            show_id = self._selected_show_id()
            show = self._library.find_show(show_id) if show_id else None
            if show is not None:
                self._on_rename_show(show)
                return
            playlist = self._selected_playlist()
            if playlist is not None:
                self._on_rename_playlist(playlist)
            return
        event.Skip()

    # -- selection anchors (move/delete keep you near where you were) --------

    def _neighbor_anchor_for_show(self, show_id: str) -> tuple[str, str] | None:
        """What to select after *show_id* leaves its current tree spot: the
        next sibling show, else the previous one, else the containing folder.
        Never the tree top -- a move must not dump you back at the root."""
        show = self._library.find_show(show_id)
        if show is None:
            return None
        siblings = sort_shows(
            [s for s in self._library.shows if s.folder_id == show.folder_id],
            self._selected_show_sort_mode(),
        )
        ids = [s.id for s in siblings]
        if show_id in ids:
            index = ids.index(show_id)
            for candidate in (index + 1, index - 1):
                if 0 <= candidate < len(ids) and ids[candidate] != show_id:
                    return ("show", ids[candidate])
        if show.folder_id:
            return ("folder", show.folder_id)
        return None

    def _restore_tree_anchor(self, anchor: tuple[str, str] | None) -> None:
        """Select the remembered neighbor after a refresh (best-effort)."""
        if anchor is None:
            return
        kind, target_id = anchor
        mapping = self._tree_item_show if kind == "show" else self._tree_item_folder
        item = self._tree.GetRootItem()
        stack = [item]
        while stack:
            current = stack.pop()
            key = _item_key(current)
            if mapping.get(key) == target_id:
                self._tree.SelectItem(current)
                return
            child, cookie = self._tree.GetFirstChild(current)
            while child.IsOk():
                stack.append(child)
                child, cookie = self._tree.GetNextChild(current, cookie)

    # -- move / rename / delete ----------------------------------------------

    def _on_move_show_to_folder(self, show: PodcastShow) -> None:
        """File one podcast -- see ui/podcasts/move_shows_dialog."""
        from quill.ui.podcasts.move_shows_dialog import move_one_show

        move_one_show(self, show)

    def _on_add_starter_playlists(self) -> None:
        """Five smart playlists worth having -- see ui/podcasts/playlist_starters."""
        from quill.ui.podcasts.playlist_starters import add_starters

        add_starters(self)

    def _on_move_several(self, preselect: str = "") -> None:
        """Move several podcasts into one folder -- see ui/podcasts/move_shows_dialog."""
        from quill.ui.podcasts.move_shows_dialog import open_move_shows

        open_move_shows(self, preselect)

    def _prompt_rename(self, title: str, current: str) -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self.dialog, "New name:", title, value=current
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            name = dialog.GetValue().strip()
        return name or None

    def _on_rename_folder(self, folder: object) -> None:
        name = self._prompt_rename("Rename Folder", folder.name)
        if name is None:
            return
        folder.name = name
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Folder renamed to {name}")

    def _on_rename_show(self, show: PodcastShow) -> None:
        name = self._prompt_rename("Rename Podcast", show.title)
        if name is None:
            return
        show.title = name
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Podcast renamed to {name}")

    def _on_rename_episode(self, episode: PodcastEpisode) -> None:
        name = self._prompt_rename("Rename Episode", episode.title)
        if name is None:
            return
        episode.title = name
        self._on_library_changed()
        self._fill_episodes(self._current_show)
        self._announce(f"Episode renamed to {name}")

    def _delete_downloaded_files_for_removed_shows(self, removed: list[PodcastShow]) -> int:
        """Best-effort removal of downloaded files for unsubscribed shows;
        returns how many files were deleted. Never the reason a delete fails."""
        deleted = 0
        for show in removed:
            for episode in show.episodes:
                if not episode.downloaded_path:
                    continue
                path = Path(episode.downloaded_path)
                try:
                    if path.exists():
                        path.unlink()
                        deleted += 1
                except OSError:
                    continue
        return deleted

    def _on_delete_folder(self, folder: object) -> None:
        """Delete a folder, and decide what happens to what is inside it.

        Body in ``ui/podcasts/folder_delete`` (GATE-11).
        """
        from quill.ui.podcasts.folder_delete import delete_folder

        delete_folder(self, folder)

    def _on_delete_inbox_folder(self, folder: object) -> None:
        from quill.core.podcasts.inbox import delete_inbox_folder

        if delete_inbox_folder(self._library, folder.id):
            self._on_library_changed()
            self.refresh_tree()
            self._announce(
                f"Inbox folder {folder.name} deleted; its episodes moved up. "
                "Episodes are never removed by Inbox actions."
            )

    def _show_tree_context_menu(self) -> None:
        wx = self._wx
        show_id = self._selected_show_id()
        show = self._library.find_show(show_id) if show_id else None
        menu = wx.Menu()
        if show is not None:
            from quill.ui.podcasts.manager_menus import build_menu

            # Pause Updates is not a Quick Action: it is a state of the
            # subscription, not something you do to the show. It was called
            # "Pause Downloads" until somebody reasonably read that as
            # "downloads only" -- it stops the feed check too, and the label
            # now says which.
            pause_label = (
                "&Resume Updates for This Podcast"
                if show.paused
                else "&Pause Updates for This Podcast"
            )
            pause_item = menu.Append(wx.ID_ANY, pause_label)
            pause_item.SetHelp(
                "Stops both halves of keeping this show current: no feed checks "
                "for new episodes, and no automatic downloads. It does not "
                "unsubscribe you, does not remove episodes or downloaded files, "
                "does not stop a download already running, and does not disable "
                "Refresh Feed on this show -- that still checks it on demand."
            )
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_toggle_show_paused(show), pause_item)
            if show.route_to_inbox and show.inbox_default_folder_id:
                forget_item = menu.Append(wx.ID_ANY, "For&get Remembered Inbox Folder")
                menu.Bind(wx.EVT_MENU, lambda _e: self._on_forget_inbox_folder(show), forget_item)
            menu.AppendSeparator()
            build_menu(self, menu, self._resolved_show_actions(show))
            # Filing several at once. On the show menu because that is where
            # somebody already is when they decide the library needs tidying.
            bulk_item = menu.Append(wx.ID_ANY, "Move Se&veral Podcasts to Folder...")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_move_several(show.id), bulk_item)
        elif self._selected_virtual_view() == "recently_expired":
            self._append_recently_expired_items(menu)
        elif self._selected_playlists_root():
            starters_item = menu.Append(wx.ID_ANY, "Add S&tarter Playlists")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_add_starter_playlists(), starters_item)
            smart_item = menu.Append(wx.ID_ANY, "New &Smart Playlist...")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_new_smart_playlist(), smart_item)
            manual_item = menu.Append(wx.ID_ANY, "New Play&list...")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_new_manual_playlist(), manual_item)
        elif (playlist := self._selected_playlist()) is not None:
            if playlist.kind == "smart":
                rules_item = menu.Append(wx.ID_ANY, "Edit R&ules...")
                menu.Bind(
                    wx.EVT_MENU, lambda _e, p=playlist: self._on_edit_playlist_rules(p), rules_item
                )
            rename_playlist_item = menu.Append(wx.ID_ANY, "Rena&me Playlist...\tF2")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, p=playlist: self._on_rename_playlist(p),
                rename_playlist_item,
            )
            delete_playlist_item = menu.Append(wx.ID_ANY, "&Delete Playlist...")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, p=playlist: self._on_delete_playlist(p),
                delete_playlist_item,
            )
        else:
            folder_id = self._selected_folder_id()
            folder = self._library.find_folder(folder_id) if folder_id else None
            if folder is not None:
                # A folder is a place you listen from, not only a place shows
                # are filed. Built in ui/podcasts/folder_menu (GATE-11).
                from quill.ui.podcasts.folder_menu import append_folder_items

                append_folder_items(self, menu, folder_id)
                rename_item = menu.Append(wx.ID_ANY, "Rena&me Folder...\tF2")
                menu.Bind(wx.EVT_MENU, lambda _e, f=folder: self._on_rename_folder(f), rename_item)
                delete_item = menu.Append(wx.ID_ANY, "&Delete Folder...")
                menu.Bind(wx.EVT_MENU, lambda _e, f=folder: self._on_delete_folder(f), delete_item)
                menu.AppendSeparator()
            new_folder_item = menu.Append(wx.ID_ANY, "&New Folder...")
            menu.Bind(wx.EVT_MENU, self._on_new_folder, new_folder_item)
        self._tree.PopupMenu(menu)
        menu.Destroy()

    def _resolved_show_actions(self, show: PodcastShow) -> list:
        from quill.ui.podcasts.manager_menus import ordered_actions, show_actions

        return ordered_actions(self, "show", show_actions(self, show))

    def _on_refresh_feed(self, show: PodcastShow) -> None:
        if self._refresh_feed_cb is None:
            return
        self._announce(f"Refreshing {show.title}...")
        self._refresh_feed_cb(show.id)

    # ------------------------------------------------------------------
    # Episodes

    def _fill_episodes(self, show: PodcastShow | None) -> None:
        self._episodes.DeleteAllItems()
        episodes = self._apply_episode_filter(list(show.episodes) if show is not None else [])
        self._current_episodes = sort_episodes(episodes, self._selected_episode_sort_mode())
        self._pair_shows = []
        for row, episode in enumerate(self._current_episodes):
            fill_row(
                self._episodes,
                row,
                self._episode_columns,
                self._episode_row_values(episode, show),
            )
        self._download_btn.Enable(False)
        self._pause_btn.Enable(False)
        self._remove_download_btn.Enable(False)
        self._chapters_btn.Enable(False)
        if show is not None:
            self._status.SetLabel(f"{len(self._current_episodes)} episode(s) for {show.title}.")
        if self._current_episodes:
            self._episodes.Select(0)
            self._episodes.Focus(0)

    def _download_item_id(self, episode: PodcastEpisode) -> str:
        return episode.guid

    def _selected_episode(self) -> PodcastEpisode | None:
        index = self._episodes.GetFirstSelected()
        if 0 <= index < len(self._current_episodes):
            return self._current_episodes[index]
        return None

    def _on_episode_selected(self, _event: object) -> None:
        episode = self._selected_episode()
        if episode is None:
            return
        already_downloaded = bool(episode.downloaded_path)
        item = self._download_queue.get(self._download_item_id(episode))
        in_flight = item is not None and item.status in ("queued", "downloading", "paused")
        self._download_btn.Enable(not already_downloaded and not in_flight)
        self._pause_btn.Enable(in_flight)
        if item is not None and item.status == "paused":
            self._pause_btn.SetLabel("&Resume Download")
        else:
            self._pause_btn.SetLabel("&Pause Download")
        self._remove_download_btn.Enable(already_downloaded)
        # Chapters are no longer only a published-feed feature: the free
        # cascade can also read them from the file's tags or the show notes.
        self._chapters_btn.Enable(episode_has_possible_chapters(episode))

    def _on_episode_activate(self, _event: object) -> None:
        """Enter (or double-click) runs the listener's default Quick Action.

        Which is Play unless they changed it -- the shipped order puts Play
        first precisely so this upgrade changes nothing until asked.
        """
        actions = self._resolved_episode_actions()
        if actions and actions[0].enabled:
            actions[0].run()
            return
        self._play_selected()

    def _on_chapters_click(self, _event: object) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.open_chapters(self, self._current_show, self._selected_episode())

    def _on_analyze_chapters(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        """Analyse Chapters, from the episode context menu.

        Routed to the frame rather than run here: the analysis needs the task
        manager and the announcement channel, and the manager dialog is a view
        onto the frame's library, not a second owner of it.
        """
        from quill.ui.podcasts.chapter_analysis import analyse_chapters_for_episode

        host = self._transport_host
        if host is None or not hasattr(host, "_task_manager"):
            self._announce("Chapters can only be analysed from the main window.")
            return
        analyse_chapters_for_episode(host, show, episode)

    def _open_chapters_dialog(
        self, show: PodcastShow, episode: PodcastEpisode, chapter_set: object
    ) -> None:
        from quill.ui.podcasts.chapters_dialog import ChaptersDialog

        chapters = list(getattr(chapter_set, "chapters", []) or [])
        if not chapters:
            self._announce("This episode has no chapters.")
            return
        # Marking chapters to skip is only offered for the episode actually
        # playing: a mark on something else would either do nothing now or
        # surprise you later, and neither is worth a button.
        state = self._controller.state
        playing_this = state.show_id == show.id and state.episode_guid == episode.guid
        dialog = ChaptersDialog(
            self.dialog,
            episode_title=episode.title,
            chapters=chapters,
            announce_cb=self._announce,
            source_label=str(getattr(chapter_set, "label", "")),
            skip_state=self._chapter_skip_state() if playing_this else None,
        )
        start_ms = dialog.show()
        if start_ms is None:
            return
        if state.show_id == show.id and state.episode_guid == episode.guid:
            self._controller.seek(start_ms)
        else:
            self._play_episode(show, episode, resume_ms=start_ms)

    def _play_selected(self) -> None:
        show = self._current_show
        episode = self._selected_episode()
        if show is None or episode is None:
            return
        self._play_episode(show, episode, resume_ms=episode.position_ms)

    def _play_episode(self, show: PodcastShow, episode: PodcastEpisode, *, resume_ms: int) -> None:
        from quill.ui.podcasts.show_actions import start_episode_playback

        if not start_episode_playback(
            self._controller, self._library, show, episode, resume_ms=resume_ms
        ):
            return
        self._update_now_playing()
        self._announce(f"Playing {episode.title}")

    def _on_play_pause(self, _event: object) -> None:
        state = self._controller.state
        if state.title:
            self._controller.toggle_play_pause()
        else:
            self._play_selected()
        self._update_now_playing()

    def _on_stop(self, _event: object) -> None:
        self._controller.stop()
        self._update_now_playing()
        self._announce("Stopped")

    def _resolved_episode_actions(self) -> list:
        """The selected episode's actions, in the listener's Quick Actions
        order -- the one list behind the context menu, Enter, and Ctrl+N."""
        from quill.ui.podcasts.manager_menus import episode_actions, ordered_actions

        episode = self._selected_episode()
        if episode is None:
            return []
        show = self._show_for_selected_episode(self._episodes.GetFirstSelected())
        if show is None:
            return []
        return ordered_actions(self, "episode", episode_actions(self, show, episode))

    def _show_episode_context_menu(self) -> None:
        from quill.ui.podcasts.manager_menus import build_menu

        episode = self._selected_episode()
        if episode is None:
            return
        wx = self._wx
        menu = wx.Menu()
        selected_count = self._episodes.GetSelectedItemCount()
        if selected_count > 1:
            self._append_bulk_episode_items(menu, selected_count)
        # The transport pair and the download-state items are not Quick
        # Actions: they act on the *player* and the *transfer*, not on the
        # episode, and reordering them would be reordering something the
        # listener did not select. They stay pinned above the ordered set.
        play_item = menu.Append(wx.ID_ANY, "Pla&y/Pause")
        stop_item = menu.Append(wx.ID_ANY, "&Stop")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_play_pause(None), play_item)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_stop(None), stop_item)

        queued_item = self._download_queue.get(self._download_item_id(episode))
        in_flight = queued_item is not None and queued_item.status in (
            "queued",
            "downloading",
            "paused",
        )
        pause_label = (
            "Resu&me Download"
            if (queued_item is not None and queued_item.status == "paused")
            else "Pause Do&wnload"
        )
        pause_item = menu.Append(wx.ID_ANY, pause_label)
        pause_item.Enable(in_flight)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_pause_resume_download(None), pause_item)

        send_notes_item = menu.Append(wx.ID_ANY, "Sen&d Show Notes to Editor")
        send_notes_item.Enable(bool(episode.description) and self._on_send_show_notes is not None)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_send_show_notes_click(episode), send_notes_item)

        show = self._show_for_selected_episode(self._episodes.GetFirstSelected())
        if show is not None:
            self._append_transcript_items(menu, show, episode)

        menu.AppendSeparator()
        build_menu(self, menu, self._resolved_episode_actions())

        self._episodes.PopupMenu(menu)
        menu.Destroy()

    def _on_episode_key_down(self, event: object) -> None:
        """Ctrl+1..Ctrl+9 and Enter, over this episode's Quick Actions."""
        from quill.ui.podcasts.manager_keys import handle_episode_key

        handle_episode_key(self, event)

    def _on_view_show_notes(self, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.view_show_notes(self, episode)

    def _on_send_show_notes_click(self, episode: PodcastEpisode) -> None:
        if self._on_send_show_notes is None:
            return
        from quill.core.podcasts.show_notes import html_to_plain_text

        self._on_send_show_notes(html_to_plain_text(episode.description))
        self._announce("Sent show notes to a new document")

    def _on_toggle_played(self, episode: PodcastEpisode) -> None:
        position_sync.mark_played(episode, not episode.played)
        if episode.played:
            from quill.core.podcasts import retention

            show = self._current_show or next(
                (
                    candidate
                    for candidate in self._library.shows
                    if any(item.guid == episode.guid for item in candidate.episodes)
                ),
                None,
            )
            retention.on_episode_played(self._library, show, episode)
        self._on_library_changed()
        self._refresh_selected_episode_row()
        self._announce("Marked as played" if episode.played else "Marked as unplayed")

    def _on_copy_episode_link(self, episode: PodcastEpisode) -> None:
        wx = self._wx
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(episode.audio_url))
            finally:
                wx.TheClipboard.Close()
        self._announce("Copied episode link")

    def _on_share_moment(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        """Copy a link and a sentence for where this episode is right now."""
        from quill.ui.podcasts.share_moment import share_moment

        share_moment(self, show, episode, int(getattr(episode, "position_ms", 0) or 0))

    # -- sharing and export (x.md item 9) ------------------------------
    # Thin wiring only; the behaviour is in show_actions so the standalone
    # QUILL Cast panel gets the same wording from the same implementation.

    def _on_copy_show_link(self, show: PodcastShow) -> None:
        from quill.ui.podcasts.share_actions import copy_show_link

        copy_show_link(show, announce=self._announce)

    def _on_show_episode_in_explorer(self, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.share_actions import reveal_episode_in_file_manager

        reveal_episode_in_file_manager(episode, announce=self._announce)

    def _on_save_episode_audio_as(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.share_actions import save_episode_audio_as

        save_episode_audio_as(
            self.dialog,
            self._download_queue,
            self._download_root,
            show,
            episode,
            announce=self._announce,
        )
        self._refresh_selected_episode_row()

    # ------------------------------------------------------------------
    # Subscriptions / folders / OPML

    def _on_add_podcast(self, _event: object) -> None:
        if self._on_open_add_podcast is not None:
            self._on_open_add_podcast()
            self.refresh_tree()

    def _on_new_folder(self, _event: object) -> None:
        wx = self._wx
        dialog = wx.TextEntryDialog(self.dialog, "Folder name:", "New Folder")
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name:
            return
        parent_folder_id = self._selected_folder_id()
        self._library.add_folder(name, parent_folder_id=parent_folder_id)
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Created folder {name}")

    def _on_import_opml(self, _event: object) -> None:
        if self._on_open_import_opml is not None:
            self._on_open_import_opml()
            self.refresh_tree()

    def _on_export_opml_click(self, _event: object) -> None:
        if self._on_export_opml is not None:
            self._on_export_opml()

    def _on_open_settings_click(self, _event: object) -> None:
        if self._on_open_settings is not None:
            self._on_open_settings()

    def _on_unsubscribe(self, _event: object) -> None:
        show_id = self._selected_show_id()
        show = self._library.find_show(show_id) if show_id else None
        if show is None:
            return
        wx = self._wx

        downloaded = [e for e in show.episodes if e.downloaded_path]
        policy = self._library.effective_settings(show).delete_files_on_remove

        confirmed = (
            show_message_box(
                f"Unsubscribe from {show.title}?",
                "Unsubscribe",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self.dialog,
                announce=self._announce,
            )
            == wx.YES
        )
        if not confirmed:
            return

        delete_files = policy == "always"
        if downloaded and policy == "ask":
            delete_files = (
                show_message_box(
                    f"Also delete the {len(downloaded)} downloaded episode file(s)?",
                    "Delete Downloaded Files",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                    self.dialog,
                    announce=self._announce,
                )
                == wx.YES
            )
        if delete_files:
            for episode in downloaded:
                path = Path(episode.downloaded_path)
                if path.exists():
                    path.unlink(missing_ok=True)

        # No orphaned secrets: unsubscribing deletes the stored feed password (S-3).
        feed_auth.delete_feed_password(show.id)
        self._library.remove_show(show.id)
        self._on_library_changed()
        self.refresh_tree()
        if delete_files and downloaded:
            self._announce(f"Unsubscribed from {show.title} and deleted its downloaded episodes")
        else:
            self._announce(f"Unsubscribed from {show.title}")
