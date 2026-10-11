"""Fill Cast's content pane, yielding the opening of a large-library place."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from quill.core.podcasts import places as places_model

logger = logging.getLogger(__name__)


class CastPlaceContentMixin:
    def _fill_place(self, place_id: str, *, keep: Any = None, focus: bool = False) -> bool:
        """Return whether an asynchronous preparation owns the remaining opening."""
        from quill.core.podcasts import queue as queue_ops
        from quill.core.podcasts.virtual_views import favorite_shows, virtual_view_pairs

        library = self._podcast_library  # type: ignore[attr-defined]
        pane = self._content  # type: ignore[attr-defined]
        entry = places_model.place(place_id)
        if entry is None:
            return False
        kind = entry.kind
        if self._podcast_library_is_large():  # type: ignore[attr-defined]
            initial_focus = self._wx.Window.FindFocus() if focus else None  # type: ignore[attr-defined]
            self._request_cast_view_preparation(  # type: ignore[attr-defined]
                place_id,
                keep=keep,
                initialize=lambda: self._loading_place_chunks(
                    place_id, focus=focus, initial_focus=initial_focus
                ),
            )
            return True
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
            except Exception:
                logger.exception("Could not read Cast notifications")
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
        self._refresh_place_counts()  # type: ignore[attr-defined]
        self._refresh_selection_buttons()  # type: ignore[attr-defined]
        self._refresh_notes_pane()  # type: ignore[attr-defined]
        return False

    def _place_heading(self, place_id: str) -> str:
        return self._place_label(place_id)  # type: ignore[attr-defined]

    def _loading_place_chunks(
        self, place_id: str, *, focus: bool, initial_focus: Any
    ) -> Generator[None]:
        entry = places_model.place(place_id)
        if entry is None or self._current_place != place_id:  # type: ignore[attr-defined]
            return
        pane = self._content  # type: ignore[attr-defined]
        pane.show(pane.TREE if entry.kind == places_model.KIND_TREE else pane.LIST)
        yield
        if self._current_place != place_id:  # type: ignore[attr-defined]
            return
        pane.set_heading(
            f"{places_model.label(self._podcast_library, place_id)} (loading...)"  # type: ignore[attr-defined]
        )
        yield
        if (
            focus
            and self._current_place == place_id  # type: ignore[attr-defined]
            and self._wx.Window.FindFocus() is initial_focus  # type: ignore[attr-defined]
        ):
            pane.focus()
        yield
