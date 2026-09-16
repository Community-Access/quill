"""The Select menu: mark and extend, structure, and marks.

Selecting text without sight is not the same job as selecting it with a mouse,
and it is not solved by the same tools. There is no drag, and there is no glance
that confirms afterwards that you took what you meant to. Shift and an arrow key
is a fine way to take two letters and a miserable way to take four paragraphs --
you press, and press, and have no idea where you are.

So this menu offers three different answers, and they are genuinely different:

**Mark and select.** Press **F8** to drop a marker where you are. Then move by
*any* means at all -- arrows, Home, End, Ctrl+arrow, Page Down, Find, Go To
Line, a bookmark, the Command Palette -- and press **Shift+F8** to take
everything between the marker and where you ended up. This is the only way to
take an arbitrary run of text without holding a modifier down the whole way,
and it is the one to reach for when the thing you want does not line up with
any structure.

**The marker does not move the caret and does not start a mode**, and that is
the whole design. It used to: F8 set an anchor and then every navigation
key-up stretched a live selection to meet the caret. That fought the control
itself -- on wxMSW an arrow key pressed with text selected *collapses the
selection to its edge and stays there*, so the next key-up re-selected the same
span, and the caret stopped advancing after one character. Reported 2026-09-15:
"if I press F8 the cursor doesn't move at all after pressing it."

Computing the span at completion time instead fixes that and buys the larger
thing: between the two keystrokes you can use **anything**, including the
commands that move the caret by changing the selection themselves. Find a word,
then Shift+F8, and you have taken everything from the marker to the match --
which live extension could never have done, because Find's own selection was
the thing being overwritten. QUILL has always worked this way
(``main_frame_selection_span.py``); this is QuillLite catching up to it, by
deleting the part that was extra.

**Structure.** Take the whole word, line, paragraph, sentence or block in one
keystroke, without knowing where any of them begin. Then **Expand** outwards a
level at a time, or **Shrink** back in.

**Marks.** A mark is not a bookmark. A bookmark is a place you mean to keep; a
mark is where you were standing ten seconds ago, before you went to look
something up. **Pop Mark** is how you get back.

Everything here announces its outcome, and says *how much* it took. That last
part is the whole point: "Selected paragraph, 412 characters" is a fact you can
act on, where a silent selection is one you have to test by pressing something
destructive.

The engine is QUILL's :mod:`quill.core.selection` throughout, including the
shrink ladder, which was added there rather than here so QUILL gains it too.
"""

from __future__ import annotations

from quill.core.marks import line_column_for_position
from quill.core.selection import (
    block_span,
    selection_scope,
    sentence_span,
    shrink_selection,
)
from quill.core.sound_events import SoundEvent

__all__ = ["DocumentSelectionMixin"]

#: How many marks the ring holds. Ten is more than anybody uses at once and
#: small enough that the list stays something you can arrow through.
_MAX_MARKS = 10


class DocumentSelectionMixin:
    """Mark-and-extend, structural selection, and the mark ring."""

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    def _init_selection(self) -> None:
        """Set up the anchor, the mark ring and the expansion history."""
        #: Where F8 was pressed. ``None`` when extend mode is off.
        self._selection_anchor: int | None = None
        #: The last completed selection, for Reselect.
        self._last_selection: tuple[int, int] | None = None
        #: Positions you can bounce back to, most recent last.
        self._marks: list[int] = []

    # ------------------------------------------------------------------ #
    # Mark and extend
    # ------------------------------------------------------------------ #

    def cmd_start_selection(self) -> None:
        """F8: drop a marker here. Nothing else -- no mode, no caret movement.

        The line and column are in the message for the same reason QUILL puts
        them there: setting a marker changes nothing a screen reader announces,
        so without the sentence F8 is a key that appears to do nothing, and the
        only way to find out whether it worked is to press Shift+F8 and hope.
        """
        self._selection_anchor = self.control.GetInsertionPoint()
        line, column = line_column_for_position(self.control.GetValue(), self._selection_anchor)
        self._action(
            SoundEvent.SELECTION_STARTED,
            f"Selection marked at line {line}, column {column}. "
            "Move anywhere, then Shift F8 to select.",
        )
        self._sync_check_items()

    def cmd_complete_selection(self) -> None:
        """Shift+F8: take everything between the marker and here, and say so.

        The span is the marker and the caret, computed at this moment -- not
        whatever happens to be selected. That distinction is the feature: a Find
        between the two keystrokes leaves its own match selected, and honouring
        *that* would hand back the match instead of the run the user marked.
        """
        if self._selection_anchor is None:
            self._announce("No selection marked. Press F8 where you want it to start.")
            return
        anchor, self._selection_anchor = self._selection_anchor, None
        limit = self.control.GetLastPosition()
        start, end = sorted((min(anchor, limit), min(self.control.GetInsertionPoint(), limit)))
        if end <= start:
            self._announce("Selection cancelled, nothing selected")
        else:
            self.control.SetSelection(start, end)
            self._last_selection = (start, end)
            # The count is spoken whatever the feedback mode is: "how much did I
            # just take" is a fact, not a cue, and a tone cannot carry it. The
            # mode governs the earcon that comes with it.
            self._cue(SoundEvent.SELECTION_COMPLETED)
            self._announce_span(start, end, "Selected")
        self._sync_check_items()
        self._touch_status()

    def cmd_toggle_extend_mode(self) -> None:
        """Ctrl+Alt+F8: turn extending on or off without moving the caret.

        The same state F8 sets, reachable as a toggle -- which is what somebody
        wants when they have already arrived at the right starting point and do
        not want a keystroke that might move them.
        """
        if self._selection_anchor is None:
            self.cmd_start_selection()
            return
        self.cmd_complete_selection()

    def cmd_reselect(self) -> None:
        """Ctrl+Shift+F8: put back the selection you just had.

        For the moment after an arrow key has silently thrown away a selection
        that took six keystrokes to build.
        """
        if self._last_selection is None:
            self._announce("No previous selection to restore")
            return
        start, end = self._last_selection
        limit = self.control.GetLastPosition()
        start, end = min(start, limit), min(end, limit)
        if end <= start:
            self._announce("The previous selection is no longer there")
            return
        self.control.SetSelection(start, end)
        self._announce_span(start, end, "Reselected")
        self._touch_status()

    def cmd_go_to_selection_start(self) -> None:
        """Alt+Shift+F8: go to where the selection begins, keeping it selected.

        Reading a long selection starts at its beginning, and after extending
        downwards the caret is at the far end of it.
        """
        start, end = self.control.GetSelection()
        if end <= start:
            self._announce("Nothing is selected")
            return
        self.control.ShowPosition(start)
        self.control.SetInsertionPoint(start)
        self.control.SetSelection(start, end)
        self._announce("At the start of the selection")
        self._touch_status()

    def selection_extend_active(self) -> bool:
        """True while F8 extending is on. Read by the menu's check mark."""
        return self._selection_anchor is not None

    def text_changed_while_extending(self) -> None:
        """End extend mode because the document changed under it.

        Typing into a selection you are still building replaces it, so there is
        nothing left to extend and the anchor now points into text that has
        moved. Called from the window's text hook rather than inferred from a key
        code: a paste, a menu command and a letter key all change the text and
        only one of them is a keystroke.
        """
        if self._selection_anchor is None:
            return
        self._selection_anchor = None
        self._sync_check_items()

    def cancel_extend_selection(self) -> bool:
        """Drop the marker without selecting anything. ``True`` when there was one.

        Silence here would leave somebody unsure whether the marker is still
        waiting -- the state is invisible, so every change to it is spoken.

        Returns whether it did anything, because Escape is bound to this and
        Escape belongs to everything else too: when no marker is waiting the
        key has to carry on to whatever would otherwise have had it.
        """
        if self._selection_anchor is None:
            return False
        self._selection_anchor = None
        self._announce("Selection marker dropped")
        self._sync_check_items()
        return True

    # ------------------------------------------------------------------ #
    # Structure
    # ------------------------------------------------------------------ #

    def cmd_select_sentence(self) -> None:
        """Ctrl+Space: take the sentence the caret is in."""
        self._select_computed(sentence_span, "sentence")

    def cmd_select_block(self) -> None:
        """Ctrl+Alt+Shift+B: take the block -- the run between blank lines."""
        self._select_computed(block_span, "block")

    def _select_computed(self, span_fn, kind: str) -> None:
        text = self.control.GetValue()
        start, end = span_fn(text, self.control.GetInsertionPoint())
        if end <= start:
            self._announce(f"No {kind} at the cursor")
            return
        self.control.SetSelection(start, end)
        self.control.ShowPosition(start)
        self._last_selection = (start, end)
        self._announce_span(start, end, f"Selected {kind},")
        self._touch_status()

    def cmd_shrink_selection(self) -> None:
        """Ctrl+Alt+Shift+X: step back inwards, the inverse of Expand.

        Computed from the text rather than remembered from an expansion, so it
        works on a selection you made any other way -- which is the case a
        history stack silently cannot answer.
        """
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        if end <= start:
            self._announce("Nothing is selected")
            return
        smaller = shrink_selection(text, start, end)
        if smaller is None:
            self._announce("Nothing smaller to select")
            return
        new_start, new_end, scope = smaller
        self.control.SetSelection(new_start, new_end)
        self.control.ShowPosition(new_start)
        self._announce_span(new_start, new_end, f"Selected {scope},")
        self._touch_status()

    def cmd_unselect_all(self) -> None:
        """Ctrl+Shift+A: drop the selection, staying where you are.

        Remembered first, so Reselect can put it back -- clearing a selection is
        exactly the action people undo.
        """
        start, end = self.control.GetSelection()
        if end <= start:
            self._announce("Nothing is selected")
            return
        self._last_selection = (start, end)
        self.control.SetSelection(start, start)
        self.control.SetInsertionPoint(start)
        self._announce("Selection cleared")
        self._touch_status()

    # ------------------------------------------------------------------ #
    # Marks
    # ------------------------------------------------------------------ #

    def cmd_set_mark(self) -> None:
        """Ctrl+Alt+Shift+K: remember where you are, so you can come back."""
        position = self.control.GetInsertionPoint()
        self._marks.append(position)
        del self._marks[:-_MAX_MARKS]
        line = self._line_of(position)
        self._announce(f"Mark set at line {line}. {self._mark_count()}.")

    def cmd_pop_mark(self) -> None:
        """Ctrl+M: go back to the most recent mark, and use it up."""
        if not self._marks:
            self._announce("No marks set")
            return
        position = min(self._marks.pop(), self.control.GetLastPosition())
        self.control.SetInsertionPoint(position)
        self.control.ShowPosition(position)
        self._announce(f"Line {self._line_of(position)}. {self._mark_count()} left.")
        self._touch_status()

    def cmd_list_marks(self) -> None:
        """Alt+M: every mark, newest first, with the line it is on."""
        from quill.apps.lite_dialogs import choose_from_rows

        if not self._marks:
            self._announce("No marks set")
            return
        text = self.control.GetValue()
        rows = []
        for position in reversed(self._marks):
            line = self._line_of(position)
            start = text.rfind("\n", 0, position) + 1
            end = text.find("\n", position)
            preview = text[start : end if end >= 0 else len(text)].strip()[:60]
            rows.append((position, f"Line {line}: {preview or '(blank line)'}"))
        chosen = choose_from_rows(
            self,
            title="Marks",
            label="Marks, newest first:",
            help_text=(
                "Choose a mark and press Enter to go there. Marks are places you "
                "passed through; bookmarks are places you meant to keep."
            ),
            rows=rows,
        )
        if not isinstance(chosen, int):
            self.control.SetFocus()
            return
        position = min(chosen, self.control.GetLastPosition())
        self.control.SetInsertionPoint(position)
        self.control.ShowPosition(position)
        self.control.SetFocus()
        self._announce(f"Line {self._line_of(position)}")
        self._touch_status()

    def cmd_exchange_point_mark(self) -> None:
        """Ctrl+Alt+X: swap the caret with the newest mark, and select between.

        Two things at once, and deliberately: you end up at the other end of the
        span *and* the span itself is selected, which is the usual reason for
        wanting to be there.
        """
        if not self._marks:
            self._announce("No marks set")
            return
        limit = self.control.GetLastPosition()
        caret = self.control.GetInsertionPoint()
        mark = min(self._marks[-1], limit)
        self._marks[-1] = caret
        self.control.SetInsertionPoint(mark)
        start, end = sorted((caret, mark))
        if end > start:
            self.control.SetSelection(start, end)
            self._last_selection = (start, end)
            self._announce_span(start, end, "Swapped with mark, selected")
        else:
            self._announce("Cursor and mark are in the same place")
        self.control.ShowPosition(mark)
        self._touch_status()

    # ------------------------------------------------------------------ #
    # Reading and duplicating
    # ------------------------------------------------------------------ #

    def cmd_say_selection(self) -> None:
        """Ctrl+Shift+Y: read back what is selected, on demand.

        Not a convenience. Without sight there is no glance that confirms the
        selection is the one you meant, and the next keystroke may replace it.
        Long selections are summarised rather than read in full -- forty seconds
        of speech you cannot interrupt usefully is not an answer.
        """
        start, end = self.control.GetSelection()
        if end <= start:
            self._announce("Nothing is selected")
            return
        selected = self.control.GetValue()[start:end]
        scope = selection_scope(self.control.GetValue(), start, end)
        if len(selected) <= 200:
            self._announce(selected)
            return
        head = selected[:100].replace("\n", " ").strip()
        tail = selected[-60:].replace("\n", " ").strip()
        self._announce(
            f"{len(selected)} characters, {len(selected.split())} words, {scope}. "
            f"Begins: {head}. Ends: {tail}"
        )

    def cmd_duplicate_selection(self) -> None:
        """Ctrl+Alt+Q: put a second copy in, right after the first.

        With nothing selected it duplicates the line, which is what the command
        is nearly always wanted for.
        """
        start, end = self.control.GetSelection()
        text = self.control.GetValue()
        what = "selection"
        if end <= start:
            from quill.core.selection import line_span

            start, end = line_span(text, self.control.GetInsertionPoint())
            what = "line"
            if end <= start:
                self._announce("Nothing to duplicate")
                return
        copied = text[start:end]
        separator = "\n" if what == "line" else ""
        self.control.SetInsertionPoint(end)
        self.control.WriteText(separator + copied)
        self._set_modified(True)
        self._announce(f"Duplicated {what}, {len(copied)} characters")
        self._touch_status()

    # ------------------------------------------------------------------ #
    # Shared
    # ------------------------------------------------------------------ #

    def _announce_span(self, start: int, end: int, prefix: str) -> None:
        """Say how much was taken. The count is the part that is load-bearing."""
        selected = self.control.GetValue()[start:end]
        words = len(selected.split())
        characters = len(selected)
        unit = "word" if words == 1 else "words"
        self._announce(f"{prefix} {characters} characters, {words} {unit}")

    def _mark_count(self) -> str:
        """ "3 marks", "1 mark", "no marks" -- because this is read aloud.

        A count that reads "1 marks" is the kind of thing a listener notices
        every single time and a reader never does.
        """
        total = len(self._marks)
        if total == 0:
            return "no marks"
        return "1 mark" if total == 1 else f"{total} marks"

    def _line_of(self, position: int) -> int:
        """The 1-based line number *position* falls on."""
        return self.control.GetValue().count("\n", 0, position) + 1
