"""The Local Media window: your playlists, their items, and every verb on them.

A peer window like Radio Recordings and Browse Stations -- its own taskbar
entry, its own menu bar, on the Window menu and in the Ctrl+Tab order -- when
Quill Radio's window manager is there; a modal dialog with the same controls
inside QUILL, which has none.

Two lists, left to right in reading order: **Playlists**, then the **Items** in
the one selected. Enter plays (and on the item playing, stops); Space pauses
and resumes the item playing; Delete removes from the playlist and never from
the disk; Shift+F10 or the Applications key opens everything a row can do.

**The empty state leads somewhere.** With nothing in Local Media at all, the
lists step aside and the window opens on a sentence and three buttons, with
the cursor on **Add Media Files...** -- the one thing anybody arriving there
can usefully do. The sentence is said once on arrival, because it is the one
thing on the screen the reader would not otherwise reach.

**Nothing moves the cursor but the listener.** The playing item is marked in
its own row's text ("playing", "paused") on a one-second tick that touches
only the rows whose words changed, never the selection; edits made elsewhere
(the Browse tree, an undo) rebuild the lists in place, keeping the cursor on
the same item by identity.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.local_media import Playlist
from quill.ui.radio import local_media_playback as playback
from quill.ui.radio import local_media_ui as ui
from quill.ui.radio import local_media_window_menu as menus
from quill.ui.radio.local_media_rows import PAUSED, PLAYING, SURFACE, cells
from quill.ui.radio.local_media_window_commands import LocalMediaCommandsMixin

__all__ = ["EMPTY_SENTENCE", "TITLE", "LocalMediaWindow"]

TITLE = "Local Media"

EMPTY_SENTENCE = (
    "Nothing in Local Media yet. Add Media Files picks music, audiobooks or video "
    "from your computer; Add a Folder brings in a whole folder, in order."
)

_TICK_MS = 1000


class LocalMediaWindow(LocalMediaCommandsMixin):
    """Playlists and their items, played and rearranged from the keyboard."""

    def __init__(
        self,
        parent: Any,
        *,
        host: Any,
        windows: Any = None,
        playlist_id: str = "",
        item_id: int = 0,
    ) -> None:
        import wx

        self._wx = wx
        self._host = ui.app_of(host)
        self._transport_host = self._host
        self._windows = windows
        self._modeless = windows is not None
        self._menu_id_refs: list[Any] = []
        self._menu_items: dict[str, Any] = {}
        self._playlist_ids: list[str] = []
        self._item_ids: list[int] = []
        self._row_text: list[dict[str, str]] = []
        self._marker: tuple[str, int, str] = ("", 0, "")
        self._empty: tuple[bool, bool] | None = None
        self._shown_id = ""
        if self._modeless:
            self._win = wx.Frame(None, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
        else:
            self._win = wx.Dialog(
                parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self._surface = self._win
        self.dialog = self._win
        self._win.SetMinSize((780, 520))
        self._build()
        if self._modeless:
            self._menu_items = menus.install_menu_bar(self, wx, self.run)
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)
        self._keys = menus.key_table(modeless=self._modeless)
        self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._win.Bind(wx.EVT_CLOSE, self._on_close)
        self._timer = wx.Timer(self._win)
        self._win.Bind(wx.EVT_TIMER, lambda _e: self._tick())
        ui.register_window(self._host, self)
        playback.remember_app(self._host)
        self.reload(select_playlist=playlist_id, select_item=item_id)

    # -- building ---------------------------------------------------------------------

    def _button(self, sizer: Any, label: str, verb: str, help_text: str) -> Any:
        wx = self._wx
        button = wx.Button(self._surface, label=label)
        button.SetHelpText(help_text)
        button.Bind(wx.EVT_BUTTON, lambda _e: self.run(verb))
        sizer.Add(button, 0, wx.RIGHT, 6)
        return button

    def _build(self) -> None:
        wx = self._wx
        surface = self._surface
        root = wx.BoxSizer(wx.VERTICAL)
        self._intro = wx.StaticText(surface, label=EMPTY_SENTENCE)
        root.Add(self._intro, 0, wx.ALL, 10)

        lists = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        self._playlists_label = wx.StaticText(surface, label="Pla&ylists:")
        left.Add(self._playlists_label, 0, wx.BOTTOM, 4)
        self._playlists = wx.ListBox(surface, style=wx.LB_SINGLE)
        # A peer window, not a modal dialog: name the lists here (#1012).
        self._playlists.SetName("Playlists")
        self._playlists.SetHelpText(
            "Your playlists, with how many items each holds and how long it plays. "
            "Enter plays the playlist; Tab moves to its items. F2 renames, Delete "
            "deletes it after asking, Alt+Shift+Up and Down move it, and the "
            "Applications key opens everything else."
        )
        self._playlists.SetMinSize((240, 300))
        left.Add(self._playlists, 1, wx.EXPAND)
        lists.Add(left, 0, wx.EXPAND | wx.RIGHT, 10)

        right = wx.BoxSizer(wx.VERTICAL)
        self._items_label = wx.StaticText(surface, label="&Items:")
        right.Add(self._items_label, 0, wx.BOTTOM, 4)
        self._items = wx.ListCtrl(surface, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._items.SetName("Items")
        self._items.SetHelpText(
            "The items in the selected playlist, in the order they play. Enter plays "
            "from here and stops the item playing; Space pauses it. Delete removes "
            "from the playlist, never from your computer. Alt+Shift+Up and Down move "
            "items; Ctrl+X then Ctrl+V moves them somewhere else; Insert adds files "
            "before the item. Type the start of a title to jump to it. The "
            "Applications key opens everything a row can do."
        )
        self._build_columns()
        right.Add(self._items, 1, wx.EXPAND)
        lists.Add(right, 1, wx.EXPAND)
        root.Add(lists, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_files_btn = self._button(
            buttons,
            "Add &Media Files...",
            "add_files",
            "Choose music, audiobooks or video from your computer. In a playlist they "
            "are added at the end; with no playlist yet, one is made, named after their folder.",
        )
        self._add_folder_btn = self._button(
            buttons,
            "Add a &Folder...",
            "add_folder",
            "Choose a folder: every file in it and its folders comes in, in the order "
            "you would read the names, as a playlist that follows the folder.",
        )
        self._new_btn = self._button(
            buttons,
            "&New Playlist...",
            "new_playlist",
            "Name a new, empty playlist to fill afterwards.",
        )
        buttons.AddStretchSpacer()
        if not self._modeless:
            from quill.ui.dialog_contract import bind_close_button

            close = wx.Button(surface, wx.ID_CANCEL, "Close")
            close.SetHelpText("Closes Local Media. Whatever is playing carries on.")
            bind_close_button(self._win, close, modeless=False)
            buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(surface, label="")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        surface.SetSizer(root)

        self._playlists.Bind(wx.EVT_LISTBOX, lambda _e: self._on_playlist_chosen())
        self._playlists.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.run("play_playlist"))
        self._playlists.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._playlist_menu())
        self._items.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.run("play"))
        self._items.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._item_menu())

    def _build_columns(self) -> None:
        from quill.ui.media.list_columns_view import build_columns, columns_for

        self._columns = columns_for("radio", SURFACE)
        build_columns(self._items, self._columns)
        self._row_text = []

    def _rebuild_columns(self) -> None:
        """After Choose Columns: the new layout, now, in this open window."""
        self._build_columns()
        self.reload()

    # -- what is selected --------------------------------------------------------------

    def _playlist(self) -> Playlist | None:
        index = self._playlists.GetSelection()
        if 0 <= index < len(self._playlist_ids):
            return ui.library(self._host).find(self._playlist_ids[index])
        return None

    def _rows(self) -> list[int]:
        rows: list[int] = []
        row = self._items.GetFirstSelected()
        while row >= 0:
            rows.append(row)
            row = self._items.GetNextSelected(row)
        return rows

    def _focus_row(self) -> int:
        row = self._items.GetFocusedItem()
        if row < 0:
            row = self._items.GetFirstSelected()
        return row

    def _playlists_focused(self) -> bool:
        return self._wx.Window.FindFocus() is self._playlists

    def _items_focused(self) -> bool:
        return self._wx.Window.FindFocus() is self._items

    # -- filling ----------------------------------------------------------------------------

    def reload(
        self,
        *,
        select_playlist: str = "",
        select_item: int = 0,
        select_rows: list[int] | None = None,
        focus: str = "",
    ) -> None:
        """Rebuild both lists from the library, keeping the cursor by identity."""
        lib = ui.library(self._host)
        current = self._playlist()
        wanted = select_playlist or (current.id if current is not None else "")
        if not wanted and lib.playlists:
            wanted = lib.playlists[0].id
        labels = [f"{p.name}, {_summary(p)}" for p in lib.playlists]
        ids = [p.id for p in lib.playlists]
        if labels != [self._playlists.GetString(i) for i in range(self._playlists.GetCount())]:
            self._playlists.Set(labels)
        self._playlist_ids = ids
        if wanted in ids:
            self._playlists.SetSelection(ids.index(wanted))
        playlist = self._playlist()
        same = playlist is not None and playlist.id == self._shown_id
        keep = same and select_rows is None and not select_item
        keep_ids = self._selected_ids() if keep else []
        if not same:
            self._row_text = []
            self._items.DeleteAllItems()
        self._fill_items(playlist)
        self._shown_id = playlist.id if playlist is not None else ""
        if playlist is not None:
            if select_item:
                select_rows = [playlist.index_of(select_item)]
            elif select_rows is None:
                select_rows = [playlist.index_of(i) for i in keep_ids]
            self._select_rows([row for row in select_rows if row >= 0])
        self._show_state(lib.total_items() == 0, bool(lib.playlists), focus)
        self._update_status(playlist)
        self._sync_checks(playlist)

    def _selected_ids(self) -> list[int]:
        return [self._item_ids[row] for row in self._rows() if row < len(self._item_ids)]

    def _fill_items(self, playlist: Playlist | None) -> None:
        """Make the items list match *playlist*, touching only rows that changed."""
        items = playlist.items if playlist is not None else []
        name = playlist.name if playlist is not None else ""
        label = f"&Items in {name}:" if name else "&Items:"
        if playlist is not None and not items:
            label = f"&Items in {name} (empty; Ctrl+O adds files):"
        if self._items_label.GetLabel() != label:
            self._items_label.SetLabel(label)
            # The list's own name follows its label (VoiceOver reads the name).
            self._items.SetName(label.replace("&", "").rstrip(":"))
        marker = self._current_marker()
        wanted = [
            cells(
                item,
                marker[2]
                if playlist is not None and marker[0] == playlist.id and marker[1] == item.id
                else "",
            )
            for item in items
        ]
        from quill.ui.media.list_columns_view import fill_row, set_row

        old = len(self._row_text)
        for row in range(min(old, len(wanted))):
            if wanted[row] != self._row_text[row]:
                set_row(self._items, row, self._columns, wanted[row])
        for row in range(old, len(wanted)):
            fill_row(self._items, row, self._columns, wanted[row])
        for row in range(old - 1, len(wanted) - 1, -1):
            self._items.DeleteItem(row)
        self._row_text = wanted
        self._item_ids = [item.id for item in items]
        self._marker = marker

    def _select_rows(self, rows: list[int]) -> None:
        for row in self._rows():
            if row not in rows:
                self._items.Select(row, False)
        for row in rows:
            if 0 <= row < self._items.GetItemCount():
                self._items.Select(row, True)
        if rows and 0 <= rows[0] < self._items.GetItemCount():
            self._items.Focus(rows[0])
            self._items.EnsureVisible(rows[0])

    def _show_state(self, empty: bool, has_playlists: bool, focus: str) -> None:
        """Swap between the empty state and the lists, and place the cursor.

        Empty means no items anywhere. The sentence and the cursor on Add Media
        Files come with it; the lists stay in view once a playlist exists, so
        a playlist somebody has just named is there to be seen, and filled.
        """
        shape = (empty, has_playlists)
        first = self._empty is None
        changed = shape != self._empty
        self._empty = shape
        if changed:
            self._intro.Show(empty)
            for control in (self._playlists_label, self._playlists, self._items_label, self._items):
                control.Show(has_playlists)
            self._surface.Layout()
        target = {
            "add": self._add_files_btn,
            "items": self._items,
            "playlists": self._playlists,
        }.get(focus)
        if empty and (first or focus == "add"):
            target = self._add_files_btn
        if target is not None:
            target.SetFocus()

    def _update_status(self, playlist: Playlist | None) -> None:
        text = "" if playlist is None else playback.summary_sentence(self._host, playlist)
        if self._status.GetLabel() != text:
            self._status.SetLabel(text)

    def _sync_checks(self, playlist: Playlist | None) -> None:
        if not self._menu_items:
            return
        session = playback.session_of(playback.controller_of(self._host))
        states = {
            "shuffle": bool(playlist is not None and playlist.shuffle),
            "follow_folder": bool(playlist is not None and playlist.watch),
            "stop_after": bool(session is not None and session.queue.stop_after_current),
        }
        for verb, on in states.items():
            item = self._menu_items.get(verb)
            if item is not None and item.IsChecked() != on:
                item.Check(on)

    def _current_marker(self) -> tuple[str, int, str]:
        playlist, item = playback.current(self._host)
        if playlist is None or item is None:
            return ("", 0, "")
        controller = playback.controller_of(self._host)
        return (playlist.id, item.id, PAUSED if playback.is_paused(controller) else PLAYING)

    def _tick(self) -> None:
        """Keep "playing" on the right row. Rows are rewritten, never reselected."""
        if self._current_marker() == self._marker:
            return
        self._fill_items(self._playlist())
        self._update_status(self._playlist())
        self._sync_checks(self._playlist())

    def _on_playlist_chosen(self) -> None:
        playlist = self._playlist()
        self.reload(select_rows=[0] if playlist is not None and playlist.items else [])
        if playlist is not None and playlist.folder and playlist.watch:
            ui.rescan_folder(self._host, playlist.id, quiet=True)

    # -- keys and menus ---------------------------------------------------------------------

    def run(self, verb: str) -> None:
        """Run one command by its verb -- a menu item, a key or a button."""
        handler = getattr(self, f"cmd_{verb}", None)
        if callable(handler):
            handler()

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if self._modeless and (
            code == wx.WXK_ESCAPE or (code == wx.WXK_F4 and event.ControlDown())
        ):
            # A frame has no Escape-to-close of its own; every peer window wires it.
            self._win.Close()
            return
        chord = menus.chord_of_event(event, wx)
        if chord in ("Enter", "Space") and (self._items_focused() or self._playlists_focused()):
            self._plain_key(chord)
            return
        verb = self._keys.get(chord)
        if verb is None or (chord in ("Delete", "Insert") and not self._list_focused()):
            event.Skip()
            return
        self.run(verb)

    def _list_focused(self) -> bool:
        return self._items_focused() or self._playlists_focused()

    def _plain_key(self, chord: str) -> None:
        if self._playlists_focused():
            self.run("play_playlist" if chord == "Enter" else "pause")
            return
        if chord == "Enter":
            self.run("play")
            return
        playing_list, playing = playback.current(self._host)
        item = self._item_at_focus()
        if playing is not None and item is not None and playing.id == item.id:
            self.run("pause")
            return
        row = self._focus_row()  # Space anywhere else selects, as it always has
        if row >= 0:
            self._items.Select(row, not self._items.IsSelected(row))

    def _item_menu(self) -> None:
        playlist = self._playlist()
        item = self._item_at_focus()
        if playlist is None or item is None:
            return
        playing_list, playing = playback.current(self._host)
        is_playing = playing is not None and playing.id == item.id
        rows = []
        for verb, label in menus.ITEM_POPUP:
            if verb == "play" and is_playing:
                rows.append(("play", "St&op"))
                continue
            if verb == "pause" and not is_playing:
                continue
            if verb == "locate" and item.exists():
                continue
            if verb == "show_in_folder" and not item.exists():
                continue
            if verb in ("paste_before", "paste_after"):
                from quill.ui.radio.local_media_edit_ui import clip

                if clip(self._host) is None:
                    continue
            rows.append((verb, label))
        menu = menus.popup(self, self._wx, rows, self.run, keys={"play": "Enter", "pause": "Space"})
        try:
            self._items.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _playlist_menu(self) -> None:
        from quill.core.radio import browse_local_media as rows_core
        from quill.ui.radio import local_media_browse

        playlist = self._playlist()
        if playlist is None:
            return
        actions = [
            action
            for action in rows_core.menu_actions(rows_core.PLAYLIST, playlist=playlist)
            if action.id not in local_media_browse.TREE_ONLY
        ]
        menu = local_media_browse.build_popup(
            self._wx, actions, lambda aid: local_media_browse.perform(self, playlist.id, aid)
        )
        self._context_id_refs = getattr(menu, "_refs", [])
        try:
            self._playlists.PopupMenu(menu)
        finally:
            menu.Destroy()

    # -- showing and closing ---------------------------------------------------------------

    def is_empty(self) -> bool:
        """Whether the window is showing its empty state (no items anywhere)."""
        return bool(self._empty and self._empty[0])

    def focus_default_control(self) -> None:
        if self.is_empty():
            self._add_files_btn.SetFocus()
        elif self._items.GetItemCount():
            self._items.SetFocus()
        else:
            self._playlists.SetFocus()

    def show(self) -> None:
        wx = self._wx
        from quill.ui.radio import transport_keys

        self._timer.Start(_TICK_MS)
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            transport_keys.install(
                self._win, self._host, wx=wx, extra_entries=self._windows.accelerator_entries()
            )
            self._windows.register(self._win, TITLE)
            show_modeless_surface(self._win, TITLE, announce=getattr(self._host, "_announce", None))
            self.focus_default_control()
            self._greet()
            return
        from quill.ui.dialog_contract import apply_modal_ids

        self._win.CentreOnParent()
        apply_modal_ids(self._win, cancel_id=wx.ID_CANCEL)
        transport_keys.install(self._win, self._host, wx=wx)
        self.focus_default_control()
        wx.CallLater(600, self._greet)
        try:
            ui.show_modal_dialog(self._host, self._win, TITLE)
        finally:
            self._teardown()
            self._win.Destroy()

    def _greet(self) -> None:
        """Say the empty-state sentence once: it is not on any focusable control."""
        if self.is_empty():
            self._wx.CallLater(600, lambda: ui.announce(self._host, EMPTY_SENTENCE))

    def _teardown(self) -> None:
        self._timer.Stop()
        ui.unregister_window(self._host, self)

    def _on_close(self, event: Any) -> None:
        self._teardown()
        if not self._modeless:
            event.Skip()
            return
        from quill.ui.dialog_contract import announce_surface_exit

        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        announce_surface_exit(TITLE, getattr(self._host, "_announce", None))
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)


def _summary(playlist: Playlist) -> str:
    from quill.core.radio.local_media import summary

    return summary(playlist)
