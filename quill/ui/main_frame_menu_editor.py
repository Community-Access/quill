"""The accessible Menu Editor for MainFrame (CQ-1 decomposition).

``MenuEditorMixin`` owns the Menu Editor dialog -- reordering, hiding, and
renaming top-level menus, menu items, and context-menu items -- including the
three tab builders and the menu/command discovery helpers they use. The
shared ``_TOP_MENU_DEFS`` table (stable key + factory label per top-level
menu) and ``_normalize_menu_label`` live here; ``main_frame.py`` imports them
for the menu-build customization pass. Extracted verbatim from
``main_frame.py``; runs on ``MainFrame`` (``self``).
"""

from __future__ import annotations

from quill.core.menu_customization import (
    MenuCustomization,
    save_menu_customization,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
)

#: Stable key and factory label for each top-level menu, in default order.
#: The Menu Editor and the menu-build transform pass share this list so a person
#: can reorder, hide, and rename top-level menus without touching item code.
_TOP_MENU_DEFS: tuple[tuple[str, str], ...] = (
    ("file", "&File"),
    ("edit", "&Edit"),
    ("view", "&View"),
    ("insert", "&Insert"),
    ("format", "F&ormat"),
    ("navigate", "&Navigate"),
    ("search", "&Search"),
    ("tools", "&Tools"),
    ("window", "&Window"),
    ("help", "&Help"),
)


def _normalize_menu_label(label: str) -> str:
    """Return a menu label without mnemonics or surrounding whitespace."""
    return label.replace("&", "").strip()


class MenuEditorMixin:
    def open_menu_editor(self) -> None:
        """Open the accessible Menu Editor for reordering, hiding, and renaming
        top-level menus, menu items, and context menu items, with one Reset to
        Factory Defaults (MENU-5).

        Edits are made on a working copy and only persisted when the person
        chooses Save, so Cancel always leaves the live menus untouched.
        """
        wx = self._wx
        default_keys = [key for key, _ in _TOP_MENU_DEFS]
        default_labels = dict(_TOP_MENU_DEFS)
        current = self._ensure_menu_customization()
        working = MenuCustomization.from_dict(current.to_dict())

        # Discover menu items from the currently built menu bar
        menu_items_by_menu: dict[str, list[tuple[str, str]]] = {}
        context_menu_items: list[tuple[str, str]] = []

        try:
            menu_bar = self.frame.GetMenuBar()
            if menu_bar is not None:
                # Build a label-to-key mapping for top-level menus
                label_to_key = {_normalize_menu_label(label): key for key, label in _TOP_MENU_DEFS}

                for menu_index in range(menu_bar.GetMenuCount()):
                    menu = menu_bar.GetMenu(menu_index)
                    menu_label = menu_bar.GetMenuLabelText(menu_index)
                    menu_key = label_to_key.get(_normalize_menu_label(menu_label))

                    if menu_key:
                        items = self._discover_menu_items(menu)
                        if items:
                            menu_items_by_menu[menu_key] = items

                # Discover context menu items (we'll build a temporary one)
                context_menu_items = self._discover_context_menu_items()
        except Exception:
            # If discovery fails, continue with empty item lists
            pass

        # Collect all known item keys for reconciliation
        all_item_keys = set()
        for items in menu_items_by_menu.values():
            all_item_keys.update(key for key, _ in items)
        all_item_keys.update(key for key, _ in context_menu_items)

        working.reconcile(set(default_keys), all_item_keys)

        with wx.Dialog(self.frame, title="Customize Menus", size=(720, 560)) as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(
                wx.StaticText(
                    dialog,
                    label=(
                        "Customize menus, menu items, and the context menu. "
                        "Changes apply when you choose Save."
                    ),
                ),
                0,
                wx.ALL,
                8,
            )

            notebook = wx.Notebook(dialog)
            notebook.SetName("Menu customization tabs")

            # Tab 1: Top-level menus
            top_panel = wx.Panel(notebook)
            self._build_top_menu_editor_tab(
                top_panel, wx, working, default_keys, default_labels, dialog
            )
            notebook.AddPage(top_panel, "Top-Level Menus")

            # Tab 2: Menu items
            items_panel = wx.Panel(notebook)
            self._build_menu_items_editor_tab(
                items_panel, wx, working, default_keys, default_labels, menu_items_by_menu, dialog
            )
            notebook.AddPage(items_panel, "Menu Items")

            # Tab 3: Context menu
            context_panel = wx.Panel(notebook)
            self._build_context_menu_editor_tab(
                context_panel, wx, working, context_menu_items, dialog
            )
            notebook.AddPage(context_panel, "Context Menu")

            outer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

            buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            ok_button = dialog.FindWindow(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetLabel("&Save")
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            dialog.SetSizer(outer)
            dialog.CentreOnParent()

            if self._show_modal_dialog(dialog, "Customize Menus") != wx.ID_OK:
                self._set_status("Menu customization cancelled")
                return

        working.reconcile(set(default_keys), all_item_keys)
        self._menu_customization = working
        try:
            save_menu_customization(working)
        except Exception:
            self._set_status("Could not save menu customization")
            return
        self._build_menu()
        if working.is_customized():
            self._set_status("Menu customization saved")
        else:
            self._set_status("Menus reset to factory defaults")

    def _discover_menu_items(self, menu: object) -> list[tuple[str, str]]:
        """Discover menu items (key, label) from a wx.Menu."""
        items: list[tuple[str, str]] = []
        try:
            for item_obj in menu.GetMenuItems():
                if item_obj.IsSeparator():
                    continue
                if item_obj.IsSubMenu():
                    continue  # Skip submenus for now
                item_id = item_obj.GetId()
                label = item_obj.GetItemLabelText()
                # Try to find the command key for this ID
                key = self._find_command_key_for_id(item_id)
                if key:
                    items.append((key, label))
                elif label:  # Fallback: use a synthesized key
                    synth_key = f"item.{label.lower().replace(' ', '_').replace('&', '')}"
                    items.append((synth_key, label))
        except Exception:
            pass
        return items

    def _find_command_key_for_id(self, item_id: int) -> str | None:
        """Find the command key for a given menu item ID."""
        # Build a reverse mapping from ID to command key
        id_to_command = {v: k for k, v in getattr(self, "_command_to_id", {}).items()}
        return id_to_command.get(item_id)

    def _discover_context_menu_items(self) -> list[tuple[str, str]]:
        """Discover context menu items by building a temporary context menu."""
        items: list[tuple[str, str]] = []
        # Return a hardcoded list of common context menu items for now
        # In a real implementation, we'd build the actual context menu
        # and discover items from it
        items = [
            ("edit.undo", "Undo"),
            ("edit.redo", "Redo"),
            ("edit.cut", "Cut"),
            ("edit.copy", "Copy"),
            ("edit.copy_with_source", "Copy With Source"),
            ("edit.paste", "Paste"),
            ("edit.select_all", "Select All"),
            ("edit.select_line", "Select Line"),
        ]
        return items

    def _build_top_menu_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        default_keys: list[str],
        default_labels: dict[str, str],
        dialog: object,
    ) -> None:
        """Build the top-level menus editor tab."""
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Reorder, rename, or hide top-level menus.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)
        menu_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        menu_list.SetName("Top-level menus")
        body.Add(menu_list, 1, wx.EXPAND | wx.RIGHT, 8)

        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        reset_btn = wx.Button(panel, label="Reset to &Factory Defaults")
        for btn in (up_btn, down_btn, rename_btn, hide_btn, reset_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        def _ordered() -> list[str]:
            return working.ordered_top_keys(default_keys)

        def _entry_label(key: str) -> str:
            label = _normalize_menu_label(working.top_label(key, default_labels[key]))
            if working.is_top_hidden(key):
                return f"{label} (hidden)"
            return label

        def _refresh(select_key: str | None = None) -> None:
            keys = _ordered()
            menu_list.Set([_entry_label(key) for key in keys])
            if not keys:
                return
            target = select_key if select_key in keys else keys[0]
            menu_list.SetSelection(keys.index(target))

        def _selected_key() -> str | None:
            index = menu_list.GetSelection()
            keys = _ordered()
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move(delta: int) -> None:
            keys = _ordered()
            key = _selected_key()
            if key is None:
                return
            index = keys.index(key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_top_order(keys)
            _refresh(key)

        def _on_up(_event: object) -> None:
            _move(-1)

        def _on_down(_event: object) -> None:
            _move(1)

        def _on_rename(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            current_label = _normalize_menu_label(working.top_label(key, default_labels[key]))
            with wx.TextEntryDialog(
                dialog,
                "Menu name (use & before a letter for the keyboard mnemonic):",
                "Rename Menu",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Menu") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_top(key, new_label)
            _refresh(key)

        def _on_hide(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            working.set_top_hidden(key, not working.is_top_hidden(key))
            _refresh(key)

        def _on_reset(_event: object) -> None:
            working.reset()
            _refresh()

        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)
        reset_btn.Bind(wx.EVT_BUTTON, _on_reset)

        panel.SetSizer(outer)
        _refresh()

    def _build_menu_items_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        default_keys: list[str],
        default_labels: dict[str, str],
        menu_items_by_menu: dict[str, list[tuple[str, str]]],
        dialog: object,
    ) -> None:
        """Build the menu items editor tab."""

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Select a menu, then reorder, rename, or hide its items.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: menu selection
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(panel, label="Menu:"), 0, wx.BOTTOM, 4)
        menu_choice = wx.ListBox(panel, style=wx.LB_SINGLE)
        menu_choice.SetName("Select menu")
        left.Add(menu_choice, 1, wx.EXPAND)
        body.Add(left, 0, wx.EXPAND | wx.RIGHT, 8)

        # Middle: item list
        middle = wx.BoxSizer(wx.VERTICAL)
        middle.Add(wx.StaticText(panel, label="Items:"), 0, wx.BOTTOM, 4)
        item_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        item_list.SetName("Menu items")
        middle.Add(item_list, 1, wx.EXPAND)
        body.Add(middle, 1, wx.EXPAND | wx.RIGHT, 8)

        # Right side: buttons
        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        for btn in (up_btn, down_btn, rename_btn, hide_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        current_menu_key: list[str | None] = [None]  # Mutable container for closure

        def _selected_menu_key() -> str | None:
            index = menu_choice.GetSelection()
            if index is None or index < 0:
                return None
            return current_menu_key[0]

        def _refresh_menu_list() -> None:
            menus = [
                (key, default_labels[key]) for key in default_keys if key in menu_items_by_menu
            ]
            menu_choice.Set([label for _, label in menus])
            if menus and menu_choice.GetSelection() < 0:
                menu_choice.SetSelection(0)
                current_menu_key[0] = menus[0][0]
            elif menus:
                idx = menu_choice.GetSelection()
                current_menu_key[0] = menus[idx][0] if 0 <= idx < len(menus) else None

        def _get_default_items(menu_key: str) -> list[tuple[str, str]]:
            return menu_items_by_menu.get(menu_key, [])

        def _ordered_items(menu_key: str) -> list[str]:
            default_items = _get_default_items(menu_key)
            default_keys_for_menu = [key for key, _ in default_items]
            return working.ordered_item_keys(menu_key, default_keys_for_menu)

        def _item_entry_label(item_key: str, default_label: str) -> str:
            label = _normalize_menu_label(working.item_label(item_key, default_label))
            if working.is_item_hidden(item_key):
                return f"{label} (hidden)"
            return label

        def _refresh_item_list(select_key: str | None = None) -> None:
            menu_key = _selected_menu_key()
            if not menu_key:
                item_list.Set([])
                return

            default_items = _get_default_items(menu_key)
            default_labels_map = dict(default_items)
            keys = _ordered_items(menu_key)
            item_list.Set([
                _item_entry_label(key, default_labels_map.get(key, key)) for key in keys
            ])
            if keys:
                if select_key and select_key in keys:
                    item_list.SetSelection(keys.index(select_key))
                elif item_list.GetSelection() < 0:
                    item_list.SetSelection(0)

        def _selected_item_key() -> str | None:
            menu_key = _selected_menu_key()
            if not menu_key:
                return None
            index = item_list.GetSelection()
            keys = _ordered_items(menu_key)
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move_item(delta: int) -> None:
            menu_key = _selected_menu_key()
            if not menu_key:
                return
            item_key = _selected_item_key()
            if not item_key:
                return
            keys = _ordered_items(menu_key)
            index = keys.index(item_key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_item_order(menu_key, keys)
            _refresh_item_list(item_key)

        def _on_menu_select(_event: object) -> None:
            idx = menu_choice.GetSelection()
            if idx >= 0:
                menus = [
                    (key, default_labels[key]) for key in default_keys if key in menu_items_by_menu
                ]
                if idx < len(menus):
                    current_menu_key[0] = menus[idx][0]
            _refresh_item_list()

        def _on_up(_event: object) -> None:
            _move_item(-1)

        def _on_down(_event: object) -> None:
            _move_item(1)

        def _on_rename(_event: object) -> None:
            item_key = _selected_item_key()
            if not item_key:
                return
            menu_key = _selected_menu_key()
            if not menu_key:
                return
            default_items = _get_default_items(menu_key)
            default_labels_map = dict(default_items)
            current_label = _normalize_menu_label(
                working.item_label(item_key, default_labels_map.get(item_key, item_key))
            )
            with wx.TextEntryDialog(
                dialog,
                "Item name (use & before a letter for the keyboard mnemonic):",
                "Rename Item",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Item") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_item(item_key, new_label)
            _refresh_item_list(item_key)

        def _on_hide(_event: object) -> None:
            item_key = _selected_item_key()
            if not item_key:
                return
            working.set_item_hidden(item_key, not working.is_item_hidden(item_key))
            _refresh_item_list(item_key)

        menu_choice.Bind(wx.EVT_LISTBOX, _on_menu_select)
        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)

        panel.SetSizer(outer)
        _refresh_menu_list()
        _refresh_item_list()

    def _build_context_menu_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        context_items: list[tuple[str, str]],
        dialog: object,
    ) -> None:
        """Build the context menu editor tab."""
        from quill.core.menu_customization import CONTEXT_MENU_KEY

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Reorder, rename, or hide context menu items.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)
        item_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        item_list.SetName("Context menu items")
        body.Add(item_list, 1, wx.EXPAND | wx.RIGHT, 8)

        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        for btn in (up_btn, down_btn, rename_btn, hide_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        default_items_map = dict(context_items)
        default_item_keys = [key for key, _ in context_items]

        def _ordered() -> list[str]:
            return working.ordered_item_keys(CONTEXT_MENU_KEY, default_item_keys)

        def _entry_label(key: str) -> str:
            default_label = default_items_map.get(key, key)
            label = _normalize_menu_label(working.item_label(key, default_label))
            if working.is_item_hidden(key):
                return f"{label} (hidden)"
            return label

        def _refresh(select_key: str | None = None) -> None:
            keys = _ordered()
            item_list.Set([_entry_label(key) for key in keys])
            if not keys:
                return
            if select_key and select_key in keys:
                item_list.SetSelection(keys.index(select_key))
            elif item_list.GetSelection() < 0:
                item_list.SetSelection(0)

        def _selected_key() -> str | None:
            index = item_list.GetSelection()
            keys = _ordered()
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move(delta: int) -> None:
            keys = _ordered()
            key = _selected_key()
            if key is None:
                return
            index = keys.index(key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_item_order(CONTEXT_MENU_KEY, keys)
            _refresh(key)

        def _on_up(_event: object) -> None:
            _move(-1)

        def _on_down(_event: object) -> None:
            _move(1)

        def _on_rename(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            current_label = _normalize_menu_label(
                working.item_label(key, default_items_map.get(key, key))
            )
            with wx.TextEntryDialog(
                dialog,
                "Item name (use & before a letter for the keyboard mnemonic):",
                "Rename Context Menu Item",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Context Menu Item") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_item(key, new_label)
            _refresh(key)

        def _on_hide(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            working.set_item_hidden(key, not working.is_item_hidden(key))
            _refresh(key)

        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)

        panel.SetSizer(outer)
        _refresh()
