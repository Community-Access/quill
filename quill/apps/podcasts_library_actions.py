"""QUILL Cast's library-tree actions: the context menu and its handlers.

Extracted from ``podcasts.py`` (GATE-11) when the episode rows gained
Play/Download, the pinned views became renamable (F2, with Reset Name), and
custom show ordering (Alt+Up/Alt+Down + Subscriptions > Sort Podcasts)
arrived. Mixed into ``PodcastsAppFrame``; every ``self._*`` here is built by
that class or ``PodcastsMixin``.
"""

from __future__ import annotations

import wx


class CastLibraryActionsMixin:
    """Context-menu entries, rename/sort/download handlers for the main
    page's library tree."""

    def _on_library_rename_key(self) -> None:
        """F2: rename what is yours to rename -- folders and the pinned views.

        A show or an episode keeps its feed's name: those labels belong to
        the podcast, and a personal alias would quietly stop matching what
        every other player, share link, and search result calls it.
        """
        selected = self._selected_tree_data()
        if selected is None:
            return
        kind = selected[0]
        if kind == "folder":
            self._on_library_rename_folder()
        elif kind == "view":
            self._on_library_rename_view()
        elif kind in ("show", "episode"):
            self._announce(
                "Show and episode names come from the podcast's own feed and "
                "can't be renamed. Folders and the pinned views can, with F2."
            )

    def _library_context_entries(self) -> list[tuple[str, object]]:
        """The context menu for whatever library row is selected, as (label,
        handler) rows -- split from the popup itself so the menu each kind of
        row offers is testable without wx."""
        selected = self._selected_tree_data()
        if selected is None:
            return []
        kind, key = selected
        entries: list[tuple[str, object]] = []
        if kind == "show":
            show = self._podcast_library.find_show(key)
            if show is None:
                return []
            playing = self._podcast_controller.state.show_id == show.id and (
                self._podcast_controller.state.state.name not in ("STOPPED", "ERROR")
            )
            fav_label = "Remove from Fa&vorites" if show.is_favorite else "Add to Fa&vorites"
            entries = [
                ("&Stop" if playing else "&Play Next Episode", self._on_library_play_stop_context),
                (fav_label, self._on_library_favorite_toggle_context),
                ("&Move to Folder...", self._on_library_move_to_folder),
                ("Move Up in &Custom Order\tAlt+Up", lambda: self._on_library_move_show(-1)),
                ("Move Do&wn in Custom Order\tAlt+Down", lambda: self._on_library_move_show(1)),
                ("Download &All Episodes", self._on_library_download_all_episodes),
                # The symmetric verb: files gone, episodes and played state
                # kept. Distinct from Remove All Episodes below, which empties
                # the list itself.
                ("Remove All Down&loads...", self._on_library_remove_all_downloads),
                ("&Remove All Episodes...", self._on_library_remove_all_episodes),
            ]
            if show.feed_url:
                entries.append(("Feed Cre&dentials...", self._on_library_feed_credentials))
            entries += [
                ("&Unsubscribe...\tDelete", self._on_library_remove),
                ("New F&older...", self._on_library_new_folder),
                ("Open &Manager...", lambda: self.open_podcast_manager()),
            ]
        elif kind == "folder":
            entries = [
                ("Rena&me Folder...\tF2", self._on_library_rename_folder),
                ("&Delete Folder...\tDelete", self._on_library_remove),
                ("New F&older...", self._on_library_new_folder),
                ("Open &Manager...", lambda: self.open_podcast_manager()),
            ]
        elif kind == "view":
            entries = [("&Rename...\tF2", self._on_library_rename_view)]
            if self._podcast_library.settings.view_names.get(key, "").strip():
                entries.append(("Reset &Name", self._on_library_reset_view_name))
            entries.append(("Open &Manager...", lambda: self.open_podcast_manager()))
        elif kind == "episode":
            pair = self._selected_episode()
            if pair is None:
                return []
            show, episode = pair
            state = self._podcast_controller.state
            playing_this = (
                state.show_id == show.id
                and state.episode_guid == episode.guid
                and state.state.name not in ("STOPPED", "ERROR")
            )
            entries = [
                ("&Stop" if playing_this else "&Play Episode", self._on_library_episode_play_stop),
                ("&Download Episode", self._on_library_download_episode),
                ("Open &Manager...", lambda: self.open_podcast_manager()),
            ]
        else:
            entries = [("Open &Manager...", lambda: self.open_podcast_manager())]
        return entries

    def _on_library_context_menu(self, _event: object) -> None:
        entries = self._library_context_entries()
        if not entries:
            return
        menu = wx.Menu()
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._keep_menu_ids(*id_refs)
        self._shows_tree.PopupMenu(menu)
        menu.Destroy()

    def _on_library_play_stop_context(self) -> None:
        show = self._selected_show()
        if show is None:
            return
        state = self._podcast_controller.state
        if state.show_id == show.id and state.state.name not in ("STOPPED", "ERROR"):
            self.podcast_stop()
        else:
            self._play_show_next_episode(show.id)

    def _on_library_favorite_toggle_context(self) -> None:
        from quill.ui.podcasts.show_actions import toggle_favorite

        show = self._selected_show()
        if show is None:
            return
        toggle_favorite(self._podcast_library, show, announce=self._announce)
        self._save_podcast_library()
        self._refresh_transport_controls()

    def _on_library_download_all_episodes(self) -> None:
        from quill.ui.podcasts.show_actions import download_all_episodes

        show = self._selected_show()
        if show is None:
            return
        download_all_episodes(
            self._podcast_download_queue,
            self._podcast_download_root(),
            show,
            announce=self._announce,
        )

    def _on_library_remove_all_downloads(self) -> None:
        from quill.ui.podcasts.show_downloads import remove_all_downloads_prompt

        show = self._selected_show()
        if show is None:
            return
        if remove_all_downloads_prompt(
            self.frame, self._podcast_library, show, announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_remove_all_episodes(self) -> None:
        from quill.ui.podcasts.show_actions import remove_all_episodes_prompt

        show = self._selected_show()
        if show is None:
            return
        if remove_all_episodes_prompt(
            self.frame, self._podcast_download_queue, show, announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_feed_credentials(self) -> None:
        from quill.ui.podcasts.show_actions import feed_credentials_prompt

        show = self._selected_show()
        if show is None or not show.feed_url:
            return
        if feed_credentials_prompt(
            self.frame, self._podcast_library, show, announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_move_to_folder(self) -> None:
        from quill.ui.podcasts.show_actions import move_show_to_folder

        show = self._selected_show()
        if show is None:
            return
        if move_show_to_folder(self.frame, self._podcast_library, show, announce=self._announce):
            self._save_podcast_library()

    def _on_library_episode_play_stop(self) -> None:
        pair = self._selected_episode()
        if pair is None:
            return
        show, episode = pair
        state = self._podcast_controller.state
        if (
            state.show_id == show.id
            and state.episode_guid == episode.guid
            and state.state.name not in ("STOPPED", "ERROR")
        ):
            self.podcast_stop()
        else:
            self._play_episode_object(show, episode)

    def _on_library_download_episode(self) -> None:
        """Download this one episode -- enqueued on the background download
        worker, never fetched inline. The file lands under the Download
        location as ``<show title>/<episode title>.<ext>`` (see
        ``episode_destination``), so the name means something outside the app."""
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        pair = self._selected_episode()
        if pair is None:
            return
        show, episode = pair
        if episode.downloaded_path:
            self._announce(f"{episode.title} is already downloaded.")
            return
        if self._podcast_download_queue.get(episode.guid) is not None:
            self._announce(f"{episode.title} is already in the download queue.")
            return
        enqueue_episode_download(
            self._podcast_download_queue, self._podcast_download_root(), show, episode
        )
        self._announce(f"Downloading {episode.title} from {show.title}.")

    def _on_library_move_show(self, offset: int) -> None:
        """Alt+Up/Alt+Down (or the context menu): hand-arrange the library.

        Taking manual control IS choosing custom order, so the first move
        switches the sort mode -- after freezing the on-screen order as the
        starting point, or that first nudge would scramble everything else.
        """
        show = self._selected_show()
        if show is None:
            return
        if self._podcast_library.settings.show_sort_mode != "custom":
            self._set_show_sort_mode("custom", announce=False)
        if not self._podcast_library.move_show(show.id, offset):
            edge = "top" if offset < 0 else "bottom"
            self._announce(f"{show.title} is already at the {edge}.")
            return
        self._save_podcast_library()
        self._announce(f"Moved {show.title} {'up' if offset < 0 else 'down'}.")

    def _set_show_sort_mode(self, mode: str, *, announce: bool = True) -> None:
        """Subscriptions > Sort Podcasts, and the silent switch a manual move
        performs. Entering custom mode freezes whatever order is on screen as
        the starting order, so nothing visibly jumps."""
        from quill.core.podcasts.sorting import sort_shows

        settings = self._podcast_library.settings
        if mode == "custom" and settings.show_sort_mode != "custom":
            self._podcast_library.shows[:] = sort_shows(
                self._podcast_library.shows, settings.show_sort_mode
            )
        changed = settings.show_sort_mode != mode
        settings.show_sort_mode = mode
        self._refresh_sort_mode_menu()
        if changed:
            self._save_podcast_library()
        if announce:
            labels = {
                "title_az": "ascending, A to Z",
                "title_za": "descending, Z to A",
                "custom": "your custom order; move shows with Alt+Up and Alt+Down",
            }
            self._announce(f"Podcasts sorted {labels.get(mode, mode)}.")

    def _on_library_rename_view(self) -> None:
        from quill.ui.podcasts.show_actions import rename_view_prompt

        selected = self._selected_tree_data()
        if selected is None or selected[0] != "view":
            return
        if rename_view_prompt(
            self.frame, self._podcast_library, selected[1], announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_reset_view_name(self) -> None:
        from quill.ui.podcasts.show_actions import reset_view_name_action

        selected = self._selected_tree_data()
        if selected is None or selected[0] != "view":
            return
        if reset_view_name_action(self._podcast_library, selected[1], announce=self._announce):
            self._save_podcast_library()

    def _on_library_rename_folder(self) -> None:
        from quill.ui.podcasts.show_actions import rename_folder_prompt

        selected = self._selected_tree_data()
        if selected is None or selected[0] != "folder":
            return
        if rename_folder_prompt(
            self.frame, self._podcast_library, selected[1], announce=self._announce
        ):
            self._save_podcast_library()

    def _on_library_new_folder(self) -> None:
        from quill.ui.podcasts.show_actions import create_folder_prompt

        selected = self._selected_tree_data()
        initial_parent = selected[1] if selected is not None and selected[0] == "folder" else None
        if create_folder_prompt(
            self.frame,
            self._podcast_library,
            announce=self._announce,
            initial_parent_id=initial_parent,
        ):
            self._save_podcast_library()

    def _on_library_remove(self) -> None:
        from quill.ui.podcasts.show_actions import delete_folder_prompt, unsubscribe_show_prompt

        selected = self._selected_tree_data()
        if selected is None:
            return
        kind, key = selected
        if kind == "show":
            show = self._podcast_library.find_show(key)
            if show is not None and unsubscribe_show_prompt(
                self.frame, self._podcast_library, show, announce=self._announce
            ):
                self._save_podcast_library()
        elif kind == "folder":
            if delete_folder_prompt(
                self.frame, self._podcast_library, key, announce=self._announce
            ):
                self._save_podcast_library()
