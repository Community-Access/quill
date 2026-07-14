"""Tools > Media > Podcasts -- menu, commands, hotkeys, status bar, tray.

Follows ``main_frame_radio.py``'s exact pattern: one shared playback
controller (never owned by a dialog), a status bar cell, a tray section, and
commands registered in ``CommandRegistry`` so they show up in the Command
Palette. See PRD §5.84g for the full feature plan; this mixin covers
subscribe, download with pause/resume, nested library folders, OPML,
playback, chapters, sorting, and show notes.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.podcasts import opml as opml_module
from quill.core.podcasts import retention
from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.podcasts.subscriptions import (
    PodcastLibrary,
    load_library,
    merge_episodes,
    save_library,
)
from quill.ui.podcasts.add_podcast_dialog import AddPodcastDialog
from quill.ui.podcasts.manager_dialog import PodcastManagerDialog
from quill.ui.podcasts.player_controller import PodcastPlaybackState, PodcastPlayerController

_SAFE_MODE_MESSAGE = "Podcasts are disabled in Safe Mode. Restart QUILL normally to use them."


class PodcastsMixin:
    """Adds Podcasts to ``MainFrame``."""

    # -- setup ----------------------------------------------------------

    def _init_podcasts(self) -> None:
        self._podcast_library: PodcastLibrary = load_library(app_data_dir())
        self._podcast_manager_dialog: PodcastManagerDialog | None = None
        self._podcast_ever_active = False
        self._podcast_current_chapters: list = []
        self._podcast_chapters_key: tuple[str, str] | None = None
        self._podcast_controller = PodcastPlayerController(
            self.frame,
            on_state_changed=self._on_podcast_state_changed,
            on_episode_finished=self._on_podcast_episode_finished,
        )
        self._podcast_download_queue = PodcastDownloadQueue(
            on_status_changed=self._on_podcast_download_status_changed,
            on_completed=self._on_podcast_download_completed,
        )

    def _podcast_download_root(self) -> Path:
        override = self._podcast_library.settings.download_root
        return Path(override) if override else app_data_dir() / "podcasts"

    def _save_podcast_library(self) -> None:
        save_library(app_data_dir(), self._podcast_library)

    # -- controller callbacks (fire on the UI thread already, per PlayerPanel's
    # / audio engine's own contract of UI-thread callbacks) -----------------

    def _on_podcast_state_changed(self, state: PodcastPlaybackState) -> None:
        self._maybe_surface_podcast_status_cell(bool(state.title))
        self._refresh_statusbar()
        self._refresh_podcast_tray_tooltip()
        self._maybe_reload_podcast_chapters(state)

    def _maybe_reload_podcast_chapters(self, state: PodcastPlaybackState) -> None:
        if not state.show_id or not state.episode_guid:
            self._podcast_current_chapters = []
            self._podcast_chapters_key = None
            return
        key = (state.show_id, state.episode_guid)
        if key == self._podcast_chapters_key:
            return
        self._podcast_chapters_key = key
        self._podcast_current_chapters = []
        show = self._podcast_library.find_show(state.show_id)
        episode = show.find_episode(state.episode_guid) if show is not None else None
        if episode is None or not episode.chapters_url:
            return

        from quill.core.podcasts import chapters as chapters_module

        def _do_fetch(**_kwargs: object):
            return chapters_module.fetch_and_parse_chapters(
                episode.chapters_url, safe_mode=self._safe_mode
            )

        def _on_success(_op: str, result: list) -> None:
            if self._podcast_chapters_key == key:
                self._podcast_current_chapters = result

        self._task_manager.submit(
            "podcast-chapters", _do_fetch, on_success=_on_success, on_failure=lambda *_a: None
        )

    def _maybe_surface_podcast_status_cell(self, active: bool) -> None:
        if not active or self._podcast_ever_active:
            return
        self._podcast_ever_active = True
        from quill.core.settings import save_settings

        hidden = list(getattr(self.settings, "status_bar_hidden", []))
        if "podcast_player" in hidden:
            hidden.remove("podcast_player")
            self.settings.status_bar_hidden = hidden
            save_settings(self.settings)

    def _on_podcast_episode_finished(self, show_id: str, episode_guid: str) -> None:
        show = self._podcast_library.find_show(show_id)
        if show is None:
            return
        episode = show.find_episode(episode_guid)
        if episode is None:
            return
        episode.played = True
        settings = self._podcast_library.effective_settings(show)
        retention.apply_delete_after_play(episode, settings)
        self._save_podcast_library()
        if self._podcast_manager_dialog is not None:
            self._podcast_manager_dialog.refresh_tree()

    # -- download queue callbacks (fire on the download worker thread --
    # everything here must be wx.CallAfter-safe) ----------------------------

    def _on_podcast_download_status_changed(self, item: DownloadItem) -> None:
        self._wx.CallAfter(self._apply_podcast_download_status, item)

    def _on_podcast_download_completed(self, item: DownloadItem) -> None:
        self._wx.CallAfter(self._apply_podcast_download_completed, item)

    def _apply_podcast_download_status(self, item: DownloadItem) -> None:
        self._refresh_statusbar()
        if self._podcast_manager_dialog is not None:
            self._podcast_manager_dialog.on_download_status_changed(item)

    def _apply_podcast_download_completed(self, item: DownloadItem) -> None:
        show = self._podcast_library.find_show(item.show_id)
        if show is not None:
            episode = show.find_episode(item.episode_guid)
            if episode is not None:
                episode.downloaded_path = str(item.destination)
            settings = self._podcast_library.effective_settings(show)
            retention.apply_keep_last_n(show, settings)
        self._save_podcast_library()
        self._refresh_statusbar()
        if self._podcast_manager_dialog is not None:
            self._podcast_manager_dialog.on_download_completed(item)

    def _refresh_podcast_tray_tooltip(self) -> None:
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        wx = self._wx
        text = self._podcast_controller.state.status_text
        radio_controller = getattr(self, "_radio_controller", None)
        radio_text = radio_controller.state.status_text if radio_controller is not None else ""
        parts = [t for t in (radio_text, text) if t and "stopped" not in t.lower()]
        tooltip = "Quill - " + " | ".join(parts) if parts else "Quill"
        try:
            icon = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
            tray_icon.SetIcon(icon, tooltip)
        except Exception:  # noqa: BLE001 - tray tooltip refresh must never crash
            pass

    # -- status bar -----------------------------------------------------

    def _podcast_status_text(self) -> str:
        controller = getattr(self, "_podcast_controller", None)
        queue = getattr(self, "_podcast_download_queue", None)
        if controller is None:
            return ""
        text = controller.state.status_text
        if queue is not None:
            active = queue.active_count()
            if active:
                text += f" ({active} downloading)"
        return text

    def _build_podcast_status_bar_menu(self, menu: object) -> None:
        wx = self._wx
        play_id, stop_id = wx.NewIdRef(), wx.NewIdRef()
        pause_all_id, resume_all_id = wx.NewIdRef(), wx.NewIdRef()
        open_id = wx.NewIdRef()
        menu.Append(play_id, "Play/Pause")
        menu.Append(stop_id, "Stop")
        menu.Bind(wx.EVT_MENU, lambda _e: self.podcast_toggle_play_pause(), id=play_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.podcast_stop(), id=stop_id)
        menu.AppendSeparator()
        menu.Append(pause_all_id, "Pause All Downloads")
        menu.Append(resume_all_id, "Resume All Downloads")
        menu.Bind(wx.EVT_MENU, lambda _e: self._podcast_download_queue.pause_all(), id=pause_all_id)
        menu.Bind(
            wx.EVT_MENU, lambda _e: self._podcast_download_queue.resume_all(), id=resume_all_id
        )
        menu.AppendSeparator()
        menu.Append(open_id, "Open Podcasts...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_manager(), id=open_id)

    # -- system tray ------------------------------------------------------

    def _build_podcast_tray_menu(self, menu: object) -> None:
        wx = self._wx
        now_playing_id = wx.NewIdRef()
        controller = getattr(self, "_podcast_controller", None)
        menu.Append(
            now_playing_id, controller.state.status_text if controller else "Podcasts: stopped"
        )
        menu.Enable(now_playing_id, False)
        self._build_podcast_status_bar_menu(menu)

    # -- commands -----------------------------------------------------------

    def podcast_toggle_play_pause(self) -> None:
        self._podcast_controller.toggle_play_pause()
        self._announce(self._podcast_controller.state.status_text)

    def podcast_stop(self) -> None:
        self._podcast_controller.stop()
        self._announce("Podcasts stopped")

    def podcast_next_chapter(self) -> None:
        from quill.core.podcasts.chapters import next_chapter

        if not self._podcast_current_chapters:
            self._announce("This episode has no chapters.")
            return
        target = next_chapter(
            self._podcast_current_chapters, self._podcast_controller.position_ms()
        )
        if target is None:
            self._announce("Already at the last chapter.")
            return
        self._podcast_controller.seek(target.start_ms)
        self._announce(f"Chapter: {target.title}")

    def podcast_previous_chapter(self) -> None:
        from quill.core.podcasts.chapters import previous_chapter

        if not self._podcast_current_chapters:
            self._announce("This episode has no chapters.")
            return
        target = previous_chapter(
            self._podcast_current_chapters, self._podcast_controller.position_ms()
        )
        if target is None:
            self._announce("Already at the first chapter.")
            return
        self._podcast_controller.seek(target.start_ms)
        self._announce(f"Chapter: {target.title}")

    def podcast_pause_all_downloads(self) -> None:
        self._podcast_download_queue.pause_all()
        self._announce("Paused all podcast downloads")

    def podcast_resume_all_downloads(self) -> None:
        self._podcast_download_queue.resume_all()
        self._announce("Resumed podcast downloads")

    # -- dialogs ------------------------------------------------------------

    def open_podcast_manager(self) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Podcasts", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        dialog = PodcastManagerDialog(
            self.frame,
            library=self._podcast_library,
            download_queue=self._podcast_download_queue,
            controller=self._podcast_controller,
            download_root=self._podcast_download_root(),
            safe_mode=self._safe_mode,
            task_manager=self._task_manager,
            announce_cb=self._announce,
            on_library_changed=self._save_podcast_library,
            on_open_add_podcast=self._podcast_open_add_dialog,
            on_open_import_opml=self._podcast_open_import_opml,
            on_export_opml=self._podcast_export_opml,
            on_refresh_feed=self.refresh_podcast_feed,
            on_open_settings=self._podcast_open_settings,
            on_send_show_notes=self._podcast_send_show_notes_to_editor,
        )
        self._podcast_manager_dialog = dialog
        try:
            dialog.show()
        finally:
            self._podcast_manager_dialog = None
        self._refresh_statusbar()

    def _podcast_send_show_notes_to_editor(self, plain_text: str) -> None:
        self._power_tools_open_text_in_new_buffer(plain_text, "Opened podcast show notes")

    def _podcast_open_settings(self) -> None:
        from quill.ui.podcasts.podcast_settings_dialog import PodcastSettingsDialog

        dialog = PodcastSettingsDialog(
            self.frame, settings=self._podcast_library.settings, announce_cb=self._announce
        )
        updated = dialog.show()
        if updated is None:
            return
        self._podcast_library.settings = updated
        self._save_podcast_library()
        self._announce("Podcast settings saved")

    def _podcast_open_add_dialog(self) -> None:
        dialog = AddPodcastDialog(
            self.frame,
            library=self._podcast_library,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_library_changed=self._save_podcast_library,
        )
        dialog.show()

    def _podcast_open_import_opml(self) -> None:
        # AddPodcastDialog already offers Import OPML...; reuse the same
        # dialog so there is one place that owns the file picker + parsing.
        self._podcast_open_add_dialog()

    def _podcast_export_opml(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Export OPML",
            wildcard="OPML files (*.opml)|*.opml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        text = opml_module.export_opml(self._podcast_library)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as error:
            self._set_status(f"Could not export OPML: {error}")
            return
        self._announce("Exported OPML")

    # -- feed refresh (Phase 1: manual only; auto-refresh is a Phase 2+ item) --

    def refresh_podcast_feed(self, show_id: str) -> None:
        from quill.core.podcasts import feed_reader

        show = self._podcast_library.find_show(show_id)
        if show is None or not show.feed_url or show.paused or self._safe_mode:
            return

        def _do_refresh(**_kwargs: object) -> feed_reader.FeedInfo:
            return feed_reader.fetch_and_parse_feed(show.feed_url, safe_mode=self._safe_mode)

        def _on_success(_op: str, info: feed_reader.FeedInfo) -> None:
            new_count = merge_episodes(show, info.episodes)
            self._save_podcast_library()
            if self._podcast_manager_dialog is not None:
                self._podcast_manager_dialog.refresh_tree()
            if new_count:
                self._announce(f"{new_count} new episode(s) for {show.title}")

        self._task_manager.submit(
            "podcast-refresh", _do_refresh, on_success=_on_success, on_failure=lambda *_a: None
        )

    # -- command palette registration ----------------------------------------

    def _register_podcasts_commands(self) -> None:
        for command_id, title, handler in (
            ("podcasts.open_manager", "Podcasts: Open Manager...", self.open_podcast_manager),
            (
                "podcasts.add",
                "Podcasts: Add Podcast...",
                self._podcast_open_add_dialog,
            ),
            (
                "podcasts.import_opml",
                "Podcasts: Import OPML...",
                self._podcast_open_import_opml,
            ),
            ("podcasts.export_opml", "Podcasts: Export OPML...", self._podcast_export_opml),
            ("podcasts.play_pause", "Podcasts: Play/Pause", self.podcast_toggle_play_pause),
            ("podcasts.stop", "Podcasts: Stop", self.podcast_stop),
            (
                "podcasts.pause_all_downloads",
                "Podcasts: Pause All Downloads",
                self.podcast_pause_all_downloads,
            ),
            (
                "podcasts.resume_all_downloads",
                "Podcasts: Resume All Downloads",
                self.podcast_resume_all_downloads,
            ),
            ("podcasts.settings", "Podcasts: Podcast Settings...", self._podcast_open_settings),
            ("podcasts.next_chapter", "Podcasts: Next Chapter", self.podcast_next_chapter),
            (
                "podcasts.previous_chapter",
                "Podcasts: Previous Chapter",
                self.podcast_previous_chapter,
            ),
        ):
            self.commands.try_register(
                command_id,
                title,
                handler,
                self._binding_for(command_id),
                feature_id="core.podcasts",
            )
