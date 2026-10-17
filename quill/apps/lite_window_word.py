"""Word documents in QUILL Lite: opened as rich text, saved as Word.

QUILL Lite opened a ``.docx`` as read-only text from 2026-10-16: readable,
never written back. From 2026-10-17 it edits one, and the rule that QUILL Lite
may never be ahead of QUILL decided how. Every decision is QUILL's own, moved
out of ``quill.ui.main_frame_rich_mode`` into :mod:`quill.core.docx_open` in the
same change, so the two editors open, ask, back up and save a Word document in
one way:

1. **Open.** The file is read on the worker into RTF for the rich control, and
   scanned for what a rich edit cannot carry (tables, images, comments, tracked
   changes, headers, footers, footnotes, extra sections). A clean file opens
   as rich text with no question.
2. **Ask, when the scan found something.** The same three answers QUILL gives,
   in the same words: open for reading and plain editing (the default, and the
   one Escape gives, because it cannot hurt the file), edit as rich text with
   the losses named, or edit a copy beside the original.
3. **Back up once.** Before the first save over a flagged original, the
   original is copied beside itself as ``name.backup-YYYYMMDD-HHMMSS.docx``.
4. **Save** through QUILL's writer, with the theme's colour taken off the
   document for the moment the RTF is read -- the same guard every rich save in
   QUILL Lite has, so dark mode never sends grey text to somebody else.

**A save is slow for a long document**, and Ctrl+S runs it on the worker so
the window keeps answering. Pressing Save again while it runs says "Still
saving" instead of starting a second write over the first; so does closing the
window, which waits for the save rather than racing it.

What lives here is only QUILL Lite's side: the dialog, the sentences on its
own window, and the save on its own task manager.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

from quill.core import docx_open
from quill.core.lite.filetypes import is_rich_path
from quill.core.lite.open_prepare import PLAIN, RICH, PreparedDocument
from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["DocumentWordMixin", "open_mode_for"]

#: Said once a Word document is in the window as rich text. QUILL's sentence.
OPENED_AS_RICH = docx_open.OPENED_RICH_SENTENCE


def open_mode_for(window: Any, path: Path) -> str:
    """The mode *path* opens in: rich for ``.rtf``, and for ``.docx`` when it can be.

    A ``.docx`` needs the rich control and python-docx; without either it opens
    as text, read-only, exactly as it did before Word editing arrived.
    """
    if is_rich_path(path.name):
        return RICH
    if not docx_open.is_rich_word_path(path):
        return PLAIN
    editor = getattr(window, "editor", None)
    try:
        rich = editor is not None and bool(editor.rtf_available())
    except Exception:  # noqa: BLE001 - a capability probe must never raise
        rich = False
    return RICH if rich and docx_open.word_rich_available() else PLAIN


class DocumentWordMixin:
    """Open, ask, back up and save a Word document. On ``DocumentFrame``."""

    #: The open Word document has features a save drops: back it up first.
    word_flagged: bool = False
    #: The one-time backup has been made (or tried) this session.
    word_backup_done: bool = False
    #: The name a background Word save is writing; empty when none is.
    _word_save_busy: str = ""
    #: Said once after opening a copy (the third answer), then cleared.
    _word_copy_note: str = ""

    # -- open ---------------------------------------------------------------- #

    def settle_word_open(
        self, path: Path, prepared: PreparedDocument
    ) -> tuple[Path, PreparedDocument]:
        """Ask the fidelity question if there is one, and answer with what to commit."""
        if not prepared.word:
            return path, prepared
        choice = docx_open.CHOICE_RICH
        if prepared.word_findings:
            choice = self._ask_word_fidelity(path, prepared.word_findings)
        if choice == docx_open.CHOICE_TEXT:
            return path, self._as_text(prepared)
        if choice == docx_open.CHOICE_COPY:
            copied = docx_open.backup_original(path)
            if copied is None:
                self._announce(f"Could not make a copy of {path.name}; opened it as text instead")
                return path, self._as_text(prepared)
            # Said with the opened sentence: the title changes, and nothing else
            # tells a listener that the window is not holding the file they chose.
            self._word_copy_note = f"Editing a copy, {copied.name}. The original is untouched."
            return copied, prepared
        return path, prepared

    @staticmethod
    def _as_text(prepared: PreparedDocument) -> PreparedDocument:
        """The text answer: what the read-only text open has always shown."""
        return replace(prepared, mode=PLAIN, rtf=b"", word=False, word_findings=())

    def _ask_word_fidelity(self, path: Path, findings: tuple[str, ...]) -> str:
        """QUILL's three-way question, on this window. Cancel is the safe answer."""
        dialog = wx.SingleChoiceDialog(
            self,
            docx_open.fidelity_question(path.name, findings, app="QUILL Lite"),
            docx_open.FIDELITY_DIALOG_TITLE,
            docx_open.fidelity_choices(findings),
        )
        dialog.SetHelpText(
            "Choose how this Word document opens. Reading and plain editing never "
            "changes the file; Save then offers Save As. Edit as Rich Text keeps "
            "headings, lists, bold, italic and links, drops what the list names, "
            "and backs the original up before the first save. Edit a copy opens a "
            "dated copy beside the original, which stays untouched."
        )
        try:
            dialog.SetSelection(0)
            if show_modal_dialog(dialog, docx_open.FIDELITY_DIALOG_TITLE) != wx.ID_OK:
                return docx_open.CHOICE_TEXT
            selection = int(dialog.GetSelection())
        finally:
            dialog.Destroy()
        return docx_open.choice_for_selection(selection)

    def note_word_source(self, path: Path, prepared: PreparedDocument) -> None:
        """After every commit: remember whether this is a Word document, and say so."""
        self.word_flagged = bool(prepared.word and prepared.word_findings)
        self.word_backup_done = False
        copy_note, self._word_copy_note = self._word_copy_note, ""
        if prepared.word_note:
            self._announce(prepared.word_note)
        elif prepared.word and prepared.mode == RICH:
            self._announce(f"{OPENED_AS_RICH} {copy_note}".strip())

    # -- save ---------------------------------------------------------------- #

    def saves_as_word(self, target: Path | str | None) -> bool:
        """Whether a save to *target* writes a Word document: a rich window and a ``.docx``."""
        if target is None or not docx_open.is_rich_word_path(target):
            return False
        return getattr(self.editor, "mode", PLAIN) == RICH

    def save_type_row(self, rich: bool) -> int | None:
        """The Save As type row to open on, or ``None`` to leave the list's first row.

        Word for a Word document; the language's row for plain text; nothing for
        other rich text, whose list already leads with Rich Text.
        """
        from quill.core.lite.filetypes import SAVE_FILTER_WORD, save_filter_index_for_language

        if rich:
            return SAVE_FILTER_WORD if self.saves_as_word(self.path) else None
        return save_filter_index_for_language(self.document_language())

    def refuse_while_word_saving(self) -> bool:
        """Save pressed again during a Word save: say so, start nothing. ``True`` when refused."""
        if not self._word_save_busy:
            return False
        self._announce(f"Still saving {self._word_save_busy}")
        return True

    def _word_rtf(self) -> str:
        """The rich control's RTF with the theme's colour off it, put back after."""
        self._set_whole_document_colour(None)
        try:
            return bytes(self.editor.get_rtf()).decode("latin-1")
        finally:
            self._apply_rich_theme_colour()

    def _back_up_before_word_save(self, destination: Path) -> None:
        """The one-time backup of a flagged original, before it is overwritten."""
        if not docx_open.needs_backup(
            flagged=self.word_flagged, backup_done=self.word_backup_done, target=destination
        ):
            return
        self.word_backup_done = True
        backup = docx_open.backup_original(destination)
        if backup is not None:
            self._announce(f"Backed up the original to {backup.name}")

    def _write_word(self, destination: Path) -> None:
        """Save now, on this thread: the close prompt and the quiet save need the answer."""
        rtf = self._word_rtf()
        self._back_up_before_word_save(destination)
        docx_open.write_docx_from_rtf(destination, rtf)
        self._after_word_write(destination)

    def _after_word_write(self, destination: Path) -> None:
        """A save to another name is a new file: nothing there to back up next time."""
        if self.path is None or Path(self.path) != destination:
            self.word_flagged = False

    def begin_word_save(self, destination: Path) -> bool:
        """Ctrl+S on a Word document: read the RTF here, write the file on the worker."""
        from quill.apps.lite_window_open import app_task_manager
        from quill.stability.task_manager import UiLifetimeToken

        try:
            rtf = self._word_rtf()
        except Exception as exc:  # noqa: BLE001 - reported as any failed save is
            self._report_failure("Save failed", f"Could not save {destination.name}.\n\n{exc}")
            return False
        self._back_up_before_word_save(destination)
        self._word_save_busy = destination.name
        baseline = self.control.GetValue()
        self._set_status_message(f"Saving {destination.name}")
        # Closing the window drops the result (cancel_background_load), never
        # the write: the file is replaced atomically or not at all.
        self._word_save_lifetime = UiLifetimeToken()
        app_task_manager(self.app).submit(
            "lite-word-save",
            lambda **_kwargs: docx_open.write_docx_from_rtf(destination, rtf),
            on_success=lambda _op, _result: self._finish_word_save(destination, baseline),
            on_failure=lambda _op, exc: self._fail_word_save(destination, exc),
            safe_to_cancel=False,
            ui_lifetime=self._word_save_lifetime,
        )
        return True

    def _finish_word_save(self, destination: Path, baseline: str) -> None:
        self._word_save_busy = ""
        self._set_status_message("")
        self._after_word_write(destination)
        typed_since = self.control.GetValue() != baseline
        self._settle_saved(destination)
        if typed_since:
            # The file holds what the window held when Save was pressed; what was
            # typed during the save is not in it, so the window is not clean.
            self._set_modified(True)
            self._update_title()
        if self.app.feature_enabled("backups"):
            from quill.core.lite.backups import write_backup

            write_backup(destination, baseline)
        self._cue_saved()
        self._announce(f"Saved {destination.name}")

    def _fail_word_save(self, destination: Path, exc: BaseException) -> None:
        self._word_save_busy = ""
        self._set_status_message("")
        self._report_failure("Save failed", f"Could not save {destination.name}.\n\n{exc}")

    def _cue_saved(self) -> None:
        from quill.core.sound_events import SoundEvent

        self._cue(SoundEvent.DOCUMENT_SAVED)
