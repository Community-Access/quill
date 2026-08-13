"""Bulk and per-show actions for the Podcast Manager (1.1.0).

Two groups of handlers that grew out of ``manager_dialog.py`` and are better
read on their own:

**Bulk actions.** The episode list has always allowed a multiple selection --
it is a plain report-mode ``wx.ListCtrl`` -- but nothing ever read past the
first row, so selecting forty episodes and choosing Add to Queue queued
exactly one. :meth:`_selected_rows` is what the bulk actions read, and they
appear in the context menu only when more than one row is selected, so an
ordinary right-click is not padded with "1 episode" variants.

**Per-show actions.** Play next unplayed, the Auto-Queue and announcement
toggles, Mark All as Played, feed credentials, and the per-podcast settings
dialog. These are the actions the Quick Actions table
(``manager_menus.show_actions``) dispatches to; keeping them beside each other
means the table and its handlers can be read together.

Mixed into ``PodcastManagerDialog``; touches only attributes that class owns.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.sorting import sort_episodes
from quill.ui.dialog_contract import show_message_box


class ManagerActionsMixin:
    """Multi-selection bulk actions and the 1.1.0 per-show actions."""

    def _selected_rows(self) -> list[tuple[int, PodcastShow, PodcastEpisode]]:
        """Every selected row as ``(index, show, episode)``, in list order.

        The episode list has always allowed a multiple selection -- it is a
        plain report-mode ListCtrl -- but nothing ever read more than the
        first row, so selecting forty episodes and choosing Add to Queue
        queued exactly one. This is what the bulk actions read.
        """
        rows: list[tuple[int, PodcastShow, PodcastEpisode]] = []
        index = self._episodes.GetFirstSelected()
        while index != -1:
            if 0 <= index < len(self._current_episodes):
                show = self._show_for_selected_episode(index)
                if show is not None:
                    rows.append((index, show, self._current_episodes[index]))
            index = self._episodes.GetNextSelected(index)
        return rows

    def _append_bulk_episode_items(self, menu: object, count: int) -> None:
        """Actions that act on the whole selection, above the single-episode
        ones. Only present when more than one row is selected, so a normal
        right-click menu is not padded with "1 episode" variants."""
        wx = self._wx
        queue_item = menu.Append(wx.ID_ANY, f"Add {count} Episodes to &Queue")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_queue(), queue_item)
        download_item = menu.Append(wx.ID_ANY, f"&Download {count} Episodes")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_download(), download_item)
        played_item = menu.Append(wx.ID_ANY, f"Mark {count} Episodes as &Played")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_mark_played(), played_item)
        menu.AppendSeparator()

    def _on_bulk_queue(self) -> None:
        from quill.core.podcasts import queue as queue_ops

        rows = self._selected_rows()
        added = sum(
            1
            for _index, show, episode in rows
            if queue_ops.add_to_queue(self._library, show.id, episode.guid)
        )
        self._on_library_changed()
        skipped = len(rows) - added
        message = f"Added {added} episode(s) to the Play Queue"
        if skipped:
            message += f"; {skipped} already queued"
        self._announce(message)

    def _on_bulk_download(self) -> None:
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        queued = 0
        for _index, show, episode in self._selected_rows():
            if episode.downloaded_path:
                continue
            item_id = self._download_item_id(episode)
            if self._download_queue.get(item_id) is not None:
                continue
            enqueue_episode_download(
                self._download_queue, self._download_root, show, episode, item_id=item_id
            )
            queued += 1
        self._announce(
            f"Downloading {queued} episode(s)"
            if queued
            else "Nothing to download: all of those are already downloaded or in progress"
        )
        self._fill_episodes(self._current_show)

    def _on_bulk_mark_played(self) -> None:
        rows = self._selected_rows()
        changed = 0
        for _index, _show, episode in rows:
            if not episode.played:
                episode.played = True
                episode.position_ms = 0
                changed += 1
        if not changed:
            self._announce("Those episodes were already played.")
            return
        self._on_library_changed()
        self._refresh_episode_list()
        self._announce(f"Marked {changed} episode(s) as played")

    # -- per-show actions ------------------------------------------------

    def _play_next_unplayed(self, show: PodcastShow) -> None:
        """The show's next unplayed episode, or its most recent if all played."""
        ordered = sort_episodes(show.episodes, "unplayed_first")
        if not ordered:
            self._announce(f"{show.title} has no episodes yet.")
            return
        episode = ordered[0]
        self._play_episode(show, episode, resume_ms=episode.position_ms)

    def _on_toggle_auto_queue(self, show: PodcastShow) -> None:
        show.auto_queue = not show.auto_queue
        self._on_library_changed()
        self._announce(
            f"New {show.title} episodes will go straight to the Play Queue"
            if show.auto_queue
            else f"{show.title} no longer auto-queues"
        )

    def _on_toggle_notify(self, show: PodcastShow) -> None:
        show.notify_new_episodes = not show.notify_new_episodes
        self._on_library_changed()
        self._announce(
            f"QUILL Cast will announce new {show.title} episodes by name"
            if show.notify_new_episodes
            else f"{show.title} new episodes will not be announced separately"
        )

    def _on_mark_all_played(self, show: PodcastShow) -> None:
        wx = self._wx
        unplayed = [e for e in show.episodes if not e.played]
        if not unplayed:
            self._announce(f"Every episode of {show.title} is already played.")
            return
        answer = show_message_box(
            f"Mark all {len(unplayed)} unplayed episode(s) of {show.title} as played? "
            "They stay in your library; downloaded files are not deleted.",
            "Mark All as Played",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        for episode in unplayed:
            episode.played = True
            episode.position_ms = 0
        self._on_library_changed()
        self.refresh_tree()
        self._fill_episodes(show if show is self._current_show else self._current_show)
        self._announce(f"Marked {len(unplayed)} episode(s) of {show.title} as played")

    def _on_feed_credentials(self, show: PodcastShow) -> None:
        from quill.ui.podcasts.show_actions import feed_credentials_prompt

        if feed_credentials_prompt(self.dialog, self._library, show, announce=self._announce):
            self._on_library_changed()

    def _on_show_settings(self, show: PodcastShow) -> None:
        """Per-show overrides: auto-download, queue expiry, Inbox caps, and
        the rest -- the settings that only make sense one podcast at a time."""
        from quill.ui.podcasts.show_settings_dialog import ShowSettingsDialog

        dialog = ShowSettingsDialog(
            self.dialog,
            library=self._library,
            show=show,
            announce_cb=self._announce,
        )
        if dialog.show():
            self._on_library_changed()
            self.refresh_tree()

    def _on_toggle_show_paused(self, show: PodcastShow) -> None:
        show.paused = not show.paused
        self._on_library_changed()
        self._announce(
            f"Paused downloads for {show.title}"
            if show.paused
            else f"Resumed downloads for {show.title}"
        )
