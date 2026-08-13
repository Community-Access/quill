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

from quill.core.podcasts import feed_auth
from quill.core.podcasts.chapter_sources import (
    build_episode_chapters,
    episode_has_possible_chapters,
)
from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.sorting import (
    EPISODE_SORT_MODES,
    SHOW_SORT_MODES,
    sort_episodes,
    sort_shows,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids, show_message_box
from quill.ui.podcasts.manager_phase4 import ManagerPhase4Mixin
from quill.ui.podcasts.player_controller import PodcastPlayerController

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
_SHOW_SORT_LABELS = ("Title A-Z", "Most unheard first", "Recently updated first")
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


class PodcastManagerDialog(ManagerPhase4Mixin):
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
        on_library_changed: Callable[[], None] | None = None,
        on_open_add_podcast: Callable[[], None] | None = None,
        on_open_import_opml: Callable[[], None] | None = None,
        on_export_opml: Callable[[], None] | None = None,
        on_refresh_feed: Callable[[str], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
        on_send_show_notes: Callable[[str], None] | None = None,
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
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_open_add_podcast = on_open_add_podcast
        self._on_open_import_opml = on_open_import_opml
        self._on_export_opml = on_export_opml
        self._refresh_feed_cb = on_refresh_feed
        self._on_open_settings = on_open_settings
        self._on_send_show_notes = on_send_show_notes

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
        self._show_sort_choice.SetSelection(0)
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
        self._episodes.InsertColumn(0, "Title", width=280)
        self._episodes.InsertColumn(1, "Published", width=110)
        self._episodes.InsertColumn(2, "Duration", width=80)
        self._episodes.InsertColumn(3, "Status", width=130)
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

        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)
        self._tree.Bind(wx.EVT_TREE_KEY_DOWN, self._on_tree_key_down)
        self._tree.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._show_tree_context_menu())
        self._episodes.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_episode_selected)
        self._episodes.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_episode_activate)
        self._episodes.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._show_episode_context_menu())
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

        self.refresh_tree()
        self._update_now_playing()
        self._sync_speed_choice()

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
        total = sum(1 for e in _shows_episodes(self._library, folder_id) if not e.played)
        for folder in self._library.folders:
            if folder.parent_folder_id == folder_id:
                total += self._unheard_count_for_folder(folder.id)
        return total

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
        from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

        picker = FolderPickerDialog(
            self.dialog,
            library=self._library,
            title=f"Move {show.title} to Folder",
            announce_cb=self._announce,
        )
        result = picker.show()
        if not result.confirmed:
            return
        chosen = result.folder_id
        anchor = self._neighbor_anchor_for_show(show.id)
        show.folder_id = chosen or None
        self._on_library_changed()
        self.refresh_tree()
        self._restore_tree_anchor(anchor)
        destination = self._library.find_folder(chosen) if chosen else None
        where = destination.name if destination is not None else "the top level"
        self._announce(f"Moved {show.title} to {where}")

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
        wx = self._wx
        with wx.SingleChoiceDialog(  # dialog_button_contract: exempt
            self.dialog,
            f'What should happen to the podcasts inside "{folder.name}"?',
            "Delete Folder",
            [
                "Move them up to the parent folder (safe)",
                "Unsubscribe them too",
            ],
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            contents = "promote" if picker.GetSelection() == 0 else "remove"
        removed = self._library.delete_folder(folder.id, contents=contents)
        deleted_files = 0
        if removed:
            confirm = show_message_box(
                f"Also delete the downloaded episode files of the "
                f"{len(removed)} unsubscribed show(s)?",
                "Delete Downloaded Files",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self.dialog,
                announce=self._announce,
            )
            if confirm == wx.YES:
                deleted_files = self._delete_downloaded_files_for_removed_shows(removed)
        self._on_library_changed()
        self.refresh_tree()
        if removed:
            suffix = f" and {deleted_files} downloaded file(s) deleted" if deleted_files else ""
            self._announce(
                f"Folder {folder.name} deleted; {len(removed)} show(s) unsubscribed{suffix}"
            )
        else:
            self._announce(f"Folder {folder.name} deleted; its contents moved up")

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
            refresh_item = menu.Append(wx.ID_ANY, "&Refresh Feed")
            refresh_item.Enable(bool(show.feed_url) and not self._safe_mode)
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_refresh_feed(show), refresh_item)

            pause_label = (
                "&Resume Downloads for This Podcast"
                if show.paused
                else "&Pause Downloads for This Podcast"
            )
            pause_item = menu.Append(wx.ID_ANY, pause_label)
            pause_item.SetHelp(
                "Keeps the podcast in your library but stops fetching or "
                "downloading new episodes for it."
            )
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_toggle_show_paused(show), pause_item)
            from quill.ui.podcasts.show_actions import append_feed_credentials_item

            append_feed_credentials_item(
                menu,
                wx,
                parent=self.dialog,
                library=self._library,
                show=show,
                announce=self._announce,
                on_changed=self._on_library_changed,
            )
            self._append_phase4_show_items(menu, show)

            move_item = menu.Append(wx.ID_ANY, "&Move to Folder...")
            menu.Bind(wx.EVT_MENU, lambda _e, s=show: self._on_move_show_to_folder(s), move_item)
            rename_show_item = menu.Append(wx.ID_ANY, "Rena&me...\tF2")
            menu.Bind(wx.EVT_MENU, lambda _e, s=show: self._on_rename_show(s), rename_show_item)

            menu.AppendSeparator()
            download_all_item = menu.Append(wx.ID_ANY, "Download &All Episodes")
            menu.Bind(
                wx.EVT_MENU, lambda _e, s=show: self._on_download_all_episodes(s), download_all_item
            )
            remove_all_item = menu.Append(wx.ID_ANY, "&Remove All Episodes...")
            menu.Bind(
                wx.EVT_MENU, lambda _e, s=show: self._on_remove_all_episodes(s), remove_all_item
            )

            menu.AppendSeparator()
            unsubscribe_item = menu.Append(wx.ID_ANY, "&Unsubscribe")
            menu.Bind(wx.EVT_MENU, self._on_unsubscribe, unsubscribe_item)
        elif self._selected_playlists_root():
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
                rename_item = menu.Append(wx.ID_ANY, "Rena&me Folder...\tF2")
                menu.Bind(wx.EVT_MENU, lambda _e, f=folder: self._on_rename_folder(f), rename_item)
                delete_item = menu.Append(wx.ID_ANY, "&Delete Folder...")
                menu.Bind(wx.EVT_MENU, lambda _e, f=folder: self._on_delete_folder(f), delete_item)
                menu.AppendSeparator()
            new_folder_item = menu.Append(wx.ID_ANY, "&New Folder...")
            menu.Bind(wx.EVT_MENU, self._on_new_folder, new_folder_item)
        self._tree.PopupMenu(menu)
        menu.Destroy()

    def _on_refresh_feed(self, show: PodcastShow) -> None:
        if self._refresh_feed_cb is None:
            return
        self._announce(f"Refreshing {show.title}...")
        self._refresh_feed_cb(show.id)

    def _on_toggle_show_paused(self, show: PodcastShow) -> None:
        show.paused = not show.paused
        self._on_library_changed()
        self._announce(
            f"Paused downloads for {show.title}"
            if show.paused
            else f"Resumed downloads for {show.title}"
        )

    # ------------------------------------------------------------------
    # Episodes

    def _fill_episodes(self, show: PodcastShow | None) -> None:
        self._episodes.DeleteAllItems()
        episodes = self._apply_episode_filter(list(show.episodes) if show is not None else [])
        self._current_episodes = sort_episodes(episodes, self._selected_episode_sort_mode())
        self._pair_shows = []
        for row, episode in enumerate(self._current_episodes):
            self._episodes.InsertItem(row, episode.title)
            self._episodes.SetItem(row, 1, episode.published[:16])
            minutes, seconds = divmod(episode.duration_seconds, 60)
            duration_text = f"{minutes}:{seconds:02d}" if episode.duration_seconds else ""
            self._episodes.SetItem(row, 2, duration_text)
            self._episodes.SetItem(row, 3, self._episode_status_text(episode))
        self._download_btn.Enable(False)
        self._pause_btn.Enable(False)
        self._remove_download_btn.Enable(False)
        self._chapters_btn.Enable(False)
        if show is not None:
            self._status.SetLabel(f"{len(self._current_episodes)} episode(s) for {show.title}.")
        if self._current_episodes:
            self._episodes.Select(0)
            self._episodes.Focus(0)

    def _episode_status_text(self, episode: PodcastEpisode) -> str:
        if episode.downloaded_path:
            return "Downloaded" + (", played" if episode.played else "")
        item = self._download_queue.get(self._download_item_id(episode))
        if item is not None and item.status in ("queued", "downloading", "paused"):
            return item.status.capitalize()
        return "Streaming"

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
        self._play_selected()

    def _on_chapters_click(self, _event: object) -> None:
        show = self._current_show
        episode = self._selected_episode()
        if show is None or episode is None:
            return
        if self._task_manager is None:
            return

        def _do_fetch(**_kwargs: object):
            return build_episode_chapters(episode, show, safe_mode=self._safe_mode)

        def _on_success(_op: str, result: object) -> None:
            self._open_chapters_dialog(show, episode, result)

        def _on_failure(_op: str, error: Exception) -> None:
            self._announce(f"Could not load chapters: {error}")

        self._announce("Loading chapters...")
        self._task_manager.submit(
            "podcast-chapters-dialog", _do_fetch, on_success=_on_success, on_failure=_on_failure
        )

    def _open_chapters_dialog(
        self, show: PodcastShow, episode: PodcastEpisode, chapter_set: object
    ) -> None:
        from quill.ui.podcasts.chapters_dialog import ChaptersDialog

        chapters = list(getattr(chapter_set, "chapters", []) or [])
        if not chapters:
            self._announce("This episode has no chapters.")
            return
        dialog = ChaptersDialog(
            self.dialog,
            episode_title=episode.title,
            chapters=chapters,
            announce_cb=self._announce,
            source_label=str(getattr(chapter_set, "label", "")),
        )
        start_ms = dialog.show()
        if start_ms is None:
            return
        state = self._controller.state
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

    def _show_episode_context_menu(self) -> None:
        episode = self._selected_episode()
        if episode is None:
            return
        wx = self._wx
        menu = wx.Menu()

        play_item = menu.Append(wx.ID_ANY, "&Play/Pause")
        stop_item = menu.Append(wx.ID_ANY, "&Stop")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_play_pause(None), play_item)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_stop(None), stop_item)
        menu.AppendSeparator()

        already_downloaded = bool(episode.downloaded_path)
        queued_item = self._download_queue.get(self._download_item_id(episode))
        in_flight = queued_item is not None and queued_item.status in (
            "queued",
            "downloading",
            "paused",
        )

        download_item = menu.Append(wx.ID_ANY, "&Download Episode")
        download_item.Enable(not already_downloaded and not in_flight)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_download(None), download_item)

        pause_label = (
            "&Resume Download"
            if (queued_item is not None and queued_item.status == "paused")
            else "&Pause Download"
        )
        pause_item = menu.Append(wx.ID_ANY, pause_label)
        pause_item.Enable(in_flight)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_pause_resume_download(None), pause_item)

        remove_item = menu.Append(wx.ID_ANY, "&Remove Downloaded Copy")
        remove_item.Enable(already_downloaded)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_remove_download(None), remove_item)

        menu.AppendSeparator()
        played_label = "Mark as &Unplayed" if episode.played else "Mark as &Played"
        played_item = menu.Append(wx.ID_ANY, played_label)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_toggle_played(episode), played_item)

        copy_item = menu.Append(wx.ID_ANY, "&Copy Episode Link")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_copy_episode_link(episode), copy_item)

        menu.AppendSeparator()
        notes_item = menu.Append(wx.ID_ANY, "&View Show Notes...")
        notes_item.Enable(bool(episode.description))
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_view_show_notes(episode), notes_item)

        send_notes_item = menu.Append(wx.ID_ANY, "Sen&d Show Notes to Editor")
        send_notes_item.Enable(bool(episode.description) and self._on_send_show_notes is not None)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_send_show_notes_click(episode), send_notes_item)

        episode_show = self._show_for_selected_episode(self._episodes.GetFirstSelected())
        if episode_show is not None:
            self._append_phase4_episode_items(menu, episode_show, episode)

        self._episodes.PopupMenu(menu)
        menu.Destroy()

    def _on_view_show_notes(self, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.show_notes_dialog import ShowNotesDialog

        dialog = ShowNotesDialog(
            self.dialog,
            episode_title=episode.title,
            description_html=episode.description,
            on_send_to_editor=self._on_send_show_notes,
            announce_cb=self._announce,
        )
        dialog.show()

    def _on_send_show_notes_click(self, episode: PodcastEpisode) -> None:
        if self._on_send_show_notes is None:
            return
        from quill.core.podcasts.show_notes import html_to_plain_text

        self._on_send_show_notes(html_to_plain_text(episode.description))
        self._announce("Sent show notes to a new document")

    def _on_toggle_played(self, episode: PodcastEpisode) -> None:
        episode.played = not episode.played
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

    # ------------------------------------------------------------------
    # Downloads

    def _on_download(self, _event: object) -> None:
        show = self._current_show
        episode = self._selected_episode()
        if show is None or episode is None:
            return
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        enqueue_episode_download(
            self._download_queue,
            self._download_root,
            show,
            episode,
            item_id=self._download_item_id(episode),
        )
        self._announce(f"Downloading {episode.title}")
        self._refresh_selected_episode_row()

    def _on_pause_resume_download(self, _event: object) -> None:
        episode = self._selected_episode()
        if episode is None:
            return
        item_id = self._download_item_id(episode)
        item = self._download_queue.get(item_id)
        if item is None:
            return
        if item.status == "paused":
            self._download_queue.resume_item(item_id)
            self._announce(f"Resuming download of {episode.title}")
        else:
            self._download_queue.pause_item(item_id)
            self._announce(f"Paused download of {episode.title}")
        self._refresh_selected_episode_row()

    def _on_remove_download(self, _event: object) -> None:
        episode = self._selected_episode()
        if episode is None or not episode.downloaded_path:
            return
        path = Path(episode.downloaded_path)
        if path.exists():
            path.unlink(missing_ok=True)
        episode.downloaded_path = ""
        self._on_library_changed()
        self._announce(f"Removed downloaded copy of {episode.title}")
        self._refresh_selected_episode_row()

    def _on_download_all_episodes(self, show: PodcastShow) -> None:
        from quill.ui.podcasts.show_actions import download_all_episodes

        queued = download_all_episodes(
            self._download_queue, self._download_root, show, announce=self._announce
        )
        if queued and show is self._current_show:
            self._fill_episodes(show)

    def _on_remove_all_episodes(self, show: PodcastShow) -> None:
        from quill.ui.podcasts.show_actions import remove_all_episodes_prompt

        removed = remove_all_episodes_prompt(
            self.dialog, self._download_queue, show, announce=self._announce
        )
        if removed:
            self._on_library_changed()
            if show is self._current_show:
                self._fill_episodes(show)

    def on_download_status_changed(self, item: DownloadItem) -> None:
        """Called (off the UI thread) by the mixin's queue callback."""
        self._wx.CallAfter(self._refresh_episode_row_for_item, item)

    def on_download_completed(self, item: DownloadItem) -> None:
        def apply() -> None:
            for show in self._library.shows:
                if show.id != item.show_id:
                    continue
                episode = show.find_episode(item.episode_guid)
                if episode is not None:
                    episode.downloaded_path = str(item.destination)
            self._on_library_changed()
            self._refresh_episode_row_for_item(item)

        self._wx.CallAfter(apply)

    def _refresh_episode_row_for_item(self, item: DownloadItem) -> None:
        for row, episode in enumerate(self._current_episodes):
            if episode.guid == item.episode_guid:
                self._episodes.SetItem(row, 3, self._episode_status_text(episode))
                break

    def _refresh_selected_episode_row(self) -> None:
        episode = self._selected_episode()
        if episode is None:
            return
        index = self._episodes.GetFirstSelected()
        if index >= 0:
            self._episodes.SetItem(index, 3, self._episode_status_text(episode))
        self._on_episode_selected(None)

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
        from quill.ui.dialog_contract import show_message_box

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
