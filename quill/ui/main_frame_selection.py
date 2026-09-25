"""Structural selection and mark-ring navigation for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``SelectionMarksMixin`` and every method resolves identically through the MRO;
the methods reference instance state (``self.editor``, ``self._mark_ring``)
and sibling commands via ``self`` exactly as before. Covers structural
selection (line/paragraph/block, expand/shrink, scope-aware selection actions,
directional select-to commands) and the temporary-jump mark ring
(set/pop/exchange/list).

There was a ``_selection_expand_stack`` here until 2026-09-17 and there is not
one now: it was never cleared, so Shrink popped a span from a selection you had
long since moved away from (bad.md L3). Shrink computes from the text, which is
what QUILL Lite has always done and is strictly better -- a history can only
answer for selections you reached by *expanding*, and the text can answer for
any of them.
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
    spoken_scope,
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
        """Announce a structural selection, in the shape both editors use.

        The sentence is :func:`quill.core.selection.describe_selection` since
        2026-09-17 (bad.md L14): QUILL said "Selected paragraph, 41 words" and
        QUILL Lite said "Selected paragraph, 412 characters, 41 words", and F8
        completion differed again. Neither was wrong, and having two was --
        somebody who uses both had to know which product they were in before
        they could parse the answer.

        **Recorded for Reselect**, which is the other half of the same fix:
        only F8 ever set ``_last_selection``, so Select Word, Line, Paragraph
        and Block -- the four people actually reach for -- were the four
        ``Ctrl+Shift+F8`` could not put back (bad.md L5).
        """
        from quill.core.selection import describe_selection

        if end <= start:
            # "Selected line, 0 words" on a blank line is a report that
            # something happened when nothing did. QUILL Lite's wording says
            # which thing was not there (bad.md L11).
            self._set_status(f"No {scope} at the cursor")
            return
        self._last_selection = (start, end)
        self._set_status(describe_selection(text, start, end, scope=scope))

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
        self.editor.SetFocus()
        self.editor.SetSelection(new_start, new_end)
        self._announce_selection_scope(scope, text, new_start, new_end)

    def shrink_selection(self) -> None:
        """Step back inwards, **computed from the text every time** (bad.md L3).

        There was an expansion stack, and it was never cleared. Expand around a
        paragraph, arrow away, select something else entirely, press Shrink --
        and it popped the span from the *earlier* selection and jumped you
        there. The stack could also hold an empty pair, so Shrink would collapse
        the selection and announce "Shrank selection" as though it had done
        something. Reproduced 2026-09-17 by ``scripts/probe_rich_edits.py``:
        stack held ``(0, 16)`` while the selection was ``(18, 39)``.

        QUILL Lite has always computed it, and computing is strictly better
        rather than merely simpler: a history can only answer for selections you
        reached *by expanding*, so selecting a paragraph outright and asking to
        shrink got a refusal a listener cannot tell from a broken command --
        even though "the line the caret is on" is an obvious answer. There is
        nothing an expansion history knows that the text does not.
        """
        from quill.core.selection import describe_selection

        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        smaller = shrink_selection_span(text, start, end)
        if smaller is None:
            self._set_status("Nothing smaller to select")
            return
        new_start, new_end, scope = smaller
        self.editor.SetFocus()
        self.editor.SetSelection(new_start, new_end)
        self._last_selection = (new_start, new_end)
        self._set_status(describe_selection(text, new_start, new_end, scope=scope))

    # ------------------------------------------------------------------ #
    # Clearing one, and reading one back
    # ------------------------------------------------------------------ #

    def unselect_all(self) -> None:
        """Drop the selection, staying where you are.

        Remembered first, so Reselect can put it back: clearing a selection is
        exactly the action people want undone, and this was one of the commands
        that never recorded one (bad.md L5).

        Moved here from ``main_frame.py`` on 2026-09-17, with ``say_selected``
        beside it. Both are selection verbs that happened to be written in the
        host rather than in the mixin whose subject they are, and GATE-11 is
        the right way to find that out: the L5 fix cost nine lines in a module
        that may not grow, and the answer to that is never a bigger budget.
        """
        start, end = self.editor.GetSelection()
        if end > start:
            self._last_selection = (start, end)
        caret = self.editor.GetInsertionPoint()
        self.editor.SetSelection(caret, caret)
        self._set_status("Selection cleared.")

    def say_selected(self) -> None:
        """Read the selection back on demand.

        Without sight there is no glance that confirms the selection is the one
        you meant, and the next keystroke may replace it.
        """
        from quill.platform.sr_announce import announce

        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("Nothing selected.")
            return
        text = self.editor.GetRange(start, end)
        preview = text[:60].replace("\n", " ")
        self._set_status_quiet("Say selected: " + preview + ("..." if len(text) > 60 else ""))
        announce(text)

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

        # The scope only goes in the title when it names something a person
        # can picture. "lines" and "span" name the classifier, not the
        # document, and this title is announced on open -- so it read
        # "Selection actions (lines, 180 words)" out loud.
        named = spoken_scope(scope)
        counted = pluralize(word_count, "word")
        inside = f"{named}, {counted}" if named else counted
        title = f"Selection actions ({inside})"
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
        """Drop a mark that can still be found after the document changes.

        The text is passed so the ring can capture an anchor (bad.md P1.2): a
        mark that remembers only an offset points at the wrong word after the
        next Replace All, and says nothing about having moved -- which is the
        failure a listener has no way to notice.
        """
        position = self.editor.GetInsertionPoint()
        self._mark_ring.set_mark(position, self.editor.GetValue())
        line, column = line_column_for_position(self.editor.GetValue(), position)
        self._set_status(f"Mark ring point set at line {line}, column {column} (temporary jump)")

    def pop_mark(self) -> None:
        """Jump to the newest mark, clamped, and remember where you came from.

        Clamped because a mark set before a big deletion can point past the end
        of the document, and an insertion point past the end is a jump to
        nowhere. Recorded on the location ring because a jump you cannot come
        back from is one people stop using (bad.md P1.2).
        """
        mark = self._mark_ring.pop_mark()
        if mark is None:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        mark = max(0, min(mark, len(self.editor.GetValue())))
        ring = getattr(self, "_location_ring", None)
        if ring is not None:
            ring.record(self.editor.GetInsertionPoint())
        self.editor.SetInsertionPoint(mark)
        self.editor.SetSelection(mark, mark)
        line, column = line_column_for_position(self.editor.GetValue(), mark)
        self._set_status(
            f"Popped to mark ring point at line {line}, column {column} (temporary jump)"
        )

    def exchange_point_and_mark(self) -> None:
        """Swap the caret with the newest mark, **and select what is between**.

        Two things at once, deliberately, which is QUILL Lite's behaviour and the
        useful one: you end up at the other end of the span *and* the span is
        selected, because wanting to be at the other end of something is
        normally a prelude to doing something to it (bad.md L12).

        It only moved before, so the span you had just defined was gone the
        moment you arrived at its far end, and taking it meant pressing the key
        again to get back and then Shift-arrowing the whole way.
        """
        from quill.core.selection import describe_selection

        text = self.editor.GetValue()
        current = self.editor.GetInsertionPoint()
        target = self._mark_ring.exchange_point_and_mark(current, text)
        if target is None:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        target = min(target, len(text))
        self.editor.SetInsertionPoint(target)
        start, end = sorted((current, target))
        if end > start:
            self.editor.SetSelection(start, end)
            self._last_selection = (start, end)
            self._set_status(describe_selection(text, start, end, prefix="Swapped with mark,"))
            return
        self.editor.SetSelection(target, target)
        self._set_status("Cursor and mark are in the same place")

    def list_marks(self) -> None:
        """The marks, as a list you can **go to one from** (bad.md L12).

        It was a message box: a read-only wall of "3. Line 41, Column 7" that
        you had to dismiss and then reach by some other means. A list of places
        that cannot take you to one of them is a list that answers the easy half
        of the question -- QUILL Lite's jumps, and has since it shipped.

        Each row leads with the line and carries a snippet of it, because "Line
        41" is not a place anybody recognises and the words on it are.
        """
        text = self.editor.GetValue()
        self._mark_ring.reanchor(text)
        self._mark_ring.clamped_to(len(text))
        marks = self._mark_ring.list_marks()
        if not marks:
            self._set_status("No marks in ring. Marks are temporary jump points.")
            return
        rows: list[tuple[int, str]] = []
        for position in reversed(marks):
            line, _column = line_column_for_position(text, position)
            start = text.rfind("\n", 0, position) + 1
            end = text.find("\n", position)
            snippet = text[start : end if end >= 0 else len(text)].strip()[:60]
            rows.append((position, f"Line {line}: {snippet or '(blank line)'}"))
        chosen = self._choose_mark_row(rows)
        if not isinstance(chosen, int):
            self._set_status(f"Listed {len(marks)} mark(s)")
            return
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(chosen)
        self.editor.SetFocus()
        line, column = line_column_for_position(text, chosen)
        self._set_status(f"Line {line}, column {column}")

    def _choose_mark_row(self, rows: list[tuple[int, str]]) -> int | None:
        """Show the mark list and return the chosen offset, or ``None``.

        A single-selection list with Enter on a row, which is the shape every
        other chooser in the product uses -- and the reason this is a method
        rather than four lines inline is that the dialog has to be substitutable
        in a test that has no display.
        """
        wx = self._wx
        dialog = wx.SingleChoiceDialog(
            self.frame,
            "Choose a mark and press Enter to go there. Marks are places you "
            "passed through; bookmarks are places you meant to keep.",
            "Marks",
            [label for _position, label in rows],
        )
        try:
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Marks") != wx.ID_OK:
                return None
            index = dialog.GetSelection()
        finally:
            dialog.Destroy()
        if not (0 <= index < len(rows)):
            return None
        return rows[index][0]
