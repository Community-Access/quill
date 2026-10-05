"""The main window's places: showing one, refreshing it, and what its keys do (qc.md 4.3, 4.4).

``show_place`` is the one verb every route uses -- the Places list, the View
menu, Go To, the status-bar cells, a notification's Enter -- so going to a
place always means landing on it, with focus, and an empty place always says
what fills it, once, on arrival. The content pane's kind follows the place:
the episode places and Favorites fill the report list, Notifications fills
it with notices, and Podcasts shows the folder tree.

Delete in a content list removes the row *from this place* and never deletes
an episode: from the queue, from the Inbox, from Downloads (the file), from
Continue Listening (the saved place), from Favorites (the mark), from New
Episodes (marks it played). Each says what it did and what survived.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import places as places_model
from quill.core.sound_events import SoundEvent
from quill.ui.podcasts.outcome_feedback import say_outcome

__all__ = ["CastPlacesHostMixin"]


class CastPlacesHostMixin:
    """On ``PodcastsAppFrame``: the Places list and the content pane as one surface."""

    _current_place: str = ""
    _place_opened_show_id: str = ""
    _place_opened_playlist_id: str = ""
    _place_announced_empty: str = ""

    # -- the layout ---------------------------------------------------------- #

    def _places_layout(self) -> places_model.PlacesLayout:
        return places_model.decode(self._podcast_library.settings.places_layout)  # type: ignore[attr-defined]

    def _save_places_layout(self, layout: places_model.PlacesLayout) -> None:
        self._podcast_library.settings.places_layout = places_model.encode(layout)  # type: ignore[attr-defined]
        self._save_podcast_library()  # type: ignore[attr-defined]

    def _visible_places(self) -> list[places_model.Place]:
        return places_model.visible(self._places_layout(), enabled=self._cast_area_enabled)  # type: ignore[attr-defined]

    def _place_label(self, place_id: str) -> str:
        library = self._podcast_library  # type: ignore[attr-defined]
        label = places_model.label(library, place_id)
        count = places_model.count(library, place_id, unread_notices=self._unread_notice_count())
        return f"{label} ({count})" if count else label

    def _unread_notice_count(self) -> int:
        try:
            from quill.core.notifications import load_notifications, unread_count

            return int(unread_count(load_notifications()))
        except Exception:  # noqa: BLE001 - a list that cannot be read counts nothing
            return 0

    def _rebuild_places(self, *, keep: str = "") -> None:
        rows = [(entry.id, self._place_label(entry.id)) for entry in self._visible_places()]
        places = getattr(self, "_places", None)
        if places is not None:
            places.set_rows(rows, keep=keep or self._current_place)

    def _refresh_place_counts(self) -> None:
        places = getattr(self, "_places", None)
        if places is None:
            return
        for entry in self._visible_places():
            places.relabel(entry.id, self._place_label(entry.id))

    # -- showing a place ------------------------------------------------------------ #

    def show_place(self, place_id: str, *, focus: bool = True, keep: Any = None) -> bool:
        """Land on *place_id*: fill the pane, name it, focus it, say if it is empty."""
        if places_model.place(place_id) is None:
            return False
        pane = getattr(self, "_content", None)
        if pane is None:
            return False
        changed = place_id != self._current_place
        self._current_place = place_id
        self._place_opened_inbox_folder = ""
        self._place_opened_show_id = ""
        self._place_opened_playlist_id = ""
        places = getattr(self, "_places", None)
        if places is not None and places.selected != place_id:
            places.select(place_id)
        self._fill_place(place_id, keep=keep)
        if focus:
            pane.focus()
        if changed or focus:
            self._say_empty_place_once(place_id)
        return True

    def _fill_place(self, place_id: str, *, keep: Any = None) -> None:
        from quill.core.podcasts import queue as queue_ops
        from quill.core.podcasts.virtual_views import favorite_shows, virtual_view_pairs

        library = self._podcast_library  # type: ignore[attr-defined]
        pane = self._content  # type: ignore[attr-defined]
        entry = places_model.place(place_id)
        if entry is None:
            return
        kind = entry.kind
        if kind == places_model.KIND_TREE:
            pane.show(pane.TREE)
            self._reload_library_tree(keep_key=keep)  # type: ignore[attr-defined]
        elif kind == places_model.KIND_PODCASTS:
            pane.show(pane.LIST)
            self._fill_podcast_rows(favorite_shows(library))  # type: ignore[attr-defined]
            self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
        elif kind == places_model.KIND_PLAYLISTS:
            pane.show(pane.LIST)
            self._fill_playlist_rows()  # type: ignore[attr-defined]
            self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
        elif kind == places_model.KIND_NOTICES:
            pane.show(pane.LIST)
            from quill.core.notifications import load_notifications, newest_first

            try:
                notices = newest_first(load_notifications())
            except Exception:  # noqa: BLE001
                notices = []
            self._fill_notice_rows(notices)  # type: ignore[attr-defined]
            self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
        else:
            pane.show(pane.LIST)
            if place_id == "queue":
                pairs = [
                    resolved
                    for resolved in (queue_ops.resolve(library, item) for item in library.queue)
                    if resolved is not None
                ]
            elif place_id == "downloads":
                pairs = [
                    (show, ep)
                    for show in library.shows
                    for ep in show.episodes
                    if ep.downloaded_path
                ]
            elif place_id == "personal_audio":
                pairs = [
                    (show, ep) for show in library.shows if show.is_local for ep in show.episodes
                ]
            else:
                pairs = list(virtual_view_pairs(library, place_id))
            if place_id == "inbox":
                from quill.ui.podcasts.inbox_view import fill_inbox

                fill_inbox(self, pairs)
            else:
                self._fill_episodes_from_pairs(pairs)  # type: ignore[attr-defined]
            self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
        pane.set_heading(self._place_heading(place_id))
        self._refresh_place_counts()
        self._refresh_selection_buttons()  # type: ignore[attr-defined]
        self._refresh_notes_pane()  # type: ignore[attr-defined]

    def _place_heading(self, place_id: str) -> str:
        return self._place_label(place_id)

    def _refresh_place(self, *, keep: bool = True) -> None:
        """Refill whatever is showing, the cursor back on the row it was on."""
        if not self._current_place:
            return
        key = self._selected_tree_data() if keep else None  # type: ignore[attr-defined]
        episodes = getattr(self, "_episodes", None)
        self._list_previous_index = episodes.GetFirstSelected() if keep and episodes else -1
        if self._place_opened_playlist_id:
            self._open_playlist_in_place(self._place_opened_playlist_id, keep=key)
            return
        if getattr(self, "_place_opened_inbox_folder", ""):
            from quill.ui.podcasts.inbox_view import open_inbox_folder

            open_inbox_folder(self, self._place_opened_inbox_folder, keep=key)
            return
        if self._place_opened_show_id:
            show = self._podcast_library.find_show(self._place_opened_show_id)  # type: ignore[attr-defined]
            if show is not None:
                self._fill_episodes(show)  # type: ignore[attr-defined]
                self._select_list_key(key) or self._select_list_row(0)  # type: ignore[attr-defined]
                self._refresh_place_counts()
                return
        self._fill_place(self._current_place, keep=key)

    def _say_empty_place_once(self, place_id: str) -> None:
        library = self._podcast_library  # type: ignore[attr-defined]
        if places_model.count(library, place_id, unread_notices=self._unread_notice_count()):
            self._place_announced_empty = ""
            return
        if self._place_announced_empty == place_id:
            return
        self._place_announced_empty = place_id
        said = places_model.empty_state(library, place_id)
        if said:
            self._announce(said)  # type: ignore[attr-defined]

    # -- a podcast opened in place (Favorites, Enter) --------------------------------- #

    def _open_show_in_place(self, show: Any) -> None:
        """Favorites > Enter: that podcast's episodes, in place; Backspace returns."""
        pane = self._content  # type: ignore[attr-defined]
        from quill.core.podcasts.sorting import unheard_count

        self._place_opened_show_id = show.id
        pane.show(pane.LIST)
        self._fill_episodes(show)  # type: ignore[attr-defined]
        self._select_list_row(0)  # type: ignore[attr-defined]
        count = unheard_count(show)
        pane.set_heading(f"{show.title} ({count} unheard)" if count else show.title)
        pane.focus()
        self._refresh_selection_buttons()  # type: ignore[attr-defined]
        self._refresh_notes_pane()  # type: ignore[attr-defined]

    def _open_playlist_in_place(self, playlist_id: str, *, keep: Any = None) -> None:
        """Playlists > Enter: the playlist's episodes, in place; Backspace returns."""
        from quill.core.podcasts.playlists import resolve_playlist

        library = self._podcast_library  # type: ignore[attr-defined]
        playlist = next((p for p in library.playlists if p.id == playlist_id), None)
        if playlist is None:
            return
        pane = self._content  # type: ignore[attr-defined]
        self._place_opened_playlist_id = playlist_id
        pane.show(pane.LIST)
        pairs = list(resolve_playlist(library, playlist))
        self._fill_episodes_from_pairs(pairs)  # type: ignore[attr-defined]
        self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
        pane.set_heading(f"{playlist.name} ({len(pairs)})" if pairs else playlist.name)
        self._refresh_selection_buttons()  # type: ignore[attr-defined]
        self._refresh_notes_pane()  # type: ignore[attr-defined]

    def _back_from_show_in_place(self) -> bool:
        folder_id = getattr(self, "_place_opened_inbox_folder", "")
        if folder_id:
            self._place_opened_inbox_folder = ""
            self._fill_place(self._current_place, keep=("inbox_folder", folder_id))
            self._content.focus()  # type: ignore[attr-defined]
            return True
        if self._place_opened_playlist_id:
            playlist_id = self._place_opened_playlist_id
            self._place_opened_playlist_id = ""
            self._fill_place(self._current_place, keep=("playlist", playlist_id))
            self._content.focus()  # type: ignore[attr-defined]
            return True
        if not self._place_opened_show_id:
            return False
        show_id = self._place_opened_show_id
        self._place_opened_show_id = ""
        self._fill_place(self._current_place, keep=("show", show_id))
        self._content.focus()  # type: ignore[attr-defined]
        return True

    # -- the Places list's own events -------------------------------------------------- #

    def _on_place_changed(self, place_id: str) -> None:
        self.show_place(place_id, focus=False)

    def _on_place_entered(self, place_id: str) -> None:
        self.show_place(place_id, focus=True)

    def _on_place_hide(self, place_id: str) -> None:
        layout = places_model.hide(self._places_layout(), place_id)
        shown = [
            entry.id for entry in places_model.visible(layout, enabled=self._cast_area_enabled)
        ]  # type: ignore[attr-defined]
        if not shown:
            self._announce("That is the last place; it stays.")  # type: ignore[attr-defined]
            return
        name = places_model.label(self._podcast_library, place_id)  # type: ignore[attr-defined]
        self._save_places_layout(layout)
        next_id = shown[0]
        self._rebuild_places(keep=next_id)
        self.show_place(next_id, focus=False)
        self._announce(f"{name} hidden. View > Places shows it again; Ctrl+Z puts it back.")  # type: ignore[attr-defined]
        undo = getattr(self, "_remember_undo", None)
        if callable(undo):
            undo(f"hiding {name}", lambda: self._on_place_show(place_id))

    def _on_place_show(self, place_id: str) -> None:
        self._save_places_layout(places_model.show(self._places_layout(), place_id))
        self._rebuild_places(keep=place_id)
        self._announce(f"{places_model.label(self._podcast_library, place_id)} shown.")  # type: ignore[attr-defined]

    def _on_place_rename(self, place_id: str) -> None:
        from quill.ui.podcasts.folder_prompt import name_prompt

        library = self._podcast_library  # type: ignore[attr-defined]
        current = places_model.label(library, place_id)
        name = name_prompt(self.frame, "Rename Place", current, announce=self._announce)  # type: ignore[attr-defined]
        if name is None:
            return
        entry = places_model.place(place_id)
        shipped = entry.label if entry is not None else place_id
        if name == shipped:
            library.settings.view_names.pop(place_id, None)
        else:
            library.settings.view_names[place_id] = name
        self._save_podcast_library()  # type: ignore[attr-defined]
        self._rebuild_places(keep=place_id)
        self._announce(f"Renamed to {name}.")  # type: ignore[attr-defined]

    def _move_place(self, place_id: str, delta: int) -> None:
        layout = self._places_layout()
        moved = places_model.move(layout, place_id, delta)
        if moved == layout:
            self._announce("It is already at the end.")  # type: ignore[attr-defined]
            return
        self._save_places_layout(moved)
        self._rebuild_places(keep=place_id)
        name = places_model.label(self._podcast_library, place_id)  # type: ignore[attr-defined]
        self._announce(places_model.move_sentence(moved, place_id, name))  # type: ignore[attr-defined]

    def _on_place_menu(self, place_id: str) -> None:
        from quill.ui.podcasts.context_menus import place_menu

        place_menu(self, place_id)

    def open_places_chooser(self) -> None:
        """View > Places...: reorder, show, hide, rename, reset."""
        from quill.ui.podcasts.places_chooser import open_places_chooser

        open_places_chooser(self)

    # -- the content list's keys ---------------------------------------------------------- #

    def _on_content_list_key(self, event: Any) -> None:
        import wx

        code = event.GetKeyCode()
        selected = self._list_selected_data()  # type: ignore[attr-defined]
        if selected is not None and selected[0] == "notice":
            # ear.md R9: Play Now and Add to Queue on the notice itself.
            if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and event.ControlDown():
                self._notice_verb(selected[1], "play")
                return
            if code == wx.WXK_SPACE and not event.HasAnyModifiers():
                self._notice_verb(selected[1], "queue")
                return
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._activate_content_row(selected)
            return
        if code == wx.WXK_SPACE and selected is not None and selected[0] == "episode":
            self._queue_selected_episode()
            return
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._remove_from_place(selected)
            return
        if code == wx.WXK_BACK:
            if not self._back_from_show_in_place():
                self._places.focus()  # type: ignore[attr-defined]
            return
        if code == wx.WXK_LEFT and self._episodes.GetFirstSelected() <= 0:  # type: ignore[attr-defined]
            self._places.focus()  # type: ignore[attr-defined]
            return
        if code == wx.WXK_F2 and selected is not None and selected[0] == "episode":
            pair = self._selected_episode()  # type: ignore[attr-defined]
            if pair is not None:
                self._on_rename_episode(pair[1])  # type: ignore[attr-defined]
            return
        if event.ControlDown() and wx.WXK_1 <= code <= wx.WXK_9 and selected is not None:
            if selected[0] == "episode":
                from quill.ui.podcasts.manager_menus import direct_key_action

                actions = self._resolved_episode_actions()  # type: ignore[attr-defined]
                resolved = direct_key_action(actions, code - wx.WXK_0)
                if resolved is None:
                    self._announce("No Quick Action on that key.")  # type: ignore[attr-defined]
                elif not resolved.enabled:
                    self._announce(resolved.unavailable_sentence())  # type: ignore[attr-defined]
                else:
                    resolved.run()
                return
        event.Skip()

    def _activate_content_row(self, selected: tuple[str, str] | None) -> None:
        if selected is None:
            return
        kind, value = selected
        if kind == "episode":
            actions = self._resolved_episode_actions()  # type: ignore[attr-defined]
            if actions and actions[0].enabled:
                actions[0].run()
                return
            show_id, _, guid = value.partition("\x00")
            self._play_specific_episode(show_id, guid)  # type: ignore[attr-defined]
        elif kind == "show":
            show = self._podcast_library.find_show(value)  # type: ignore[attr-defined]
            if show is not None:
                self._open_show_in_place(show)
        elif kind == "notice":
            self._open_notice(value)
        elif kind == "playlist":
            self._open_playlist_in_place(value)
            self._content.focus()  # type: ignore[attr-defined]
        elif kind == "inbox_folder":
            from quill.ui.podcasts.inbox_view import open_inbox_folder

            open_inbox_folder(self, value)

    def _queue_selected_episode(self) -> None:
        from quill.core.podcasts import queue as queue_ops

        pair = self._selected_episode()  # type: ignore[attr-defined]
        if pair is None:
            return
        show, episode = pair
        if queue_ops.add_to_queue(self._podcast_library, show.id, episode.guid):  # type: ignore[attr-defined]
            self._save_podcast_library()  # type: ignore[attr-defined]
            self._refresh_place_counts()
            say_outcome(
                self, f"Added {episode.title} to the Play Queue.", sound=SoundEvent.CAST_QUEUE_ADDED
            )
        else:
            self._announce(f"{episode.title} is already in the Play Queue.")  # type: ignore[attr-defined]

    def _remove_from_place(self, selected: tuple[str, str] | None) -> None:
        """Delete: out of *this place*, never out of the library."""
        if selected is None:
            return
        kind, value = selected
        place_id = self._current_place
        library = self._podcast_library  # type: ignore[attr-defined]
        if self._place_opened_playlist_id:
            self._announce(  # type: ignore[attr-defined]
                "Delete does nothing inside a playlist. Its rules, or Add to "
                "Playlist, decide what is in it."
            )
            return
        if self._place_opened_show_id or place_id == "podcasts":
            self._on_library_remove()  # type: ignore[attr-defined]
            return
        if kind == "show" and place_id == "favorites":
            show = library.find_show(value)
            if show is not None:
                show.is_favorite = False
                self._save_podcast_library()  # type: ignore[attr-defined]
                self._refresh_place(keep=True)
                self._announce(f"Removed {show.title} from Favorites. It is still followed.")  # type: ignore[attr-defined]
            return
        if kind == "notice":
            self._dismiss_notice(value)
            return
        if kind == "playlist":
            playlist = next((p for p in library.playlists if p.id == value), None)
            if playlist is not None:
                self._on_delete_playlist(playlist)  # type: ignore[attr-defined]
            return
        pair = self._selected_episode()  # type: ignore[attr-defined]
        if pair is None:
            return
        show, episode = pair
        said = ""
        if place_id == "queue":
            from quill.core.podcasts import queue as queue_ops

            index = next(
                (
                    i
                    for i, item in enumerate(library.queue)
                    if item.show_id == show.id and item.episode_guid == episode.guid
                ),
                -1,
            )
            if index >= 0 and queue_ops.remove_at(library, index):
                said = f"Removed {episode.title} from the Play Queue. It stays in {show.title}."
        elif place_id == "inbox":
            from quill.core.podcasts.inbox import REMOVED_MARKER, inbox_key

            library.inbox_assignments[inbox_key(show.id, episode.guid)] = REMOVED_MARKER
            said = f"Removed {episode.title} from the Inbox. It is still unheard in {show.title}."
            # Earshot R4: with "Delete downloads when done" on, an episode you
            # dismiss is done with, so its file goes too -- unless it is kept.
            from quill.core.podcasts import retention

            if (
                episode.downloaded_path
                and library.effective_settings(show).delete_after_play
                and not retention.is_protected(library, show, episode)
                and retention.remove_downloaded_copy(episode)
            ):
                said += " Its download was deleted."
        elif place_id == "downloads":
            from quill.core.podcasts.retention import remove_downloaded_copy

            if remove_downloaded_copy(episode):
                said = f"Removed the downloaded copy of {episode.title}. It still streams."
        elif place_id == "continue_listening":
            from quill.core.podcasts.position_sync import remember_position

            remember_position(episode, 0)
            said = f"Forgot your place in {episode.title}. It will start from the beginning."
        elif place_id == "recently_expired":
            self._on_forget_expired((show, episode))  # type: ignore[attr-defined]
            self._refresh_place(keep=False)
            return
        elif place_id == "new_episodes":
            from quill.core.podcasts import retention
            from quill.core.podcasts.position_sync import mark_played

            mark_played(episode)
            retention.on_episode_played(library, show, episode)
            said = f"Marked {episode.title} as played. It stays in {show.title}."
        else:
            self._announce(
                "Delete does nothing here. Unfollow removes a podcast; "
                "Remove Download frees a file."
            )  # type: ignore[attr-defined]
            return
        if not said:
            return
        self._save_podcast_library()  # type: ignore[attr-defined]
        # keep=True: the row has gone, so the cursor lands on the one that moved
        # into its place rather than back at the top (qc.md F-10).
        self._refresh_place(keep=True)
        if place_id == "new_episodes":
            say_outcome(self, said, sound=SoundEvent.CAST_MARKED_PLAYED)
        else:
            say_outcome(self, said, sound=SoundEvent.CAST_REMOVED)

    # -- notices in the list ------------------------------------------------------------------ #

    def _notice_by_id(self, notice_id: str) -> Any:
        from quill.core.notifications import load_notifications

        try:
            return next((n for n in load_notifications() if n.id == notice_id), None)
        except Exception:  # noqa: BLE001
            return None

    def _open_notice(self, notice_id: str) -> None:
        from quill.core.notifications import mark_read

        notice = self._notice_by_id(notice_id)
        if notice is None:
            return
        if not notice.read:
            mark_read(notice.id)
            self._refresh_place(keep=True)
        target = str(getattr(notice, "target", "") or "")
        if not target:
            self._announce("There is nothing to open for this one.")  # type: ignore[attr-defined]
            return
        self.open_notification_target(target)  # type: ignore[attr-defined]

    def _notice_verb(self, notice_id: str, verb: str) -> None:
        """Play Now ("play") or Add to Queue ("queue") on a notice row."""
        from quill.ui.podcasts import notice_actions

        notice = self._notice_by_id(notice_id)
        if notice is None:
            return
        done = (
            notice_actions.play_now(self, notice)
            if verb == "play"
            else notice_actions.add_to_queue(self, notice)
        )
        if done:
            self._refresh_place(keep=True)

    def _dismiss_notice(self, notice_id: str) -> None:
        from quill.core.notifications import load_notifications, save_notifications

        try:
            entries = load_notifications()
            kept = [n for n in entries if n.id != notice_id]
            if len(kept) == len(entries):
                return
            save_notifications(kept)
        except Exception:  # noqa: BLE001
            return
        self._refresh_place(keep=False)
        self._announce("Notification removed. Nothing it was about was touched.")  # type: ignore[attr-defined]
