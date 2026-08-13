"""Phase 4 surfaces for the Podcast Manager (mixin on PodcastManagerDialog).

Everything docs/planning/podcasts.md's remaining-work list adds to the
manager, kept out of manager_dialog.py per its own CQ-1 decomposition note:

- the pinned virtual-view nodes (Favorites / New Episodes / Continue
  Listening / Inbox) at the top of the folder tree;
- the filter row (episode + show filters, Search Everywhere, Play Queue,
  volume boost);
- the Play Queue dialog (accessible reordering: nudge + mark-and-move);
- episode context-menu additions (Play Next / Add to Queue, Episode
  Notes..., transcripts, File to Inbox Folder..., Rename);
- show context-menu additions (Favorite, Route to Inbox).

The mixin only touches attributes PodcastManagerDialog owns; every new
control carries an accessible name.
"""

from __future__ import annotations

from quill.core.podcasts.filtering import (
    filter_episodes,
    filter_shows,
    search_everywhere,
)
from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastShow
from quill.core.podcasts.virtual_views import virtual_view_pairs
from quill.ui.podcasts.manager_expired import ManagerExpiredMixin

_EPISODE_FILTER_LABELS = (
    "All",
    "Unplayed",
    "In progress",
    "Played",
    "Downloaded",
    "Not downloaded",
)
_EPISODE_FILTER_MODES = (
    "all",
    "unplayed",
    "in_progress",
    "played",
    "downloaded",
    "not_downloaded",
)
_SHOW_FILTER_LABELS = ("All shows", "Favorites only", "Has unplayed")
_SHOW_FILTER_MODES = ("all", "favorites_only", "has_unplayed")
_BOOST_LABELS = ("Boost off", "1.5x boost", "2x boost", "3x boost")
_BOOST_FACTORS = (1.0, 1.5, 2.0, 3.0)

#: (view_id, tree label) for the pinned nodes, in pinned order.
_PINNED_VIEWS = (
    ("favorites", "Favorites"),
    ("new_episodes", "New Episodes"),
    ("continue_listening", "Continue Listening"),
    ("inbox", "Inbox"),
    ("recently_expired", "Recently Expired"),
)

#: How many rows a cross-show view fills at once.
#:
#: New Episodes over a 1,300-show library is around 196,000 unplayed
#: episodes, and inserting 196,000 rows into a wx.ListCtrl one at a time
#: takes minutes and produces a list nobody can navigate. The newest are what
#: the view is for; the filters, the sort order, and the show's own node
#: reach everything else.
#:
#: Never a silent truncation: the status line always says how many were
#: shown out of how many there are, and what to do about it.
_MAX_CROSS_SHOW_ROWS = 1000


class ManagerPhase4Mixin(ManagerExpiredMixin):
    """Phase 4 wiring; mixed into PodcastManagerDialog."""

    # -- filter row -----------------------------------------------------------

    def _build_phase4_row(self, parent_sizer: object) -> None:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._episode_filter_choice = wx.Choice(self.dialog, choices=list(_EPISODE_FILTER_LABELS))
        self._episode_filter_choice.SetName("Filter episodes by state")
        self._episode_filter_choice.SetSelection(0)
        self._show_filter_choice = wx.Choice(self.dialog, choices=list(_SHOW_FILTER_LABELS))
        self._show_filter_choice.SetName("Filter shows in the folder tree")
        self._show_filter_choice.SetSelection(0)
        self._boost_choice = wx.Choice(self.dialog, choices=list(_BOOST_LABELS))
        self._boost_choice.SetName("Volume boost for quiet audio; playback gain only")
        self._boost_choice.SetSelection(0)
        search_btn = wx.Button(self.dialog, label="Search &Everywhere...")
        queue_btn = wx.Button(self.dialog, label="Play &Queue...")
        row.Add(wx.StaticText(self.dialog, label="Ep&isodes:"), 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self._episode_filter_choice, 0, wx.LEFT | wx.RIGHT, 4)
        row.Add(wx.StaticText(self.dialog, label="S&hows:"), 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self._show_filter_choice, 0, wx.LEFT | wx.RIGHT, 4)
        row.Add(self._boost_choice, 0, wx.RIGHT, 4)
        row.Add(search_btn, 0, wx.RIGHT, 4)
        row.Add(queue_btn, 0)
        parent_sizer.Add(row, 0, wx.EXPAND | wx.BOTTOM, 6)
        self._episode_filter_choice.Bind(
            wx.EVT_CHOICE, lambda _e: self._fill_episodes(self._current_show)
        )
        self._show_filter_choice.Bind(wx.EVT_CHOICE, lambda _e: self.refresh_tree())
        self._boost_choice.Bind(wx.EVT_CHOICE, self._on_boost_choice)
        search_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_search_everywhere())
        queue_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_open_play_queue())

    def _selected_episode_filter(self) -> str:
        choice = getattr(self, "_episode_filter_choice", None)
        if choice is None:
            return "all"
        index = choice.GetSelection()
        return _EPISODE_FILTER_MODES[index] if index >= 0 else "all"

    def _selected_show_filter(self) -> str:
        choice = getattr(self, "_show_filter_choice", None)
        if choice is None:
            return "all"
        index = choice.GetSelection()
        return _SHOW_FILTER_MODES[index] if index >= 0 else "all"

    def _apply_episode_filter(self, episodes: list[PodcastEpisode]) -> list[PodcastEpisode]:
        return filter_episodes(episodes, self._selected_episode_filter())

    def _apply_show_filter(self, shows: list[PodcastShow]) -> list[PodcastShow]:
        return filter_shows(shows, self._selected_show_filter())

    def _on_boost_choice(self, _event: object) -> None:
        index = max(0, self._boost_choice.GetSelection())
        factor = _BOOST_FACTORS[index]
        self._controller.set_volume_boost(factor)
        self._announce(
            "Volume boost off" if factor == 1.0 else f"Volume boost {factor:g}x for quiet audio"
        )

    # -- pinned virtual views ---------------------------------------------------

    def _add_virtual_view_nodes(self, root: object) -> None:
        """Called by refresh_tree right after the root is created, so the
        pinned views sit above every folder."""
        self._tree_item_virtual: dict[int, str] = {}
        self._tree_item_inbox_folder: dict[int, str] = {}
        #: Folders view mode only: synthetic per-podcast child nodes under a
        #: pinned view, auto-generated at every refresh (never persisted,
        #: never manually edited) -- key -> (view_id, show_id).
        self._tree_item_virtual_show: dict[int, tuple[str, str]] = {}
        for view_id, label in _PINNED_VIEWS:
            count = len(self._virtual_pairs(view_id))
            text = f"{label} ({count})" if count else label
            item = self._tree.AppendItem(root, text)
            key = item.GetID() if hasattr(item, "GetID") else id(item)
            self._tree_item_virtual[key] = view_id
            if view_id == "inbox":
                self._add_inbox_folder_children(item, None)
            if self._library.settings.episode_list_view_mode == "folders":
                self._add_virtual_view_show_children(item, view_id)
        self._add_playlist_nodes(root)

    # -- saved playlists (Phase 5) ----------------------------------------------

    def _add_playlist_nodes(self, root: object) -> None:
        """Playlists sit below the pinned views: one "Playlists" parent
        (its own context menu offers New Smart Playlist.../New
        Playlist...), one child per saved playlist -- Smart or manual
        alike, each showing its currently resolved episode count."""
        from quill.core.podcasts.playlists import resolve_playlist

        self._tree_item_playlists_root: int | None = None
        self._tree_item_playlist: dict[int, str] = {}
        parent = self._tree.AppendItem(root, "Playlists")
        parent_key = parent.GetID() if hasattr(parent, "GetID") else id(parent)
        self._tree_item_playlists_root = parent_key
        for playlist in sorted(self._library.playlists, key=lambda p: p.name.casefold()):
            count = len(resolve_playlist(self._library, playlist))
            kind_suffix = " (Smart)" if playlist.kind == "smart" else ""
            item = self._tree.AppendItem(parent, f"{playlist.name}{kind_suffix} ({count})")
            key = item.GetID() if hasattr(item, "GetID") else id(item)
            self._tree_item_playlist[key] = playlist.id

    def _selected_playlists_root(self) -> bool:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return False
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        return key == getattr(self, "_tree_item_playlists_root", None)

    def _selected_playlist(self) -> Playlist | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        playlist_id = getattr(self, "_tree_item_playlist", {}).get(key)
        return self._library.find_playlist(playlist_id) if playlist_id else None

    def _add_virtual_view_show_children(self, parent_item: object, view_id: str) -> None:
        """Folders view mode: one child node per podcast that has at least
        one episode in this pinned view, sorted by title."""
        pairs = self._virtual_pairs(view_id)
        shows_by_id: dict[str, PodcastShow] = {}
        counts: dict[str, int] = {}
        for show, _episode in pairs:
            shows_by_id[show.id] = show
            counts[show.id] = counts.get(show.id, 0) + 1
        for show_id in sorted(shows_by_id, key=lambda sid: shows_by_id[sid].title.casefold()):
            show = shows_by_id[show_id]
            label = f"{show.title} ({counts[show_id]})"
            item = self._tree.AppendItem(parent_item, label)
            key = item.GetID() if hasattr(item, "GetID") else id(item)
            self._tree_item_virtual_show[key] = (view_id, show_id)

    def _add_inbox_folder_children(self, parent_item: object, parent_id: str | None) -> None:
        from quill.core.podcasts.inbox import inbox_pairs_in_folder

        for folder in sorted(
            (f for f in self._library.inbox_folders if f.parent_folder_id == parent_id),
            key=lambda f: f.name.casefold(),
        ):
            count = len(inbox_pairs_in_folder(self._library, folder.id))
            label = f"{folder.name} ({count})" if count else folder.name
            item = self._tree.AppendItem(parent_item, label)
            key = item.GetID() if hasattr(item, "GetID") else id(item)
            self._tree_item_inbox_folder[key] = folder.id
            self._add_inbox_folder_children(item, folder.id)

    def _selected_virtual_view(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        return getattr(self, "_tree_item_virtual", {}).get(key)

    def _selected_inbox_folder_id(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        return getattr(self, "_tree_item_inbox_folder", {}).get(key)

    def _selected_virtual_show(self) -> PodcastShow | None:
        """The podcast behind the selected per-show Folders node, or None
        when the selection isn't one of those (a plain virtual view, an
        Inbox folder, a library folder/show, or nothing selected)."""
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = item.GetID() if hasattr(item, "GetID") else id(item)
        entry = getattr(self, "_tree_item_virtual_show", {}).get(key)
        if entry is None:
            return None
        _view_id, show_id = entry
        return self._library.find_show(show_id)

    def _virtual_pairs(self, view_id: str) -> list[tuple[PodcastShow, PodcastEpisode]]:
        if view_id == "favorites":
            return [
                (show, episode)
                for show in self._library.shows
                if show.is_favorite
                for episode in show.episodes
            ]
        if view_id == "recently_expired":
            from quill.core.podcasts.expiration import expired_pairs

            return list(expired_pairs(self._library))  # type: ignore[arg-type]
        return virtual_view_pairs(self._library, view_id)

    def _fill_episodes_from_pairs(
        self, pairs: list[tuple[PodcastShow, PodcastEpisode]], *, view_label: str
    ) -> None:
        """Fill the episode list from cross-show pairs (virtual views and
        Inbox folders); titles carry the show name so rows stay unambiguous
        when several shows interleave.

        Sorted and grouped per the library's "View cross-show lists as"
        setting (flat / grouped / folders) and each show's own effective
        sort mode (see sort_pairs) -- the Sort dropdown now actually takes
        effect here too, instead of leaving cross-show views in raw
        feed-fetch order.
        """
        from quill.core.podcasts.sorting import sort_pairs

        pairs = sort_pairs(
            self._library, pairs, view_mode=self._library.settings.episode_list_view_mode
        )
        total = len(pairs)
        shown = pairs[:_MAX_CROSS_SHOW_ROWS]
        self._episodes.DeleteAllItems()
        self._current_show = None
        self._current_episodes = [episode for _show, episode in shown]
        self._pair_shows = [show for show, _episode in shown]
        name_first = self._library.settings.announce_show_name_first
        # Freeze/Thaw around a bulk fill: without it wxMSW repaints and
        # re-measures per row, which is the difference between a snappy list
        # and a visible redraw storm at a thousand rows.
        self._episodes.Freeze()
        try:
            for row, (show, episode) in enumerate(shown):
                label = (
                    f"{show.title} — {episode.title}"
                    if name_first
                    else f"{episode.title} — {show.title}"
                )
                self._episodes.InsertItem(row, label)
                self._episodes.SetItem(row, 1, episode.published[:16])
                minutes, seconds = divmod(episode.duration_seconds, 60)
                self._episodes.SetItem(
                    row, 2, f"{minutes}:{seconds:02d}" if episode.duration_seconds else ""
                )
                self._episodes.SetItem(row, 3, self._episode_status_text(episode))
        finally:
            self._episodes.Thaw()
        if total > len(shown):
            self._status.SetLabel(
                f"Showing the newest {len(shown)} of {total} episode(s) in {view_label}. "
                "Narrow it with the Episodes filter, or open one podcast to see all of its own."
            )
        else:
            self._status.SetLabel(f"{total} episode(s) in {view_label}.")
        if shown:
            self._episodes.Select(0)
            self._episodes.Focus(0)

    def _maybe_fill_virtual_selection(self) -> bool:
        """Handle tree selection landing on a pinned view, an Inbox folder,
        or (Folders view mode) a per-podcast node inside a pinned view;
        True when handled (the caller skips its normal show fill)."""
        view_id = self._selected_virtual_view()
        if view_id is not None:
            labels = dict(_PINNED_VIEWS)
            self._fill_episodes_from_pairs(
                self._virtual_pairs(view_id), view_label=labels.get(view_id, view_id)
            )
            return True
        inbox_folder_id = self._selected_inbox_folder_id()
        if inbox_folder_id is not None:
            from quill.core.podcasts.inbox import inbox_pairs_in_folder

            folder = next((f for f in self._library.inbox_folders if f.id == inbox_folder_id), None)
            self._fill_episodes_from_pairs(
                inbox_pairs_in_folder(self._library, inbox_folder_id),
                view_label=folder.name if folder else "Inbox folder",
            )
            return True
        virtual_show = self._selected_virtual_show()
        if virtual_show is not None:
            item = self._tree.GetSelection()
            key = item.GetID() if hasattr(item, "GetID") else id(item)
            view_id = self._tree_item_virtual_show[key][0]
            pairs = [
                (show, episode)
                for show, episode in self._virtual_pairs(view_id)
                if show.id == virtual_show.id
            ]
            self._fill_episodes_from_pairs(pairs, view_label=virtual_show.title)
            return True
        if self._selected_playlists_root():
            self._fill_episodes_from_pairs([], view_label="Playlists")
            return True
        playlist = self._selected_playlist()
        if playlist is not None:
            from quill.core.podcasts.playlists import resolve_playlist

            self._fill_episodes_from_pairs(
                resolve_playlist(self._library, playlist), view_label=playlist.name
            )
            return True
        return False

    def _show_for_selected_episode(self, index: int) -> PodcastShow | None:
        """The show behind an episode row: the current show normally, the
        pair's own show inside a virtual view."""
        if self._current_show is not None:
            return self._current_show
        pair_shows = getattr(self, "_pair_shows", [])
        if 0 <= index < len(pair_shows):
            return pair_shows[index]
        return None

    # -- Search Everywhere ------------------------------------------------------

    def _on_search_everywhere(self) -> None:
        from quill.core.podcasts.episode_notes import load_episode_notes
        from quill.core.podcasts.transcripts import iter_cached_transcripts
        from quill.ui.podcasts.search_everywhere_dialog import SearchEverywhereDialog

        try:
            transcripts = list(iter_cached_transcripts())
        except Exception:  # noqa: BLE001 - a broken cache must not block search
            transcripts = []
        dialog = SearchEverywhereDialog(
            self.dialog,
            on_search=lambda query: search_everywhere(
                self._library,
                query,
                episode_notes=load_episode_notes(),
                transcripts=transcripts,
            ),
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        self._select_search_result(result)

    def _select_search_result(self, result: object) -> None:
        """Land the tree/list selection on a Search Everywhere hit."""
        show = self._library.find_show(getattr(result, "show_id", "") or "")
        if show is None:
            return
        self.refresh_tree()
        self._restore_tree_anchor(("show", show.id))
        guid = getattr(result, "episode_guid", "") or ""
        if guid:
            for row, episode in enumerate(self._current_episodes):
                if episode.guid == guid:
                    self._episodes.Select(row)
                    self._episodes.Focus(row)
                    break
        self._announce(f"Selected {show.title}")

    # -- Play Queue ---------------------------------------------------------------

    def _on_open_play_queue(self) -> None:
        from quill.ui.podcasts.play_queue_dialog import PlayQueueDialog

        dialog = PlayQueueDialog(
            self.dialog,
            library=self._library,
            announce_cb=self._announce,
            on_library_changed=self._on_library_changed,
            on_play=self._play_pair,
        )
        dialog.show()

    def _play_pair(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        from quill.ui.podcasts.show_actions import start_episode_playback

        start_episode_playback(self._controller, self._library, show, episode)

    # -- context-menu additions -----------------------------------------------

    def _append_transcript_items(
        self, menu: object, show: PodcastShow, episode: PodcastEpisode
    ) -> None:
        """Transcript items, appended only when the episode publishes one.

        Not Quick Actions: they appear and disappear with the episode's own
        metadata, and an orderable list whose entries vanish per row is a
        list whose order means nothing.
        """
        if not episode.transcript_url:
            return
        wx = self._wx
        save_tr_item = menu.Append(wx.ID_ANY, "Save &Transcript As...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_save_transcript(show, episode), save_tr_item)
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
        show.route_to_inbox = not show.route_to_inbox
        self._on_library_changed()
        self.refresh_tree()
        self._announce(
            f"New {show.title} episodes will appear in the Inbox"
            if show.route_to_inbox
            else f"{show.title} no longer routes to the Inbox"
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
            self.dialog,
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

    # -- saved playlists (Phase 5) ------------------------------------------------

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
            self.dialog, f"Add {episode.title} to which playlist?", "Add to Playlist", choices
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
            self.dialog, "Playlist name:", title, initial
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
            self.dialog,
            shows=list(self._library.shows),
            rules=PlaylistRules(),
            announce_cb=self._announce,
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
            self.dialog,
            shows=list(self._library.shows),
            rules=playlist.rules,
            announce_cb=self._announce,
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
            self.dialog,
            announce=self._announce,
        )
        if confirm != wx.YES:
            return
        self._library.remove_playlist(playlist.id)
        self._on_library_changed()
        self.refresh_tree()
        self._announce(f"Deleted playlist {playlist.name}")

    # -- episode notes ------------------------------------------------------------

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

    # -- transcripts ----------------------------------------------------------------

    def _on_save_transcript(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        wx = self._wx
        with wx.FileDialog(  # dialog_button_contract: exempt
            self.dialog,
            "Save Transcript As",
            defaultFile=f"{episode.title}.txt",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            target = dialog.GetPath()
        self._fetch_transcript_then(
            show, episode, lambda text: self._write_transcript(target, text)
        )

    def _write_transcript(self, target: str, text: str) -> None:
        from pathlib import Path

        try:
            Path(target).write_text(text, encoding="utf-8", newline="\n")
        except OSError as error:
            self._announce(f"Could not save the transcript: {error}")
            return
        self._announce(f"Transcript saved to {Path(target).name}")

    def _on_open_transcript(self, show: PodcastShow, episode: PodcastEpisode) -> None:
        send = self._on_send_show_notes
        if send is None:
            self._announce("Opening in the editor is not available here.")
            return
        self._fetch_transcript_then(show, episode, send)

    def _fetch_transcript_then(
        self, show: PodcastShow, episode: PodcastEpisode, consume: object
    ) -> None:
        from quill.core.podcasts import feed_auth
        from quill.core.podcasts import transcripts as transcripts_module

        if self._task_manager is None:
            self._announce("Transcript fetching is unavailable right now.")
            return
        self._announce("Fetching transcript...")
        auth_header = feed_auth.auth_header_for_url(show, episode.transcript_url)

        def _do_fetch(**_kwargs: object) -> str:
            text = transcripts_module.fetch_and_parse_transcript(
                episode.transcript_url,
                episode.transcript_type,
                safe_mode=self._safe_mode,
                auth_header=auth_header,
            )
            if text:
                # Cache so Search Everywhere can search it with no re-fetch.
                transcripts_module.save_cached_transcript(show.id, episode.guid, text)
            return text

        def _on_success(_op: str, text: str) -> None:
            wx = self._wx
            wx.CallAfter(consume, text)

        def _on_failure(_op: str, error: object) -> None:
            wx = self._wx
            wx.CallAfter(self._announce, f"Transcript failed: {error}")

        self._task_manager.submit(
            "podcast-transcript", _do_fetch, on_success=_on_success, on_failure=_on_failure
        )
