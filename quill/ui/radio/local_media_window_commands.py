"""What each Local Media window command does: one ``cmd_<verb>`` per menu row.

Mixed into :class:`~quill.ui.radio.local_media_window.LocalMediaWindow`. Each
method reads the window's selection, hands it to the shared verb (the same
function the Browse tree's menu calls), and puts the selection back where the
items went. The window itself only knows layout, refreshing and keys.

Selection is the listener's, always: after an edit the moved or pasted items
are selected and the cursor is on the first of them; after a removal the
cursor lands on whatever took the first removed item's place. Nothing here
moves focus between controls.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.local_media import Playlist
from quill.ui.radio import local_media_edit_ui as edit_ui
from quill.ui.radio import local_media_manage as manage
from quill.ui.radio import local_media_playback as playback
from quill.ui.radio import local_media_ui as ui

__all__ = ["LocalMediaCommandsMixin"]


class LocalMediaCommandsMixin:
    """The window's verbs. The host class supplies the selection helpers."""

    _host: Any

    # The window supplies _playlist, _rows, _focus_row, _playlists_focused,
    # reload and _win; this class only ever calls them.

    def _need_playlist(self) -> Playlist | None:
        playlist = self._playlist()
        if playlist is None:
            ui.announce(self._host, "There is no playlist yet. New Playlist makes one.")
        return playlist

    def _need_rows(self, playlist: Playlist) -> list[int]:
        rows = self._rows()
        if not rows and playlist.items:
            focused = self._focus_row()
            rows = [focused] if focused >= 0 else []
        if not rows:
            ui.announce(self._host, "Select an item first.")
        return rows

    def _selected_items(self) -> list[Any]:
        playlist = self._playlist()
        if playlist is None:
            return []
        return [playlist.items[row] for row in self._rows() if 0 <= row < len(playlist.items)]

    def _item_at_focus(self) -> Any:
        playlist = self._playlist()
        row = self._focus_row()
        if playlist is None or not 0 <= row < len(playlist.items):
            return None
        return playlist.items[row]

    def _after_rows(self, playlist: Playlist, rows: list[int]) -> None:
        self.reload(select_playlist=playlist.id, select_rows=rows)

    # -- Local Media menu ---------------------------------------------------------

    def cmd_new_playlist(self) -> None:
        made = manage.new_playlist(self._host)
        if made is not None:
            self.reload(select_playlist=made.id, focus="add")

    def _add(self, *, folder: bool, position: int | None) -> None:
        playlist = self._playlist()
        if folder:
            chosen = ui.ask_folder(self._host)
            paths = [chosen] if chosen else []
        else:
            paths = ui.ask_files(self._host)
        if not paths:
            return
        target = playlist.id if playlist is not None else ""

        def _then(made: Playlist, ids: list[int]) -> None:
            rows = [made.index_of(item_id) for item_id in ids]
            self.reload(select_playlist=made.id, select_rows=rows, focus="items")

        ui.add_paths(
            self._host,
            paths,
            playlist_id=target,
            position=position,
            folder=paths[0] if folder and not target else "",
            then=_then,
        )

    def cmd_add_files(self) -> None:
        self._add(folder=False, position=None)

    def cmd_add_folder(self) -> None:
        self._add(folder=True, position=None)

    def _insert_position(self, *, after: bool) -> int | None:
        playlist = self._playlist()
        if playlist is None or not playlist.items:
            return None
        row = self._focus_row()
        if row < 0:
            return None
        return row + 1 if after else row

    def cmd_insert_before(self) -> None:
        self._add(folder=False, position=self._insert_position(after=False))

    def cmd_insert_after(self) -> None:
        self._add(folder=False, position=self._insert_position(after=True))

    def cmd_import_playlist(self) -> None:
        manage.import_playlist(self._host)

    def cmd_export_playlist(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            manage.export_playlist(self._host, playlist.id)

    def cmd_rename(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None and manage.rename_playlist(self._host, playlist.id):
            self.reload(select_playlist=playlist.id)

    def cmd_save_opened(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None and manage.save_opened(self._host, playlist.id):
            self.reload(select_playlist=playlist.id)

    def cmd_duplicate(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            twin = manage.duplicate_playlist(self._host, playlist.id)
            if twin is not None:
                self.reload(select_playlist=twin.id)

    def cmd_delete_playlist(self) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        lib = ui.library(self._host)
        index = lib.index_of(playlist.id)
        if manage.delete_playlist(self._host, playlist.id):
            remaining = lib.playlists
            landing = remaining[min(index, len(remaining) - 1)].id if remaining else ""
            self.reload(select_playlist=landing, focus="playlists")

    def cmd_follow_folder(self) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        if not playlist.folder:
            ui.announce(
                self._host,
                f"{playlist.name} was not made from a folder. Add a Folder makes one that is.",
            )
            return
        playlist.watch = not playlist.watch
        ui.commit(self._host, source=self)
        self.reload(select_playlist=playlist.id)
        if playlist.watch:
            ui.announce(self._host, "New files in the folder will be added whenever it opens.")
            ui.rescan_folder(self._host, playlist.id, quiet=True)
        else:
            ui.announce(self._host, "No longer following the folder. The list stays as it is.")

    def cmd_rescan(self) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        if not playlist.folder:
            ui.announce(self._host, f"{playlist.name} was not made from a folder.")
            return
        ui.rescan_folder(self._host, playlist.id)

    def cmd_columns(self) -> None:
        from quill.ui.radio.list_columns_command import open_list_columns

        open_list_columns(self._host)
        rebuild = getattr(self, "_rebuild_columns", None)
        if callable(rebuild):
            rebuild()

    def cmd_close(self) -> None:
        self._win.Close()  # type: ignore[attr-defined]

    # -- Edit menu ------------------------------------------------------------------

    def cmd_undo(self) -> None:
        undo = getattr(ui.app_of(self._host), "undo_last_action", None)
        if not callable(undo):
            ui.announce(self._host, "Undo is not available here.")
            return
        undo()
        self.reload()

    def cmd_cut(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            edit_ui.cut_items(self._host, playlist, self._need_rows(playlist))

    def cmd_copy(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            edit_ui.copy_items(self._host, playlist, self._need_rows(playlist))

    def _paste(self, *, after: bool) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        row = self._focus_row()
        position = len(playlist.items) if row < 0 else row + (1 if after else 0)
        rows = edit_ui.paste(self._host, playlist, position, source=self)
        if rows:
            self._after_rows(playlist, rows)

    def cmd_paste_before(self) -> None:
        self._paste(after=False)

    def cmd_paste_after(self) -> None:
        self._paste(after=True)

    def cmd_remove(self) -> None:
        if self._playlists_focused():
            self.cmd_delete_playlist()
            return
        playlist = self._need_playlist()
        if playlist is None:
            return
        rows = self._need_rows(playlist)
        if rows:
            landing = edit_ui.remove_rows(self._host, playlist, rows, source=self)
            self._after_rows(playlist, [landing] if landing >= 0 else [])

    def cmd_remove_missing(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None and manage.remove_missing(self._host, playlist.id):
            self.reload(select_playlist=playlist.id)

    def cmd_select_all(self) -> None:
        playlist = self._playlist()
        if playlist is None or not playlist.items:
            return
        self.reload(select_playlist=playlist.id, select_rows=list(range(len(playlist.items))))
        count = len(playlist.items)
        ui.announce(self._host, f"Selected all {count} item{'' if count == 1 else 's'}.")

    def cmd_properties(self) -> None:
        playlist, item = self._playlist(), self._item_at_focus()
        if playlist is not None and item is not None:
            manage.properties(self._host, playlist.id, item.id)

    def cmd_show_in_folder(self) -> None:
        item = self._item_at_focus()
        if item is not None:
            manage.show_in_folder(self._host, item)

    def cmd_locate(self) -> None:
        playlist, item = self._playlist(), self._item_at_focus()
        if playlist is None or item is None:
            return
        if item.exists():
            missing = playlist.missing()
            if not missing:
                ui.announce(self._host, f"Nothing in {playlist.name} is missing.")
                return
            item = missing[0]
        if manage.locate(self._host, playlist.id, item.id):
            self.reload(select_playlist=playlist.id, select_rows=[playlist.index_of(item.id)])

    # -- Arrange menu -------------------------------------------------------------

    def _move_playlist(self, delta: int, *, to_end: bool = False) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        from quill.core.radio import local_media_edit as edit

        lib = ui.library(self._host)
        index = lib.index_of(playlist.id)
        if to_end:
            lib.playlists, rows = edit.move_to(lib.playlists, [index], delta)
        else:
            lib.playlists, rows = edit.move_by(lib.playlists, [index], delta)
        ui.commit(self._host, source=self)
        self.reload(select_playlist=playlist.id, focus="playlists")
        ui.announce(self._host, edit.moved_sentence(rows, len(lib.playlists)))

    def _move(self, delta: int) -> None:
        if self._playlists_focused():
            self._move_playlist(delta)
            return
        playlist = self._need_playlist()
        if playlist is not None:
            rows = self._need_rows(playlist)
            if rows:
                self._after_rows(
                    playlist, edit_ui.move(self._host, playlist, rows, delta, source=self)
                )

    def _move_to(self, position: int) -> None:
        if self._playlists_focused():
            self._move_playlist(position, to_end=True)
            return
        playlist = self._need_playlist()
        if playlist is not None:
            rows = self._need_rows(playlist)
            if rows:
                self._after_rows(
                    playlist, edit_ui.move_to(self._host, playlist, rows, position, source=self)
                )

    def cmd_move_up(self) -> None:
        self._move(-1)

    def cmd_move_down(self) -> None:
        self._move(1)

    def cmd_move_top(self) -> None:
        self._move_to(0)

    def cmd_move_bottom(self) -> None:
        self._move_to(10**9)

    def cmd_move_to(self) -> None:
        playlist = self._need_playlist()
        if playlist is None or not self._need_rows(playlist):
            return
        total = len(playlist.items)
        answer = ui.ask_text(
            self._host, f"Move to which position, 1 to {total}?", "Move to Position"
        )
        if answer is None:
            return
        if not answer.isdigit() or not 1 <= int(answer) <= total:
            ui.announce(self._host, f"Type a number from 1 to {total}.")
            return
        self._move_to(int(answer) - 1)

    def cmd_sort(self) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        import wx

        from quill.core.radio.local_media_edit import SORT_KEYS

        labels = [label for _key, label in SORT_KEYS]
        with wx.SingleChoiceDialog(
            self._win,  # type: ignore[attr-defined]
            f"Sort {playlist.name} by:",
            "Sort Playlist",
            labels,
        ) as chooser:
            if ui.show_modal_dialog(self._host, chooser, "Sort Playlist") != wx.ID_OK:
                return
            key = SORT_KEYS[chooser.GetSelection()][0]
        edit_ui.sort(self._host, playlist, key, source=self)
        self.reload(select_playlist=playlist.id, select_rows=[0])

    # -- Play menu ------------------------------------------------------------------

    def cmd_play(self) -> None:
        playlist, item = self._playlist(), self._item_at_focus()
        if playlist is None:
            ui.announce(self._host, "There is nothing to play yet.")
            return
        if item is None:
            playback.play_playlist(self._host, playlist.id)
            return
        playing_list, playing = playback.current(self._host)
        if playing is not None and playing_list is not None and playing.id == item.id:
            controller = playback.controller_of(self._host)
            controller.stop()
            ui.announce(self._host, "Stopped.")
            return
        playback.play_item(self._host, playlist.id, item.id)

    def cmd_pause(self) -> None:
        controller = playback.controller_of(self._host)
        playing_list, _item = playback.current(self._host)
        if controller is None or playing_list is None:
            ui.announce(self._host, "Nothing from Local Media is playing.")
            return
        paused = playback.is_paused(controller)
        controller.toggle_play_pause()
        ui.announce(self._host, "Resumed." if paused else "Paused.")

    def cmd_next(self) -> None:
        if not playback.step(self._host, 1):
            ui.announce(self._host, "Nothing from Local Media is playing.")

    def cmd_previous(self) -> None:
        if not playback.step(self._host, -1):
            ui.announce(self._host, "Nothing from Local Media is playing.")

    def cmd_play_playlist(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            playback.play_playlist(self._host, playlist.id)

    def cmd_continue(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            playback.continue_playlist(self._host, playlist.id)

    def _queue(self, *, first: bool) -> None:
        playlist = self._need_playlist()
        if playlist is None:
            return
        ids = [item.id for item in self._selected_items()]
        if not ids:
            ui.announce(self._host, "Select an item first.")
            return
        if first:
            playback.play_next(self._host, playlist.id, ids)
        else:
            playback.add_up_next(self._host, playlist.id, ids)

    def cmd_play_next(self) -> None:
        self._queue(first=True)

    def cmd_up_next(self) -> None:
        self._queue(first=False)

    def cmd_shuffle(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            playback.toggle_shuffle(self._host, playlist.id)
            self.reload(select_playlist=playlist.id)

    def cmd_reshuffle(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            playback.reshuffle(self._host, playlist.id)
            self.reload(select_playlist=playlist.id)

    def cmd_repeat(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            playback.cycle_repeat(self._host, playlist.id)
            self.reload(select_playlist=playlist.id)

    def cmd_stop_after(self) -> None:
        playback.toggle_stop_after(self._host)
        self.reload()

    def cmd_summary(self) -> None:
        playlist = self._need_playlist()
        if playlist is not None:
            ui.announce(self._host, playback.summary_sentence(self._host, playlist))
