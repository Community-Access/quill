"""File > Import / Convert Document: QUILL's converter, on QUILL Lite's File menu.

QUILL has had this command since 2026-07; QUILL Lite gained it on 2026-10-17,
and nothing here is a second implementation of it. The reading is QUILL's
(:mod:`quill.io.docconvert`: QUILL's own Word, Excel, PowerPoint, OpenDocument,
HTML, EPUB and CSV readers, the PDF's own text through QUILL's PDF reader, and
OCR on this computer), and every sentence is QUILL's
(:mod:`quill.core.import_convert`). What lives here is only where the text
goes on QUILL Lite's window, and three things QUILL Lite does differently
because it is QUILL Lite:

* **It never downloads anything.** QUILL offers to install Tesseract when
  neither engine is present and, with a configured key, cloud OCR; QUILL Lite
  does neither. OCR is Tesseract when it is already installed, Windows OCR
  otherwise (:func:`quill.io.docconvert_windows.convert_with_on_device_ocr`),
  and a sentence saying so when there is no engine at all.
* **The result opens in a window, not a tab.** This window when it is blank,
  a new one otherwise -- the rule Open and Open from URL already follow -- as
  an untitled document named ``"report (converted)"``, marked changed, because
  the text exists nowhere else until it is saved.
* **The work is the app's, not the box's.** Reading runs on the app's task
  manager, so the window stays usable; the status bar's message cell says
  what is happening; closing the window that asked is Cancel.

Spoken: one sentence when it starts, one when the text arrives (who read it,
how many pages, that nothing was uploaded, and any warning such as "Only the
first 200 of 340 pages were read"), and a box when it fails -- a failure cost
the person the thing they asked for, so it is never only a status message.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.import_convert import (
    CANCELLED_SENTENCE,
    IMPORT_TITLE,
    converted_name,
    failed_sentence,
    import_wildcard,
    opened_sentence,
    scanned_import_question,
)
from quill.ui.dialog_contract import show_message_box

__all__ = ["DocumentImportMixin"]


class DocumentImportMixin:
    """``cmd_import_convert`` and its two endings. On ``DocumentFrame``."""

    def cmd_import_convert(self) -> None:
        """Choose a document or a picture of a page, and open it as new text."""
        with wx.FileDialog(
            self,
            IMPORT_TITLE,
            defaultDir=str(self.path.parent) if self.path else self._default_document_folder(),
            wildcard=import_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            source = Path(dialog.GetPath())
        self._start_import(source)

    # -- the background work ------------------------------------------------ #

    def _start_import(self, source: Path, *, ocr: bool = False) -> None:
        """Read *source* off the UI thread: its own text, or (``ocr``) its pictures."""
        from quill.apps.lite_window_open import app_task_manager
        from quill.stability.task_manager import UiLifetimeToken

        previous = getattr(self, "_import_lifetime", None)
        if previous is not None:
            previous.invalidate()  # one conversion per window; the newer wins
        lifetime = UiLifetimeToken()
        self._import_lifetime = lifetime
        language = self._import_language()
        message = (
            f"Reading {source.name} with OCR on this computer"
            if ocr
            else f"Converting {source.name}"
        )
        self._announce(message)

        def work(progress_callback: Any = None, **_kwargs: object) -> Any:
            def said(_fraction: float, text: str) -> None:
                if progress_callback is not None:
                    progress_callback(text)

            if not ocr:
                from quill.io.docconvert import convert_document

                return convert_document(source, language=language, on_progress=said)
            from quill.io.docconvert_windows import convert_with_on_device_ocr

            return convert_with_on_device_ocr(
                source,
                language=language,
                on_progress=said,
                # Closing the window is Cancel: stop between pages, not after.
                cancel_requested=lambda: not lifetime.is_alive,
            )

        app_task_manager(self.app).submit(
            "lite-import-ocr" if ocr else "lite-import",
            work,
            on_success=lambda _op, outcome: self._import_finished(lifetime, source, outcome),
            on_failure=lambda _op, exc: self._import_failed(lifetime, source, exc),
            on_progress=lambda _op, text: self._import_progress(lifetime, str(text)),
            ui_lifetime=lifetime,
        )

    def _import_progress(self, lifetime: Any, text: str) -> None:
        """A step of the reading ("Recognizing page 3 of 12"): the message cell only."""
        if lifetime.is_alive:
            self._set_status_message(text)

    # -- the two endings ---------------------------------------------------- #

    def _import_finished(self, lifetime: Any, source: Path, outcome: Any) -> None:
        if not lifetime.is_alive:
            return
        if getattr(outcome, "offer_local_ocr", False):
            answer = show_message_box(
                scanned_import_question(source.name, app_name=self._import_app_name()),
                IMPORT_TITLE,
                wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if answer == wx.YES:
                self._start_import(source, ocr=True)
                return
            if answer != wx.NO:
                self._set_status_message(CANCELLED_SENTENCE)
                return
        self._open_converted(source, outcome)

    def _open_converted(self, source: Path, outcome: Any) -> None:
        """The text in a window: this one when blank, a new one otherwise."""
        from quill.core.lite.open_prepare import PLAIN, PreparedDocument

        target = self if self._is_blank() else self.app.new_window(PLAIN)
        if target is None:
            return
        target._commit_download(
            PreparedDocument(mode=PLAIN, text=str(outcome.text)), converted_name(source.stem)
        )
        warnings = " ".join(str(warning) for warning in getattr(outcome, "warnings", ()))
        target._announce(f"{opened_sentence(source.name, outcome)} {warnings}".strip())

    def _import_failed(self, lifetime: Any, source: Path, exc: BaseException) -> None:
        from quill.io.docconvert import DocConvertCancelled

        if not lifetime.is_alive:
            return
        if isinstance(exc, DocConvertCancelled):
            self._set_status_message(CANCELLED_SENTENCE)
            return
        reason: object = exc
        if "Download Optional Components" in str(exc):
            # The reader's sentence names a QUILL menu QUILL Lite does not have.
            from quill.apps.lite_window_pdf import NO_PDF_READER

            reason = NO_PDF_READER
        self._report_failure(
            IMPORT_TITLE,
            failed_sentence(source.name, reason, app_name=self._import_app_name()),
        )

    # -- small adapters ------------------------------------------------------ #

    def _import_language(self) -> str:
        """Tesseract's language: QUILL's setting when QUILL Lite has one, else English.

        Windows OCR ignores it and reads the languages installed in Windows.
        """
        from quill.io.tesseract_ocr import DEFAULT_LANGUAGE

        value = str(getattr(self.app.settings, "ocr_language", "") or "").strip()
        return value or DEFAULT_LANGUAGE

    def _import_app_name(self) -> str:
        from quill.core.lite import APP_NAME

        return APP_NAME
