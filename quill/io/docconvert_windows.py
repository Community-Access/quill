"""Windows OCR as a docconvert tier, and the router that picks an engine.

Split from :mod:`quill.io.docconvert` under GATE-11 on the day it was written
(2026-10-15); the tier shares that module's outcome shape, its injectable
seams and its one page loop (``_ocr_pdf_pages``), so the two engines cannot
drift into two ways of reading the same scanned page.

**Windows OCR** (``Windows.Media.Ocr``) is reached through the ``winrt``
packages the shared runtime already freezes in. It needs no download, which is
the whole reason it is here: QUILL Lite never downloads an engine, so without
it a scanned PDF is a dead end there, and QUILL gains the same no-download
path in the same change. A build without the packages answers
:data:`WINDOWS_OCR_UNAVAILABLE` -- a sentence the caller speaks -- rather than an
import error.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from pathlib import Path

from quill.io.docconvert import (
    IMAGE_EXTENSIONS,
    PDF_EXTENSION,
    TIER_WINDOWS_OCR,
    CancelFn,
    ConversionOutcome,
    DocConvertError,
    ProgressCallback,
    _Deps,
    _ocr_pdf_pages,
    convert_with_local_ocr,
)
from quill.io.ocr import OcrResult
from quill.io.tesseract_ocr import DEFAULT_LANGUAGE

__all__ = [
    "NO_ON_DEVICE_OCR",
    "WINDOWS_OCR_UNAVAILABLE",
    "convert_with_on_device_ocr",
    "convert_with_windows_ocr",
    "windows_ocr_available",
]


#: What a build or a machine without Windows OCR says, in place of an import error.
WINDOWS_OCR_UNAVAILABLE = (
    "Windows OCR is not available on this computer, so the scanned pages could not "
    "be read. Nothing was uploaded."
)

#: What is said when neither on-device engine can run.
NO_ON_DEVICE_OCR = (
    "No OCR engine is available on this computer, so the scanned pages could not be "
    "read. Nothing was uploaded."
)


def windows_ocr_available() -> bool:
    """Whether Windows OCR can run here: Windows, with the ``winrt`` OCR packages.

    Guarded twice, because a build may leave the packages out: the platform
    module imports them inside its own ``try``, and this asks it rather than
    importing ``winrt`` itself, so nothing here can fail on an import.
    """
    try:
        from quill.platform.windows.windows_ocr import winrt_ocr_importable
    except ImportError:
        return False
    return winrt_ocr_importable()


def _default_windows_ocr_image(image: Path, language: str | None) -> OcrResult:
    from quill.io.ocr import ENGINE_WINDOWS
    from quill.platform.windows.windows_ocr import recognize_with_windows_ocr

    text, lines = recognize_with_windows_ocr(image, language)
    return OcrResult(
        text=text.rstrip() + "\n" if text else "",
        engine=ENGINE_WINDOWS,
        language=language or "",
        lines=lines,
    )


def convert_with_windows_ocr(
    path: Path,
    *,
    language: str | None = None,
    deps: _Deps | None = None,
    on_progress: ProgressCallback | None = None,
    cancel_requested: CancelFn | None = None,
) -> ConversionOutcome:
    """Tier 2 with Windows OCR: a scanned PDF or an image, read on this computer.

    ``language`` is a BCP-47 tag (``en-US``); ``None`` uses the languages the
    person has in Windows Settings, which is the right default because the OCR
    language packs come with those. Windows OCR reports no confidence, so the
    outcome's ``mean_confidence`` stays ``-1`` and nothing is flagged weak --
    an honest "not measured", never a made-up number.
    """
    from quill.io.ocr import OcrFailedError, OcrUnavailableError

    resolved = deps or _Deps()
    ready = resolved.windows_ocr_ready or windows_ocr_available
    if not ready():
        raise DocConvertError(WINDOWS_OCR_UNAVAILABLE)
    recognize_one = resolved.windows_ocr_image or _default_windows_ocr_image
    suffix = path.suffix.lower()
    try:
        if suffix in IMAGE_EXTENSIONS:
            if on_progress is not None:
                on_progress(0.2, f"Reading {path.name} with Windows OCR...")
            result = recognize_one(path, language)
            return ConversionOutcome(
                text=result.text,
                tier=TIER_WINDOWS_OCR,
                source=path,
                page_count=1,
                pages=(result.text.strip(),),
            )
        if suffix != PDF_EXTENSION:
            raise DocConvertError(
                f"Windows OCR reads images and PDFs; {path.suffix or 'this file'} is neither."
            )
        return _ocr_pdf_pages(
            path,
            lambda image: recognize_one(image, language),
            tier=TIER_WINDOWS_OCR,
            deps=resolved,
            on_progress=on_progress,
            cancel_requested=cancel_requested,
        )
    except (OcrUnavailableError, OcrFailedError) as exc:
        detail = str(exc.args[0]) if exc.args else ""  # the reason, without its code
        raise DocConvertError(f"{WINDOWS_OCR_UNAVAILABLE} {detail}".strip()) from exc


def convert_with_on_device_ocr(
    path: Path,
    *,
    language: str = DEFAULT_LANGUAGE,
    deps: _Deps | None = None,
    on_progress: ProgressCallback | None = None,
    cancel_requested: CancelFn | None = None,
) -> ConversionOutcome:
    """Tier 2, whichever engine this computer has: Tesseract first, then Windows OCR.

    Tesseract first because it reports a confidence per line, which is what
    the weak-result warning and OCR Review stand on. *language* is Tesseract's
    (``eng``); Windows OCR uses the person's Windows languages instead, because
    the two engines name languages differently and a wrong guess at a mapping
    is worse than the system default.
    """
    resolved = deps or _Deps()
    if resolved.tesseract_ready():
        return convert_with_local_ocr(
            path,
            language=language,
            deps=resolved,
            on_progress=on_progress,
            cancel_requested=cancel_requested,
        )
    if (resolved.windows_ocr_ready or windows_ocr_available)():
        return convert_with_windows_ocr(
            path, deps=resolved, on_progress=on_progress, cancel_requested=cancel_requested
        )
    raise DocConvertError(NO_ON_DEVICE_OCR)
