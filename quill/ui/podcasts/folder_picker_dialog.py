"""Move to Folder... picker for the Podcast Manager.

A search field over a folder tree: type to filter folders by name (ancestors
of a match stay visible so the hierarchy keeps making sense), arrow through
the tree, and press Move. New Folder... creates a folder as a child of
whatever is selected — any level, including the top — and selects it so the
just-created folder can immediately receive the show. The dialog never moves
anything itself; it returns the choice and the caller applies it, so the
manager can preserve the user's position in its own tree afterward.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids

_TOP_LEVEL_LABELS = {
    "library": "Library (top level)",
    "inbox": "Inbox (top level)",
}


@dataclass(frozen=True, slots=True)
class FolderPickerResult:
    """The user's choice: ``confirmed`` False means cancelled; a ``folder_id``
    of None means the library's top level (no folder)."""

    confirmed: bool
    folder_id: str | None = None


def _visible_folder_ids(folders: list, needle: str) -> set[str]:
    """Folders whose name matches *needle*, plus every ancestor of a match."""
    query = needle.casefold().strip()
    if not query:
        return {folder.id for folder in folders}
    by_id = {folder.id: folder for folder in folders}
    visible: set[str] = set()
    for folder in folders:
        if query in folder.name.casefold():
            visible.add(folder.id)
            parent_id = folder.parent_folder_id
            while parent_id is not None and parent_id not in visible:
                visible.add(parent_id)
                parent = by_id.get(parent_id)
                parent_id = parent.parent_folder_id if parent is not None else None
    return visible


def _tree_item_key(item: object) -> int:
    """A stable, hashable identity for a wx.TreeItemId.

    ``TreeItemId.GetID()`` returns a fresh ``sip.voidptr`` wrapper on every
    call; two wrappers for the SAME tree item never compare equal, so using
    them as dict keys silently made every lookup miss — the "selecting a
    podcast shows no episodes" bug. ``int()`` of the voidptr is the raw
    pointer value: stable, equal, hashable.
    """
    get_id = getattr(item, "GetID", None)
    if callable(get_id):
        try:
            return int(get_id())
        except (TypeError, ValueError):
            pass
    return id(item)


class FolderPickerDialog:
    """Search + tree + inline New Folder; returns a :class:`FolderPickerResult`."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary | None = None,
        title: str = "Move to Folder",
        scope: str = "library",
        folders_provider: Callable[[], list] | None = None,
        create_folder: Callable[[str, str | None], object] | None = None,
        rename_folder: Callable[[str, str], bool] | None = None,
        delete_folder: Callable[[str], None] | None = None,
        top_level_label: str = "",
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._scope = scope if scope in _TOP_LEVEL_LABELS else "library"
        # Generic mode (e.g. Radio favorites): the caller supplies the folder
        # list and creation function directly instead of a podcast library.
        self._folders_provider = folders_provider
        self._create_folder_cb = create_folder
        self._rename_folder_cb = rename_folder
        self._delete_folder_cb = delete_folder
        self._top_level_label = top_level_label or _TOP_LEVEL_LABELS[self._scope]
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._item_folder: dict[object, str | None] = {}
        self._result = FolderPickerResult(confirmed=False)

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((480, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.dialog, label="&Search folders:")
        search_row.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._search_ctrl = wx.TextCtrl(self.dialog)
        self._search_ctrl.SetName("Search folders by name")
        search_row.Add(self._search_ctrl, 1, wx.EXPAND)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        self._tree = wx.TreeCtrl(
            self.dialog,
            style=wx.TR_DEFAULT_STYLE | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
        )
        self._tree.SetName("Folders")
        root.Add(self._tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        new_folder_btn = wx.Button(self.dialog, label="&New Folder...")
        new_folder_btn.SetName("Create a new folder inside the selected folder")
        self._rename_btn = wx.Button(self.dialog, label="&Rename...")
        self._rename_btn.SetName("Rename the selected folder")
        self._rename_btn.Enable(False)
        self._delete_btn = wx.Button(self.dialog, label="De&lete")
        self._delete_btn.SetName(
            "Delete the selected folder; whatever is inside moves up to its parent"
        )
        self._delete_btn.Enable(False)
        move_btn = wx.Button(self.dialog, wx.ID_OK, label="&Move Here")
        move_btn.SetDefault()
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        btn_row.Add(new_folder_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._rename_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._delete_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(move_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._search_ctrl.Bind(wx.EVT_TEXT, self._on_search_changed)
        new_folder_btn.Bind(wx.EVT_BUTTON, self._on_new_folder)
        self._rename_btn.Bind(wx.EVT_BUTTON, self._on_rename)
        self._delete_btn.Bind(wx.EVT_BUTTON, self._on_delete)
        move_btn.Bind(wx.EVT_BUTTON, self._on_move)
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selection_changed)

        self._rebuild_tree()
        self._search_ctrl.SetFocus()

    # ------------------------------------------------------------------

    def show(self) -> FolderPickerResult:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            outcome = show_modal_dialog(self.dialog, "Move to Folder", announce=self._announce)
            if outcome == wx.ID_OK and not self._result.confirmed:
                # The default OK button ended the modal directly (Enter from
                # the search field or the tree); adopt the tree selection.
                self._result = FolderPickerResult(True, self._selected_folder_id())
            return self._result
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------

    def _folders(self) -> list:
        """The folder tree this picker browses: a caller-supplied provider
        (generic mode), the podcast library's tree, or the Inbox's own
        independent tree (scope="inbox")."""
        if self._folders_provider is not None:
            return list(self._folders_provider())
        if self._library is None:
            return []
        if self._scope == "inbox":
            return list(self._library.inbox_folders)
        return list(self._library.folders)

    def _create_folder(self, name: str, parent_folder_id: str | None):
        if self._create_folder_cb is not None:
            return self._create_folder_cb(name, parent_folder_id)
        if self._library is None:
            return None
        if self._scope == "inbox":
            from quill.core.podcasts import inbox

            return inbox.add_inbox_folder(self._library, name, parent_folder_id=parent_folder_id)
        return self._library.add_folder(name, parent_folder_id=parent_folder_id)

    def _selected_folder_id(self) -> str | None:
        item = self._tree.GetSelection()
        if not item.IsOk():
            return None
        key = _tree_item_key(item)
        return self._item_folder.get(key)

    def _rebuild_tree(self, *, select_folder_id: str | None = None) -> None:
        needle = self._search_ctrl.GetValue()
        folders = self._folders()
        visible = _visible_folder_ids(folders, needle)
        self._tree.DeleteAllItems()
        self._item_folder.clear()
        root = self._tree.AddRoot(self._top_level_label)
        self._item_folder[_tree_item_key(root)] = None
        target_item: object | None = None

        def _add_children(parent_item: object, parent_folder_id: str | None) -> None:
            nonlocal target_item
            children = sorted(
                (f for f in folders if f.parent_folder_id == parent_folder_id and f.id in visible),
                key=lambda f: f.name.casefold(),
            )
            for folder in children:
                item = self._tree.AppendItem(parent_item, folder.name)
                self._item_folder[_tree_item_key(item)] = folder.id
                if select_folder_id is not None and folder.id == select_folder_id:
                    target_item = item
                _add_children(item, folder.id)

        _add_children(root, None)
        self._tree.ExpandAll()
        if target_item is not None:
            self._tree.SelectItem(target_item)
            self._tree.EnsureVisible(target_item)
        else:
            self._tree.SelectItem(root)

    def _on_selection_changed(self, _event: object) -> None:
        has_folder = self._selected_folder_id() is not None
        self._rename_btn.Enable(has_folder)
        self._delete_btn.Enable(has_folder)

    def _rename_folder(self, folder_id: str, new_name: str) -> bool:
        if self._rename_folder_cb is not None:
            return bool(self._rename_folder_cb(folder_id, new_name))
        if self._library is None:
            return False
        if self._scope == "inbox":
            from quill.core.podcasts import inbox

            return inbox.rename_inbox_folder(self._library, folder_id, new_name)
        return self._library.rename_folder(folder_id, new_name)

    def _delete_folder(self, folder_id: str) -> None:
        """Delete = contents move up to the parent — the picker never offers
        the destructive variant; that lives on the Podcast Manager's tree."""
        if self._delete_folder_cb is not None:
            self._delete_folder_cb(folder_id)
            return
        if self._library is None:
            return
        if self._scope == "inbox":
            from quill.core.podcasts import inbox

            inbox.delete_inbox_folder(self._library, folder_id)
            return
        self._library.delete_folder(folder_id, contents="promote")

    def _on_rename(self, _event: object) -> None:
        wx = self._wx
        folder_id = self._selected_folder_id()
        if folder_id is None:
            return
        current = next((f.name for f in self._folders() if f.id == folder_id), "")
        dialog = wx.TextEntryDialog(self.dialog, "Folder name:", "Rename Folder", value=current)
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name or name == current:
            return
        if self._rename_folder(folder_id, name):
            self._on_library_changed()
            self._rebuild_tree(select_folder_id=folder_id)
            self._announce(f"Renamed folder to {name}")

    def _on_delete(self, _event: object) -> None:
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        folder_id = self._selected_folder_id()
        if folder_id is None:
            return
        current = next((f.name for f in self._folders() if f.id == folder_id), "")
        confirmed = (
            show_message_box(
                f"Delete the folder {current}? Anything inside moves up to its parent.",
                "Delete Folder",
                wx.YES_NO | wx.ICON_QUESTION,
                self.dialog,
                announce=self._announce,
            )
            == wx.YES
        )
        if not confirmed:
            return
        self._delete_folder(folder_id)
        self._on_library_changed()
        self._rebuild_tree()
        self._announce(f"Deleted folder {current}; its contents moved up.")

    def _on_search_changed(self, _event: object) -> None:
        selected = self._selected_folder_id()
        self._rebuild_tree(select_folder_id=selected)

    def _on_new_folder(self, _event: object) -> None:
        wx = self._wx
        parent_folder_id = self._selected_folder_id()
        dialog = wx.TextEntryDialog(self.dialog, "Folder name:", "New Folder")
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name:
            return
        folder = self._create_folder(name, parent_folder_id)
        if folder is None:
            return
        self._on_library_changed()
        # Clear the filter so the new folder is guaranteed visible, then
        # select it — the natural next action is Move Here into it.
        self._search_ctrl.ChangeValue("")
        self._rebuild_tree(select_folder_id=folder.id)
        self._tree.SetFocus()
        self._announce(f"Created folder {name}. It is selected; press Move Here to use it.")

    def _on_move(self, _event: object) -> None:
        self._result = FolderPickerResult(True, self._selected_folder_id())
        self.dialog.EndModal(self._wx.ID_OK)
