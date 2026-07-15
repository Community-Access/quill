"""Internet Radio > Manage Favorites... -- the favorites, made organizable.

A screen-reader-first manager for saved stations, shared verbatim by
embedded QUILL and standalone Quill Radio: a live search box over
everything (name, country, language, tags, folder, homepage), a tree of
arbitrarily nested folders (path-based; see ``core/radio/favorites.py``),
and podcast-grade ordering -- Move Up/Down inside a folder, plus the
Mark-and-Move pattern (Mark for Move, then Move Above / Move Below any
other station, adopting its folder) for long hops.

Folders here live as long as they hold stations: filing a station into a
path creates the folders on the way, and deleting a folder simply walks
its stations back to the top level -- stations are never deleted with it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_TOP_LEVEL_CHOICE = "(Top level -- no folder)"
_NEW_FOLDER_CHOICE = "(New folder...)"


class FavoritesManagerDialog:
    """Search, play, remove, reorder, and file favorite stations."""

    def __init__(
        self,
        parent: object,
        *,
        favorites: RadioFavoritesStore,
        controller: object,
        announce_cb: Callable[[str], None] | None = None,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._store = favorites
        self._controller = controller
        self._announce = announce_cb or (lambda _m: None)
        self._on_changed = on_changed or (lambda: None)
        self._marked_key: str | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Manage Favorite Stations",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((720, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(self.dialog, label="&Search favorites:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._search_ctrl = wx.TextCtrl(self.dialog)
        self._search_ctrl.SetName(
            "Filter favorites as you type; matches names, countries, tags, and folders"
        )
        search_row.Add(self._search_ctrl, 1, wx.EXPAND)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(
            wx.StaticText(self.dialog, label="&Favorites and folders"), 0, wx.LEFT | wx.TOP, 10
        )
        self._tree = wx.TreeCtrl(
            self.dialog, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT
        )
        self._tree.SetName(
            "Favorite stations, organized in folders; Enter plays, Delete removes, "
            "Shift+F10 opens all actions"
        )
        root.Add(self._tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = self._button(row1, "&Play", self._on_play, "Play the selected station")
        self._remove_btn = self._button(
            row1, "&Remove", self._on_remove, "Remove the selected station from favorites"
        )
        self._up_btn = self._button(
            row1, "Move &Up", lambda: self._on_move(-1), "Move the station up within its folder"
        )
        self._down_btn = self._button(
            row1,
            "Move &Down",
            lambda: self._on_move(1),
            "Move the station down within its folder",
        )
        self._folder_btn = self._button(
            row1,
            "Move to F&older...",
            self._on_move_to_folder,
            "File the selected station into a folder; type / to nest folders",
        )
        root.Add(row1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self._mark_btn = self._button(
            row2,
            "&Mark for Move",
            self._on_mark,
            "Mark the selected station, then Move Above or Move Below a destination",
        )
        self._above_btn = self._button(
            row2,
            "Move &Above",
            lambda: self._on_move_marked(True),
            "Place the marked station directly above the selected one, joining its folder",
        )
        self._below_btn = self._button(
            row2,
            "Move Be&low",
            lambda: self._on_move_marked(False),
            "Place the marked station directly below the selected one, joining its folder",
        )
        self._rename_btn = self._button(
            row2,
            "Re&name...",
            self._on_rename,
            "Rename the selected station or folder (F2); a blank station name "
            "restores the directory's own",
        )
        self._delete_folder_btn = self._button(
            row2,
            "Delete Fol&der...",
            self._on_delete_folder,
            "Delete the selected folder; its stations return to the top level",
        )
        row2.AddStretchSpacer()
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close the favorites manager")
        row2.Add(close_btn)
        root.Add(row2, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._search_ctrl.Bind(wx.EVT_TEXT, lambda _e: self._refresh_tree())
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, lambda _e: self._on_selection_changed())
        self._tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda _e: self._on_play())
        self._tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_context_menu)
        self._tree.Bind(wx.EVT_KEY_DOWN, self._on_tree_key)

        self._refresh_tree()

    # -- construction helpers -------------------------------------------------

    def _button(self, sizer: Any, label: str, handler: Callable[[], None], accessible: str) -> Any:
        wx = self._wx
        button = wx.Button(self.dialog, label=label)
        button.SetName(accessible)
        button.Bind(wx.EVT_BUTTON, lambda _e: handler())
        sizer.Add(button, 0, wx.RIGHT, 6)
        return button

    def show(self) -> None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL)
        try:
            show_modal_dialog(self.dialog, "Manage Favorite Stations", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # -- tree -----------------------------------------------------------------

    def _refresh_tree(self, keep_key: str | None = None) -> None:
        query = self._search_ctrl.GetValue().strip()
        tree = self._tree
        tree.DeleteAllItems()
        root = tree.AddRoot("Favorites")
        select_item = None

        if query:
            # A filter flattens the view: every match in one list, its folder
            # spoken as part of the label, so results are one arrow-key apart.
            matches = self._store.search(query)
            for favorite in matches:
                label = favorite.display_label
                if favorite.folder:
                    label += f" -- in {favorite.folder}"
                item = tree.AppendItem(root, label)
                tree.SetItemData(item, ("station", favorite.key))
                if favorite.key == keep_key:
                    select_item = item
            self._set_status(f"{len(matches)} match(es) for {query}")
        else:
            folder_items: dict[str, Any] = {}

            def folder_item(path: str) -> Any:
                if not path:
                    return root
                existing = folder_items.get(path)
                if existing is not None:
                    return existing
                parent_path, _, name = path.rpartition("/")
                parent = folder_item(parent_path)
                item = tree.AppendItem(parent, name)
                tree.SetItemData(item, ("folder", path))
                folder_items[path] = item
                return item

            for path in self._store.folder_names():
                folder_item(path)
            for favorite in self._store.favorites:
                parent = folder_item(favorite.folder)
                item = tree.AppendItem(parent, favorite.display_label)
                tree.SetItemData(item, ("station", favorite.key))
                if favorite.key == keep_key:
                    select_item = item
            count = len(self._store.favorites)
            folders = len(self._store.folder_names())
            self._set_status(f"{count} favorite(s), {folders} folder(s)")

        tree.ExpandAll()
        first, _cookie = tree.GetFirstChild(root)
        if select_item is not None:
            tree.SelectItem(select_item)
        elif first.IsOk():
            tree.SelectItem(first)
        self._on_selection_changed()

    def _selected(self) -> tuple[str, str] | None:
        """("station", key) or ("folder", path) for the tree selection."""
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        data = self._tree.GetItemData(item)
        if isinstance(data, tuple) and len(data) == 2:
            return data
        return None

    def _selected_favorite(self) -> FavoriteStation | None:
        selected = self._selected()
        if selected is None or selected[0] != "station":
            return None
        return self._store.find(selected[1])

    def _set_status(self, text: str) -> None:
        self._status.SetLabel(text)

    def _on_selection_changed(self) -> None:
        selected = self._selected()
        is_station = selected is not None and selected[0] == "station"
        is_folder = selected is not None and selected[0] == "folder"
        for button in (self._play_btn, self._remove_btn, self._up_btn, self._down_btn):
            button.Enable(is_station)
        self._folder_btn.Enable(is_station)
        self._mark_btn.Enable(is_station)
        marked = self._marked_key is not None
        self._above_btn.Enable(is_station and marked)
        self._below_btn.Enable(is_station and marked)
        self._rename_btn.Enable(is_station or is_folder)
        self._delete_folder_btn.Enable(is_folder)

    # -- actions ----------------------------------------------------------------

    def _changed(self, keep_key: str | None = None) -> None:
        self._on_changed()
        self._refresh_tree(keep_key)

    def _on_play(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            return
        self._controller.play_station(favorite.station)
        self._announce(f"Playing {favorite.display_label}")

    def _on_remove(self) -> None:
        wx = self._wx
        favorite = self._selected_favorite()
        if favorite is None:
            return
        name = favorite.display_label
        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation inside a managed dialog
            f"Remove {name} from your favorites?",
            "Remove Favorite",
            wx.ICON_QUESTION | wx.YES_NO,
            self.dialog,
        )
        if answer != wx.YES:
            return
        if self._marked_key == favorite.key:
            self._marked_key = None
        self._store.remove(favorite.key)
        self._changed()
        self._announce(f"Removed {name} from favorites")

    def _on_move(self, delta: int) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            return
        if not self._store.move(favorite.key, delta=delta):
            self._announce("Already at the edge of its folder.")
            return
        self._changed(keep_key=favorite.key)
        self._announce(f"Moved {'down' if delta > 0 else 'up'}")

    def _on_mark(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            return
        self._marked_key = favorite.key
        self._on_selection_changed()
        self._announce(
            f"Marked {favorite.display_label}. Select a destination, then Move Above or Move Below."
        )

    def _on_move_marked(self, before: bool) -> None:
        marked = self._marked_key
        target = self._selected_favorite()
        if marked is None or target is None:
            return
        if not self._store.move_relative_to(marked, target.key, before=before):
            self._announce("Could not move the marked station there.")
            return
        moved = self._store.find(marked)
        self._marked_key = None
        self._changed(keep_key=marked)
        where = "above" if before else "below"
        suffix = f", in {moved.folder}" if moved is not None and moved.folder else ""
        self._announce(f"Moved {where} {target.display_label}{suffix}")

    def _on_move_to_folder(self) -> None:
        wx = self._wx
        favorite = self._selected_favorite()
        if favorite is None:
            return
        choices = [_TOP_LEVEL_CHOICE, *self._store.folder_names(), _NEW_FOLDER_CHOICE]
        picker = wx.SingleChoiceDialog(
            self.dialog,
            "Where should this station live? Choose a folder, the top level, "
            "or create a new folder (use / to nest, like News/Morning).",
            f"Move {favorite.display_label} to Folder",
            choices,
        )
        try:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            choice = picker.GetStringSelection()
        finally:
            picker.Destroy()
        if choice == _NEW_FOLDER_CHOICE:
            entry = wx.TextEntryDialog(
                self.dialog,
                "New folder path (use / to nest, like News/Morning):",
                "New Folder",
            )
            try:
                if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                    return
                choice = entry.GetValue().strip().strip("/")
            finally:
                entry.Destroy()
            if not choice:
                return
        folder = "" if choice == _TOP_LEVEL_CHOICE else choice
        self._store.set_folder(favorite.key, folder)
        self._changed(keep_key=favorite.key)
        destination = folder or "the top level"
        self._announce(f"Filed {favorite.display_label} under {destination}")

    def _on_rename(self) -> None:
        """Rename whatever is selected: a station gets a custom display name,
        a folder renames in place (carrying its subfolders along)."""
        selected = self._selected()
        if selected is None:
            return
        if selected[0] == "station":
            self._on_rename_station()
        else:
            self._on_rename_folder()

    def _on_rename_station(self) -> None:
        wx = self._wx
        favorite = self._selected_favorite()
        if favorite is None:
            return
        entry = wx.TextEntryDialog(
            self.dialog,
            f"Your name for this station (leave blank to use {favorite.station.display_name}):",
            "Rename Station",
            value=favorite.custom_name,
        )
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = entry.GetValue().strip()
        finally:
            entry.Destroy()
        self._store.rename(favorite.key, name)
        self._changed(keep_key=favorite.key)
        if name:
            self._announce(f"Station renamed to {name}")
        else:
            self._announce(f"Station name restored to {favorite.display_label}")

    def _on_rename_folder(self) -> None:
        wx = self._wx
        selected = self._selected()
        if selected is None or selected[0] != "folder":
            return
        path = selected[1]
        parent_path, _, current = path.rpartition("/")
        entry = wx.TextEntryDialog(self.dialog, "Folder name:", "Rename Folder", value=current)
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = entry.GetValue().strip().strip("/")
        finally:
            entry.Destroy()
        if not name or name == current:
            return
        new_path = f"{parent_path}/{name}" if parent_path else name
        touched = self._store.rename_folder(path, new_path)
        self._changed()
        self._announce(f"Folder renamed to {name}; {touched} station(s) came along.")

    def _on_delete_folder(self) -> None:
        wx = self._wx
        selected = self._selected()
        if selected is None or selected[0] != "folder":
            return
        path = selected[1]
        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation inside a managed dialog
            f"Delete the folder {path}?\n\n"
            "Your stations are completely safe: they simply step out of the "
            "folder and line up at the top level of your favorites, in the "
            "same order. Nothing leaves your collection.",
            "Delete Folder",
            wx.ICON_QUESTION | wx.YES_NO,
            self.dialog,
        )
        if answer != wx.YES:
            return
        moved = self._store.delete_folder(path)
        self._changed()
        self._announce(f"Folder {path} deleted; {moved} station(s) moved to the top level.")

    # -- keyboard and context menu -------------------------------------------

    def _on_tree_key(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            selected = self._selected()
            if selected is not None and selected[0] == "station":
                self._on_remove()
            elif selected is not None and selected[0] == "folder":
                self._on_delete_folder()
            return
        if code == wx.WXK_F2:
            self._on_rename()
            return
        event.Skip()

    def _on_context_menu(self, _event: Any) -> None:
        wx = self._wx
        selected = self._selected()
        if selected is None:
            return
        menu = wx.Menu()
        entries: list[tuple[str, Callable[[], None]]]
        if selected[0] == "station":
            entries = [
                ("&Play", self._on_play),
                ("Rena&me Station...\tF2", self._on_rename_station),
                ("&Remove...\tDelete", self._on_remove),
                ("Move &Up", lambda: self._on_move(-1)),
                ("Move &Down", lambda: self._on_move(1)),
                ("&Mark for Move", self._on_mark),
                ("Move to F&older...", self._on_move_to_folder),
            ]
            if self._marked_key is not None:
                entries.insert(5, ("Move &Above", lambda: self._on_move_marked(True)))
                entries.insert(6, ("Move Be&low", lambda: self._on_move_marked(False)))
        else:
            entries = [
                ("Rena&me Folder...\tF2", self._on_rename_folder),
                ("&Delete Folder...", self._on_delete_folder),
            ]
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._menu_id_refs = id_refs  # pinned while the popup can fire
        self._tree.PopupMenu(menu)
        menu.Destroy()
