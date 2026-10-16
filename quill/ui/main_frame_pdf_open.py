"""A scanned PDF opened with File > Open: offer OCR on this computer.

QUILL has offered OCR for scanned files from Import / Convert Document for a
long time, but File > Open on a scanned PDF opened a note saying "use File >
Import and choose OCR" -- the answer was one menu away and the person had to
go and find it. QUILL Lite gained PDFs on 2026-10-15 with the question asked
right there, at the open, and QUILL Lite may never be ahead of QUILL, so QUILL
asks the same question in the same words (:mod:`quill.core.pdf_open`).

Yes reads the pages with whichever on-device engine this computer has --
Tesseract when it is installed, Windows OCR otherwise -- on the task manager,
with the page count on the status bar, and puts the result in the PDF's own
tab with real page breaks. The tab is marked changed, because the text exists
nowhere else, and Save still goes to Save As: the PDF is never written to.
Nothing is uploaded at any point.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.pdf_open import (
    SCANNED_DIALOG_TITLE,
    PdfOpen,
    ocr_finished_sentence,
    ocr_pdf_for_open,
    ocr_started_sentence,
    scanned_question,
)

__all__ = ["PdfOpenOcrMixin"]


class PdfOpenOcrMixin:
    """The scanned-PDF question on open, and what Yes does. On ``MainFrame``."""

    def _offer_ocr_for_scanned_pdf(self, loaded: Any, path: Path, suffix: str) -> None:
        """After a PDF opens, ask about OCR if it looks scanned. Never blocks the open."""
        if suffix != ".pdf":
            return
        metadata = getattr(loaded, "source_metadata", None)
        if not isinstance(metadata, dict):
            return
        found = PdfOpen(
            text=str(getattr(loaded, "text", "") or ""),
            engine=str(metadata.get("engine", "")),
            page_count=int(metadata.get("page_count", 0) or 0),
            outline=tuple(tuple(entry) for entry in metadata.get("pdf_outline") or ()),
        )
        if not found.looks_scanned:
            return
        # After the open settles, so the question is not asked over a tab that
        # has not finished arriving.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self._ask_ocr_for_scanned_pdf, path, found)
        else:
            self._ask_ocr_for_scanned_pdf(path, found)

    def _ask_ocr_for_scanned_pdf(self, path: Path, found: PdfOpen) -> None:
        wx = self._wx
        answer = self._show_message_box(
            scanned_question(path.name, found.page_count, some_text=found.has_text),
            SCANNED_DIALOG_TITLE,
            wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
        )
        if answer != wx.YES:
            return
        from quill.io.docconvert import _Deps
        from quill.io.tesseract_ocr import tesseract_available

        override = self._docconvert_tesseract_override()
        deps = _Deps(tesseract_ready=lambda: tesseract_available(override))
        language = self._docconvert_language()
        started = ocr_started_sentence(found.page_count)
        self._announce(started)
        self._set_status(started)

        def _run(progress_callback, cancellation_token, **_kw):
            return ocr_pdf_for_open(
                path,
                found,
                language=language,
                deps=deps,
                on_progress=lambda _fraction, message: progress_callback(message),
                cancel_requested=cancellation_token.is_cancelled,
            )

        self._task_manager.submit(
            name="pdf-open-ocr",
            func=_run,
            on_success=lambda _op, result: self._scanned_pdf_read(path, result),
            on_failure=lambda _op, error: self._scanned_pdf_failed(path, error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )

    def _scanned_pdf_read(self, path: Path, result: PdfOpen) -> None:
        """Put the OCR text in the PDF's tab, or a new tab if the old one was edited."""
        from quill.core.document import Document

        index = self._find_tab_index(path)
        tab = self._document_tabs[index] if index >= 0 else None
        if tab is None or getattr(tab.document, "modified", False):
            # Closed, or typed into while the pages were read: never overwrite
            # somebody's own words with a recognizer's.
            index = self._create_document_tab(
                Document(text=result.text, path=None, modified=True), select=True
            )
            self._set_tab_page_text(index, f"{path.stem} (OCR)")
        else:
            tab.document.text = result.text
            tab.document.modified = True
            tab.editor.ChangeValue(result.text)
        self._refresh_title()
        self._announce(ocr_finished_sentence(result))

    def _scanned_pdf_failed(self, path: Path, error: BaseException) -> None:
        from quill.io.docconvert import DocConvertCancelled

        if isinstance(error, DocConvertCancelled):
            self._set_status("OCR cancelled. The PDF opened as it was.")
            return
        self._set_status("OCR could not run")
        self._show_message_box(
            f"QUILL could not read the pages of {path.name}.\n\n{error}",
            SCANNED_DIALOG_TITLE,
            self._wx.ICON_ERROR | self._wx.OK,
        )

    # -- Import / Convert Document, when Tesseract is not installed ---------- #

    def _docconvert_run_windows_ocr(self, source: Path) -> None:
        """Tier 2 with Windows OCR: the engine every Windows machine has."""
        from quill.io.docconvert_windows import convert_with_windows_ocr

        self._set_status(f"Reading {source.name} with Windows OCR on this computer...")

        def _run(progress_callback, cancellation_token, **_kw):
            return convert_with_windows_ocr(
                source,
                on_progress=lambda fraction, message: progress_callback(message),
                cancel_requested=cancellation_token.is_cancelled,
            )

        self._task_manager.submit(
            name="docconvert-windows-ocr",
            func=_run,
            on_success=lambda _op, outcome: self._docconvert_open(source, outcome),
            on_failure=lambda _op, error: self._docconvert_failed(source, error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )
