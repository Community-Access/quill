"""TypingAssistMixin -- Enter in a list, and AutoCorrect for misspellings, in QUILL.

Two typing assists that change text you did not type, both run through shared,
wx-free rules so QUILL Lite does exactly the same thing:

* **Enter in a list** (:mod:`quill.core.list_continuation`). Moved here from
  ``main_frame.py`` (GATE-11) when it gained the plain-text preference and
  renumbering. Markdown always; plain text only with Settings, Editing,
  *Continue lists in plain text* (off by default) and never in a code or
  configuration file; rich text never, because its lists are paragraph
  properties the control draws itself.
* **AutoCorrect** (:mod:`quill.core.autocorrect`). With Settings, Editing,
  *Correct common misspellings as I type* on, a space or Enter after a
  misspelling replaces it -- ``teh`` becomes ``the`` -- as one undo step, with
  the word-corrected sound and the new word spoken (the reader echoes the
  space, never the correction). Ctrl+Z straight after puts back what you typed,
  and that word is then left alone in this window for the rest of the session.
  Your own corrections are entries in the abbreviation library; Insert,
  AutoCorrect Entries (Ctrl+Alt+Shift+F12) manages them.

Runs on ``EVT_CHAR_HOOK`` (``_on_editor_char_hook``), before the native control
sees the key: the space is consumed and written *with* the correction in one
``WriteText``, so one Ctrl+Z restores the misspelling exactly; Enter is
corrected first and then allowed through, so list continuation and the
ordinary new line still happen.

Assumes ``self.editor``, ``self.document``, ``self.settings``, ``self.frame``,
``self._announce``, ``self._set_status``, ``self._show_modal_dialog``,
``self._effective_markup_kind``, ``self._current_editor_mode``,
``self._replace_document_text`` and ``self._abbreviation_library`` from
MainFrame and its other mixins.
"""

from __future__ import annotations

from typing import Any

AUTOCORRECT_ENTRIES_COMMAND = "format.autocorrect_entries"


class TypingAssistMixin:
    # -- Enter in a list ----------------------------------------------------- #

    def _handle_markdown_list_return(self) -> bool:
        from quill.core.list_continuation import (
            continuation_message,
            continue_markdown_list,
            list_continuation_allowed,
        )

        allowed = list_continuation_allowed(
            self._effective_markup_kind(),
            getattr(self.document, "path", None),
            rich=self._current_editor_mode().startswith("rich"),
            plain_text_enabled=bool(getattr(self.settings, "continue_lists_in_plain_text", False)),
        )
        if not allowed:
            return False
        start, end = self.editor.GetSelection()
        if start != end:
            return False
        continuation = continue_markdown_list(
            self.editor.GetValue(), self.editor.GetInsertionPoint()
        )
        if continuation is None:
            return False
        # One write of the changed span, so one Ctrl+Z takes back the new line,
        # its marker and any renumbering together.
        self._replace_document_text(continuation.text)
        self.document.set_text(continuation.text)
        self.editor.SetInsertionPoint(continuation.caret)
        self.editor.SetSelection(continuation.caret, continuation.caret)
        self._set_status(continuation_message(continuation))
        return True

    # -- AutoCorrect ---------------------------------------------------------- #

    def _autocorrect_on(self) -> bool:
        from quill.core.autocorrect import autocorrect_allows

        if not bool(getattr(self.settings, "autocorrect_misspellings", False)):
            return False
        return autocorrect_allows(
            self._effective_markup_kind(), getattr(self.document, "path", None)
        )

    def _maybe_autocorrect_char(self, event: Any) -> bool:
        """Correct the word a space or Enter just ended. ``True`` when the key was consumed.

        Only a space is consumed (it goes in with the correction, one undo
        step). Enter is never consumed: the word is corrected and the key goes
        on to list continuation or the control's own new line.
        """
        if event.ControlDown() or event.AltDown():
            return False
        key = event.GetKeyCode()
        typed = " " if key == 32 else ("\n" if key in (13, 370) else "")
        if not typed or not self._autocorrect_on():
            return False
        popup = getattr(self, "_intellisense_popup", None)
        if typed == "\n" and popup is not None and popup.is_visible():
            return False  # Enter accepts the word prediction; leave the word to it
        editor = self.editor
        start, end = editor.GetSelection()
        if start != end:
            return False
        match = self._autocorrect_match_at(editor.GetInsertionPoint())
        if match is None:
            return False
        caret = editor.GetInsertionPoint()
        between = editor.GetRange(match.end, caret)
        written = match.replacement + between + (" " if typed == " " else "")
        from quill.ui.atomic_edit import replace_as_one_undo

        self._abbreviation_expansion_guard = True
        try:
            replace_as_one_undo(editor, match.start, caret, written)
        finally:
            self._abbreviation_expansion_guard = False
        if typed == "\n":
            editor.SetInsertionPoint(match.start + len(match.replacement) + len(between))
        self.document.set_text(editor.GetValue())
        record = getattr(self, "record_edit", None)
        if callable(record):
            record("AutoCorrect", match.original, match.replacement, position=match.start)
        self._autocorrect_last = match
        self.cue_typing_assist("autocorrect")
        self._announce(f"Corrected to {match.replacement}")
        return typed == " "

    def _autocorrect_match_at(self, caret: int) -> Any:
        """The correction for the word before *caret*, honouring an undone one."""
        from quill.core.autocorrect import WINDOW, find_correction, note_declined

        offset = max(0, caret - WINDOW)
        before = self.editor.GetRange(offset, caret)
        declined = getattr(self, "_autocorrect_declined", None)
        if declined is None:
            declined = set()
            self._autocorrect_declined = declined
        last = getattr(self, "_autocorrect_last", None)
        self._autocorrect_last = None
        if note_declined(last, before, offset, declined):
            self._set_status(f"Kept {last.original} as you typed it")
            return None
        return find_correction(
            before,
            offset,
            getattr(self, "_abbreviation_library", None),
            declined=declined,
            suppressed=self._autocorrect_suppressed,
        )

    def _autocorrect_suppressed(self, start: int, end: int) -> bool:
        """Inside a code span, a fenced block, or a web or email address."""
        from quill.core.spellcheck_live import live_alert_suppressed

        return live_alert_suppressed(self.editor.GetValue(), start, end)

    # -- AutoCorrect Entries --------------------------------------------------- #

    def _register_typing_assist_commands(self) -> None:
        self.commands.register(
            AUTOCORRECT_ENTRIES_COMMAND,
            "AutoCorrect Entries...",
            self.open_autocorrect_entries,
            self._binding_for(AUTOCORRECT_ENTRIES_COMMAND),
        )

    def _append_autocorrect_entries_item(self, menu: Any) -> None:
        """Called from the Insert menu, after the abbreviation rows. No access key:
        every letter in the name is already taken in Insert (GATE-14)."""
        import wx

        from quill.core.i18n import _

        self._id_autocorrect_entries = wx.NewIdRef()
        menu.Append(
            self._id_autocorrect_entries,
            self._menu_label(_("AutoCorrect Entries..."), AUTOCORRECT_ENTRIES_COMMAND),
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _event: self.open_autocorrect_entries(),
            id=self._id_autocorrect_entries,
        )

    def open_autocorrect_entries(self) -> None:
        """Ctrl+Alt+Shift+F12: the corrections, built-in and yours, in one list."""
        from quill.core.abbreviations import save_abbreviation_library
        from quill.ui.autocorrect_entries_dialog import TITLE, AutocorrectEntriesDialog

        library = self._abbreviation_library
        dialog = AutocorrectEntriesDialog(self.frame, library, announce=self._announce)
        try:
            self._show_modal_dialog(dialog.dialog, TITLE)
        finally:
            dialog.close()
        if not dialog.changed:
            return
        try:
            save_abbreviation_library(library)
        except Exception:  # noqa: BLE001 - say so rather than lose the window
            self._announce("AutoCorrect entries could not be saved")
            return
        self._set_status("AutoCorrect entries saved")
