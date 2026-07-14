"""Tests for the free-first document conversion router (PRD §11.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.docconvert import (
    MIN_CHARS_PER_PAGE,
    TIER_LOCAL_OCR,
    TIER_MARKITDOWN,
    ConversionOutcome,
    DocConvertCancelled,
    DocConvertError,
    _Deps,
    convert_born_digital,
    convert_document,
    convert_with_local_ocr,
    supported_import_extensions,
    text_layer_looks_empty,
)
from quill.io.ocr import OcrLine, OcrResult


def _fake_ocr(text: str, confidence: float) -> OcrResult:
    return OcrResult(
        text=text,
        engine="tesseract",
        lines=[OcrLine(text=text.strip(), confidence=confidence)],
    )


def test_supported_extensions_cover_the_three_tiers() -> None:
    extensions = supported_import_extensions()
    assert ".docx" in extensions
    assert ".pdf" in extensions
    assert ".png" in extensions


def test_text_layer_emptiness_heuristic() -> None:
    assert text_layer_looks_empty("", 10)
    assert text_layer_looks_empty("   \n\n  ", 3)
    # 10 pages of a scanned PDF yielding one short line looks empty.
    assert text_layer_looks_empty("Cover page", 10)
    # A real single page of text does not.
    assert not text_layer_looks_empty("x" * (MIN_CHARS_PER_PAGE + 1), 1)


def test_born_digital_routes_through_markitdown() -> None:
    deps = _Deps(markitdown=lambda path: "# Converted\n\nBody text.\n")
    outcome = convert_document(Path("report.docx"), deps=deps)
    assert outcome.tier == TIER_MARKITDOWN
    assert "Converted" in outcome.text
    assert not outcome.offer_local_ocr


def test_pdf_with_healthy_text_layer_does_not_offer_ocr() -> None:
    deps = _Deps(
        markitdown=lambda path: "word " * 300,
        pdf_page_count=lambda path: 2,
    )
    outcome = convert_document(Path("manual.pdf"), deps=deps)
    assert outcome.tier == TIER_MARKITDOWN
    assert not outcome.offer_local_ocr


def test_scanned_pdf_offers_free_local_ocr() -> None:
    deps = _Deps(
        markitdown=lambda path: "  ",
        pdf_page_count=lambda path: 12,
    )
    outcome = convert_document(Path("scan.pdf"), deps=deps)
    assert outcome.offer_local_ocr
    assert outcome.warnings


def test_markitdown_empty_error_on_pdf_becomes_escalation_not_failure() -> None:
    def _empty(path: Path) -> str:
        raise ValueError("MarkItDown produced empty output")

    deps = _Deps(markitdown=_empty, pdf_page_count=lambda path: 4)
    outcome = convert_document(Path("scan.pdf"), deps=deps)
    assert outcome.offer_local_ocr
    assert outcome.text == ""


def test_markitdown_missing_is_a_friendly_error() -> None:
    def _missing(path: Path) -> str:
        raise ImportError("markitdown not available")

    deps = _Deps(markitdown=_missing)
    with pytest.raises(DocConvertError) as excinfo:
        convert_born_digital(Path("report.docx"), deps=deps)
    assert "not installed" in str(excinfo.value)


def test_image_goes_straight_to_local_ocr() -> None:
    deps = _Deps(
        ocr_image=lambda path, lang: _fake_ocr("Recognized text.\n", 92.0),
        tesseract_ready=lambda: True,
    )
    outcome = convert_document(Path("photo.png"), deps=deps)
    assert outcome.tier == TIER_LOCAL_OCR
    assert outcome.page_count == 1
    assert outcome.mean_confidence == pytest.approx(92.0)
    assert not outcome.looks_weak
    assert outcome.warnings == ()


def test_local_ocr_requires_the_engine() -> None:
    deps = _Deps(tesseract_ready=lambda: False)
    with pytest.raises(DocConvertError) as excinfo:
        convert_with_local_ocr(Path("photo.png"), deps=deps)
    assert "not installed" in str(excinfo.value)


def test_weak_ocr_result_is_flagged_for_review() -> None:
    deps = _Deps(
        ocr_image=lambda path, lang: _fake_ocr("blurry\n", 35.0),
        tesseract_ready=lambda: True,
    )
    outcome = convert_with_local_ocr(Path("photo.jpg"), deps=deps)
    assert outcome.looks_weak
    assert any("low" in warning for warning in outcome.warnings)


def test_pdf_ocr_adds_page_delimiters_and_mean_confidence(tmp_path: Path) -> None:
    def _render(path: Path, work_dir: Path) -> list[Path]:
        images = []
        for number in (1, 2):
            image = work_dir / f"page-{number}.png"
            image.write_bytes(b"png")
            images.append(image)
        return images

    deps = _Deps(
        ocr_image=lambda path, lang: _fake_ocr(f"Text of {path.stem}.\n", 90.0),
        pdf_page_images=_render,
        tesseract_ready=lambda: True,
    )
    outcome = convert_with_local_ocr(tmp_path / "scan.pdf", deps=deps)
    assert outcome.page_count == 2
    assert "<!-- Page 1 -->" in outcome.text
    assert "<!-- Page 2 -->" in outcome.text
    assert outcome.mean_confidence == pytest.approx(90.0)


def test_pdf_ocr_honors_cancellation(tmp_path: Path) -> None:
    def _render(path: Path, work_dir: Path) -> list[Path]:
        image = work_dir / "page-1.png"
        image.write_bytes(b"png")
        return [image]

    deps = _Deps(
        ocr_image=lambda path, lang: _fake_ocr("x\n", 90.0),
        pdf_page_images=_render,
        tesseract_ready=lambda: True,
    )
    with pytest.raises(DocConvertCancelled):
        convert_with_local_ocr(tmp_path / "scan.pdf", deps=deps, cancel_requested=lambda: True)


def test_unsupported_extension_is_rejected_clearly() -> None:
    with pytest.raises(DocConvertError):
        convert_document(Path("archive.zip"), deps=_Deps())


def test_outcome_defaults_are_safe() -> None:
    outcome = ConversionOutcome(text="", tier=TIER_MARKITDOWN, source=Path("x.docx"))
    assert not outcome.looks_weak
    assert outcome.warnings == ()
    assert outcome.low_confidence == ()
    assert outcome.provider == ""


def test_local_ocr_flags_low_confidence_lines_for_review() -> None:
    def _mixed(path: Path, lang: str) -> OcrResult:
        return OcrResult(
            text="Clear line\nblurry line\n",
            engine="tesseract",
            lines=[
                OcrLine(text="Clear line", confidence=95.0),
                OcrLine(text="blurry line", confidence=31.0),
            ],
        )

    deps = _Deps(ocr_image=_mixed, tesseract_ready=lambda: True)
    outcome = convert_with_local_ocr(Path("photo.png"), deps=deps)
    assert outcome.low_confidence == ("Page 1: [31%] blurry line",)


def test_cloud_wrapper_adapts_the_datalab_result() -> None:
    class _Result:
        content = "# Cloud rescued\n"
        page_count = 7

    captured: dict[str, object] = {}

    def _fake_cloud(path, **kwargs):
        captured.update(kwargs, path=path)
        return _Result()

    from quill.io.docconvert import TIER_CLOUD_OCR, convert_with_cloud_ocr

    outcome = convert_with_cloud_ocr(
        Path("scan.pdf"),
        cloud_convert=_fake_cloud,
        endpoint="https://www.datalab.to",
        mode="accurate",
        output_format="markdown",
    )
    assert outcome.tier == TIER_CLOUD_OCR
    assert outcome.provider == "datalab"
    assert outcome.text == "# Cloud rescued\n"
    assert outcome.page_count == 7
    assert captured["mode"] == "accurate"
