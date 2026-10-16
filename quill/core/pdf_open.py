"""Opening a PDF as text: the one way both editors do it.

QUILL has opened PDFs through :mod:`quill.io.pdf` for a long time -- pdfplumber
then pypdf, repaired text, form feeds between pages, the outline, a password
that is used once and never kept. QUILL Lite gained PDFs on 2026-10-15, and the
rule that it may never be ahead of QUILL has a twin that is easier to break
quietly: it may not grow a *second* implementation either. So the decisions
live here, wx-free, and both editors call them:

* **What the reader found** -- :func:`read_pdf_for_open` returns a
  :class:`PdfOpen`: the text, the page count, the outline, and which of the
  reader's outcomes this was (text, locked, damaged, no reader, no text layer).
  QUILL's ``quill.io.structured`` and QUILL Lite's open path both read through
  it, so a PDF cannot open with pages in one editor and without them in the
  other.
* **Whether it looks scanned** -- :attr:`PdfOpen.looks_scanned`, the reader's
  own "no text" outcome or docconvert's chars-per-page heuristic, which is the
  moment both editors offer OCR on this computer.
* **OCR on open** -- :func:`ocr_pdf_for_open` reads the pages with whichever
  on-device engine is here (Tesseract, then Windows OCR) and joins them with
  form feeds, so a scanned PDF has real pages afterwards too.
* **Where the outline points** -- :func:`outline_places` (Go To's Outline kind,
  both editors) and :func:`outline_bookmark_offsets` (QUILL's named bookmarks).
  An outline entry names a page; the page is found from the form feeds in the
  text *now*, so an edit above it does not leave the entry pointing at the
  wrong place.
* **The sentences** -- the password prompt, the scanned question, the open
  summary and Save's refusal, so the two editors say the same thing about the
  same file.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.navigation import page_start_for_number, page_starts

__all__ = [
    "ENGINE_DAMAGED",
    "ENGINE_EMPTY",
    "ENGINE_ENCRYPTED",
    "ENGINE_OCR",
    "ENGINE_UNAVAILABLE",
    "PASSWORD_DIALOG_TITLE",
    "SCANNED_DIALOG_TITLE",
    "PdfOpen",
    "is_pdf_path",
    "ocr_finished_sentence",
    "ocr_pdf_for_open",
    "ocr_started_sentence",
    "opened_summary",
    "outline_bookmark_offsets",
    "outline_places",
    "page_places",
    "password_cancelled_sentence",
    "password_prompt",
    "read_pdf_for_open",
    "save_refusal",
    "scanned_question",
    "unique_outline_name",
]

#: The reader's outcomes that are not text (``quill.io.pdf.extract_pdf_text``).
ENGINE_ENCRYPTED = "encrypted"
ENGINE_DAMAGED = "damaged"
ENGINE_UNAVAILABLE = "unavailable"
ENGINE_EMPTY = "empty"
#: Text that came from OCR on this computer rather than from the file.
ENGINE_OCR = "ocr"

#: The password dialog's title, in both editors.
PASSWORD_DIALOG_TITLE = "Open Password-Protected PDF"
#: The scanned question's title, in both editors.
SCANNED_DIALOG_TITLE = "Read with OCR?"

#: Beyond this the Page kind stops being a list and starts being a scroll; a
#: thousand-page PDF's rows differ only by number, so the number is faster.
_MAX_LISTED_PAGES = 200


def is_pdf_path(path: Path | str | None) -> bool:
    """True for a file named ``.pdf``. The name decides, as it does for ``.rtf``."""
    return str(path or "").lower().endswith(".pdf")


@dataclass(frozen=True, slots=True)
class PdfOpen:
    """What opening one PDF found. Never holds the password."""

    text: str
    engine: str
    page_count: int = 0
    extracted_pages: int = 0
    quality_score: int = 0
    page_scores: tuple[int, ...] = ()
    #: ``(title, page)`` pairs, page 1-based, in document order.
    outline: tuple[tuple[str, int], ...] = ()
    #: A password was tried and did not open the file.
    password_rejected: bool = False
    #: Mean OCR confidence 0-100, or -1 when not measured (Windows OCR, or no OCR).
    ocr_confidence: float = -1.0

    @property
    def needs_password(self) -> bool:
        return self.engine == ENGINE_ENCRYPTED

    @property
    def refused(self) -> bool:
        """Nothing can be opened: the file is damaged, or no reader is installed."""
        return self.engine in {ENGINE_DAMAGED, ENGINE_UNAVAILABLE}

    @property
    def looks_scanned(self) -> bool:
        """No text layer, or too little of one: the moment to offer OCR."""
        if self.engine == ENGINE_EMPTY:
            return True
        if self.engine in {ENGINE_ENCRYPTED, ENGINE_DAMAGED, ENGINE_UNAVAILABLE, ENGINE_OCR}:
            return False
        from quill.io.docconvert import text_layer_looks_empty

        return text_layer_looks_empty(self.text, self.page_count)

    @property
    def has_text(self) -> bool:
        """Whether there is any text worth opening (the reader's notes are not)."""
        if self.engine in {ENGINE_EMPTY, ENGINE_ENCRYPTED, ENGINE_DAMAGED, ENGINE_UNAVAILABLE}:
            return False
        return bool(self.text.strip())

    def metadata(self) -> dict[str, object]:
        """The ``source_metadata`` QUILL's document carries for this read."""
        metadata: dict[str, object] = {
            "source_kind": "pdf",
            "engine": self.engine,
            "quality_score": self.quality_score,
            "page_count": self.page_count,
            "extracted_pages": self.extracted_pages,
            "page_scores": list(self.page_scores),
        }
        if self.outline:
            metadata["pdf_outline"] = [tuple(entry) for entry in self.outline]
        return metadata


def read_pdf_for_open(
    path: Path,
    *,
    password: str | None = None,
    extract: Callable[..., Any] | None = None,
    read_outline: Callable[..., list[tuple[str, int]]] | None = None,
) -> PdfOpen:
    """Read *path* with the shared reader; *password* is used for this read only.

    ``extract`` and ``read_outline`` are seams for tests; by default they are
    :func:`quill.io.pdf.extract_pdf_text` and
    :func:`quill.io.pdf.extract_pdf_outline`. The outline is read only when the
    reader saw pages, because a locked or unreadable file has none.
    """
    if extract is None or read_outline is None:
        from quill.io.pdf import extract_pdf_outline, extract_pdf_text

        extract = extract or extract_pdf_text
        read_outline = read_outline or extract_pdf_outline
    result = extract(path, password=password)
    page_count = int(getattr(result, "page_count", 0) or 0)
    outline: tuple[tuple[str, int], ...] = ()
    if page_count > 0:
        outline = tuple(
            (str(title), int(page)) for title, page in read_outline(path, password=password)
        )
    engine = str(getattr(result, "engine", ""))
    # format_pdf_document's own answer for a result in hand: the text, with
    # nothing prepended (#1279).
    return PdfOpen(
        text=str(getattr(result, "text", "")).rstrip() + "\n",
        engine=engine,
        page_count=page_count,
        extracted_pages=int(getattr(result, "extracted_pages", 0) or 0),
        quality_score=int(getattr(result, "quality_score", 0) or 0),
        page_scores=tuple(int(score) for score in getattr(result, "page_scores", []) or []),
        outline=outline,
        password_rejected=engine == ENGINE_ENCRYPTED and bool(password),
    )


def ocr_pdf_for_open(
    path: Path,
    found: PdfOpen,
    *,
    language: str | None = None,
    deps: Any = None,
    on_progress: Callable[[float, str], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> PdfOpen:
    """Read a scanned PDF's pages on this computer and return them as text.

    Tesseract when it is installed, otherwise Windows OCR
    (:func:`quill.io.docconvert_windows.convert_with_on_device_ocr`). Pages are
    joined with form feeds, so Go To Page and the Page cell work on the result
    exactly as on a PDF that had text. Nothing leaves the computer. Raises
    ``DocConvertError`` with a sentence to speak when no engine can run.
    """
    from quill.io.docconvert_windows import convert_with_on_device_ocr

    kwargs: dict[str, Any] = {
        "deps": deps,
        "on_progress": on_progress,
        "cancel_requested": cancel_requested,
    }
    if language:
        kwargs["language"] = language
    outcome = convert_with_on_device_ocr(path, **kwargs)
    pages = list(outcome.pages) or [outcome.text.strip()]
    text = "\f".join(pages).strip()
    return PdfOpen(
        text=text + "\n" if text else "",
        engine=ENGINE_OCR,
        page_count=len(pages),
        extracted_pages=sum(1 for page in pages if page),
        quality_score=found.quality_score,
        outline=found.outline,
        ocr_confidence=float(outcome.mean_confidence),
    )


# -- where things are --------------------------------------------------------- #


def unique_outline_name(title: str, used: set[str]) -> str:
    """A whitespace-collapsed, de-duplicated name for one outline entry.

    Two entries can share a title ("Introduction" in every chapter); a named
    bookmark must be unique, so the second becomes "Introduction (2)".
    """
    base = " ".join(str(title).split()) or "Bookmark"
    if base not in used:
        return base
    suffix = 2
    while f"{base} ({suffix})" in used:
        suffix += 1
    return f"{base} ({suffix})"


def _resolved(text: str, outline: Iterable[object]) -> list[tuple[str, int, int]]:
    """``(title, page, offset)`` for each entry whose page the text has.

    A malformed entry, or one pointing past the last page, is skipped:
    importing an outline must never block opening a PDF.
    """
    found: list[tuple[str, int, int]] = []
    for entry in outline:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            continue
        try:
            page = int(entry[1])
        except (TypeError, ValueError):
            continue
        offset = page_start_for_number(text, page)
        if offset is not None:
            found.append((str(entry[0]), page, offset))
    return found


def outline_bookmark_offsets(text: str, outline: Iterable[object]) -> dict[str, int]:
    """Each outline entry as a unique name and the offset of its page's start."""
    offsets: dict[str, int] = {}
    for title, _page, offset in _resolved(text, outline):
        offsets[unique_outline_name(title, set(offsets))] = offset
    return offsets


def outline_places(text: str, outline: Iterable[object]) -> list[tuple[str, int]]:
    """Go To's Outline kind: ``("Chapter 2, page 14", offset)`` rows, in order.

    Led by the title, because that is what a listener is choosing between; the
    page follows so two entries with one title can still be told apart.
    """
    return [
        (f"{' '.join(title.split()) or 'Untitled'}, page {page}", offset)
        for title, page, offset in _resolved(text, outline)
    ]


def page_places(text: str) -> list[tuple[str, int]]:
    """Go To's Page kind for a document with real pages: ``("3", offset)`` rows.

    Empty when the text has no form feeds, which is how a host knows not to
    offer the kind at all (QUILL Lite) or to fall back to estimates (QUILL).
    """
    starts = page_starts(text)
    if len(starts) < 2:
        return []
    return [
        (str(number), start) for number, start in enumerate(starts[:_MAX_LISTED_PAGES], start=1)
    ]


# -- what is said ------------------------------------------------------------- #


def password_prompt(file_name: str, *, incorrect: bool) -> str:
    """The password dialog's question. The password is never stored."""
    if incorrect:
        return f"That password did not open {file_name}. Try again, or Cancel:"
    return f"{file_name} is password-protected. Enter its password to open it:"


def password_cancelled_sentence(file_name: str) -> str:
    return f"Open cancelled. {file_name} is password-protected."


def _pages(page_count: int) -> str:
    """``"12 pages"``, ``"1 page"``, or ``"the pages"`` when the count is unknown."""
    if page_count <= 0:
        return "the pages"
    return f"{page_count} pages" if page_count != 1 else "1 page"


def scanned_question(file_name: str, page_count: int, *, some_text: bool) -> str:
    """The OCR offer. Says what happens, that it stays here, and what No does."""
    how_long = f" ({_pages(page_count)})" if page_count > 0 else ""
    found = (
        f"{file_name}{how_long} has very little text in it; it looks scanned."
        if some_text
        else f"{file_name}{how_long} has no text in it; it looks scanned."
    )
    no = "No opens the little text there is." if some_text else "No opens nothing."
    return (
        f"{found}\n\nRead it with OCR on this computer? Nothing is uploaded, and the "
        f"PDF is not changed.\n\nYes reads the pages now. {no}"
    )


def ocr_started_sentence(page_count: int) -> str:
    return f"Scanned; reading {_pages(page_count)} with OCR on this computer"


def ocr_finished_sentence(found: PdfOpen) -> str:
    pages = _pages(found.page_count)
    confidence = f", confidence {found.ocr_confidence:.0f}" if found.ocr_confidence >= 0.0 else ""
    return f"OCR done, {pages}{confidence}. Check the text; OCR makes mistakes."


def opened_summary(found: PdfOpen) -> str:
    """One sentence after a PDF opens: pages, outline, and what Save will do."""
    parts = [f"Opened as text, {_pages(found.page_count)}"]
    read = len(found.page_scores)
    if 0 < read < found.page_count:
        parts.append(f"the first {read} read")
    if found.outline:
        entries = len(found.outline)
        parts.append(f"{entries} outline {'entry' if entries == 1 else 'entries'} in Go To")
    return ", ".join(parts) + ". Saving makes a new file; the PDF is not changed."


def save_refusal(name: str, suffix: str, *, app_name: str, formats: str) -> str:
    """Why Save went to Save As for a file opened as extracted text.

    Both editors refuse the same way (``quill.io.export.EXPORT_ONLY_SUFFIXES``):
    the buffer is text read *out of* the file, and writing it back would put
    text into a file other programs expect to be a PDF.
    """
    return (
        f"{name} was opened as extracted text. {app_name} cannot write {suffix} files "
        f"directly, so saving over the original would destroy it. Choose a new name "
        f"and format ({formats})"
    )
