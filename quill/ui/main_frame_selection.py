"""Structural selection and mark-ring navigation for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``SelectionMarksMixin`` and every method resolves identically through the MRO;
the methods reference instance state (``self.editor``, ``self._mark_ring``,
``self._selection_expand_stack``) and sibling commands via ``self`` exactly as
before. Covers structural selection (line/paragraph/block, expand/shrink,
scope-aware selection actions, directional select-to commands) and the
temporary-jump mark ring (set/pop/exchange/list).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.marks import line_column_for_position
from quill.core.selection import (
    block_span,
    expand_selection,
    line_span,
    paragraph_span,
    selection_scope,
    word_span,
)
from quill.core.selection import (
    shrink_selection as shrink_selection_span,
)
from quill.ui.dialog_contract import apply_modal_ids


class SelectionMarksMixin:
    def select_word(self) -> None:
        """Select the word the caret is in.

        QUILL had select_line, select_paragraph and select_block and no
        select_word, which left the innermost rung of its own expansion ladder
        as the only one you could not ask for directly.
        """
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = word_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(start, end)
        self._announce_selection_scope("word", text, start, end)

    def select_line(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = line_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(start, end)
        self._announce_selection_scope("line", text, start, end)

    def select_paragraph(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = paragraph_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(start, end)
        self._announce_selection_scope("paragraph", text, start, end)

    def select_block(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = block_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(start, end)
        self._announce_selection_scope("block", text, start, end)

    def _announce_selection_scope(self, scope: str, text: str, start: int, end: int) -> None:
        """Announce a structural selection with its scope and word count (SEL-1)."""
        from quill.core.announcements import format_announcement

        words = len(text[start:end].split())
        self._set_status(format_announcement("Selected", scope, count=words, unit="word"))

    def expand_selection(self) -> None:
        """Grow the selection to the next structural unit, announcing scope (SEL-2)."""
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        if start == end:
            start = end = self.editor.GetInsertionPoint()
        result = expand_selection(text, start, end)
        if result is None:
            self._set_status("Selection already spans the whole document")
            return
        new_start, new_end, scope = result
        stack = getattr(self, "_selection_expand_stack", None)
        if stack is None:
            stack = []
            self._selection_expand_stack = stack
        stack.append((start, end))
        self.editor.SetFocus()
        self.editor.SetSelection(new_start, new_end)
        self._announce_selection_scope(scope, text, new_start, new_end)

    def shrink_selection(self) -> None:
        """Shrink the selection to the previously expanded unit (SEL-2).

        With no expansion history, fall back to the computed inverse
        (``quill.core.selection.shrink_selection``) rather than refusing. The
        stack only knows about selections you reached *by expanding*: select a
        paragraph outright and ask to shrink, and it has nothing to say, even
        though "the line the caret is on" is an obvious answer. A listener
        cannot tell that refusal apart from a broken command.
        """
        stack = getattr(self, "_selection_expand_stack", None)
        if not stack:
            text = self.editor.GetValue()
            start, end = self.editor.GetSelection()
            smaller = shrink_selection_span(text, start, end)
            if smaller is None:
                self._set_status("No selection to shrink")
                return
            new_start, new_end, scope = smaller
            self.editor.SetFocus()
            self.editor.SetSelection(new_start, new_end)
            self._announce_selection_scope(scope, text, new_start, new_end)
            return
        previous_start, previous_end = stack.pop()
        text = self.editor.GetValue()
        self.editor.SetFocus()
        self.editor.SetSelection(previous_start, previous_end)
        if previous_start == previous_end:
            self._set_status("Shrank selection")
            return
        words = len(text[previous_start:previous_end].split())
        from quill.core.announcements import format_announcement

        self._set_status(format_announcement("Shrank", "selection", count=words, unit="word"))

    def _has_active_selection(self) -> bool:
        editor = getattr(self, "editor", None)
        get_selection = getattr(editor, "GetSelection", None)
        if not callable(get_selection):
            return False
        start, end = get_selection()
        return start != end

    def _selection_action_specs(
        self, scope: str, surface: str | None
    ) -> list[tuple[str, Callable[[], None]]]:
        """Build the scope-aware list of actions for the current selection (SEL-3).

        The list adapts to what is selected: case and clipboard actions always
        apply, Markdown/HTML emphasis appears only on a markup surface, and the
        line-oriented actions (sort, indent, comment) appear only for multi-line
        selections where they are meaningful.
        """
        multiline = scope in {"line", "lines", "paragraph", "block", "document"}
        specs: list[tuple[str, Callable[[], None]]] = [
            ("Copy", lambda: self.editor.Copy()),
            ("Cut", lambda: self.editor.Cut()),
            ("Upper case", self.format_upper_case),
            ("Lower case", self.format_lower_case),
            ("Title case", self.format_title_case),
            ("Sentence case", self.format_sentence_case),
            ("Toggle case", self.format_toggle_case),
        ]
        if surface is not None:
            specs.append(("Bold", self.format_bold))
            specs.append(("Italic", self.format_italic))
        specs.append(("Expand selection", self.expand_selection))
        specs.append(("Shrink selection", self.shrink_selection))
        if multiline:
            specs.append(("Sort lines ascending", self.sort_lines_ascending))
            specs.append(("Sort lines descending", self.sort_lines_descending))
            specs.append(("Indent", self.format_indent))
            specs.append(("Outdent", self.format_outdent))
            specs.append(("Toggle line comment", self.format_toggle_line_comment))
        return specs

    def quill_key_selection_actions(self) -> None:
        """Offer scope-aware actions for the active selection (SEL-3).

        Invoked from the QUILL key when text is selected. Presents an accessible
        stock choice dialog whose actions match the selection's structural scope,
        then runs the chosen action against the existing, tested commands.
        """
        wx = self._wx
        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("Select text first to use selection actions")
            return
        text = self.editor.GetValue()
        scope = selection_scope(text, start, end)
        surface = self._active_markup_surface()
        specs = self._selection_action_specs(scope, surface)
        labels = [label for label, _action in specs]
        word_count = len(text[start:end].split())
        from quill.core.announcements import pluralize

        title = f"Selection actions ({scope}, {pluralize(word_count, 'word')})"
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose an action for the selection:",
            title,
            choices=labels,
        ) as dialog:
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                self._set_status("Selection actions cancelled")
                return
            chosen = dialog.GetStringSelection()
        for label, action in specs:
            if label == chosen:
                action()
                return

    def set_named_mark(self) -> None:
        """Prompt for a name and store the current cursor position (SEL-4)."""
        wx = self._wx
        with wx.TextEntryDialog(self.frame, "Mark name:", "Set Named Mark") as dlg:
            apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dlg, "Set Named Mark") != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
        if not name:
            self._set_status("Mark name cannot be empty")
            return
        position = self.editor.GetInsertionPoint()
        self._named_marks.set(name, position)
        line, column = line_column_for_position(self.editor.GetValue(), position)
        self._set_status(f"Named mark '{name}' set at line {line}, column {column}")

    def jump_to_named_mark(self) -> None:
        """Show all named marks and jump to the chosen one (SEL-4)."""
        wx = self._wx
        names = self._named_marks.names()
        if not names:
            self._set_status("No named marks. Use Set Named Mark to create one.")
            return
        text = self.editor.GetValue()
        labels = []
        for name in names:
            pos = self._named_marks.get(name)
            if pos is not None:
                pos = min(pos, len(text))
                line, col = line_column_for_position(text, pos)
                labels.append(f"{name}  (line {line}, col {col})")
            else:
                labels.append(name)
        with wx.SingleChoiceDialog(
            self.frame,
            "Jump to mark:",
            "Named Marks",
            choices=labels,
        ) as dlg:
            apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dlg, "Named Marks") != wx.ID_OK:
                return
            idx = dlg.GetSelection()
        if idx < 0 or idx >= len(names):
            return
        pos = self._named_marks.get(names[idx])
        if pos is None:
            return
        pos = min(pos, len(self.editor.GetValue()))
        self.editor.SetInsertionPoint(pos)
        self.editor.SetFocus()
        line, column = line_column_for_position(self.editor.GetValue(), pos)
        self._set_status(f"Jumped to mark '{names[idx]}' at line {line}, column {column}")

    def open_review_buffer(self) -> None:
        """Open the active selection in a read-only dialog for screen-reader review (SEL-4)."""
        wx = self._wx
        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("Select text first to open in review buffer")
            return
        text = self.editor.GetValue()[start:end]
        with wx.Dialog(self.frame, title="Review Buffer") as dlg:
            sizer = wx.BoxSizer(wx.VERTICAL)
            ctrl = wx.TextCtrl(
                dlg,
                value=text,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
            )
            ctrl.SetName("Review buffer — read-only copy of the selected text")
            ctrl.SetFocus()
            sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, 8)
            close_btn = wx.Button(dlg, wx.ID_CLOSE, "Close")
            btn_row = wx.BoxSizer(wx.HORIZONTAL)
            btn_row.AddStretchSpacer()
            btn_row.Add(close_btn, 0)
            sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
            dlg.SetSizer(sizer)
            dlg.SetSize((500, 400))
            close_btn.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_CLOSE))
            apply_modal_ids(dlg, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
            self._show_modal_dialog(dlg, "Review Buffer")
        words = len(text.split())
        self._set_status_quiet(f"Closed review buffer ({words} words)")

    def select_to_start_of_line(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, _end = line_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(start, cursor)
        self._set_status("Selected to start of line")

    def select_to_end_of_line(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        _start, end = line_span(text, cursor)
        self.editor.SetFocus()
        self.editor.SetSelection(cursor, end)
        self._set_status("Selected to end of line")

    def select_to_start_of_document(self) -> None:
        cursor = self.editor.GetInsertionPoint()
        self.editor.SetFocus()
        self.editor.SetSelection(0, cursor)
        self._set_status("Selected to start of document")

    def select_to_end_of_document(self) -> None:
        cursor = self.editor.GetInsertionPoint()
        self.editor.SetFocus()
        self.editor.SetSelection(cursor, self.editor.GetLastPosition())
        self._set_status("Selected to end of document")

    def set_mark(self) -> None:
        position = self.editor.GetInsertionPoint()
        self._mark_ring.set_mark(position)
        line, column = line_column_for_position(self.editor.GetValue(), position)
        self._set_status(f"Mark ring point set at line {line}, column {column} (temporary jump)")

    def pop_mark(self) -> None:
        mark = self._mark_ring.pop_mark()
        if mark is None:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        self.editor.SetInsertionPoint(mark)
        self.editor.SetSelection(mark, mark)
        line, column = line_column_for_position(self.editor.GetValue(), mark)
        self._set_status(
            f"Popped to mark ring point at line {line}, column {column} (temporary jump)"
        )

    def exchange_point_and_mark(self) -> None:
        current = self.editor.GetInsertionPoint()
        target = self._mark_ring.exchange_point_and_mark(current)
        if target is None:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        self.editor.SetInsertionPoint(target)
        self.editor.SetSelection(target, target)
        line, column = line_column_for_position(self.editor.GetValue(), target)
        self._set_status(f"Exchanged point and mark to line {line}, column {column}")

    def list_marks(self) -> None:
        wx = self._wx
        marks = self._mark_ring.list_marks()
        if not marks:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        lines: list[str] = []
        text = self.editor.GetValue()
        for index, position in enumerate(reversed(marks), start=1):
            line, column = line_column_for_position(text, position)
            lines.append(f"{index}. Line {line}, Column {column}")
        self._show_message_box(
            "\n".join(lines),
            "Mark Ring (Temporary Jump Points)",
            wx.ICON_INFORMATION | wx.OK,
        )
        self._set_status(f"Listed {len(marks)} mark(s)")
