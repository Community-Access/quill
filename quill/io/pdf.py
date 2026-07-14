from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.io.markitdown_bridge import convert_with_markitdown

# PERF-13: bound how many pages we pull text from so a very large PDF cannot
# materialize every page at once. Pages beyond this cap are counted but skipped.
_PDF_MAX_PAGES = 200


@dataclass(slots=True)
class PdfExtractionResult:
    text: str
    quality_score: int
    engine: str
    page_count: int
    extracted_pages: int
    page_scores: list[int]


def extract_pdf_text(path: Path) -> PdfExtractionResult:
    # Distinguish four outcomes (#909, #58): (1) no extractor installed, (2) an
    # encrypted/password-protected PDF, (3) a damaged/corrupt PDF that parse-fails
    # in the extractor, and (4) a scanned/image-only PDF with no text layer. They
    # are different problems with different remedies, and the previous broad
    # ``except Exception`` collapsed 2/3 into 4 -- telling users with a corrupt or
    # password-locked file to run OCR (the wrong fix).
    any_extractor_available = False
    parse_error = False
    for extractor in (_extract_with_pdfplumber, _extract_with_pypdf):
        try:
            result = extractor(path)
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
        message = (
            f"({path.name} is encrypted. QUILL cannot read password-protected "
            f"PDFs. Remove the password (for example `qpdf --decrypt in.pdf out.pdf`) "
            f"and open the decrypted copy, or export it unlocked from the original "
            f"application.)\n"
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


def _extract_with_pdfplumber(path: Path) -> PdfExtractionResult:
    import pdfplumber

    page_texts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
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


def _extract_with_pypdf(path: Path) -> PdfExtractionResult:
    from pypdf import PdfReader  # type: ignore[import-not-found]

    reader = PdfReader(str(path))
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
