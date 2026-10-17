"""Opening a PDF in QUILL Lite: as text, never as a PDF to be written.

QUILL Lite opened text files and nothing else until 2026-10-15. Now Ctrl+O
offers PDFs too, and the rule that QUILL Lite may never be ahead of QUILL
decided almost everything about how: the reading is QUILL's
(:mod:`quill.core.pdf_open`, through the same :mod:`quill.io.pdf` reader
QUILL's File > Open uses), the password box is QUILL's
(:mod:`quill.ui.pdf_password`), the OCR is QUILL's (docconvert's on-device
tier), and the sentences are QUILL's. What lives here is only the order the
questions are asked in, on QUILL Lite's window:

1. **Locked** -- ask for the password, then read the file again with it. A
   wrong one asks again and says so; Cancel opens nothing. The password goes
   to the reader for that one read and is not kept anywhere.
2. **Damaged, or no reader** -- say why, in the reader's own sentence, and
   open nothing. OCR cannot help a damaged file and the box says so.
3. **Scanned** (no text, or very little) -- ask whether to read it with OCR
   on this computer. Yes reads the pages in the background (Tesseract if it is
   installed, Windows OCR otherwise) and opens the result with real pages,
   marked changed because the text exists nowhere else. No opens what text
   there is, or nothing.
4. **Text** -- opens, with one sentence: how many pages, whether there is an
   outline, and that saving makes a new file.

Afterwards the window holds the PDF's path, so Recent Documents, the title and
the document's own bookmarks all name the PDF -- and Save, which would write
text into a file named ``.pdf``, goes to Save As instead with a ``.txt``
proposed (:meth:`DocumentPdfMixin.refuse_save_over_source`), exactly as QUILL
refuses (``quill.io.export.EXPORT_ONLY_SUFFIXES``). The PDF itself is never
written to.
"""

from __future__ import annotations

from pathlib import Path

import wx

from quill.core.pdf_open import (
    ENGINE_OCR,
    ENGINE_UNAVAILABLE,
    SCANNED_DIALOG_TITLE,
    PdfOpen,
    ocr_finished_sentence,
    opened_summary,
    password_cancelled_sentence,
    save_refusal,
    scanned_question,
)
from quill.ui.dialog_contract import show_message_box

__all__ = ["DocumentPdfMixin", "is_read_only_source"]

#: The formats QUILL Lite's Save As writes, named as its type list names them.
_LITE_FORMATS = "text, Markdown or rich text"


def is_read_only_source(path: Path | str | None) -> bool:
    """True for a file QUILL Lite opened as extracted text and must not write back.

    The list is QUILL's own (``EXPORT_ONLY_SUFFIXES``), so the two editors
    refuse the same files. QUILL Lite opens only one of them today: ``.pdf``.
    """
    if path is None:
        return False
    from quill.io.export import EXPORT_ONLY_SUFFIXES

    return Path(path).suffix.lower() in EXPORT_ONLY_SUFFIXES


class DocumentPdfMixin:
    """The PDF half of opening a file, and Save's refusal. On ``DocumentFrame``."""

    #: The open PDF's outline as ``(title, page)`` pairs; empty for anything else.
    pdf_outline: tuple[tuple[str, int], ...] = ()
    #: Each outline entry's nesting level, for Go To's wording only.
    pdf_outline_levels: tuple[int, ...] = ()

    # -- before the commit -------------------------------------------------- #

    def pdf_ready_to_commit(self, path: Path, found: PdfOpen) -> bool:
        """Whether this read can be put in the window as it is.

        ``False`` means something else happens instead -- a password retry, OCR,
        or a sentence saying why nothing opened -- and the commit must stop.
        """
        if found.needs_password:
            self._retry_pdf_with_password(path, found)
            return False
        if found.refused:
            reason = found.text.strip().strip("()").strip()
            if found.engine == ENGINE_UNAVAILABLE:
                # The reader's own sentence names QUILL's Download Optional
                # Components, which QUILL Lite does not have.
                reason = (
                    "This copy of QUILL Lite has no PDF reader, so it cannot open PDFs. "
                    "The installed QUILL Lite has one."
                )
            self._report_failure("Open failed", f"Could not open {path.name}.\n\n{reason}")
            return False
        if found.looks_scanned:
            return self._offer_pdf_ocr(path, found)
        return True

    def _retry_pdf_with_password(self, path: Path, found: PdfOpen) -> None:
        from quill.ui.pdf_password import ask_pdf_password

        password = ask_pdf_password(self, path.name, incorrect=found.password_rejected)
        if password is None:
            self._announce(password_cancelled_sentence(path.name))
            return
        # After this commit has unwound, so the retry's "Opening" title is the
        # last one written. The password travels in this call and nowhere else.
        wx.CallAfter(self.begin_background_load, path, password=password)

    def _offer_pdf_ocr(self, path: Path, found: PdfOpen) -> bool:
        """The scanned question. ``True`` opens the text layer as it is."""
        answer = show_message_box(
            scanned_question(path.name, found.page_count, some_text=found.has_text),
            SCANNED_DIALOG_TITLE,
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        if answer == wx.YES:
            wx.CallAfter(self.begin_background_load, path, ocr_of=found)
            return False
        if found.has_text:
            return True
        self._announce(f"Nothing opened. {path.name} has no text to show.")
        return False

    # -- after the commit --------------------------------------------------- #

    def note_pdf_source(self, found: PdfOpen | None) -> None:
        """Remember the outline, and say what opened. Every commit calls this.

        A non-PDF commit clears the outline, so a window that held a PDF and
        then opened a text file does not keep offering the PDF's chapters.
        """
        self.pdf_outline = tuple(found.outline) if found is not None else ()
        self.pdf_outline_levels = tuple(found.outline_levels) if found is not None else ()
        if found is None:
            return
        if found.engine == ENGINE_OCR:
            # The recognized text exists nowhere else: closing must ask.
            self._set_modified(True)
            self._announce(ocr_finished_sentence(found))
            return
        self._announce(opened_summary(found))

    # -- Save --------------------------------------------------------------- #

    def refuse_save_over_source(self) -> bool:
        """Save on a PDF: say why, then Save As. ``True`` when Save was refused.

        The buffer is text read out of the PDF; writing it back would put text
        into a file every other program expects to be a PDF. QUILL refuses the
        same way, with the same sentence.
        """
        path = getattr(self, "path", None)
        if not is_read_only_source(path):
            return False
        assert path is not None
        name, suffix = Path(path).name, Path(path).suffix
        show_message_box(
            save_refusal(name, suffix, app_name=self._app_name(), formats=_LITE_FORMATS) + ".",
            "Save",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        return True

    def refuse_save_as_target(self, target: Path) -> bool:
        """A Save As name ending ``.pdf``: refuse it rather than write text there."""
        if not is_read_only_source(target):
            return False
        show_message_box(
            f"{self._app_name()} cannot save to {target.suffix}. Choose text, Markdown "
            "or rich text in the Save as type list.",
            "Format not supported",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        return True

    def _app_name(self) -> str:
        from quill.core.lite import APP_NAME

        return APP_NAME
