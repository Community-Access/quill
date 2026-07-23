from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.io.markitdown_bridge import convert_with_markitdown

# PERF-13: bound how many pages we pull text from so a very large PDF cannot
# materialize every page at once. Pages beyond this cap are counted but skipped.
_PDF_MAX_PAGES = 200

# Bound how many embedded outline (bookmark) entries we import so a pathological
# PDF with thousands of outline nodes cannot flood the bookmark store.
_PDF_MAX_OUTLINE_ENTRIES = 500


@dataclass(slots=True)
class PdfExtractionResult:
    text: str
    quality_score: int
    engine: str
    page_count: int
    extracted_pages: int
    page_scores: list[int]


def extract_pdf_text(path: Path, *, password: str | None = None) -> PdfExtractionResult:
    # Distinguish four outcomes (#909, #58): (1) no extractor installed, (2) an
    # encrypted/password-protected PDF, (3) a damaged/corrupt PDF that parse-fails
    # in the extractor, and (4) a scanned/image-only PDF with no text layer. They
    # are different problems with different remedies, and the previous broad
    # ``except Exception`` collapsed 2/3 into 4 -- telling users with a corrupt or
    # password-locked file to run OCR (the wrong fix).
    #
    # ``password`` (when the UI has collected one) is threaded to both extractors:
    # a correct password unlocks the file and it extracts like any other PDF; a
    # wrong/absent password leaves the file locked and falls through to the
    # ``encrypted`` branch below. The password is used only for this read and is
    # never persisted.
    any_extractor_available = False
    parse_error = False
    for extractor in (_extract_with_pdfplumber, _extract_with_pypdf):
        try:
            result = extractor(path, password=password)
        except ModuleNotFoundError:
            continue  # this extractor's package is absent; try the next
        except Exception:
            # It imported but failed on this file: a real parse failure (corrupt
            # xref, password-required, malformed object, ...). Record it so the
            # fallthrough can tell a damaged file from a scanned one (#58).
            any_extractor_available = True
            parse_error = True
            continue
        any_extractor_available = True
        if result.text.strip():
            return result
    if not any_extractor_available:
        message = (
            f"(No PDF text extractor is installed, so QUILL could not read "
            f"{path.name}. Open Help > Download Optional Components and download "
            f'"PDF and Office text extraction".)\n'
        )
        engine = "unavailable"
    elif _is_encrypted_pdf(path):
        # The file is locked with a real user password. ``password`` distinguishes
        # "no password tried yet" (prompt for one) from "the password just tried
        # was wrong" (re-prompt) -- both keep ``engine="encrypted"`` so the open
        # flow knows to ask. The password is never stored.
        if password:
            message = (
                f"(The password for {path.name} was not correct, so the encrypted "
                f"PDF could not be opened. Check the password and try again.)\n"
            )
        else:
            message = (
                f"({path.name} is encrypted (password-protected). Enter its password "
                f"to open it; QUILL uses the password only to unlock this file and "
                f"never stores it.)\n"
            )
        engine = "encrypted"
    elif parse_error:
        message = (
            f"({path.name} could not be parsed -- it is likely damaged or corrupt. "
            f"OCR will not help a corrupt file. Try re-downloading or re-exporting it "
            f"from the original application; a tool like `qpdf --check` can confirm "
            f"whether the file is still valid.)\n"
        )
        engine = "damaged"
    else:
        message = (
            f"(No selectable text was found in {path.name}. It is likely a scanned "
            f"or image-only PDF — use File > Import and choose OCR to read it.)\n"
        )
        engine = "empty"
    return PdfExtractionResult(
        text=message,
        quality_score=0,
        engine=engine,
        page_count=0,
        extracted_pages=0,
        page_scores=[],
    )


def _is_encrypted_pdf(path: Path) -> bool:
    """Return True when *path* is a password-protected PDF (#58).

    Uses pypdf's ``is_encrypted`` flag and attempts an empty-user-password decrypt:
    a permissions-only "encrypted" PDF (empty password, common) is still readable
    and must not be reported as encrypted, so only treat it as locked when the
    empty password fails to unlock it. Any construction/parse failure reads as
    "not encrypted" (a corrupt file is handled by the ``damaged`` branch instead).
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return False
    try:
        reader = PdfReader(str(path))
    except Exception:  # noqa: BLE001 - corrupt/unreadable -> not our encryption path
        return False
    if not getattr(reader, "is_encrypted", False):
        return False
    try:
        matched = reader.decrypt("")
    except Exception:  # noqa: BLE001 - decrypt API differs across pypdf versions
        return True
    return not bool(matched)


def extract_pdf_outline(path: Path, *, password: str | None = None) -> list[tuple[str, int]]:
    """Return a PDF's embedded outline (Adobe bookmarks) as ``(title, page)`` pairs.

    ``page`` is the 1-based page number the entry points to. The nested outline
    tree is flattened in document order (hierarchy is not preserved — QUILL's
    bookmark store is flat). Best-effort: returns ``[]`` when pypdf is absent, the
    PDF has no outline, it is locked and ``password`` does not unlock it, or any
    entry fails to resolve — importing an outline must never block opening a PDF.
    Capped at :data:`_PDF_MAX_OUTLINE_ENTRIES` entries.
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return []
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt(password or "")
            except Exception:  # noqa: BLE001 - decrypt API varies; treat as locked
                return []
        raw_outline = reader.outline  # property; can raise on a malformed tree
    except Exception:  # noqa: BLE001 - corrupt/unreadable -> no outline
        return []

    entries: list[tuple[str, int]] = []

    def _walk(items: object) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if len(entries) >= _PDF_MAX_OUTLINE_ENTRIES:
                return
            if isinstance(item, list):
                _walk(item)  # a nested sub-tree of child bookmarks
                continue
            title = getattr(item, "title", None)
            if not title or not str(title).strip():
                continue
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:  # noqa: BLE001 - unresolvable destination -> skip
                continue
            if not isinstance(page_index, int) or page_index < 0:
                continue
            entries.append((str(title).strip(), page_index + 1))

    try:
        _walk(raw_outline)
    except Exception:  # noqa: BLE001 - any traversal failure -> what we have so far
        pass
    return entries


def format_pdf_document(path: Path | PdfExtractionResult) -> str:
    result = path if isinstance(path, PdfExtractionResult) else extract_pdf_text(path)
    header = [
        "# PDF Extract",
        "",
        f"Engine: {result.engine}",
        f"Quality score: {result.quality_score}/100",
    ]
    if result.quality_score < 50:
        header.append("Low-confidence extraction. MarkItDown or OCR may improve the result.")
    header.append("")
    body = result.text.rstrip() + "\n"
    if isinstance(path, Path) and result.quality_score < 50:
        try:
            markitdown_text = convert_with_markitdown(path)
        except (ImportError, ValueError, RuntimeError):
            return "\n".join(header) + body
        if len(markitdown_text.strip()) > len(result.text.strip()):
            return (
                "\n".join([
                    "# PDF Extract",
                    "",
                    "Engine: markitdown",
                    "Quality score: 85/100",
                    "",
                ])
                + markitdown_text.rstrip()
                + "\n"
            )
    return "\n".join(header) + body


def _extract_with_pdfplumber(path: Path, *, password: str | None = None) -> PdfExtractionResult:
    import pdfplumber

    page_texts: list[str] = []
    # pdfplumber accepts ``password=None`` (treated as no password); a supplied
    # user password unlocks an encrypted PDF, and a wrong one raises, which the
    # caller records as a parse failure.
    with pdfplumber.open(str(path), password=password or "") as pdf:
        page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages):
            if index >= _PDF_MAX_PAGES:
                break
            text = page.extract_text() or ""
            page_texts.append(text.strip())
            flush_cache = getattr(page, "flush_cache", None)
            if callable(flush_cache):
                flush_cache()
    # #872: join with a form feed, not a blank line, so real page
    # boundaries survive into the editable Document text. This makes
    # quill.core.navigation.page_starts()/page_start_for_number() -- already
    # built for this, previously unreachable for real documents -- report
    # exact pages for PDFs.
    text = "\f".join(page_texts).strip()
    score = _score_pdf_text(text, page_count, sum(1 for page_text in page_texts if page_text))
    return PdfExtractionResult(
        text=text + "\n" if text else "",
        quality_score=score,
        engine="pdfplumber",
        page_count=page_count,
        extracted_pages=sum(1 for page_text in page_texts if page_text),
        page_scores=[_score_pdf_text(page_text, 1, 1) for page_text in page_texts],
    )


def _extract_with_pypdf(path: Path, *, password: str | None = None) -> PdfExtractionResult:
    from pypdf import PdfReader  # type: ignore[import-not-found]

    reader = PdfReader(str(path))
    if getattr(reader, "is_encrypted", False):
        # An empty string unlocks a permissions-only ("empty user password") PDF;
        # a supplied password unlocks a locked one. A failed decrypt leaves the
        # reader locked so page access raises, recorded upstream as a parse error.
        try:
            reader.decrypt(password or "")
        except Exception:  # noqa: BLE001 - decrypt API differs across pypdf versions
            pass
    page_count = len(reader.pages)
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages):
        if index >= _PDF_MAX_PAGES:
            break
        page_texts.append((page.extract_text() or "").strip())
    # #872: see the matching comment in _extract_with_pdfplumber above.
    text = "\f".join(page_texts).strip()
    score = _score_pdf_text(text, page_count, sum(1 for page_text in page_texts if page_text))
    return PdfExtractionResult(
        text=text + "\n" if text else "",
        quality_score=score,
        engine="pypdf",
        page_count=page_count,
        extracted_pages=sum(1 for page_text in page_texts if page_text),
        page_scores=[_score_pdf_text(page_text, 1, 1) for page_text in page_texts],
    )


def _score_pdf_text(text: str, page_count: int, extracted_pages: int) -> int:
    normalized = " ".join(text.split())
    if not normalized:
        return 0
    words = len(normalized.split())
    char_score = min(40, len(normalized) // 80)
    word_score = min(30, words // 4)
    page_score = min(30, extracted_pages * 10 if page_count else 0)
    return min(100, char_score + word_score + page_score)
