"""The F8 anchor-and-complete selection span, and the two verbs beside it.

Split out of ``main_frame.py`` on 2026-09-10 for GATE-11. Four methods that
share one piece of state (``_selection_anchor`` / ``_last_selection``) and one
job: making a selection without holding Shift, which is the only way to select
a large region when arrowing with a modifier held is not available to you.

**Every one of them answers in words, and that is the feature.** Setting an
anchor changes nothing a screen reader announces -- no focus moves, no control
is named, the caret does not go anywhere -- so without the sentence, F8 is a key
that appears to do nothing, and the way you find out whether it worked is by
pressing Shift+F8 and hoping. The line and column in each message is what makes
the pair usable across a page of scrolling.

:meth:`~SelectionSpanMixin.start_selection` asks
:meth:`~quill.ui.main_frame_cues.CueMixin.action_channels` for the two halves
separately rather than calling ``action``, because QUILL's ``_set_status``
*speaks* what it is given -- so "put it on the bar without saying it" is a
decision only this method can make.

QuillLite's equivalent is ``lite_window_selection.py``, and it is a different
implementation on purpose: it has a key-up hook this does not, which is where
its F8 bug lived for a release. These compute the span at completion time and
were never affected.
"""

from __future__ import annotations

from quill.core.marks import line_column_for_position
from quill.core.sound_events import SoundEvent
from quill.ui.sound_manager import post_sound

__all__ = ["SelectionSpanMixin"]


class SelectionSpanMixin:
    """Composed onto ``MainFrame``, which supplies ``editor`` and the status bar."""

    def start_selection(self) -> None:
        self._selection_anchor = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        line, col = line_column_for_position(text, self._selection_anchor)
        message = f"Selection started at line {line}, column {col}."
        # Both halves are asked for separately because the status bar here
        # *speaks* what it is given, so "show it without saying it" is a call
        # only this method can make. See CueMixin.action_channels.
        play, speak = self.action_channels(SoundEvent.SELECTION_STARTED)
        if play:
            post_sound(SoundEvent.SELECTION_STARTED)
        if speak:
            self._set_status(message)
        else:
            self._set_status_quiet(message)

    def cancel_selection_anchor(self) -> bool:
        """Drop a waiting F8 marker. ``True`` when there was one.

        The marker could not be cancelled at all before 2026-09-16. Escape
        cleared *extend mode* and left the anchor sitting there, so once F8 was
        pressed the only ways out were to complete a selection you did not want
        or to press F8 again -- which silently moved the marker somewhere else
        rather than dropping it. The state is invisible, so it was also
        impossible to tell which had happened (bad.md L4).

        Returns whether it did anything, because Escape belongs to everything
        else too: with no marker waiting the key must carry on.
        """
        if getattr(self, "_selection_anchor", None) is None:
            return False
        self._selection_anchor = None
        self._announce_result("Selection marker dropped")
        return True

    def complete_selection(self) -> None:
        if self._selection_anchor is None:
            self._set_status("No selection anchor. Press F8 to set one.")
            return
        caret = self.editor.GetInsertionPoint()
        start = min(self._selection_anchor, caret)
        end = max(self._selection_anchor, caret)
        self.editor.SetSelection(start, end)
        if start != end:
            self._last_selection = (start, end)
            post_sound(SoundEvent.SELECTION_COMPLETED)
        self._selection_anchor = None
        text = self.editor.GetValue()
        s_line, s_col = line_column_for_position(text, start)
        e_line, e_col = line_column_for_position(text, end)
        char_count = end - start
        self._set_status(
            f"Selected {char_count} character{'s' if char_count != 1 else ''},"
            f" line {s_line} column {s_col} to line {e_line} column {e_col}."
        )

    def reselect(self) -> None:
        if self._last_selection is None:
            self._set_status("No previous selection to restore.")
            return
        start, end = self._last_selection
        text_len = len(self.editor.GetValue())
        start = min(start, text_len)
        end = min(end, text_len)
        if start == end:
            self._set_status("Previous selection is no longer valid.")
            return
        self.editor.SetSelection(start, end)
        text = self.editor.GetValue()
        s_line, s_col = line_column_for_position(text, start)
        e_line, e_col = line_column_for_position(text, end)
        char_count = end - start
        self._set_status(
            f"Reselected {char_count} character{'s' if char_count != 1 else ''},"
            f" line {s_line} column {s_col} to line {e_line} column {e_col}."
        )

    def go_to_start_of_selection(self) -> None:
        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("No selection.")
            return
        self.editor.SetInsertionPoint(start)
        text = self.editor.GetValue()
        line, col = line_column_for_position(text, start)
        self._set_status(f"Moved to start of selection: line {line}, column {col}.")
