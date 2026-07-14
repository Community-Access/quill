"""Free-first document conversion routing (MarkItDown -> local Tesseract OCR).

The supported QUILL import tool routes every document through free, local
tiers before anything else, per the OCR/document-conversion PRD:

* **Tier 1 — MarkItDown** (:mod:`quill.io.markitdown_bridge`): pure-Python
  extraction of the existing text layer from *born-digital* files (DOCX, PPTX,
  XLSX, HTML, EPUB, and PDFs that already carry text). Free, offline, no
  upload. Not an OCR engine — a scanned PDF comes back empty here.
* **Tier 2 — local Tesseract OCR** (:mod:`quill.io.tesseract_ocr`): real OCR
  for images and image-based PDFs, run entirely on-device, CPU-only. Free,
  offline, no upload. PDF pages are rasterized with ``pypdfium2`` and
  recognized page by page with ``<!-- Page N -->`` delimiters.

A paid cloud tier (Datalab Chandra) is deliberately **not** implemented here;
when it arrives it plugs in behind the same outcome model, reached only when
these free tiers fall short and only with explicit consent.

QUILL must never silently open an empty or garbled result, so this module
measures what each tier recovered: :func:`text_layer_looks_empty` implements
the PRD's chars-per-page heuristic for the Tier 1 -> 2 escalation prompt, and
Tier 2 reports mean OCR confidence for the "result looks weak" warning.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.io.ocr import OcrResult
from quill.io.tesseract_ocr import (
    DEFAULT_LANGUAGE,
    ocr_image_with_tesseract,
    tesseract_available,
)

# (fraction 0.0-1.0, human message) — matches the speech/component callbacks.
ProgressCallback = Callable[[float, str], None]
CancelFn = Callable[[], bool]


class DocConvertError(CodedError):
    """A conversion tier could not run (missing dependency, unreadable file)."""

    code = "QUILL-IO-DOCCONVERT-FAILED"


class DocConvertCancelled(DocConvertError):
    """The user cancelled a conversion in progress."""


#: Born-digital formats Tier 1 (MarkItDown) handles directly.
BORN_DIGITAL_EXTENSIONS: frozenset[str] = frozenset({
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".epub",
    ".csv",
    ".odt",
    ".odp",
    ".ods",
})

#: Image formats Tier 2 (local OCR) handles directly.
IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
})

#: PDFs are ambiguous: born-digital when they carry a text layer, scanned
#: otherwise. Tier 1 is tried first; the emptiness heuristic decides.
PDF_EXTENSION = ".pdf"

#: Tier 1 -> 2 escalation heuristic (PRD §11.4): a text layer that recovered
#: fewer than this many characters per page "looks scanned".
MIN_CHARS_PER_PAGE = 50

#: Tier 2 mean word confidence (0-100) below which the OCR result is flagged
#: as weak — the future cloud tier's escalation point, and today an honest
#: "review this carefully" warning.
WEAK_OCR_CONFIDENCE = 60.0

#: Conversion tiers, as recorded on the outcome.
TIER_MARKITDOWN = "markitdown"
TIER_LOCAL_OCR = "local-ocr"
TIER_CLOUD_OCR = "cloud-ocr"


def supported_import_extensions() -> frozenset[str]:
    """Every extension the free-first import tool accepts."""
    return BORN_DIGITAL_EXTENSIONS | IMAGE_EXTENSIONS | {PDF_EXTENSION}


@dataclass(slots=True)
class ConversionOutcome:
    """What a conversion produced and how much to trust it."""

    text: str
    tier: str
    source: Path
    page_count: int = 0
    mean_confidence: float = -1.0
    warnings: tuple[str, ...] = ()
    #: Tier 1 result that looks scanned/empty — offer free local OCR next.
    offer_local_ocr: bool = False
    #: Which service produced the result ("" for the local tiers).
    provider: str = ""
    #: Low-confidence lines flagged for OCR Review Mode, pre-formatted as
    #: "Page N: [NN%] text" so the review surface is a spoken checklist.
    low_confidence: tuple[str, ...] = ()

    @property
    def looks_weak(self) -> bool:
        """True when Tier 2 confidence fell below the review threshold."""
        return 0.0 <= self.mean_confidence < WEAK_OCR_CONFIDENCE


@dataclass(slots=True)
class _Deps:
    """Injectable seams so the router is fully unit-testable offline."""

    markitdown: Callable[[Path], str] | None = None
    ocr_image: Callable[[Path, str], OcrResult] | None = None
    pdf_page_count: Callable[[Path], int] | None = None
    pdf_page_images: Callable[[Path, Path], list[Path]] | None = None
    tesseract_ready: Callable[[], bool] = field(default=tesseract_available)


def text_layer_looks_empty(text: str, page_count: int) -> bool:
    """PRD §11.4 emptiness heuristic for a Tier 1 extraction.

    True when the recovered text averages fewer than
    :data:`MIN_CHARS_PER_PAGE` characters per page (a multi-page document that
    yields almost nothing is almost certainly image-based) or is effectively
    whitespace.
    """
    meaningful = len("".join(text.split()))
    if meaningful == 0:
        return True
    pages = max(page_count, 1)
    return meaningful < MIN_CHARS_PER_PAGE * pages


def _default_markitdown(path: Path) -> str:
    from quill.io.markitdown_bridge import convert_with_markitdown

    return convert_with_markitdown(path)


def _default_pdf_page_count(path: Path) -> int:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped,import-not-found]
    except ImportError:
        return 0
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def _default_pdf_page_images(path: Path, work_dir: Path) -> list[Path]:
    """Rasterize each PDF page to a PNG for OCR (about 150 dpi)."""
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped,import-not-found]
    except ImportError as exc:
        raise DocConvertError(
            "Reading PDF pages requires the pypdfium2 package, which is not installed."
        ) from exc
    images: list[Path] = []
    document = pdfium.PdfDocument(str(path))
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=150 / 72)
            image = bitmap.to_pil()
            target = work_dir / f"page-{index + 1:04d}.png"
            image.save(target)
            images.append(target)
            page.close()
    finally:
        document.close()
    return images


def convert_born_digital(
    path: Path,
    *,
    deps: _Deps | None = None,
    on_progress: ProgressCallback | None = None,
) -> ConversionOutcome:
    """Tier 1: extract the existing text layer with MarkItDown.

    Raises :class:`DocConvertError` with a friendly message when MarkItDown is
    not installed or cannot read the file. An empty-but-successful extraction
    of a PDF is *not* an error — it returns an outcome flagged
    ``offer_local_ocr`` so the caller can show the escalation prompt.
    """
    resolved = deps or _Deps()
    run = resolved.markitdown or _default_markitdown
    if on_progress is not None:
        on_progress(0.1, f"Reading {path.name} with the free local converter...")
    page_count = 0
    if path.suffix.lower() == PDF_EXTENSION:
        count = resolved.pdf_page_count or _default_pdf_page_count
        page_count = count(path)
    try:
        text = run(path)
    except ImportError as exc:
        raise DocConvertError(
            "The free local converter (MarkItDown) is not installed. Open "
            'Help > Download Optional Components and download "PDF and '
            'Office text extraction" to enable born-digital conversion.'
        ) from exc
    except ValueError:
        # MarkItDown raises on empty output; for PDFs that usually means a
        # scanned document — surface the escalation rather than an error.
        if path.suffix.lower() == PDF_EXTENSION:
            return ConversionOutcome(
                text="",
                tier=TIER_MARKITDOWN,
                source=path,
                page_count=page_count,
                offer_local_ocr=True,
                warnings=(
                    "No readable text layer was found; the document looks scanned or image-based.",
                ),
            )
        raise DocConvertError(
            f"The free local converter produced no text for {path.name}."
        ) from None
    if on_progress is not None:
        on_progress(0.9, "Checking the recovered text...")
    outcome = ConversionOutcome(
        text=text,
        tier=TIER_MARKITDOWN,
        source=path,
        page_count=page_count,
    )
    if path.suffix.lower() == PDF_EXTENSION and text_layer_looks_empty(text, page_count):
        outcome.offer_local_ocr = True
        outcome.warnings = (
            "Very little readable text was found; the document looks scanned or image-based.",
        )
    return outcome


def convert_with_local_ocr(
    path: Path,
    *,
    language: str = DEFAULT_LANGUAGE,
    deps: _Deps | None = None,
    on_progress: ProgressCallback | None = None,
    cancel_requested: CancelFn | None = None,
) -> ConversionOutcome:
    """Tier 2: OCR an image or an image-based PDF locally with Tesseract.

    Everything stays on-device. PDF pages are rasterized and recognized one at
    a time with cancel checks between pages; page boundaries are preserved as
    ``<!-- Page N -->`` delimiters (screen-reader-searchable, Markdown-clean).
    """
    resolved = deps or _Deps()
    if not resolved.tesseract_ready():
        raise DocConvertError(
            "The local OCR engine (Tesseract) is not installed. "
            "Install it from Tools > OCR and Document Conversion, then try again."
        )
    ocr = resolved.ocr_image or (lambda image, lang: ocr_image_with_tesseract(image, lang))
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        if on_progress is not None:
            on_progress(0.2, f"Running free on-device OCR on {path.name}...")
        result = ocr(path, language)
        mean = _mean_confidence([result])
        return ConversionOutcome(
            text=result.text,
            tier=TIER_LOCAL_OCR,
            source=path,
            page_count=1,
            mean_confidence=mean,
            warnings=_weak_warning(mean),
            low_confidence=_flag_low_confidence([result]),
        )
    if suffix != PDF_EXTENSION:
        raise DocConvertError(
            f"Local OCR supports images and PDFs; {path.suffix or 'this file'} is neither."
        )
    render = resolved.pdf_page_images or _default_pdf_page_images
    results: list[OcrResult] = []
    parts: list[str] = []
    with tempfile.TemporaryDirectory(prefix="quill-ocr-") as raw_dir:
        work_dir = Path(raw_dir)
        if on_progress is not None:
            on_progress(0.05, "Preparing PDF pages for on-device OCR...")
        images = render(path, work_dir)
        total = len(images)
        for number, image in enumerate(images, start=1):
            if cancel_requested is not None and cancel_requested():
                raise DocConvertCancelled("Conversion cancelled. No result was imported.")
            if on_progress is not None:
                on_progress(
                    0.05 + 0.9 * (number - 1) / max(total, 1),
                    f"Recognizing page {number} of {total}...",
                )
            result = ocr(image, language)
            results.append(result)
            parts.append(f"<!-- Page {number} -->\n\n{result.text.rstrip()}\n")
    text = "\n".join(parts).rstrip() + "\n" if parts else ""
    mean = _mean_confidence(results)
    return ConversionOutcome(
        text=text,
        tier=TIER_LOCAL_OCR,
        source=path,
        page_count=len(results),
        mean_confidence=mean,
        warnings=_weak_warning(mean),
        low_confidence=_flag_low_confidence(results),
    )


CloudConvertFn = Callable[..., Any]


def convert_with_cloud_ocr(
    path: Path,
    *,
    cloud_convert: CloudConvertFn | None = None,
    endpoint: str = "",
    mode: str = "balanced",
    output_format: str = "markdown",
    paginate: bool = True,
    on_progress: ProgressCallback | None = None,
    cancel_requested: CancelFn | None = None,
) -> ConversionOutcome:
    """Tier 3: convert via the consent-gated Datalab Chandra cloud service.

    The caller has already collected the per-upload consent (PRD §15.1) —
    this function only performs the conversion and adapts the result into the
    shared outcome shape. ``cloud_convert`` is injectable for offline tests;
    the default is :func:`quill.core.datalab_ocr.convert_with_datalab`.
    """
    convert = cloud_convert
    if convert is None:
        from quill.core.datalab_ocr import convert_with_datalab

        convert = convert_with_datalab
    result = convert(
        path,
        endpoint=endpoint or "https://www.datalab.to",
        mode=mode,
        output_format=output_format,
        paginate=paginate,
        on_progress=(lambda message: on_progress(0.5, message)) if on_progress else None,
        cancel_requested=cancel_requested,
    )
    return ConversionOutcome(
        text=str(getattr(result, "content", "") or ""),
        tier=TIER_CLOUD_OCR,
        source=path,
        page_count=int(getattr(result, "page_count", 0) or 0),
        provider="datalab",
    )


def convert_document(
    path: Path,
    *,
    prefer_free_local: bool = True,
    language: str = DEFAULT_LANGUAGE,
    deps: _Deps | None = None,
    on_progress: ProgressCallback | None = None,
    cancel_requested: CancelFn | None = None,
) -> ConversionOutcome:
    """Route one import through the free-first tiers (PRD §11.4).

    Born-digital types go to Tier 1; images go straight to Tier 2; PDFs try
    Tier 1 and come back flagged ``offer_local_ocr`` when the text layer looks
    empty — the caller owns the accessible escalation prompt, because QUILL
    never runs OCR (or, later, a paid upload) without asking.

    ``prefer_free_local=False`` currently changes nothing — there is no paid
    tier to prefer — but is honored so the setting's contract is stable.
    """
    del prefer_free_local  # No paid tier exists yet; free-first is the only route.
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return convert_with_local_ocr(
            path,
            language=language,
            deps=deps,
            on_progress=on_progress,
            cancel_requested=cancel_requested,
        )
    if suffix in BORN_DIGITAL_EXTENSIONS or suffix == PDF_EXTENSION:
        return convert_born_digital(path, deps=deps, on_progress=on_progress)
    raise DocConvertError(
        f"{path.suffix or 'This file type'} is not supported by Import / Convert Document."
    )


def _mean_confidence(results: list[OcrResult]) -> float:
    values = [
        line.confidence for result in results for line in result.lines if line.confidence >= 0.0
    ]
    if not values:
        return -1.0
    return sum(values) / len(values)


def _flag_low_confidence(results: list[OcrResult]) -> tuple[str, ...]:
    """Pre-format the flagged lines for OCR Review Mode: "Page N: [NN%] text"."""
    flagged: list[str] = []
    for page_number, result in enumerate(results, start=1):
        for line in result.lines:
            if line.is_low_confidence:
                flagged.append(f"Page {page_number}: [{line.confidence:.0f}%] {line.text}")
    return tuple(flagged)


def _weak_warning(mean: float) -> tuple[str, ...]:
    if 0.0 <= mean < WEAK_OCR_CONFIDENCE:
        return (
            f"On-device OCR confidence is low ({mean:.0f} out of 100). "
            "Review the result carefully; a cleaner scan may recognize better.",
        )
    return ()


__all__ = [
    "BORN_DIGITAL_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "MIN_CHARS_PER_PAGE",
    "PDF_EXTENSION",
    "TIER_CLOUD_OCR",
    "TIER_LOCAL_OCR",
    "TIER_MARKITDOWN",
    "WEAK_OCR_CONFIDENCE",
    "ConversionOutcome",
    "DocConvertCancelled",
    "DocConvertError",
    "convert_born_digital",
    "convert_document",
    "convert_with_cloud_ocr",
    "convert_with_local_ocr",
    "supported_import_extensions",
    "text_layer_looks_empty",
]
