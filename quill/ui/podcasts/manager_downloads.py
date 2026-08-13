"""The Podcast Manager's download controls.

Split out of ``manager_dialog.py`` under GATE-11: enqueue, pause/resume,
remove, the two whole-show bulk actions, and the two callbacks the download
queue fires from its worker thread.

Both queue callbacks arrive **off the UI thread** and marshal through
``wx.CallAfter`` before touching a control -- the reason they are methods on
the dialog at all rather than closures at the call site.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.download_queue import DownloadItem
from quill.core.podcasts.models import PodcastShow


class ManagerDownloadsMixin:
    """Download actions and queue callbacks for the Podcast Manager."""

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
