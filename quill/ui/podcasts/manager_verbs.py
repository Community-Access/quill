"""The verbs on an episode or a podcast, shared by the Podcast Manager and Cast's one window.

Extracted from ``manager_dialog.py`` and ``manager_phase4.py`` on 2026-10-02
(qc.md Phase 2): QUILL's Podcast Manager and QUILL Cast's main window both act
on the same rows with the same words, and a verb written twice is a sentence
that drifts. Everything here speaks to the Manager-shaped surface -- ``_library``,
``_controller``, ``_download_queue``, ``_announce``, ``_on_library_changed``,
``refresh_tree``, ``_fill_episodes`` -- which the Manager has natively and
Cast's frame answers through :mod:`quill.ui.podcasts.episode_list`.

Two hooks let one body serve two windows: :meth:`_verb_parent` is the window
the verbs' own dialogs open over (the Manager's dialog, Cast's frame), and
:meth:`_verb_selected_episode` is the selected row's episode, which the two
hosts name differently.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import position_sync
from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastShow

__all__ = ["ManagerVerbsMixin"]


class ManagerVerbsMixin:
    """Per-episode and per-podcast verbs, on both hosts."""

    def _verb_parent(self) -> Any:
        return getattr(self, "dialog", None) or getattr(self, "frame", None)

    def _verb_selected_episode(self) -> PodcastEpisode | None:
        selected = getattr(self, "_selected_episode", None)
        return selected() if callable(selected) else None

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
            self._verb_parent(), "New name:", title, value=current
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

    def _on_chapters_click(self, _event: object) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.open_chapters(self, self._current_show, self._verb_selected_episode())

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
            self._verb_parent(),
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
        self._announce("Marked as played" if episode.played else "Marked as unheard")

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

    def _on_copy_show_link(self, show: PodcastShow) -> None:
        from quill.ui.podcasts.share_actions import copy_show_link

        copy_show_link(show, announce=self._announce)

    def _on_show_episode_in_explorer(self, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.share_actions import reveal_episode_in_file_manager

        reveal_episode_in_file_manager(episode, announce=self._announce)

    def _on_save_episode_audio_as(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.export_audio import export_episode_audio

        export_episode_audio(
            self._verb_parent(),
            self._download_queue,
            self._download_root,
            show,
            episode,
            announce=self._announce,
            wx=self._wx,
            # However it ended: the download changed the row, and a wait that
            # finished can be several minutes after the click.
            on_finished=self._refresh_selected_episode_row,
        )

    def _on_copy_episode_path(self, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.export_audio import copy_episode_path

        copy_episode_path(episode, announce=self._announce, wx=self._wx)

    def _append_transcript_items(
        self, menu: object, show: PodcastShow, episode: PodcastEpisode
    ) -> None:
        """The per-episode items that come and go with the episode's own feed
        metadata: About This Episode..., and the transcript trio.

        Not Quick Actions: they appear and disappear with the episode's own
        metadata, and an orderable list whose entries vanish per row is a
        list whose order means nothing.
        """
        wx = self._wx
        # About This Episode... appears for any episode whose feed published
        # Podcasting 2.0 details, which is independent of whether it published a
        # transcript -- so it is decided on its own, before the early return.
        from quill.ui.podcasts.extras_command import has_extras, open_episode_extras

        if has_extras(show, episode):
            about_item = menu.Append(wx.ID_ANY, "&About This Episode...")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e: open_episode_extras(self, show, episode),
                about_item,
            )
        if not episode.transcript_url:
            return
        save_tr_item = menu.Append(wx.ID_ANY, "Save &Transcript As...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_save_transcript(show, episode), save_tr_item)
        read_tr_item = menu.Append(wx.ID_ANY, "&Read Transcript...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_read_transcript(show, episode), read_tr_item)
        open_tr_item = menu.Append(wx.ID_ANY, "Open Transcript in &Editor")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_open_transcript(show, episode), open_tr_item)

    def _queue_and_announce(self, action: object, message: str) -> None:
        action()
        self._on_library_changed()
        self._announce(message)

    def _on_toggle_favorite(self, show: PodcastShow) -> None:
        show.is_favorite = not show.is_favorite
        self._on_library_changed()
        self.refresh_tree()
        self._announce(
            f"Added {show.title} to Favorites"
            if show.is_favorite
            else f"Removed {show.title} from Favorites"
        )

    def _on_toggle_route_to_inbox(self, show: PodcastShow) -> None:
        """Flip this show's Inbox mark, and say what the mark now *means*.

        Under opt-out the same flag reads as "keep this one out", so the
        announcement has to change with the mode -- saying "will appear in the
        Inbox" while excluding it would be a confident wrong answer.
        """
        from quill.core.podcasts.inbox import in_inbox

        show.route_to_inbox = not show.route_to_inbox
        self._on_library_changed()
        self.refresh_tree()
        inside = in_inbox(self._library, show)
        self._announce(
            f"New {show.title} episodes will appear in the Inbox"
            if inside
            else f"{show.title} is kept out of the Inbox"
        )

    def _on_forget_inbox_folder(self, show: PodcastShow) -> None:
        from quill.core.podcasts.inbox import forget_remembered_folder

        forget_remembered_folder(show)
        self._on_library_changed()
        self._announce(f"{show.title} episodes now file manually; no remembered folder")

    def _on_file_to_inbox_folder(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.core.podcasts import inbox as inbox_ops
        from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

        picker = FolderPickerDialog(
            self._verb_parent(),
            title=f"File {episode.title} to Inbox Folder",
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
        remembered = inbox_ops.file_episode(self._library, show, episode, result.folder_id)
        self._on_library_changed()
        self.refresh_tree()
        if remembered:
            self._announce(
                f"Filed {episode.title}. Future {show.title} episodes will file here "
                "automatically; use Forget Remembered Inbox Folder to revert."
            )
        else:
            self._announce(f"Filed {episode.title}")

    def _on_add_to_playlist(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.core.podcasts.models import Playlist, QueueItem
        from quill.core.podcasts.playlists import new_playlist_id

        wx = self._wx
        manual = sorted(
            (p for p in self._library.playlists if p.kind == "manual"),
            key=lambda p: p.name.casefold(),
        )
        choices = [*[p.name for p in manual], "New Playlist..."]
        with wx.SingleChoiceDialog(  # dialog_button_contract: exempt
            self._verb_parent(),
            f"Add {episode.title} to which playlist?",
            "Add to Playlist",
            choices,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            index = picker.GetSelection()
        if index == len(manual):
            name = self._prompt_playlist_name("New Playlist")
            if name is None:
                return
            playlist = Playlist(id=new_playlist_id(), name=name, kind="manual")
            self._library.add_playlist(playlist)
        else:
            playlist = manual[index]
        if any(
            item.show_id == show.id and item.episode_guid == episode.guid for item in playlist.items
        ):
            self._announce(f"{episode.title} is already in {playlist.name}")
            return
        playlist.items.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Added {episode.title} to {playlist.name}")

    def _prompt_playlist_name(self, title: str, *, initial: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self._verb_parent(), "Playlist name:", title, initial
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            name = dialog.GetValue().strip()
        return name or None

    def _on_new_smart_playlist(self) -> None:
        from quill.core.podcasts.models import Playlist, PlaylistRules
        from quill.core.podcasts.playlists import new_playlist_id
        from quill.ui.podcasts.playlist_rules_dialog import PlaylistRulesDialog

        name = self._prompt_playlist_name("New Smart Playlist")
        if name is None:
            return
        dialog = PlaylistRulesDialog(
            self._verb_parent(),
            shows=list(self._library.shows),
            rules=PlaylistRules(),
            announce_cb=self._announce,
            # For the live "matches N episodes right now" count.
            library=self._library,
        )
        rules = dialog.show()
        if rules is None:
            return
        self._library.add_playlist(
            Playlist(id=new_playlist_id(), name=name, kind="smart", rules=rules)
        )
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Created Smart Playlist {name}")

    def _on_new_manual_playlist(self) -> None:
        from quill.core.podcasts.models import Playlist
        from quill.core.podcasts.playlists import new_playlist_id

        name = self._prompt_playlist_name("New Playlist")
        if name is None:
            return
        self._library.add_playlist(Playlist(id=new_playlist_id(), name=name, kind="manual"))
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Created playlist {name}")

    def _on_edit_playlist_rules(self, playlist: Playlist) -> None:
        from quill.ui.podcasts.playlist_rules_dialog import PlaylistRulesDialog

        dialog = PlaylistRulesDialog(
            self._verb_parent(),
            shows=list(self._library.shows),
            rules=playlist.rules,
            announce_cb=self._announce,
            library=self._library,
        )
        rules = dialog.show()
        if rules is None:
            return
        playlist.rules = rules
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Updated rules for {playlist.name}")

    def _on_rename_playlist(self, playlist: Playlist) -> None:
        name = self._prompt_playlist_name("Rename Playlist", initial=playlist.name)
        if name is None:
            return
        self._library.rename_playlist(playlist.id, name)
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Renamed playlist to {name}")

    def _on_delete_playlist(self, playlist: Playlist) -> None:
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        confirm = show_message_box(
            f'Delete the playlist "{playlist.name}"? Its episodes stay in your library either way.',
            "Delete Playlist",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self._verb_parent(),
            announce=self._announce,
        )
        if confirm != wx.YES:
            return
        self._library.remove_playlist(playlist.id)
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Deleted playlist {playlist.name}")

    def _on_episode_notes(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        """Wiring only -- shared with the player's route (item 11)."""
        from quill.ui.podcasts import episode_notes_commands

        episode_notes_commands.open_for_episode(self, show, episode)

    def add_note_for_playing_episode(self, text: str) -> bool:
        """Timestamped note on the playing episode (the mixin/command path)."""
        from quill.core.podcasts.episode_notes import add_episode_note

        state = self._controller.state
        if not state.show_id or not state.episode_guid:
            return False
        add_episode_note(
            show_id=state.show_id,
            episode_guid=state.episode_guid,
            position_ms=self._controller.position_ms(),
            text=text,
        )
        return True

    def _on_read_transcript(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        """Open the transcript in the shared reader, with its timings."""
        from quill.ui.podcasts import transcript_actions

        transcript_actions.read_transcript(self, show, episode)

    def _on_save_transcript(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.save_transcript(self, show, episode)

    def _on_open_transcript(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.open_in_editor(self, show, episode)

    def _fetch_transcript_then(
        self, show: PodcastShow, episode: PodcastEpisode, consume: object
    ) -> None:
        from quill.ui.podcasts import transcript_actions

        transcript_actions.fetch_then(self, show, episode, consume)
