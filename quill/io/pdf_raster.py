"""PDF pages as pictures, for the OCR tiers that read them.

Moved out of :mod:`quill.io.docconvert` on 2026-10-15, when that module gained
its second on-device OCR engine (Windows OCR beside Tesseract) and needed the
room under GATE-11. Both engines read the same pictures: ``pypdfium2`` renders
each page at about 150 dots per inch, which is enough for either engine and
small enough that a long scan does not fill the temporary folder.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = ["PdfRasterError", "pdf_page_count", "render_pdf_pages"]

#: The resolution the pages are drawn at. 150 dpi reads well with both engines.
RENDER_DPI = 150


class PdfRasterError(CodedError):
    """The pages could not be drawn (``pypdfium2`` is missing or the file is unreadable)."""

    code = "QUILL-IO-PDFRASTER-FAILED"


def pdf_page_count(path: Path) -> int:
    """How many pages *path* has, or ``0`` when ``pypdfium2`` is not installed."""
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped,import-not-found]
    except ImportError:
        return 0
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def render_pdf_pages(path: Path, work_dir: Path) -> list[Path]:
    """Draw each page of *path* as a PNG in *work_dir*, in order."""
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped,import-not-found]
    except ImportError as exc:
        raise PdfRasterError(
            "Reading PDF pages requires the pypdfium2 package, which is not installed."
        ) from exc
    images: list[Path] = []
    document = pdfium.PdfDocument(str(path))
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=RENDER_DPI / 72)
            image = bitmap.to_pil()
            target = work_dir / f"page-{index + 1:04d}.png"
            image.save(target)
            images.append(target)
            page.close()
    finally:
        document.close()
    return images
