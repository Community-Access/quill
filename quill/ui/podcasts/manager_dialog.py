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

from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.podcasts.player_controller import PodcastPlayerController

_FOLDER_ROOT_LABEL = "All Podcasts"
_SPEED_CHOICES = ("0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x")


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "show"


def episode_destination(download_root: Path, show: PodcastShow, episode: PodcastEpisode) -> Path:
    """Where a downloaded episode's file lands: ``<root>/<show-slug>/<episode-slug><ext>``."""
    suffix = Path(episode.audio_url.split("?", 1)[0]).suffix or ".mp3"
    return download_root / _slug(show.title) / f"{_slug(episode.title)}{suffix}"


class PodcastManagerDialog:
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
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
        on_open_add_podcast: Callable[[], None] | None = None,
        on_open_import_opml: Callable[[], None] | None = None,
        on_export_opml: Callable[[], None] | None = None,
        on_refresh_feed: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._download_queue = download_queue
        self._controller = controller
        self._download_root = download_root
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_open_add_podcast = on_open_add_podcast
        self._on_open_import_opml = on_open_import_opml
        self._on_export_opml = on_export_opml
        self._refresh_feed_cb = on_refresh_feed

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

        body = wx.BoxSizer(wx.HORIZONTAL)

        tree_col = wx.BoxSizer(wx.VERTICAL)
        tree_col.Add(wx.StaticText(self.dialog, label="&Folders and Podcasts"), 0, wx.BOTTOM, 4)
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
        self._download_btn = wx.Button(self.dialog, label="&Download")
        self._download_btn.SetName("Download the selected episode")
        self._download_btn.Enable(False)
        self._pause_btn = wx.Button(self.dialog, label="&Pause Download")
        self._pause_btn.SetName("Pause or resume this episode's download")
        self._pause_btn.Enable(False)
        self._remove_download_btn = wx.Button(self.dialog, label="&Remove Download")
        self._remove_download_btn.Enable(False)
        unsubscribe_btn = wx.Button(self.dialog, label="&Unsubscribe")
        unsubscribe_btn.SetName("Unsubscribe from the selected show (Delete key also works)")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        for widget in (
            add_podcast_btn,
            new_folder_btn,
            import_opml_btn,
            export_opml_btn,
            self._download_btn,
            self._pause_btn,
            self._remove_download_btn,
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
        self._download_btn.Bind(wx.EVT_BUTTON, self._on_download)
        self._pause_btn.Bind(wx.EVT_BUTTON, self._on_pause_resume_download)
        self._remove_download_btn.Bind(wx.EVT_BUTTON, self._on_remove_download)
        unsubscribe_btn.Bind(wx.EVT_BUTTON, self._on_unsubscribe)
        self._play_pause_btn.Bind(wx.EVT_BUTTON, self._on_play_pause)
        self._stop_btn.Bind(wx.EVT_BUTTON, self._on_stop)
        self._speed_choice.Bind(wx.EVT_CHOICE, self._on_speed_choice)

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

    def refresh_tree(self) -> None:
        self._tree.DeleteAllItems()
        self._tree_item_show.clear()
        self._tree_item_folder.clear()
        root = self._tree.AddRoot(_FOLDER_ROOT_LABEL)

        def add_folder_children(parent_item: object, folder_id: str | None) -> None:
            for folder in self._library.folders:
                if folder.parent_folder_id != folder_id:
                    continue
                item = self._tree.AppendItem(parent_item, folder.name)
                self._tree_item_folder[item.GetID() if hasattr(item, "GetID") else id(item)] = (
                    folder.id
                )
                add_folder_children(item, folder.id)
                add_shows(item, folder.id)
            add_shows(parent_item, folder_id)

        def add_shows(parent_item: object, folder_id: str | None) -> None:
            for show in self._library.shows:
                if show.folder_id != folder_id:
                    continue
                item = self._tree.AppendItem(parent_item, show.title)
                self._tree_item_show[item.GetID() if hasattr(item, "GetID") else id(item)] = show.id

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
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        return self._tree_item_show.get(key)

    def _selected_folder_id(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        return self._tree_item_folder.get(key)

    def _on_tree_selection(self, _event: object) -> None:
        show_id = self._selected_show_id()
        show = self._library.find_show(show_id) if show_id else None
        self._current_show = show
        self._fill_episodes(show)
        self._sync_speed_choice()

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
        base = self._library.effective_settings(show)
        show.settings = PodcastSettings(
            playback_mode=base.playback_mode,
            retention=base.retention,
            retention_count=base.retention_count,
            speed=speed,
            download_root=base.download_root,
        )
        self._on_library_changed()
        if self._controller.state.show_id == show.id:
            self._controller.set_rate(speed)
        self._announce(f"Playback speed set to {speed:g}x for {show.title}")

    def _on_tree_key_down(self, event: object) -> None:
        if event.GetKeyCode() == self._wx.WXK_DELETE:
            self._on_unsubscribe(event)
            return
        event.Skip()

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

            menu.AppendSeparator()
            unsubscribe_item = menu.Append(wx.ID_ANY, "&Unsubscribe")
            menu.Bind(wx.EVT_MENU, self._on_unsubscribe, unsubscribe_item)
        else:
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
        self._current_episodes = list(show.episodes) if show is not None else []
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

    def _on_episode_activate(self, _event: object) -> None:
        self._play_selected()

    def _play_selected(self) -> None:
        show = self._current_show
        episode = self._selected_episode()
        if show is None or episode is None:
            return
        source = episode.downloaded_path or episode.audio_url
        if not source:
            return
        self._controller.play_episode(
            show_id=show.id,
            episode_guid=episode.guid,
            title=episode.title,
            source=source,
            resume_ms=episode.position_ms,
            rate=self._library.effective_settings(show).speed,
        )
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

        self._episodes.PopupMenu(menu)
        menu.Destroy()

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
        destination = episode_destination(self._download_root, show, episode)
        self._download_queue.enqueue(
            self._download_item_id(episode),
            show_id=show.id,
            episode_guid=episode.guid,
            url=episode.audio_url,
            destination=destination,
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

    def _on_unsubscribe(self, _event: object) -> None:
        show_id = self._selected_show_id()
        show = self._library.find_show(show_id) if show_id else None
        if show is None:
            return
        wx = self._wx
        from quill.ui.dialog_contract import show_message_box

        confirmed = (
            show_message_box(
                f"Unsubscribe from {show.title}? Downloaded episodes are not deleted.",
                "Unsubscribe",
                wx.YES_NO | wx.ICON_QUESTION,
                self.dialog,
                announce=self._announce,
            )
            == wx.YES
        )
        if not confirmed:
            return
        self._library.remove_show(show.id)
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Unsubscribed from {show.title}")
