"""Quill Media Player's bookmarks: add, note, edit, copy, export, remove, jump.

Moved out of ``player.py`` (2026-11-04), which sat at its GATE-11 budget, to make
room for opening a web address. Every method reads the frame's ``_player``,
``_book_key``, ``_bookmarks`` (a :class:`~quill.core.media.bookmarks.BookmarkStore`)
and ``_bookmarks_list``; the window owns those, this owns what is done with them.
The note prompt (``_prompt_text``) stays in the frame, where the dialog inventory
finds it.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.media import format_spoken
from quill.core.media.bookmarks import MediaBookmark

__all__ = ["PlayerBookmarksMixin"]

_PLAYER_TITLE = "Quill Media Player"


class PlayerBookmarksMixin:
    """The Bookmarks menu's handlers and the bookmark list, for the Player frame."""

    _player: Any
    _book_key: str
    _bookmarks: Any
    _bookmarks_list: Any
    _now_playing: Any

    def _on_add_bookmark(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a file first.", _PLAYER_TITLE)
            return
        position = self._player.playhead_ms()
        self._bookmarks.add(self._book_key, position)
        self._refresh_bookmarks()
        self._announce(f"Bookmark added at {format_spoken(position)}.")

    def _on_add_bookmark_note(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a file first.", _PLAYER_TITLE)
            return
        note = self._prompt_text("Add Bookmark", "Note for this bookmark:", "")
        if note is None:
            return
        position = self._player.playhead_ms()
        self._bookmarks.add(self._book_key, position, note=note)
        self._refresh_bookmarks()
        self._announce(f"Bookmark added at {format_spoken(position)}.")

    def _on_edit_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        note = self._prompt_text("Edit Bookmark", "Note:", mark.note)
        if note is None:
            return
        self._bookmarks.add(self._book_key, mark.position_ms, label=mark.label, note=note)
        self._refresh_bookmarks()
        self._announce("Bookmark note updated.")

    def _on_copy_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        from quill.ui.media.bookmark_actions import copy_bookmark_to_clipboard

        copy_bookmark_to_clipboard(self, mark, self._now_playing.GetValue())

    def _on_export_bookmarks(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a book first.", _PLAYER_TITLE)
            return
        from quill.ui.media.bookmark_actions import export_bookmarks_markdown

        export_bookmarks_markdown(
            self, self._now_playing.GetValue(), self._bookmarks.list(self._book_key)
        )

    def _on_export_sync(self, _event: Any) -> None:
        from quill.ui.media.bookmark_actions import export_sync_bundle

        export_sync_bundle(self, self._bookmarks)

    def _on_import_sync(self, _event: Any) -> None:
        from quill.ui.media.bookmark_actions import import_sync_bundle

        import_sync_bundle(self, self._bookmarks, self._refresh_bookmarks)

    def _on_remove_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        self._bookmarks.remove(self._book_key, mark.position_ms)
        self._refresh_bookmarks()
        self._announce("Bookmark removed.")

    def _on_bookmark_activate(self, _control: object) -> None:
        mark = self._selected_bookmark()
        if mark is not None:
            self._player.seek_to(mark.position_ms)

    def _selected_bookmark(self) -> MediaBookmark | None:
        index = self._bookmarks_list.GetSelection()
        marks = self._bookmarks.list(self._book_key) if self._book_key else []
        if index == wx.NOT_FOUND or not (0 <= index < len(marks)):
            return None
        return marks[index]

    def _refresh_bookmarks(self) -> None:
        self._bookmarks_list.Clear()
        for mark in self._bookmarks.list(self._book_key) if self._book_key else []:
            when = format_spoken(mark.position_ms)
            note = mark.note or mark.label
            self._bookmarks_list.Append(f"{note} ({when})" if note else when)
