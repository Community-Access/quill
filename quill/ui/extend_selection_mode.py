"""Extend Selection Mode: a sticky Shift, shared by both editors.

Select by navigating. No modifier held down the whole way, and -- the part that
matters for somebody listening -- no "selected" from the screen reader on every
single arrow press, which is what makes Shift+Down unusable for taking four
paragraphs.

**Why this mechanism and not the obvious one.** The obvious one is to set an
anchor and stretch a live selection to meet the caret after each navigation key.
QUILL Lite shipped that, and it did not work: on wxMSW an arrow key pressed while
text is selected *collapses the selection to its edge and stays there*, so the
next key-up re-selected the same span and the caret never advanced. It was
deleted in ``d20fabe`` and QUILL Lite has had nothing since.

QUILL's version, which is this one, intercepts the key **before** the control,
moves the caret itself, and leaves no selection behind for the control to
fight -- the span is applied only when a non-movement key commits it. Opposite
mechanism, and it works. The first pass of bad.md called it "the design Lite
deleted"; it is the reverse, and 5.3a is the correction.

Extracted here on 2026-09-17 so QUILL Lite can take it (bad.md P2.13, Tier 2)
rather than writing a third attempt, and so the four movement bugs it carried
were fixed once instead of twice (bad.md P1.2a):

* the line table was rebuilt by scanning the whole document on **every
  keystroke**, which in a 50 MB log is the cost the document mirror exists to
  remove;
* Page Up and Page Down were hardcoded to **ten lines**, which is a page on
  nobody's screen;
* Up and Down moved by **logical** line, so one press inside a soft-wrapped
  paragraph sent the caret a whole paragraph away;
* word movement stopped only at whitespace, where Windows also stops at
  punctuation.

A host supplies two things: ``editor`` (the wx text control) and ``doc_text``
(a :class:`~quill.core.document_text.DocumentText` mirror). Everything else is
here, including the ``wx`` handle -- QUILL keeps one on ``self._wx`` so the
module can be imported without wx present, and this honours that where it finds
it rather than making each host implement a hook.
"""

from __future__ import annotations

import sys
from typing import Any

from quill.core.caret_motion import lines_per_page, word_boundary

__all__ = ["ExtendSelectionMixin"]


class ExtendSelectionMixin:
    """Caret movement while extending, and the state that says we are."""

    #: On or off. The state is invisible -- there is no selection on screen
    #: while it is on -- so every change to it is spoken.
    _extend_selection_mode: bool = False
    #: Where the span starts, set on the first movement key rather than when the
    #: mode is switched on, so turning it on and then thinking about it does not
    #: pin the anchor somewhere stale.
    _extend_selection_anchor: int | None = None

    #: The keys this mode owns. Anything else commits the span and is passed to
    #: the control, which is how typing a letter replaces the selection.
    _EXTEND_MOVEMENT_KEYS = (
        "WXK_LEFT",
        "WXK_RIGHT",
        "WXK_UP",
        "WXK_DOWN",
        "WXK_HOME",
        "WXK_END",
        "WXK_PAGEUP",
        "WXK_PAGEDOWN",
    )

    # ------------------------------------------------------------------ #
    # The state machine
    # ------------------------------------------------------------------ #

    def _extend_say(self, message: str) -> None:
        """Say something, through whichever seam this host announces with.

        ``_set_status`` **first**, because in QUILL that is the one that both
        writes the status bar and announces -- reaching for ``_announce`` there
        speaks the sentence and leaves the bar empty, so F6 could not bring it
        back. QUILL Lite has no ``_set_status`` and announces directly.
        """
        status = getattr(self, "_set_status", None)
        if callable(status):
            status(message)
            return
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(message)

    def toggle_extend_selection_mode(self, enabled: bool | None = None) -> None:
        """Turn the sticky Shift on or off, and say which.

        Spoken in both directions because there is nothing on screen to read:
        with the mode on and no movement yet there is no selection, no changed
        control state and no focus move, so silence here is a key that appears
        to have done nothing.
        """
        from quill.core.marks import line_column_for_position

        next_state = (not self._extend_selection_mode) if enabled is None else bool(enabled)
        self._extend_selection_mode = next_state
        if next_state:
            self._extend_selection_anchor = self._extend_control().GetInsertionPoint()
            line, column = line_column_for_position(
                self._extend_control().GetValue(), self._extend_selection_anchor
            )
            self._extend_say(f"Extend selection mode on. Anchor at line {line}, column {column}.")
        else:
            self._extend_selection_anchor = None
            # What you ended up with, when there is something to report. The
            # span was just collapsed, so this sentence is the only evidence of
            # how far it reached -- there is nothing on screen to go back and
            # read.
            last = getattr(self, "_last_selection", None)
            if last is None:
                self._extend_say("Extend selection mode off.")
            else:
                text = self._extend_control().GetValue()
                start_line, start_col = line_column_for_position(text, last[0])
                end_line, end_col = line_column_for_position(text, last[1])
                self._extend_say(
                    f"Extend selection mode off. Last region: line {start_line} "
                    f"column {start_col} to line {end_line} column {end_col}."
                )
        sync = getattr(self, "_sync_check_items", None)
        if callable(sync):
            sync()

    def extend_selection_active(self) -> bool:
        """True while the mode is on. Read by the menu's check mark."""
        return bool(self._extend_selection_mode)

    def _apply_extend_selection(self) -> None:
        """Put the span on screen: anchor to caret, whichever way round."""
        if not self._extend_selection_mode or self._extend_selection_anchor is None:
            return
        caret = self._extend_control().GetInsertionPoint()
        start = min(self._extend_selection_anchor, caret)
        end = max(self._extend_selection_anchor, caret)
        self._extend_control().SetSelection(start, end)
        if start != end:
            self._last_selection = (start, end)

    def _has_pending_extend_selection(self) -> bool:
        if not self._extend_selection_mode or self._extend_selection_anchor is None:
            return False
        selection_start, selection_end = self._extend_control().GetSelection()
        if selection_start != selection_end:
            return False
        return self._extend_control().GetInsertionPoint() != self._extend_selection_anchor

    def _commit_pending_extend_selection(self) -> bool:
        if not self._has_pending_extend_selection():
            return False
        self._apply_extend_selection()
        return True

    def handle_extend_selection_key(self, event: Any) -> bool:
        """One key while the mode is on. ``True`` when this handled it.

        ``False`` means the caller should let the control have the key --
        including for a non-movement key, which commits the span on the way
        past so that the letter typed next replaces the selection, exactly as
        it would after a Shift+arrow.

        **The selection is collapsed after every move**, and that is the whole
        mechanism rather than an oddity: on wxMSW an arrow key pressed while
        text is selected collapses the selection to its edge and stops, so a
        live selection between the two keystrokes would fight the caret and
        win. Leaving the control nothing to fight is what makes this work where
        QUILL Lite's key-up version (``d20fabe``) could not (5.3a).
        """
        if not self._extend_selection_mode:
            return False
        wx = self._extend_wx()
        movement = {getattr(wx, name) for name in self._EXTEND_MOVEMENT_KEYS}
        if event.GetKeyCode() not in movement:
            self._commit_pending_extend_selection()
            return False
        if self._extend_selection_anchor is None:
            self._extend_selection_anchor = self._extend_control().GetInsertionPoint()
        if not self._move_extend_selection_caret(event):
            return False
        caret = self._extend_control().GetInsertionPoint()
        self._extend_control().SetSelection(caret, caret)
        return True

    def cancel_extend_selection_mode(self) -> bool:
        """Escape: turn the mode off, collapsing whatever it had. ``True`` if on.

        Returns whether it did anything, because Escape belongs to everything
        else too: with the mode off the key must carry on to whatever would
        otherwise have had it.
        """
        if not self._extend_selection_mode:
            return False
        caret = self._extend_control().GetInsertionPoint()
        self.toggle_extend_selection_mode(False)
        self._extend_control().SetSelection(caret, caret)
        return True

    # ------------------------------------------------------------------ #
    # The line table
    # ------------------------------------------------------------------ #

    def _extend_line_starts(self) -> list[int]:
        """Where every line begins, from the mirror rather than from a scan.

        ``_move_extend_selection_caret`` used to build this list inline, walking
        every character of the document, on each arrow press. The mirror caches
        it against a revision counter and invalidates on edit, so holding Down
        in a large file costs one lookup per key instead of one pass per key.
        """
        mirror = getattr(self, "doc_text", None)
        if mirror is not None:
            return mirror.line_starts()
        text = self._extend_control().GetValue()
        starts = [0]
        for index, character in enumerate(text):
            if character == "\n":
                starts.append(index + 1)
        return starts

    def _extend_lines_per_page(self) -> int:
        """A real page, measured from the window rather than assumed to be ten."""
        editor = self._extend_control()
        try:
            height = int(editor.GetClientSize().height)
            char_height = int(editor.GetCharHeight())
        except Exception:  # noqa: BLE001 - a measurement must never raise
            return lines_per_page(0, 0)
        return lines_per_page(height, char_height)

    # ------------------------------------------------------------------ #
    # Vertical movement, through the control's own idea of a line
    # ------------------------------------------------------------------ #

    def _extend_move_vertical(self, delta: int) -> bool:
        """Move *delta* lines, following soft wrap where the control can say.

        ``PositionToXY`` / ``XYToPosition`` are the control's own mapping, and
        on a wrapped multiline control the "line" in that mapping is the one on
        screen -- which is the line a person means when they press Down. Moving
        by *logical* line instead sent the caret past an entire wrapped
        paragraph in one press, which is the bug rather than a rounding error.

        The text-based walk is kept as the fallback for a control that will not
        answer (off Windows, a plain ``wx.TextCtrl``, a window not yet shown),
        because a Down key that does nothing is worse than one that moves by
        paragraph.
        """
        editor = self._extend_control()
        caret = editor.GetInsertionPoint()
        position = self._extend_visual_move(caret, delta)
        if position is None:
            return self._extend_move_vertical_by_text(delta)
        if position == caret:
            return False
        editor.SetInsertionPoint(position)
        return True

    def _extend_visual_move(self, caret: int, delta: int) -> int | None:
        """The offset *delta* display lines away, or ``None`` if unanswerable."""
        editor = self._extend_control()
        to_xy = getattr(editor, "PositionToXY", None)
        to_position = getattr(editor, "XYToPosition", None)
        if not callable(to_xy) or not callable(to_position):
            return None
        try:
            result = to_xy(caret)
        except Exception:  # noqa: BLE001
            return None
        # wxMSW returns (ok, col, row); other ports return (col, row).
        if not isinstance(result, tuple) or len(result) not in (2, 3):
            return None
        if len(result) == 3:
            ok, column, row = result
            if not ok:
                return None
        else:
            column, row = result
        try:
            total = int(editor.GetNumberOfLines())
        except Exception:  # noqa: BLE001
            return None
        target_row = max(0, min(int(row) + delta, total - 1))
        if target_row == int(row):
            return None if delta else caret
        try:
            length = int(editor.GetLineLength(target_row))
        except Exception:  # noqa: BLE001
            length = int(column)
        try:
            position = int(to_position(min(int(column), max(0, length)), target_row))
        except Exception:  # noqa: BLE001
            return None
        # XYToPosition answers -1 for a position it cannot map.
        return None if position < 0 else position

    def _extend_move_vertical_by_text(self, delta: int) -> bool:
        """The fallback: logical lines, from the mirror's table."""
        line_starts = self._extend_line_starts()
        text = self._extend_control().GetValue()
        caret = self._extend_control().GetInsertionPoint()
        current = self._extend_line_index(line_starts, caret)
        target_line = max(0, min(current + delta, len(line_starts) - 1))
        if target_line == current:
            return False
        column = caret - line_starts[current]
        limit = self._extend_line_limit(line_starts, text, target_line)
        self._extend_control().SetInsertionPoint(min(line_starts[target_line] + column, limit))
        return True

    @staticmethod
    def _extend_line_index(line_starts: list[int], position: int) -> int:
        """Which line *position* falls on. Binary search, not a walk."""
        from bisect import bisect_right

        return max(0, bisect_right(line_starts, position) - 1)

    @staticmethod
    def _extend_line_limit(line_starts: list[int], text: str, index: int) -> int:
        if index + 1 < len(line_starts):
            return line_starts[index + 1] - 1
        return len(text)

    # ------------------------------------------------------------------ #
    # The key
    # ------------------------------------------------------------------ #

    def _extend_control(self) -> Any:
        """The wx text control to move the caret in.

        The two hosts disagree about what ``editor`` means, and the disagreement
        is old and not worth unpicking: in ``MainFrame`` it *is* the text
        control, and in QUILL Lite's document window it is the rich surface
        wrapper while ``control`` is the text control. A mixin shared by both has
        to ask rather than assume -- assuming cost an ``AttributeError`` on the
        first keystroke in QUILL Lite, which is the cheapest possible version of
        this bug and the reason the accessor exists.
        """
        control = getattr(self, "control", None)
        return self.editor if control is None else control

    def _extend_wx(self) -> Any:
        """The ``wx`` module. ``MainFrame`` holds one on ``self._wx``; honour it.

        That attribute exists so ``main_frame`` can be imported in an
        environment without wx, and reaching past it to a module-level import
        here would quietly undo that for every host.
        """
        held = getattr(self, "_wx", None)
        if held is not None:
            return held
        import wx

        return wx

    def _move_extend_selection_caret(self, event: Any) -> bool:
        """Move the caret for one navigation key. ``True`` when it moved.

        Returning ``False`` means "this was not a movement key", and the caller
        lets the control have it -- which is how a letter typed in extend mode
        commits the span and replaces it, as a selection should.
        """
        wx = self._extend_wx()
        text = self._extend_control().GetValue()
        caret = self._extend_control().GetInsertionPoint()
        key_code = event.GetKeyCode()
        line_starts = self._extend_line_starts()

        def line_of(position: int) -> int:
            return self._extend_line_index(line_starts, position)

        # macOS text semantics (#7/#8): Option is the word modifier and Cmd is
        # the line/document bound. Windows uses Ctrl for both.
        is_darwin = sys.platform == "darwin"
        word_mod = event.AltDown() if is_darwin else event.ControlDown()
        cmd_down = event.ControlDown()

        if cmd_down and key_code == wx.WXK_HOME:
            target = 0
        elif cmd_down and key_code == wx.WXK_END:
            target = len(text)
        elif word_mod and key_code == wx.WXK_LEFT:
            target = word_boundary(text, caret, reverse=True)
        elif word_mod and key_code == wx.WXK_RIGHT:
            target = word_boundary(text, caret, reverse=False)
        elif is_darwin and cmd_down and key_code == wx.WXK_LEFT:
            target = line_starts[line_of(caret)]
        elif is_darwin and cmd_down and key_code == wx.WXK_RIGHT:
            target = self._extend_line_limit(line_starts, text, line_of(caret))
        elif key_code == wx.WXK_LEFT:
            target = max(0, caret - 1)
        elif key_code == wx.WXK_RIGHT:
            target = min(len(text), caret + 1)
        elif key_code == wx.WXK_UP:
            return self._extend_move_vertical(-1)
        elif key_code == wx.WXK_DOWN:
            return self._extend_move_vertical(1)
        elif key_code == wx.WXK_HOME:
            target = line_starts[line_of(caret)]
        elif key_code == wx.WXK_END:
            target = self._extend_line_limit(line_starts, text, line_of(caret))
        elif key_code == wx.WXK_PAGEUP:
            return self._extend_move_vertical(-self._extend_lines_per_page())
        elif key_code == wx.WXK_PAGEDOWN:
            return self._extend_move_vertical(self._extend_lines_per_page())
        else:
            return False
        if target == caret:
            return False
        self._extend_control().SetInsertionPoint(target)
        return True
