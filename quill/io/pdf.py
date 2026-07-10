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
    # Distinguish "no extractor installed" from "an extractor ran but found no
    # text" (#909). They are different problems with different remedies: the
    # former is a broken/partial install, the latter is almost always a scanned
    # or image-only PDF that needs OCR. Collapsing both into one message sent
    # users chasing the wrong fix.
    any_extractor_available = False
    for extractor in (_extract_with_pdfplumber, _extract_with_pypdf):
        try:
            result = extractor(path)
        except ModuleNotFoundError:
            continue  # this extractor's package is absent; try the next
        except Exception:
            any_extractor_available = True  # it imported, it just failed on this file
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
