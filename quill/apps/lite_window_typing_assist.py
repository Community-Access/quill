"""Enter in a list, and AutoCorrect for misspellings, in a QUILL Lite document.

QUILL had both and QUILL Lite had neither, which is backwards (QUILL Lite may
never be ahead of QUILL, and should not be needlessly behind it either). The
rules are QUILL's, shared and wx-free -- :mod:`quill.core.list_continuation`
and :mod:`quill.core.autocorrect` -- and this mixin is only the delivery:

* **Enter in a list.** In a Markdown document (with the Markdown and HTML area
  on, as everything Markdown-shaped in QUILL Lite is), Enter at the end of
  ``- item`` or ``2. item`` starts the next item, in the middle of one splits
  it, and on an empty one ends the list; a new numbered item renumbers the
  ones below it. In plain text only when Preferences says *Continue lists in
  plain text* (off by default), and never in a code or settings file. Never in
  rich text, whose lists the control draws itself. One undo step, and the
  outcome is said, because the reader echoes Enter and nothing else.
* **AutoCorrect.** With the Autocorrect area on and Preferences, *Correct
  common misspellings as I type* checked, a space or Enter after ``teh``
  makes it ``the``: one undo step, the word-corrected sound, and the new word
  spoken. Ctrl+Z straight after puts back what you typed, and that word is
  left alone in this window from then on. Your own corrections live in the
  abbreviation library this window already uses; Tools, AutoCorrect Entries
  (Alt+Shift+9) manages them, in the same window QUILL opens.

Inherited by :class:`~quill.apps.lite_window_typing.DocumentTypingMixin`, whose
key handlers call in here, so every window and test stub has it.
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.sound_events import SoundEvent
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentTypingAssistMixin"]

#: The cheap first look: does the line up to the caret start with a list
#: marker? Asked of the line alone, so an ordinary Enter never reads the
#: document (bad.md T1 -- the typing path reads one line, not the buffer).
_LIST_LINE_START = re.compile(r"^[ \t]*(?:[-+*]|\d+[.)])[ \t]")


class DocumentTypingAssistMixin:
    """Typing assists that change text: list continuation and AutoCorrect."""

    # -- Enter in a list ------------------------------------------------------ #

    def _list_continuation_allowed(self) -> bool:
        from quill.core.list_continuation import list_continuation_allowed

        kind = self.document_language()
        if kind == "markdown" and not self.app.feature_enabled("markup"):
            return False
        return list_continuation_allowed(
            kind,
            getattr(self, "path", None),
            rich=self.editor.mode == RICH,
            plain_text_enabled=bool(
                getattr(self.app.settings, "continue_lists_in_plain_text", False)
            ),
        )

    def _handle_list_return(self) -> bool:
        """Enter on a list line: the next marker, a split, or the end of the list.

        ``True`` when the key was handled; ``False`` lets the control type its
        own new line, which is what happens everywhere that is not a list.
        """
        start, end = self.control.GetSelection()
        if start != end or not self._list_continuation_allowed():
            return False
        caret = self.control.GetInsertionPoint()
        _ok, column, _line = self.control.PositionToXY(caret)
        if not _LIST_LINE_START.match(self.control.GetRange(caret - column, caret)):
            return False
        from quill.core.list_continuation import continuation_message, continue_markdown_list
        from quill.core.selection import changed_span

        text = self.control.GetValue()
        result = continue_markdown_list(text, caret)
        if result is None:
            return False
        low, high, replacement = changed_span(text, result.text)
        # The changed span only, as one undo step: Ctrl+Z takes back the new
        # line, its marker and any renumbering together.
        replace_as_one_undo(self.control, low, high, replacement)
        self.control.SetInsertionPoint(result.caret)
        self._set_modified(True)
        self._touch_status()
        self._announce(continuation_message(result))
        return True

    # -- AutoCorrect ---------------------------------------------------------- #

    def _autocorrect_library(self) -> AbbreviationLibrary | None:
        provider = getattr(self.app, "autocorrect_library", None)
        if callable(provider):
            library = provider()
        else:
            library = getattr(self.app, "abbreviations", None)
        return library if isinstance(library, AbbreviationLibrary) else None

    def _autocorrect_on(self) -> bool:
        from quill.core.autocorrect import autocorrect_allows

        if not self.app.feature_enabled("autoformat"):
            return False
        if not bool(getattr(self.app.settings, "autocorrect_misspellings", False)):
            return False
        return autocorrect_allows(self.document_language(), getattr(self, "path", None))

    def _autocorrect_word(self, typed: str) -> bool:
        """Correct the word a space or Enter (*typed*) is about to end.

        ``True`` when a space was consumed -- it went in with the correction, as
        one undo step. Enter is never consumed: the word is corrected and the
        key goes on to list continuation or the control's own new line.
        """
        if typed not in (" ", "\n") or not self._autocorrect_on():
            return False
        start, end = self.control.GetSelection()
        if start != end:
            return False
        caret = self.control.GetInsertionPoint()
        match = self._autocorrect_match_at(caret)
        if match is None:
            return False
        between = self.control.GetRange(match.end, caret)
        written = match.replacement + between + (" " if typed == " " else "")
        replace_as_one_undo(self.control, match.start, caret, written)
        self._autocorrect_last = match
        self._set_modified(True)
        self._touch_status()
        self._cue(SoundEvent.WORD_CORRECTED)
        self._announce(f"Corrected to {match.replacement}")
        return typed == " "

    def _autocorrect_match_at(self, caret: int) -> Any:
        """The correction for the word before *caret*, honouring an undone one."""
        from quill.core.autocorrect import WINDOW, find_correction, note_declined

        offset = max(0, caret - WINDOW)
        before = self.control.GetRange(offset, caret)
        declined = getattr(self, "_autocorrect_declined", None)
        if declined is None:
            declined = set()
            self._autocorrect_declined = declined
        last = getattr(self, "_autocorrect_last", None)
        self._autocorrect_last = None
        if note_declined(last, before, offset, declined):
            self._set_status_message(f"Kept {last.original} as you typed it")
            return None
        return find_correction(
            before,
            offset,
            self._autocorrect_library(),
            declined=declined,
            suppressed=self._autocorrect_suppressed,
        )

    def _autocorrect_suppressed(self, start: int, end: int) -> bool:
        """Inside a code span, a fenced block, or a web or email address."""
        from quill.core.spellcheck_live import live_alert_suppressed

        return live_alert_suppressed(self.control.GetValue(), start, end)

    def cmd_autocorrect_entries(self) -> None:
        """Alt+Shift+9: QUILL's AutoCorrect Entries window, over this library."""
        from quill.ui.autocorrect_entries_dialog import TITLE, AutocorrectEntriesDialog
        from quill.ui.dialog_contract import show_modal_dialog

        library = self._autocorrect_library()
        if library is None:
            self._announce("AutoCorrect entries are not available right now")
            return
        dialog = AutocorrectEntriesDialog(self, library, announce=self._announce)
        try:
            show_modal_dialog(dialog.dialog, TITLE)
        finally:
            dialog.close()
        if dialog.changed:
            save = getattr(self.app, "save_autocorrect_library", None)
            if callable(save):
                save()
            self._set_status_message("AutoCorrect entries saved")
        self.control.SetFocus()
