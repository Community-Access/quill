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
        rows = self._selected_rows()
        # Filing is the Inbox's whole job, and triage happens a handful of
        # episodes at a time -- so this is the one bulk action the Inbox
        # actually needed, and the one it did not have. Offered only when
        # something in the selection is routed there, since filing an episode
        # of a show that never reaches the Inbox files it nowhere.
        if any(show.route_to_inbox for _index, show, _episode in rows):
            file_item = menu.Append(wx.ID_ANY, f"F&ile {count} Episodes to Inbox Folder...")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_file_to_inbox(), file_item)
        playlist_item = menu.Append(wx.ID_ANY, f"Add {count} Episodes to Play&list...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_add_to_playlist(), playlist_item)
        if any(episode.downloaded_path for _index, _show, episode in rows):
            remove_item = menu.Append(wx.ID_ANY, f"&Remove {count} Downloaded Copies")
            menu.Bind(wx.EVT_MENU, lambda _e: self._on_bulk_remove_download(), remove_item)
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
        from quill.core.podcasts import retention
        from quill.core.podcasts.position_sync import mark_played

        rows = self._selected_rows()
        changed = 0
        for _index, show, episode in rows:
            if not episode.played:
                mark_played(episode)
                retention.on_episode_played(self._library, show, episode)
                changed += 1
        if not changed:
            self._announce("Those episodes were already played.")
            return
        self._on_library_changed()
        self._refresh_episode_list()
        self._announce(f"Marked {changed} episode(s) as played")

    def _on_bulk_file_to_inbox(self) -> None:
        """File the whole selection into one Inbox folder, chosen once.

        One picker for the selection rather than one per episode: being asked
        the same question forty times is how a bulk action stops being one.
        """
        from quill.core.podcasts import inbox as inbox_ops
        from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

        rows = [
            (show, episode)
            for _index, show, episode in self._selected_rows()
            if show.route_to_inbox
        ]
        if not rows:
            self._announce("None of those podcasts route to the Inbox.")
            return
        picker = FolderPickerDialog(
            self.dialog,
            title=f"File {len(rows)} Episodes to Inbox Folder",
            scope="inbox",
            folders_provider=lambda: list(self._library.inbox_folders),
            create_folder=lambda name, parent_id: inbox_ops.add_inbox_folder(
                self._library, name, parent_folder_id=parent_id
            ),
            rename_folder=lambda folder_id, name: inbox_ops.rename_inbox_folder(
                self._library, folder_id, name
            ),
            delete_folder=lambda folder_id: inbox_ops.delete_inbox_folder(self._library, folder_id),
            top_level_label="Inbox (top level)",
            announce_cb=self._announce,
        )
        result = picker.show()
        if not result.confirmed:
            return
        filed, remembered = inbox_ops.file_episodes(self._library, rows, result.folder_id)
        self._on_library_changed()
        self.refresh_tree()
        message = f"Filed {filed} episode(s)"
        if remembered:
            # Said once per show that gained a default, not once per episode.
            names = ", ".join(sorted(set(remembered)))
            message += f". Future episodes of {names} will file here automatically"
        self._announce(message)

    def _pick_manual_playlist(self, count: int) -> object | None:
        """Ask once which manual playlist the selection goes to.

        Manual playlists only: a Smart Playlist re-asks its own question every
        time it is opened, so adding episodes to one by hand would be putting
        them somewhere the next refresh takes them straight back out of.
        """
        wx = self._wx
        manual = sorted(
            (p for p in self._library.playlists if p.kind == "manual"),
            key=lambda p: p.name.casefold(),
        )
        if not manual:
            self._announce(
                "There are no playlists to add to yet. Make one from a single "
                "episode's Add to Playlist first."
            )
            return None
        with wx.SingleChoiceDialog(  # dialog_button_contract: exempt
            self.dialog,
            f"Add {count} episodes to which playlist?",
            "Add to Playlist",
            [p.name for p in manual],
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return manual[dialog.GetSelection()]

    def _on_bulk_add_to_playlist(self) -> None:
        """Add the selection to one manual playlist, chosen once."""
        from quill.core.podcasts.models import QueueItem

        rows = self._selected_rows()
        playlist = self._pick_manual_playlist(len(rows))
        if playlist is None:
            return
        existing = {(item.show_id, item.episode_guid) for item in playlist.items}
        added = 0
        for _index, show, episode in rows:
            if (show.id, episode.guid) in existing:
                continue
            playlist.items.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
            existing.add((show.id, episode.guid))
            added += 1
        self._on_library_changed()
        skipped = len(rows) - added
        message = f"Added {added} episode(s) to {playlist.name}"
        if skipped:
            message += f"; {skipped} already there"
        self._announce(message)

    def _on_bulk_remove_download(self) -> None:
        """Delete the downloaded copies in the selection, keeping the episodes.

        Never touches an episode that is not downloaded, and never removes the
        episode itself -- freeing space and unsubscribing are very different
        things to want.
        """
        from quill.core.podcasts.retention import remove_downloaded_copy

        removed = sum(
            1 for _index, _show, episode in self._selected_rows() if remove_downloaded_copy(episode)
        )
        if not removed:
            self._announce("None of those had a downloaded copy.")
            return
        self._on_library_changed()
        self._refresh_episode_list()
        self._announce(
            f"Removed {removed} downloaded copy(ies). The episodes are still in your library."
        )

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
        from quill.core.podcasts import retention
        from quill.core.podcasts.position_sync import mark_played
        from quill.ui import undo_last_ui

        library = self._library
        # What each episode was before, so Ctrl+Z restores the marks *and* the
        # positions -- "unplayed" alone would lose where you had got to.
        before = [(e, e.played, e.position_ms, e.downloaded_path) for e in unplayed]
        with undo_last_ui.capturing_deletes() as held:
            for episode in unplayed:
                mark_played(episode)
                # Same rule as finishing one by ear: marking it played is saying
                # you are done with it, however you say it.
                retention.on_episode_played(library, show, episode)

        def _undo() -> None:
            for episode, played, position, path in before:
                episode.played = played
                episode.position_ms = position
                episode.downloaded_path = path
            undo_last_ui.restore(held)
            self._on_library_changed()
            self.refresh_tree()
            self._fill_episodes(self._current_show)

        undo_last_ui.remember(
            "Mark All as Played",
            show.title,
            f"{len(unplayed)} unplayed episode(s)"
            + (f" and {len(held)} downloaded file(s)" if held else ""),
            _undo,
            dispose=lambda: undo_last_ui.discard(held),
        )
        self._on_library_changed()
        self.refresh_tree()
        self._fill_episodes(show if show is self._current_show else self._current_show)
        self._announce(
            undo_last_ui.offer(f"Marked {len(unplayed)} episode(s) of {show.title} as played")
        )

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
            # Says what pausing does *not* do, because "paused" reads as
            # "downloads only" and it is both halves: no feed check either.
            f"Paused updates for {show.title} -- no feed checks and no automatic "
            "downloads; Refresh Feed on this show still works"
            if show.paused
            else f"Resumed updates for {show.title} -- feed checks and automatic "
            "downloads are back on"
        )

    def _on_check_all_feeds(self) -> None:
        """Check every subscribed feed now, paused shows included.

        Refresh Feed on a *show* answers "anything new in this one?". This is
        the other question -- "anything new anywhere?" -- which otherwise had
        no answer short of walking the tree, and which the automatic check
        only answers on a cadence somebody has to have turned on first.

        Forced, so it ignores both the pause on a show and the shared "the
        other app just checked" stamp: a key somebody pressed is not a timer
        firing, and "Quill Radio did that a moment ago" is not an answer.
        """
        monitor = getattr(self._transport_host, "_podcast_check_monitor", None)
        if monitor is None or self._safe_mode:
            self._announce("Subscribed feeds cannot be checked right now.")
            return
        # The count up front, because this is the one verb whose result
        # arrives show by show over the next few seconds: "checking three
        # feeds" tells you when it is finished, where "checking" does not.
        started = monitor.check_now(force=True)
        if not started:
            self._announce("No subscribed feed to check.")
            return
        self._announce(f"Checking {started} feed{'' if started == 1 else 's'}...")
