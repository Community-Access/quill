"""Windows OCR as a docconvert tier, and the engine router (2026-10-15).

No real engine runs here: the recognizer, the page renderer and the
availability probes are the injectable seams on ``docconvert._Deps``. What is
checked is the routing -- Tesseract first, Windows OCR next, a sentence when
neither -- and that a build without the ``winrt`` packages says so rather
than failing on an import.
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

from quill.io import docconvert_windows as dw
from quill.io.docconvert import (
    TIER_LOCAL_OCR,
    TIER_WINDOWS_OCR,
    DocConvertCancelled,
    DocConvertError,
    _Deps,
)
from quill.io.ocr import OcrLine, OcrResult, OcrUnavailableError


def _pages(count: int):
    def render(_path: Path, work_dir: Path) -> list[Path]:
        return [work_dir / f"page-{n:04d}.png" for n in range(1, count + 1)]

    return render


def _windows(text_for=lambda image: f"Read {image.stem}"):
    def recognize(image: Path, language: str | None) -> OcrResult:
        return OcrResult(text=text_for(image) + "\n", engine="windows", language=language or "")

    return recognize


def test_windows_ocr_reads_each_pdf_page_and_keeps_the_pages() -> None:
    progress: list[str] = []
    deps = _Deps(
        windows_ocr_ready=lambda: True,
        windows_ocr_image=_windows(),
        pdf_page_images=_pages(2),
    )
    outcome = dw.convert_with_windows_ocr(
        Path("scan.pdf"), deps=deps, on_progress=lambda _f, message: progress.append(message)
    )
    assert outcome.tier == TIER_WINDOWS_OCR
    assert outcome.page_count == 2
    assert outcome.pages == ("Read page-0001", "Read page-0002")
    assert "<!-- Page 2 -->" in outcome.text
    assert outcome.mean_confidence < 0 and not outcome.looks_weak
    assert "Recognizing page 2 of 2..." in progress


def test_windows_ocr_reads_an_image_too() -> None:
    deps = _Deps(windows_ocr_ready=lambda: True, windows_ocr_image=_windows())
    outcome = dw.convert_with_windows_ocr(Path("photo.png"), deps=deps)
    assert outcome.pages == ("Read photo",) and outcome.page_count == 1


def test_windows_ocr_stops_between_pages_when_cancelled() -> None:
    deps = _Deps(
        windows_ocr_ready=lambda: True, windows_ocr_image=_windows(), pdf_page_images=_pages(3)
    )
    with pytest.raises(DocConvertCancelled):
        dw.convert_with_windows_ocr(Path("scan.pdf"), deps=deps, cancel_requested=lambda: True)


def test_without_windows_ocr_the_tier_says_so_in_a_sentence() -> None:
    deps = _Deps(windows_ocr_ready=lambda: False)
    with pytest.raises(DocConvertError) as caught:
        dw.convert_with_windows_ocr(Path("scan.pdf"), deps=deps)
    assert caught.value.args[0] == dw.WINDOWS_OCR_UNAVAILABLE


def test_a_missing_language_pack_becomes_the_same_sentence() -> None:
    def no_pack(_image: Path, _language: str | None) -> OcrResult:
        raise OcrUnavailableError("No Windows OCR language pack is installed.")

    deps = _Deps(
        windows_ocr_ready=lambda: True, windows_ocr_image=no_pack, pdf_page_images=_pages(1)
    )
    with pytest.raises(DocConvertError, match="Windows OCR is not available on this computer"):
        dw.convert_with_windows_ocr(Path("scan.pdf"), deps=deps)


def test_the_router_prefers_tesseract_when_it_is_installed() -> None:
    def tesseract(image: Path, language: str) -> OcrResult:
        return OcrResult(text="T\n", engine="tesseract", lines=[OcrLine("T", 88.0)])

    deps = _Deps(
        tesseract_ready=lambda: True,
        ocr_image=tesseract,
        windows_ocr_ready=lambda: pytest.fail("Windows OCR asked while Tesseract was there"),
        pdf_page_images=_pages(1),
    )
    assert dw.convert_with_on_device_ocr(Path("scan.pdf"), deps=deps).tier == TIER_LOCAL_OCR


def test_the_router_falls_back_to_windows_ocr_and_then_to_a_sentence() -> None:
    deps = _Deps(
        tesseract_ready=lambda: False,
        windows_ocr_ready=lambda: True,
        windows_ocr_image=_windows(),
        pdf_page_images=_pages(1),
    )
    assert dw.convert_with_on_device_ocr(Path("scan.pdf"), deps=deps).tier == TIER_WINDOWS_OCR
    nothing = _Deps(tesseract_ready=lambda: False, windows_ocr_ready=lambda: False)
    with pytest.raises(DocConvertError) as caught:
        dw.convert_with_on_device_ocr(Path("scan.pdf"), deps=nothing)
    assert caught.value.args[0] == dw.NO_ON_DEVICE_OCR


def test_a_build_without_the_platform_module_reports_windows_ocr_absent(monkeypatch) -> None:
    """Guarded imports: no winrt, no platform module -- False, never an ImportError."""
    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "quill.platform.windows.windows_ocr":
            raise ImportError("not in this build")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "quill.platform.windows.windows_ocr", raising=False)
    monkeypatch.setattr(builtins, "__import__", refuse)
    assert dw.windows_ocr_available() is False


def test_the_probe_asks_whether_winrt_came_not_whether_the_module_did(monkeypatch) -> None:
    from quill.platform.windows import windows_ocr

    monkeypatch.setattr(windows_ocr, "_WINRT_AVAILABLE", False)
    assert dw.windows_ocr_available() is False
    monkeypatch.setattr(windows_ocr, "_WINRT_AVAILABLE", True)
    assert dw.windows_ocr_available() is True


def test_image_ocr_backend_no_longer_claims_windows_ocr_without_winrt(monkeypatch) -> None:
    """The same import-proves-nothing bug, in quill.io.ocr's backend."""
    from quill.io.ocr import WindowsOcrBackend
    from quill.platform.windows import windows_ocr

    monkeypatch.setattr(windows_ocr, "_WINRT_AVAILABLE", False)
    assert WindowsOcrBackend().is_available() is False
