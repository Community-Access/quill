"""The episode list in the main window, and the Manager-shaped surface over it (qc.md 4.4).

The Podcast Manager's episode list, its actions and its verbs were written
against one set of names -- ``_library``, ``_controller``, ``_episodes``,
``_current_show``, ``_current_episodes``, ``_pair_shows``, ``_on_library_changed``,
``refresh_tree``, ``dialog`` -- and the five Manager mixins and the helper
modules beside them (transcripts, notes, extras, sharing, single settings,
folder moves) all speak to them. Rather than rewrite forty verbs, the main
window answers to those names: this mixin is the adapter, and the Manager's
mixins are re-homed on the frame through it, so one implementation serves
QUILL's Podcast Manager and Cast's one window alike.

What is new here is the list itself: one report list for every place whose
content is rows (the episode places, Favorites' podcast rows, Notifications),
filled by column id through the shared column view so Choose Columns applies
and no cell is ever written by position (the Manager's cross-show fill did,
and ignored the listener's columns -- fixed by being replaced).
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

__all__ = ["CastEpisodeListMixin", "PODCAST_COLUMNS", "NOTICE_COLUMNS"]

#: The Favorites place's columns (qc.md 4.4): Title, Unheard, Last new episode, Folder.
PODCAST_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("title", "Title", 320),
    ("unheard", "Unheard", 80),
    ("last_new", "Last new episode", 140),
    ("folder", "Folder", 160),
)
PLAYLIST_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("title", "Playlist", 320),
    ("kind", "Kind", 120),
    ("count", "Episodes", 100),
)
NOTICE_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("title", "Notice", 420),
    ("when", "When", 140),
    ("state", "State", 80),
)

_MAX_ROWS = 1000


class CastEpisodeListMixin:
    """The one list in the content pane, and the names the Manager code expects."""

    # -- the Manager-shaped surface ------------------------------------------- #

    @property
    def _library(self) -> Any:
        return self._podcast_library  # type: ignore[attr-defined]

    @property
    def _controller(self) -> Any:
        return self._podcast_controller  # type: ignore[attr-defined]

    @property
    def _download_queue(self) -> Any:
        return self._podcast_download_queue  # type: ignore[attr-defined]

    @property
    def _download_root(self) -> Any:
        return self._podcast_download_root()  # type: ignore[attr-defined]

    @property
    def dialog(self) -> Any:
        """The parent window for the verbs' own dialogs: this frame."""
        return self.frame  # type: ignore[attr-defined]

    @property
    def _transport_host(self) -> Any:
        return self

    @property
    def _quick_actions(self) -> Any:
        return self.podcast_quick_actions()  # type: ignore[attr-defined]

    @property
    def _refresh_feed_cb(self) -> Any:
        return self.refresh_podcast_feed  # type: ignore[attr-defined]

    @property
    def _on_send_show_notes(self) -> Any:
        return getattr(self, "_podcast_send_show_notes_to_editor", None)

    @property
    def _chapter_skip_state(self) -> Any:
        return self.podcast_chapter_skip_state  # type: ignore[attr-defined]

    def _on_library_changed(self) -> None:
        self._save_podcast_library()  # type: ignore[attr-defined]

    def refresh_tree(self) -> None:
        """What the Manager's verbs call after changing the library: in the one
        window, both the tree and whichever place is showing."""
        self._reload_library_tree()  # type: ignore[attr-defined]
        self._refresh_place(keep=True)  # type: ignore[attr-defined]

    def _play_episode(
        self, show: PodcastShow, episode: PodcastEpisode, *, resume_ms: int | None = None
    ) -> None:
        """The Manager's play verb, which its Play Next Episode and chapter jump
        call. The Manager defined it and the one window never did, so both
        raised here; this answers with the frame's own starter."""
        from quill.ui.podcasts.show_actions import start_episode_playback

        if start_episode_playback(
            self._podcast_controller,  # type: ignore[attr-defined]
            self._podcast_library,  # type: ignore[attr-defined]
            show,
            episode,
            resume_ms=resume_ms,
            announce=self._announce,  # type: ignore[attr-defined]
        ):
            self._announce(f"Playing {episode.title} from {show.title}")  # type: ignore[attr-defined]

    def _verb_selected_episode(self) -> PodcastEpisode | None:
        """The selected row's episode (the Manager's ``_selected_episode``)."""
        pair = self._selected_episode()  # type: ignore[attr-defined]
        return pair[1] if pair is not None else None

    def _selected_show_id(self) -> str | None:
        show = self._selected_show()  # type: ignore[attr-defined]
        return show.id if show is not None else None

    def _selected_folder_id(self) -> str | None:
        selected = self._selected_tree_data()  # type: ignore[attr-defined]
        if selected is not None and selected[0] == "folder":
            return str(selected[1]) or None
        return None

    def _sort_context_show(self) -> PodcastShow | None:
        return (
            self._selected_show()
            or (  # type: ignore[attr-defined]
                (self._selected_episode() or (None, None))[0]  # type: ignore[attr-defined]
            )
        )

    def _selected_episode_sort_mode(self) -> str:
        show = self._sort_context_show()
        if show is not None:
            return str(self._library.effective_settings(show).episode_sort_mode)
        return str(self._library.settings.episode_sort_mode)

    def _update_now_playing(self) -> None:
        self._refresh_statusbar()  # type: ignore[attr-defined]

    def _show_for_selected_episode(self, index: int) -> PodcastShow | None:
        if self._current_show is not None:
            return self._current_show
        pair_shows = getattr(self, "_pair_shows", [])
        if 0 <= index < len(pair_shows):
            return pair_shows[index]
        return None

    def _refresh_episode_list(self) -> None:
        self._refresh_place(keep=True)  # type: ignore[attr-defined]

    # -- the list ---------------------------------------------------------------- #

    def _build_episode_list(self, parent: Any) -> Any:
        """The one report list, multi-select, with the episode columns to start."""
        wx = self._wx
        from quill.ui.media.list_columns_view import columns_for

        # The heading the content pane shows above the list, created first so it
        # is the list's accessible name on wxMSW ("Inbox (6)").
        self._list_heading = wx.StaticText(parent, label="Places")
        self._episodes = wx.ListCtrl(parent, style=wx.LC_REPORT)
        self._episodes.SetHelpText(
            "The episodes (or podcasts) of the place you chose, one per row, read "
            "column by column. Enter plays an episode or opens a podcast; Space "
            "adds an episode to the queue; Delete removes it from this place; "
            "Shift+F10 offers everything else. Left Arrow at the top returns to Places."
        )
        self._current_show: PodcastShow | None = None
        self._current_episodes: list[PodcastEpisode] = []
        self._pair_shows: list[PodcastShow] = []
        self._list_kind = "episodes"
        self._list_rows: list[Any] = []
        self._episode_columns = columns_for("cast", "cast.episodes")
        self._apply_list_columns("episodes")
        return self._episodes

    def _apply_list_columns(self, kind: str) -> None:
        from quill.core.media.list_columns import ColumnDef
        from quill.ui.media.list_columns_view import build_columns, columns_for

        if kind == "episodes":
            self._episode_columns = columns_for("cast", "cast.episodes")
            columns = self._episode_columns
        else:
            spec = {"podcasts": PODCAST_COLUMNS, "playlists": PLAYLIST_COLUMNS}.get(
                kind, NOTICE_COLUMNS
            )
            columns = [ColumnDef(cid, label, "", width=width) for cid, label, width in spec]
        self._list_columns = columns
        self._list_kind = kind
        build_columns(self._episodes, columns)

    def _build_episode_columns(self) -> None:
        self._apply_list_columns("episodes")

    def reapply_columns(self) -> None:
        """Choose Columns saved a layout: rebuild the list in it, now."""
        self._refresh_place(keep=True)  # type: ignore[attr-defined]

    def _fill_episodes(self, show: PodcastShow | None) -> None:
        """One podcast's episodes, as the Manager filled them."""
        from quill.core.podcasts.sorting import sort_episodes
        from quill.ui.media.list_columns_view import fill_row

        if self._list_kind != "episodes":
            self._apply_list_columns("episodes")
        self._episodes.DeleteAllItems()
        episodes = self._visible_show_episodes(show) if show is not None else []
        self._current_show = show
        self._current_episodes = sort_episodes(episodes, self._selected_episode_sort_mode())
        self._pair_shows = []
        self._list_rows = (
            [("episode", f"{show.id}\x00{ep.guid}") for ep in self._current_episodes]
            if show
            else []
        )
        self._episodes.Freeze()
        try:
            for row, episode in enumerate(self._current_episodes):
                fill_row(
                    self._episodes,
                    row,
                    self._episode_columns,
                    self._episode_row_values(episode, show),  # type: ignore[attr-defined]
                )
        finally:
            self._episodes.Thaw()

    def _visible_show_episodes(self, show: PodcastShow) -> list[PodcastEpisode]:
        """The podcast's own Episode Filter, the catalogue limit, then the View > Show filter."""
        from quill.core.podcasts.episode_filter_maintenance import visible
        from quill.core.podcasts.filtering import filter_episodes
        from quill.core.podcasts.models_filters import SCOPE_LIBRARY
        from quill.core.podcasts.show_policy import visible_episodes

        episodes = visible_episodes(self._library, show, list(show.episodes))
        return filter_episodes(
            visible(self._library, show, episodes, SCOPE_LIBRARY), self._episode_show_filter()
        )

    def _episode_show_filter(self) -> str:
        """View > Show: the one episode filter, applied to every list."""
        return str(getattr(self._podcast_history, "episode_filter", "all") or "all")  # type: ignore[attr-defined]

    def _fill_episodes_from_pairs(
        self,
        pairs: list[tuple[PodcastShow, PodcastEpisode]],
        *,
        view_label: str = "",
        lead_rows: list[tuple[str, str, str]] | None = None,
    ) -> None:
        """Cross-podcast rows, in the listener's columns (never by position).

        *lead_rows* are ``(kind, value, label)`` rows drawn first -- the Inbox's
        folders, when it is laid out folders first. They sit in the same list
        so arrowing is one motion; an episode verb on one of them finds no
        episode and does nothing, because its ``_pair_shows`` entry is None.
        """
        from quill.core.podcasts.filtering import filter_episodes
        from quill.core.podcasts.sorting import sort_pairs
        from quill.ui.media.list_columns_view import fill_row

        del view_label
        if self._list_kind != "episodes":
            self._apply_list_columns("episodes")
        mode = self._episode_show_filter()
        if mode != "all":
            wanted = {id(ep) for ep in filter_episodes([ep for _s, ep in pairs], mode)}
            pairs = [(show, ep) for show, ep in pairs if id(ep) in wanted]
        pairs = sort_pairs(
            self._library, pairs, view_mode=self._library.settings.episode_list_view_mode
        )
        shown = pairs[:_MAX_ROWS]
        lead = list(lead_rows or [])
        self._episodes.DeleteAllItems()
        self._current_show = None
        self._current_episodes = [
            PodcastEpisode(guid="", title=label, audio_url="") for _k, _v, label in lead
        ]
        self._current_episodes += [episode for _show, episode in shown]
        self._pair_shows = [None] * len(lead) + [show for show, _episode in shown]
        self._list_rows = [(kind, value) for kind, value, _label in lead]
        self._list_rows += [("episode", f"{show.id}\x00{ep.guid}") for show, ep in shown]
        self._episodes.Freeze()
        try:
            for row, (_kind, _value, label) in enumerate(lead):
                fill_row(self._episodes, row, self._episode_columns, {"title": label})
            for row, (show, episode) in enumerate(shown, start=len(lead)):
                fill_row(
                    self._episodes,
                    row,
                    self._episode_columns,
                    self._episode_row_values(episode, show),  # type: ignore[attr-defined]
                )
        finally:
            self._episodes.Thaw()

    def _fill_podcast_rows(self, shows: list[PodcastShow]) -> None:
        """Favorites: podcast rows with Title, Unheard, Last new episode, Folder."""
        from quill.core.podcasts.sorting import unheard_count
        from quill.ui.media.list_columns_view import fill_row

        self._apply_list_columns("podcasts")
        self._current_show = None
        self._current_episodes = []
        self._pair_shows = []
        self._list_rows = [("show", show.id) for show in shows]
        self._episodes.Freeze()
        try:
            for row, show in enumerate(shows):
                folder = self._library.find_folder(show.folder_id) if show.folder_id else None
                newest = max((ep.published for ep in show.episodes), default="")
                fill_row(
                    self._episodes,
                    row,
                    self._list_columns,
                    {
                        "title": show.title,
                        "unheard": str(unheard_count(show)),
                        "last_new": newest[:16],
                        "folder": folder.name if folder is not None else "",
                    },
                )
        finally:
            self._episodes.Thaw()

    def _fill_playlist_rows(self) -> None:
        """Playlists: one row each, smart or by hand, with its live count."""
        from quill.core.podcasts.playlists import resolve_playlist
        from quill.ui.media.list_columns_view import fill_row

        self._apply_list_columns("playlists")
        self._current_show = None
        self._current_episodes = []
        self._pair_shows = []
        playlists = sorted(self._library.playlists, key=lambda p: p.name.casefold())
        self._list_rows = [("playlist", p.id) for p in playlists]
        self._episodes.Freeze()
        try:
            for row, playlist in enumerate(playlists):
                try:
                    count = len(resolve_playlist(self._library, playlist))
                except Exception:  # noqa: BLE001 - a broken rule counts nothing
                    count = 0
                fill_row(
                    self._episodes,
                    row,
                    self._list_columns,
                    {
                        "title": playlist.name,
                        "kind": "Smart" if playlist.kind == "smart" else "By hand",
                        "count": str(count),
                    },
                )
        finally:
            self._episodes.Thaw()

    def _fill_notice_rows(self, notices: list[Any]) -> None:
        """Notifications: one row per notice, newest first."""
        from quill.ui.media.list_columns_view import fill_row
        from quill.ui.notification_center import _ago

        self._apply_list_columns("notices")
        self._current_show = None
        self._current_episodes = []
        self._pair_shows = []
        self._list_rows = [("notice", str(getattr(n, "id", ""))) for n in notices]
        self._episodes.Freeze()
        try:
            for row, notice in enumerate(notices):
                title = str(getattr(notice, "title", "") or "")
                body = str(getattr(notice, "body", "") or "")
                fill_row(
                    self._episodes,
                    row,
                    self._list_columns,
                    {
                        "title": f"{title} -- {body}" if body else title,
                        "when": _ago(str(getattr(notice, "timestamp", "") or "")),
                        "state": "New" if not getattr(notice, "read", True) else "",
                    },
                )
        finally:
            self._episodes.Thaw()

    # -- selection ---------------------------------------------------------------- #

    def _list_selected_data(self) -> tuple[str, str] | None:
        try:
            index = self._episodes.GetFirstSelected()
        except RuntimeError:  # the list is mid-teardown
            return None
        if 0 <= index < len(self._list_rows):
            kind, value = self._list_rows[index]
            return kind, value
        return None

    def _select_list_row(self, index: int) -> None:
        count = self._episodes.GetItemCount()
        if not count:
            return
        index = max(0, min(count - 1, index))
        # The list allows several rows at once, and Select *adds*: without this
        # the row the cursor was on stays selected too, and the next verb acts
        # on both.
        selected = self._episodes.GetFirstSelected()
        while selected != -1:
            if selected != index:
                self._episodes.Select(selected, on=False)
            selected = self._episodes.GetNextSelected(selected)
        self._episodes.Select(index)
        self._episodes.Focus(index)
        self._episodes.EnsureVisible(index)

    def _select_list_key(self, key: tuple[str, str] | None) -> bool:
        """The cursor back on *key*'s row, or -- when that row has gone (Delete,
        Mark as Played, a refresh) -- on the row that moved into its place, by
        the shared rule (qc.md F-10, ``activity.restore_index``)."""
        if key is None:
            return False
        from quill.core.activity import restore_index

        previous = int(getattr(self, "_list_previous_index", -1))
        self._list_previous_index = -1
        keys = [repr(row) for row in self._list_rows]
        if repr(key) in keys:
            index = keys.index(repr(key))
        elif previous >= 0:
            index = restore_index(keys, None, previous)
        else:
            return False
        if index < 0:
            return False
        self._select_list_row(index)
        return True

    def _selected_rows(self) -> list[tuple[int, PodcastShow, PodcastEpisode]]:
        rows: list[tuple[int, PodcastShow, PodcastEpisode]] = []
        index = self._episodes.GetFirstSelected()
        while index != -1:
            if 0 <= index < len(self._current_episodes):
                show = self._show_for_selected_episode(index)
                if show is not None:
                    rows.append((index, show, self._current_episodes[index]))
            index = self._episodes.GetNextSelected(index)
        return rows

    # -- rows that change under a download ------------------------------------------- #

    def _refresh_episode_row_for_item(self, item: Any) -> None:
        from quill.ui.media.list_columns_view import set_row

        if self._list_kind != "episodes":
            return
        for row, episode in enumerate(self._current_episodes):
            if episode.guid and episode.guid == item.episode_guid:
                show = self._show_for_selected_episode(row)
                set_row(
                    self._episodes,
                    row,
                    self._episode_columns,
                    self._episode_row_values(episode, show),  # type: ignore[attr-defined]
                )
                break

    def _refresh_selected_episode_row(self) -> None:
        from quill.ui.media.list_columns_view import set_row

        index = self._episodes.GetFirstSelected()
        if self._list_kind != "episodes" or not (0 <= index < len(self._current_episodes)):
            return
        if index < len(self._list_rows) and self._list_rows[index][0] != "episode":
            return  # an Inbox folder row is not an episode to redraw
        episode = self._current_episodes[index]
        set_row(
            self._episodes,
            index,
            self._episode_columns,
            self._episode_row_values(episode, self._show_for_selected_episode(index)),  # type: ignore[attr-defined]
        )

    def _on_episode_selected(self, _event: object = None) -> None:
        """The Manager enabled four buttons here; the one window has none to enable."""
        return None

    # -- the Winamp letters read the list when it is showing ------------------------------ #

    def _list_winamp_rows(self) -> list[tuple[object, object]]:
        rows: list[tuple[object, object]] = []
        for index, episode in enumerate(self._current_episodes):
            show = self._show_for_selected_episode(index)
            if show is not None:
                rows.append((show, episode))
        return rows
