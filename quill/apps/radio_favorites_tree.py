"""Quill Radio's Favorites tree: drawing it, moving and marking stations,
its keys and context menu, details, rename, remove, folders and their order.

Moved whole out of ``RadioAppFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged.
"""

from __future__ import annotations

import wx

from quill.ui.radio.volume_keys import volume_chord_handled


class RadioFavoritesTreeMixin:
    """The Favorites tree and its verbs; mixed into ``RadioAppFrame``."""

    def _reload_favorites_tree(self, keep_key: str | None = None) -> None:
        tree = self._favorites_tree
        if keep_key is None:
            selected = self._selected_tree_data()
            if selected is not None and selected[0] == "station":
                keep_key = selected[1]
        tree.DeleteAllItems()
        root = tree.AddRoot("Favorites")
        folder_items: dict[str, wx.TreeItemId] = {}
        select_item = None

        def folder_item(path: str) -> wx.TreeItemId:
            if not path:
                return root
            existing = folder_items.get(path)
            if existing is not None:
                return existing
            parent_path, _, name = path.rpartition("/")
            item = tree.AppendItem(folder_item(parent_path), name)
            tree.SetItemData(item, ("folder", path))
            folder_items[path] = item
            return item

        store = self._radio_favorites
        sort = self._radio_history.favorites_sort
        folder_sorts = self._radio_history.folder_sort_orders
        for path in store.folders_in_display_order(sort):
            folder_item(path)
        for favorite in store.favorites_in_display_order(sort, folder_sorts):
            item = tree.AppendItem(folder_item(favorite.folder), favorite.display_label)
            tree.SetItemData(item, ("station", favorite.key))
            if favorite.key == keep_key:
                select_item = item
        tree.ExpandAll()
        first, _cookie = tree.GetFirstChild(root)
        if select_item is not None:
            tree.SelectItem(select_item)
        elif first.IsOk():
            tree.SelectItem(first)

    def _selected_tree_data(self) -> tuple[str, str] | None:
        tree = getattr(self, "_favorites_tree", None)
        if tree is None:
            return None
        item = tree.GetSelection()
        if not item.IsOk():
            return None
        data = tree.GetItemData(item)
        return data if isinstance(data, tuple) and len(data) == 2 else None

    def _selected_favorite(self):
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "station":
            return None
        return self._radio_favorites.find(selected[1])

    def _on_favorites_activated(self, event: wx.CommandEvent) -> None:
        selected = self._selected_tree_data()
        if selected is not None and selected[0] == "station":
            self._play_selected_favorite()
            return
        event.Skip()  # a folder: let the tree toggle it

    def _on_favorites_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_favorites_activated(event)
            return
        # Space on the row you are listening to pauses it. Only that row: Space
        # everywhere else in a tree belongs to the tree, and hijacking it would
        # take away a key people use to select. A podcast paused here keeps its
        # place; the old behaviour reloaded the episode from the beginning.
        if code == wx.WXK_SPACE and not (
            event.ControlDown() or event.ShiftDown() or event.AltDown()
        ):
            favorite = self._selected_favorite()
            if favorite is not None and self._favorite_is_playing(favorite):
                self._toggle_current_playback()
                return
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_tree_remove()
            return
        if code == wx.WXK_F2:
            self._on_tree_rename()
            return
        # The tree claims Up/Down before the menu accelerator can (volume_keys).
        if volume_chord_handled(self, event, code):
            return
        # Alt+Shift+Up/Down reordering is handled in the frame char hook
        # (_on_radio_char_hook) -- Windows steals Alt+arrow for the menu before
        # a focused TreeCtrl's EVT_KEY_DOWN can see it.
        event.Skip()

    def _move_selected_favorite(self, delta: int) -> None:
        """Move the selected favorite up (-1) or down (+1) within its folder,
        only when that folder is in manual order, and speak where it landed."""
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("Select a station to move it.")
            return
        folder_sort = self._radio_history.folder_sort_orders.get(
            favorite.folder, self._radio_history.favorites_sort
        )
        switched = False
        if folder_sort != "manual":
            # Reordering is a clear intent to reorder: switch to manual order
            # (revealing the preserved hand-arranged order, announced below) and
            # move within it. No longer bakes the sorted view over the stored
            # order, which used to destroy it (#1186).
            self._force_favorites_manual_order()
            switched = True
        from quill.ui.radio.favorites_manager_dialog import move_announcement

        if not self._radio_favorites.move(favorite.key, delta=delta):
            self._announce("Already at the edge of its folder.")
            if switched:
                self._reload_favorites_tree(keep_key=favorite.key)
            return
        # Speak the new position before the tree reload re-announces the item, so
        # "Moved down, now above X" is what the listener hears.
        prefix = "Switched to manual order. " if switched else ""
        self._announce(prefix + move_announcement(self._radio_favorites, favorite.key, delta))
        self._save_radio_favorites()
        self._reload_favorites_tree(keep_key=favorite.key)

    def _force_favorites_manual_order(self) -> None:
        """Switch favorites to manual sort WITHOUT rewriting the stored order.

        Reordering from a sorted (A-Z/Z-A) view is a clear intent to hand-arrange,
        so flip the sort to manual -- which reveals the preserved stored order (the
        caller reloads the tree and announces "Switched to manual order") -- and
        then the move happens within that now-visible order. Crucially this does
        NOT bake the sorted display over the stored list: doing so silently
        destroyed a listener's hand-arranged order the first time they reordered
        from an A-Z view, with no way to recover it (#1186). The stored list is
        left untouched; only the sort setting changes.
        """
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        self._radio_history.favorites_sort = "manual"
        self._radio_history.folder_sort_orders = {}
        radio_history.save_history(app_data_dir(), self._radio_history)
        self._save_radio_favorites()

    def _on_favorites_context_menu(self, _event: object) -> None:
        from quill.ui.radio.playback_state import ACTIVE_STATES

        selected = self._selected_tree_data()
        if selected is None:
            return
        menu = wx.Menu()
        entries: list[tuple[str, object]] = []
        if selected[0] == "station":
            favorite = self._selected_favorite()
            playing = (
                favorite is not None
                and self._radio_controller.state.station is not None
                and self._radio_controller.state.station.stream_url == favorite.station.stream_url
                and self._radio_controller.state.state in ACTIVE_STATES
            )
            entries = [
                ("&Stop" if playing else "&Play", self._on_play_stop_context),
                ("Station &Details...", self._on_favorite_details),
                ("Edit Station &Tags...", self._on_favorite_tags),
                ("Rena&me...\tF2", self._on_tree_rename),
                # The chord already worked; the menu now says so. A shortcut
                # only a document mentions is a shortcut most listeners never
                # hear about.
                ("Move &Up\tAlt+Shift+Up", lambda: self._move_selected_favorite(-1)),
                ("Move Dow&n\tAlt+Shift+Down", lambda: self._move_selected_favorite(1)),
                # "F&older"/"Fold&er": Move to Folder and New Folder both said
                # &o, so one of the pair silently never answered its key.
                ("Move to F&older...", self._on_tree_move_to_folder),
                ("&Remove...\tDelete", self._on_tree_remove),
                ("New Fold&er...\tCtrl+Shift+E", self._on_new_folder),
            ]
            # Mark-and-Move (#1190): pick a station up once, then drop it above
            # or below any destination in one step -- no Alt+Shift+Up/Down 30
            # times. Mirrors the Favorites Manager's Mark for Move. "Mar&k",
            # not "&Mark": Rena&me already answers M in this menu.
            marked = getattr(self, "_marked_favorite_key", None)
            entries.append(("Mar&k for Move", self._on_mark_favorite))
            if marked is not None and (favorite is None or marked != favorite.key):
                entries.append(("Move Marked A&bove", lambda: self._on_move_marked_favorite(True)))
                entries.append(("Move Marked Belo&w", lambda: self._on_move_marked_favorite(False)))
            entries.append(("Manage Fa&vorites...", self.open_manage_radio_favorites))
        else:
            entries = [
                ("Rena&me Folder...\tF2", self._on_tree_rename),
                ("&Sort This Folder...", self._on_sort_folder),
                ("&Delete Folder...", self._on_tree_remove),
                ("New F&older...\tCtrl+Shift+E", self._on_new_folder),
                ("Manage Fa&vorites...", self.open_manage_radio_favorites),
            ]
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._keep_menu_ids(*id_refs)
        self._favorites_tree.PopupMenu(menu)
        menu.Destroy()

    def _on_play_stop_context(self) -> None:
        from quill.ui.radio.playback_state import ACTIVE_STATES

        favorite = self._selected_favorite()
        if favorite is None:
            return
        state = self._radio_controller.state
        if (
            state.station is not None
            and state.station.stream_url == favorite.station.stream_url
            and state.state in ACTIVE_STATES
        ):
            self.radio_stop()
        else:
            self._radio_controller.play_station(favorite.station)
            self._announce(f"Playing {favorite.display_label}.")

    def _on_favorite_details(self) -> None:
        """Show the selected favorite's details (name, source, stream, format,
        country) in the same reviewable, copyable window the search results use,
        so a listener can arrow through them and copy -- reachable per favorite."""
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("Select a station to see its details.")
            return
        from quill.core.radio.station_tags import details_with_tags
        from quill.ui.radio.now_playing_dialog import NowPlayingDialog

        NowPlayingDialog(
            self.frame,
            details_with_tags(favorite.station.details_text, favorite.user_tags),
            self._show_modal_dialog,
            self._copy_to_clipboard,
            self._announce,
            title=f"Details: {favorite.display_name}",
            transport_host=self,
            windows=getattr(self, "_windows", None),
        ).show()

    def _on_favorite_tags(self) -> None:
        """Edit Station Tags... on the selected favorite: words a search should
        find it by ("Detroit Tigers, MLB"), kept with the favorite."""
        favorite = self._selected_favorite()
        if favorite is None:
            self._announce("Select a station to tag.")
            return
        from quill.ui.radio.station_tags_dialog import edit_station_tags

        edit_station_tags(self, favorite.station)

    def _on_mark_favorite(self) -> None:
        """Mark-and-Move step 1 (#1190): remember the selected station so a
        single Move Marked Above/Below drops it, instead of nudging one step at
        a time with Alt+Shift+Up/Down."""
        favorite = self._selected_favorite()
        if favorite is None:
            return
        self._marked_favorite_key = favorite.key
        self._announce(
            f"Marked {favorite.display_label}. Select a destination, then choose "
            "Move Marked Above or Move Marked Below from this menu."
        )

    def _on_move_marked_favorite(self, before: bool) -> None:
        """Mark-and-Move step 2 (#1190): drop the marked station directly above
        or below the currently selected one (adopting its folder)."""
        target = self._selected_favorite()
        marked_key = getattr(self, "_marked_favorite_key", None)
        if target is None or marked_key is None:
            return
        if marked_key == target.key:
            self._announce("Select a different station as the destination.")
            return
        # Reordering only makes sense in manual order; switch to it first. This
        # reveals your preserved hand-arranged order -- it never overwrites it.
        folder_sort = self._radio_history.folder_sort_orders.get(
            target.folder, self._radio_history.favorites_sort
        )
        if folder_sort != "manual":
            self._force_favorites_manual_order()
        if self._radio_favorites.move_relative_to(marked_key, target.key, before=before):
            self._marked_favorite_key = None
            self._save_radio_favorites()
            self._reload_favorites_tree(keep_key=marked_key)
            where = "above" if before else "below"
            self._announce(f"Moved {where} {target.display_label}.")
        else:
            self._announce("Could not move the marked station there.")

    def _on_tree_rename(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        if selected is None:
            return
        if selected[0] == "station":
            favorite = self._selected_favorite()
            if favorite is not None and favorite_actions.rename_favorite(
                self.frame, self._radio_favorites, favorite, announce=self._announce
            ):
                self._save_radio_favorites()
                self._reload_favorites_tree(keep_key=favorite.key)
        elif favorite_actions.rename_folder_prompt(
            self.frame, self._radio_favorites, selected[1], announce=self._announce
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_tree_remove(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        if selected is None:
            return
        if selected[0] == "station":
            favorite = self._selected_favorite()
            if favorite is not None and favorite_actions.remove_favorite(
                self.frame, self._radio_favorites, favorite, announce=self._announce
            ):
                self._save_radio_favorites()
                self._reload_favorites_tree()
        elif favorite_actions.delete_folder_prompt(
            self.frame, self._radio_favorites, selected[1], announce=self._announce
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_new_folder(self) -> None:
        from quill.ui.radio import favorite_actions

        selected = self._selected_tree_data()
        initial_parent = selected[1] if selected is not None and selected[0] == "folder" else ""
        if favorite_actions.create_folder_prompt(
            self.frame,
            self._radio_favorites,
            announce=self._announce,
            initial_parent=initial_parent,
        ):
            self._save_radio_favorites()
            self._reload_favorites_tree()

    def _on_sort_folder(self) -> None:
        """Give the selected folder its own sort order -- A to Z, Z to A,
        Unsorted, or follow the global default -- applied to its stations and
        remembered (per-folder override of Favorites sort order)."""
        selected = self._selected_tree_data()
        if selected is None or selected[0] != "folder":
            return
        path = selected[1]
        labels = [
            "Follow the default",
            "Ascending (A to Z)",
            "Descending (Z to A)",
            "Unsorted (manual order)",
        ]
        values: list[str | None] = [None, "az", "za", "manual"]
        current = self._radio_history.folder_sort_orders.get(path)
        with wx.SingleChoiceDialog(
            self.frame, f'Sort order for the folder "{path}":', "Sort Folder", labels
        ) as dlg:
            dlg.SetSelection(values.index(current) if current in values else 0)
            if dlg.ShowModal() != wx.ID_OK:
                return
            chosen = values[dlg.GetSelection()]
        orders = dict(self._radio_history.folder_sort_orders)
        if chosen is None:
            orders.pop(path, None)
        else:
            orders[path] = chosen
        self._radio_history.folder_sort_orders = orders
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        radio_history.save_history(app_data_dir(), self._radio_history)
        self._reload_favorites_tree()
        self._announce(f"{path}: {dict(zip(values, labels, strict=True))[chosen]}.")
