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

from quill.core.podcasts import volume_boost
from quill.core.podcasts.filtering import (
    filter_shows,
)
from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastShow
from quill.core.podcasts.virtual_views import virtual_view_pairs
from quill.ui.podcasts import volume_boost_ui
from quill.ui.podcasts.episode_search import EpisodeSearchMixin
from quill.ui.podcasts.manager_expired import ManagerExpiredMixin
from quill.ui.podcasts.manager_search_everywhere import SearchEverywhereMixin
from quill.ui.podcasts.say_status import say_status

_EPISODE_FILTER_LABELS = (
    "All",
    "Unplayed",
    "In progress",
    "Played",
    "Downloaded",
    "Not downloaded",
    # The way back from an Episode Filter. Last in the list because it is the
    # rarest choice, and present in every show's dropdown -- not only filtered
    # ones -- so it is somewhere a person can *learn* to look rather than a
    # control that appears and disappears.
    "Filtered out",
)
_EPISODE_FILTER_MODES = (
    "all",
    "unplayed",
    "in_progress",
    "played",
    "downloaded",
    "not_downloaded",
    "filtered_out",
)
_SHOW_FILTER_LABELS = ("All shows", "Favorites only", "Has unheard")
_SHOW_FILTER_MODES = ("all", "favorites_only", "has_unplayed")
#: Volume Boost, from the shared table (list.md 2.8).
_BOOST_LABELS = tuple(label for _value, label, _factor in volume_boost.LEVELS)

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


class ManagerPhase4Mixin(ManagerExpiredMixin, EpisodeSearchMixin, SearchEverywhereMixin):
    """Phase 4 wiring; mixed into PodcastManagerDialog."""

    # -- filter row -----------------------------------------------------------

    def _build_phase4_row(self, parent_sizer: object) -> None:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        # Each label is constructed immediately before the control it names, and
        # that ordering is the whole point. On wxMSW a control's accessible name
        # comes from the StaticText created before it in z-order -- so these three
        # labels existed for a long time, were all built *after* all four controls,
        # and named nothing: the combo boxes announced as bare "combo box" (Jeff,
        # 2026-09-30). SetName does not help; it sets wxWindow's own name, which no
        # screen reader reads. The gate for this is tools/check_control_labels.py.
        episodes_label = wx.StaticText(self.dialog, label="Ep&isodes:")
        self._episode_filter_choice = wx.Choice(self.dialog, choices=list(_EPISODE_FILTER_LABELS))
        self._episode_filter_choice.SetHelpText(
            "Which episodes the list shows: all of them, only the unheard ones, "
            "only what is downloaded, and so on. It narrows the list you are "
            "looking at and changes nothing about the episodes themselves."
        )
        self._episode_filter_choice.SetSelection(0)
        find_label = wx.StaticText(self.dialog, label="Fi&nd:")
        self._episode_search_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        shows_label = wx.StaticText(self.dialog, label="S&hows:")
        self._show_filter_choice = wx.Choice(self.dialog, choices=list(_SHOW_FILTER_LABELS))
        self._show_filter_choice.SetHelpText(
            "Which podcasts the folder tree shows -- all of them, or only the ones "
            "with something unplayed. Nothing is unfollowed or hidden permanently."
        )
        self._show_filter_choice.SetSelection(0)
        # The boost had no label at all, in any order.
        boost_label = wx.StaticText(self.dialog, label="&Boost:")
        self._boost_choice = wx.Choice(self.dialog, choices=list(_BOOST_LABELS))
        self._boost_choice.SetHelpText(volume_boost_ui.HELP)
        self._boost_choice.SetSelection(0)
        # Find in this show -- see episode_search.py for what it composes with.
        self._episode_search_ctrl.SetHelpText(
            "Narrows the episode list of the podcast you are on, matching "
            "episode titles and the show notes. It searches this podcast only "
            "-- Search Everywhere is the one that crosses your whole library "
            "-- and it narrows whatever the filter and sort above already "
            "chose rather than replacing them. Enter says how many matched."
        )
        search_btn = wx.Button(self.dialog, label="Search &Everywhere...")
        queue_btn = wx.Button(self.dialog, label="Play &Queue...")
        row.Add(episodes_label, 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self._episode_filter_choice, 0, wx.LEFT | wx.RIGHT, 4)
        row.Add(find_label, 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self._episode_search_ctrl, 1, wx.LEFT | wx.RIGHT, 4)
        row.Add(shows_label, 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self._show_filter_choice, 0, wx.LEFT | wx.RIGHT, 4)
        row.Add(boost_label, 0, wx.ALIGN_CENTER_VERTICAL)
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
        self._episode_search_ctrl.Bind(wx.EVT_TEXT, self._on_episode_search_typed)
        self._episode_search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_episode_search_submit)

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

    def _apply_show_filter(self, shows: list[PodcastShow]) -> list[PodcastShow]:
        return filter_shows(shows, self._selected_show_filter())

    def _on_boost_choice(self, _event: object) -> None:
        from quill.ui.podcasts import volume_boost_ui

        volume_boost_ui.chosen(self, max(0, self._boost_choice.GetSelection()))

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
        from quill.core.podcasts.virtual_views import view_label

        for view_id, _default in _PINNED_VIEWS:
            label = view_label(self._library, view_id)
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
            say_status(
                self._status,
                f"Showing the newest {len(shown)} of {total} episode(s) in {view_label}. "
                "Narrow it with the Episodes filter, or open one podcast to see all of its own.",
                self._announce,
            )
        else:
            # Follows the selection, which the reader already says; not spoken.
            say_status(self._status, f"{total} episode(s) in {view_label}.", speak=False)
        if shown:
            self._episodes.Select(0)
            self._episodes.Focus(0)

    def _maybe_fill_virtual_selection(self) -> bool:
        """Handle tree selection landing on a pinned view, an Inbox folder,
        or (Folders view mode) a per-podcast node inside a pinned view;
        True when handled (the caller skips its normal show fill)."""
        view_id = self._selected_virtual_view()
        if view_id is not None:
            from quill.core.podcasts.virtual_views import view_label as pinned_view_label

            self._fill_episodes_from_pairs(
                self._virtual_pairs(view_id), view_label=pinned_view_label(self._library, view_id)
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

        start_episode_playback(
            self._controller, self._library, show, episode, announce=self._announce
        )

    # -- context-menu additions -----------------------------------------------

    # -- saved playlists (Phase 5) ------------------------------------------------

    # -- episode notes ------------------------------------------------------------

    # -- transcripts ----------------------------------------------------------------
