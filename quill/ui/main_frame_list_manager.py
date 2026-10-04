"""The List Manager on QUILL's main window: reading a list block, its window,
and writing the list back.

Moved whole out of ``MainFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged: these methods use the same ``self`` attributes they did.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.selection import line_span
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


@dataclass(slots=True)
class _ListManagerItem:
    kind: str
    text: str
    level: int
    bullet: str = "-"
    checked: bool = False


@dataclass(slots=True)
class _ListManagerState:
    start: int
    end: int
    trailing_newline: bool
    base_indent: str
    items: list[_ListManagerItem]


class ListManagerMixin:
    """The List Manager; mixed into ``MainFrame``."""

    def open_list_manager(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("List Manager is unavailable in this profile")
            return
        if self._effective_markup_kind() not in {"markdown", "plain"}:
            self._set_status("List Manager is only available in Markdown documents")
            return
        state = self._extract_list_manager_state()
        if state is None or not state.items:
            self._set_status("Place the cursor inside a Markdown list to open List Manager")
            return
        updated_text = self._show_list_manager_dialog(state)
        if updated_text is None:
            self._set_status("List Manager cancelled")
            return
        if updated_text == self.editor.GetValue():
            self._set_status("List Manager closed without changes")
            return
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        self._set_status("Applied list manager changes")

    def _extract_list_manager_state(self) -> _ListManagerState | None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        current_start, current_end = line_span(text, cursor)
        current_line = text[current_start:current_end]
        if self._parse_list_manager_line(current_line) is None:
            return None

        starts: list[int] = [0]
        for index, character in enumerate(text):
            if character == "\n":
                starts.append(index + 1)

        current_index = 0
        for index, start in enumerate(starts):
            if start <= current_start:
                current_index = index
            else:
                break

        def line_text(line_index: int) -> str:
            line_start = starts[line_index]
            line_end = starts[line_index + 1] if line_index + 1 < len(starts) else len(text)
            return text[line_start:line_end]

        top = current_index
        while top > 0 and self._parse_list_manager_line(line_text(top - 1)) is not None:
            top -= 1
        bottom = current_index
        while (
            bottom + 1 < len(starts)
            and self._parse_list_manager_line(line_text(bottom + 1)) is not None
        ):
            bottom += 1

        block_start = starts[top]
        block_end = starts[bottom + 1] if bottom + 1 < len(starts) else len(text)
        block_lines = [line_text(i) for i in range(top, bottom + 1)]
        parsed: list[tuple[str, str, str, bool, str]] = []
        indent_widths: list[int] = []
        for raw_line in block_lines:
            item = self._parse_list_manager_line(raw_line)
            if item is None:
                return None
            parsed.append(item)
            indent, _kind, _bullet, _checked, _body = item
            indent_widths.append(self._indent_measure(indent))
        if not parsed:
            return None

        base_indent_width = min(indent_widths)
        step_width = max(1, self._indent_width())
        items: list[_ListManagerItem] = []
        for indent, kind, bullet, checked, body in parsed:
            level = max(0, (self._indent_measure(indent) - base_indent_width) // step_width)
            items.append(
                _ListManagerItem(
                    kind=kind,
                    text=body,
                    level=level,
                    bullet=bullet or "-",
                    checked=checked,
                )
            )
        return _ListManagerState(
            start=block_start,
            end=block_end,
            trailing_newline=text[block_end - 1 : block_end] == "\n",
            base_indent=" " * base_indent_width,
            items=items,
        )

    def _parse_list_manager_line(self, line: str) -> tuple[str, str, str, bool, str] | None:
        text = line.rstrip("\r\n")
        match = re.match(
            r"^(?P<indent>[ \t]*)(?:(?P<number>\d+)(?P<number_sep>[.)])|(?P<bullet>[-+*]))"
            r"(?P<spacing>[ \t]+)(?:(?P<task>\[[ xX]\])(?P<task_spacing>[ \t]+))?"
            r"(?P<body>.*)$",
            text,
        )
        if match is None:
            return None
        indent = match.group("indent") or ""
        bullet = match.group("bullet") or "-"
        task = match.group("task")
        body = match.group("body") or ""
        if task is not None:
            return indent, "task", bullet, "x" in task.lower(), body
        if match.group("number") is not None:
            return indent, "ordered", ".", False, body
        return indent, "bullet", bullet, False, body

    def _indent_measure(self, indent: str) -> int:
        return len(indent.expandtabs(self._indent_width()))

    def _render_list_manager_block(self, state: _ListManagerState) -> str:
        lines: list[str] = []
        ordered_counters: dict[int, int] = {}
        for item in state.items:
            level = max(0, item.level)
            indent = f"{state.base_indent}{self._indent_unit() * level}"
            for key in list(ordered_counters):
                if key > level:
                    ordered_counters.pop(key, None)
            if item.kind == "ordered":
                ordered_counters[level] = ordered_counters.get(level, 0) + 1
                marker = f"{ordered_counters[level]}. "
            elif item.kind == "task":
                marker = f"{item.bullet} [{'x' if item.checked else ' '}] "
                ordered_counters[level] = 0
            else:
                marker = f"{item.bullet} "
                ordered_counters[level] = 0
            lines.append(f"{indent}{marker}{item.text}".rstrip())
        block_text = "\n".join(lines)
        if state.trailing_newline:
            block_text += "\n"
        return block_text

    def _show_list_manager_dialog(self, state: _ListManagerState) -> str | None:
        wx = self._wx
        working_items = [
            _ListManagerItem(
                kind=item.kind,
                text=item.text,
                level=item.level,
                bullet=item.bullet,
                checked=item.checked,
            )
            for item in state.items
        ]
        selected_index: int | None = 0 if working_items else None
        dialog = wx.Dialog(self.frame, title="List Manager", size=(1020, 700))
        splitter = wx.SplitterWindow(dialog, style=wx.SP_LIVE_UPDATE)
        tree = wx.TreeCtrl(
            splitter,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HAS_VARIABLE_ROW_HEIGHT,
        )
        set_accessible_name(tree, "List items")
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(preview, "List item preview")
        splitter.SplitVertically(tree, preview, 420)
        splitter.SetMinimumPaneSize(260)
        item_indexes: dict[object, int] = {}
        root = tree.AddRoot("List Items")

        def list_preview(index: int | None) -> str:
            if index is None or index < 0 or index >= len(working_items):
                return "No list item selected."
            item = working_items[index]
            kind_label = {"bullet": "Bullet", "ordered": "Numbered", "task": "Task"}[item.kind]
            status = f"{kind_label} item at level {item.level + 1}"
            if item.kind == "task":
                status = f"{status} ({'checked' if item.checked else 'unchecked'})"
            return f"{status}\n\n{item.text or '(empty item)'}"

        def build_tree() -> None:
            nonlocal root, selected_index
            tree.DeleteAllItems()
            root = tree.AddRoot("List Items")
            item_indexes.clear()
            node_stack: list[tuple[int, object]] = []
            first_item = None
            selected_item = None
            for index, item in enumerate(working_items):
                label_prefix = (
                    "[ ]"
                    if item.kind == "task" and not item.checked
                    else "[x]"
                    if item.kind == "task"
                    else "1."
                    if item.kind == "ordered"
                    else item.bullet
                )
                label = f"{label_prefix} {item.text or '(empty item)'}"
                while node_stack and node_stack[-1][0] >= item.level:
                    node_stack.pop()
                parent = root if not node_stack else node_stack[-1][1]
                node = tree.AppendItem(parent, label)
                item_indexes[node] = index
                if first_item is None:
                    first_item = node
                if selected_index == index:
                    selected_item = node
                node_stack.append((item.level, node))
            tree.Expand(root)
            target = selected_item if selected_item is not None else first_item
            if target is not None:
                tree.SelectItem(target)
                selected_index = item_indexes.get(target)
            else:
                selected_index = None
            preview.ChangeValue(list_preview(selected_index))

        def subtree_bounds(index: int) -> tuple[int, int]:
            level = working_items[index].level
            end = index + 1
            while end < len(working_items) and working_items[end].level > level:
                end += 1
            return index, end

        def update_after_change(message: str, preferred_index: int | None) -> None:
            nonlocal selected_index
            if not working_items:
                selected_index = None
            elif preferred_index is None:
                selected_index = min(len(working_items) - 1, selected_index or 0)
            else:
                selected_index = max(0, min(preferred_index, len(working_items) - 1))
            build_tree()
            self._set_status(message)

        def require_selection() -> int | None:
            if selected_index is None or selected_index < 0 or selected_index >= len(working_items):
                return None
            return selected_index

        def move_up() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            target = start - 1
            while target >= 0 and working_items[target].level != working_items[index].level:
                target -= 1
            if target < 0:
                return
            block = working_items[start:end]
            del working_items[start:end]
            insert_at = target
            working_items[insert_at:insert_at] = block
            update_after_change("Moved list item up", insert_at)

        def move_down() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            target = end
            while (
                target < len(working_items)
                and working_items[target].level != working_items[index].level
            ):
                target += 1
            if target >= len(working_items):
                return
            next_start, next_end = subtree_bounds(target)
            block = working_items[start:end]
            del working_items[start:end]
            insert_at = next_end - len(block)
            working_items[insert_at:insert_at] = block
            update_after_change("Moved list item down", insert_at)

        def promote() -> None:
            index = require_selection()
            if index is None or working_items[index].level == 0:
                return
            start, end = subtree_bounds(index)
            for cursor in range(start, end):
                working_items[cursor].level = max(0, working_items[cursor].level - 1)
            update_after_change("Promoted list item", start)

        def demote() -> None:
            index = require_selection()
            if index is None or index == 0:
                return
            previous_level = working_items[index - 1].level
            if previous_level < working_items[index].level:
                return
            start, end = subtree_bounds(index)
            for cursor in range(start, end):
                working_items[cursor].level += 1
            update_after_change("Nested list item", start)

        def edit_item() -> None:
            index = require_selection()
            if index is None:
                return
            current = working_items[index]
            with wx.TextEntryDialog(
                dialog,
                "Edit list item text:",
                "Edit List Item",
                value=current.text,
            ) as entry:
                if self._show_modal_dialog(entry, "Edit List Item") != wx.ID_OK:
                    return
                current.text = entry.GetValue().strip()
            update_after_change("Updated list item", index)

        def add_item(as_child: bool) -> None:
            index = require_selection()
            if index is None:
                return
            current = working_items[index]
            with wx.TextEntryDialog(
                dialog,
                "Enter text for the new list item:",
                "Add List Item",
                value="",
            ) as entry:
                if self._show_modal_dialog(entry, "Add List Item") != wx.ID_OK:
                    return
                text_value = entry.GetValue().strip()
            level = current.level + 1 if as_child else current.level
            insert_at = subtree_bounds(index)[1] if as_child else subtree_bounds(index)[1]
            working_items.insert(
                insert_at,
                _ListManagerItem(
                    kind=current.kind,
                    text=text_value,
                    level=level,
                    bullet=current.bullet,
                    checked=False,
                ),
            )
            update_after_change("Added list item", insert_at)

        def delete_item() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            del working_items[start:end]
            update_after_change("Deleted list item", start - 1 if start > 0 else 0)

        def on_select(event: object) -> None:
            nonlocal selected_index
            selected_index = item_indexes.get(event.GetItem())
            preview.ChangeValue(list_preview(selected_index))
            event.Skip()

        button_column = wx.BoxSizer(wx.VERTICAL)
        move_up_button = wx.Button(dialog, label="Move Up")
        move_down_button = wx.Button(dialog, label="Move Down")
        promote_button = wx.Button(dialog, label="Promote")
        demote_button = wx.Button(dialog, label="Demote")
        edit_button = wx.Button(dialog, label="Edit...")
        add_child_button = wx.Button(dialog, label="Add Child...")
        add_sibling_button = wx.Button(dialog, label="Add Sibling...")
        delete_button = wx.Button(dialog, label="Delete")
        apply_button = wx.Button(dialog, id=wx.ID_OK, label="Apply Changes")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")

        for button in (
            move_up_button,
            move_down_button,
            promote_button,
            demote_button,
            edit_button,
            add_child_button,
            add_sibling_button,
            delete_button,
        ):
            button_column.Add(button, 0, wx.EXPAND | wx.BOTTOM, 6)
        button_column.AddStretchSpacer(1)
        button_column.Add(apply_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        button_column.Add(cancel_button, 0, wx.EXPAND)

        controls = wx.BoxSizer(wx.VERTICAL)
        controls.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Manage the current Markdown list as a tree. "
                    "Use Move/Promote/Demote to restructure without editing markers by hand."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        controls.Add(splitter, 1, wx.ALL | wx.EXPAND, 8)
        content = wx.BoxSizer(wx.HORIZONTAL)
        content.Add(controls, 1, wx.EXPAND)
        content.Add(button_column, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(content)

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, on_select)
        move_up_button.Bind(wx.EVT_BUTTON, lambda _e: move_up())
        move_down_button.Bind(wx.EVT_BUTTON, lambda _e: move_down())
        promote_button.Bind(wx.EVT_BUTTON, lambda _e: promote())
        demote_button.Bind(wx.EVT_BUTTON, lambda _e: demote())
        edit_button.Bind(wx.EVT_BUTTON, lambda _e: edit_item())
        add_child_button.Bind(wx.EVT_BUTTON, lambda _e: add_item(as_child=True))
        add_sibling_button.Bind(wx.EVT_BUTTON, lambda _e: add_item(as_child=False))
        delete_button.Bind(wx.EVT_BUTTON, lambda _e: delete_item())
        apply_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        build_tree()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "List Manager") != wx.ID_OK:
                return None
        finally:
            # Destroyed here: it used to outlive the edit (found by the A11Y-4
            # gate once this moved out of main_frame.py under F-08).
            dialog.Destroy()

        block = self._render_list_manager_block(
            _ListManagerState(
                start=state.start,
                end=state.end,
                trailing_newline=state.trailing_newline,
                base_indent=state.base_indent,
                items=working_items,
            )
        )
        text = self.editor.GetValue()
        return text[: state.start] + block + text[state.end :]
