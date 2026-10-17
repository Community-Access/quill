"""Tests for the free-first document conversion router (PRD §11.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.docconvert import (
    MIN_CHARS_PER_PAGE,
    TIER_LOCAL_OCR,
    TIER_MARKITDOWN,
    TIER_OWN_READER,
    TIER_PDF_TEXT,
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
    # A web page still tries MarkItDown first; Word, Excel, PowerPoint and
    # OpenDocument go to QUILL's own reader first (test_office_reader_order.py).
    deps = _Deps(markitdown=lambda path: "# Converted\n\nBody text.\n")
    outcome = convert_document(Path("report.html"), deps=deps)
    assert outcome.tier == TIER_MARKITDOWN
    assert "Converted" in outcome.text
    assert not outcome.offer_local_ocr


def _pdf_result(text: str, engine: str = "pdfplumber", pages: int = 2, read: int | None = None):
    from quill.io.pdf import PdfExtractionResult

    read = pages if read is None else read
    return PdfExtractionResult(
        text=text,
        quality_score=90 if text.strip() else 0,
        engine=engine,
        page_count=pages if engine in ("pdfplumber", "pypdf") else 0,
        extracted_pages=read,
        page_scores=[90] * read,
    )


def _no_markitdown(path: Path) -> str:
    raise AssertionError("a PDF must never be sent to MarkItDown")


def test_pdf_with_healthy_text_layer_does_not_offer_ocr() -> None:
    deps = _Deps(
        markitdown=_no_markitdown,
        pdf_text=lambda path: _pdf_result("word " * 300),
    )
    outcome = convert_document(Path("manual.pdf"), deps=deps)
    assert outcome.tier == TIER_PDF_TEXT
    assert outcome.page_count == 2
    assert not outcome.offer_local_ocr
    assert not outcome.warnings


def test_scanned_pdf_offers_free_local_ocr() -> None:
    deps = _Deps(
        markitdown=_no_markitdown,
        pdf_text=lambda path: _pdf_result("(No selectable text...)\n", engine="empty"),
        pdf_page_count=lambda path: 12,
    )
    outcome = convert_document(Path("scan.pdf"), deps=deps)
    assert outcome.offer_local_ocr
    assert outcome.text == ""
    assert outcome.page_count == 12
    assert outcome.warnings


def test_a_thin_text_layer_still_offers_ocr() -> None:
    deps = _Deps(pdf_text=lambda path: _pdf_result("Cover page\n", pages=10))
    outcome = convert_document(Path("scan.pdf"), deps=deps)
    assert outcome.offer_local_ocr
    assert "Cover page" in outcome.text


@pytest.mark.parametrize(
    ("engine", "said"),
    [
        ("encrypted", "password-protected"),
        ("damaged", "looks damaged"),
        ("unavailable", "no PDF text reader"),
    ],
)
def test_a_pdf_that_cannot_be_read_says_why_and_what_to_do(engine: str, said: str) -> None:
    deps = _Deps(
        pdf_text=lambda path: _pdf_result("(message)\n", engine=engine),
        pdf_page_count=lambda path: 0,
    )
    with pytest.raises(DocConvertError) as excinfo:
        convert_document(Path("locked.pdf"), deps=deps)
    message = str(excinfo.value)
    assert said in message and "locked.pdf" in message
    assert "MarkItDown" not in message


def test_a_capped_read_says_how_many_pages_came_through() -> None:
    deps = _Deps(pdf_text=lambda path: _pdf_result("word " * 5000, pages=350, read=200))
    outcome = convert_document(Path("big.pdf"), deps=deps)
    assert any("first 200 of 350 pages" in w for w in outcome.warnings)


def test_a_real_pdf_imports_with_markitdown_unimportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shipped runtime, simulated: markitdown's chain cannot import.

    The QuillVille runtime freezes markitdown in but excludes onnxruntime,
    which magika (imported at the top of markitdown) needs, so ``import
    markitdown`` raises. Blocking onnxruntime here reproduces that; the PDF
    must still come through, from its own text, with no MarkItDown involved.
    """
    pypdf = pytest.importorskip("pypdf")
    pytest.importorskip("pdfplumber")
    import sys

    for name in [
        n for n in sys.modules if n == "markitdown" or n.startswith(("markitdown.", "magika"))
    ]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    with pytest.raises(ImportError):
        import markitdown  # noqa: F401

    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    })
    stream = DecodedStreamObject()
    words = " ".join(["accessible"] * 12)
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({words}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf = tmp_path / "born-digital.pdf"
    with pdf.open("wb") as handle:
        writer.write(handle)

    outcome = convert_document(pdf)
    assert outcome.tier == TIER_PDF_TEXT
    assert "accessible" in outcome.text
    assert not outcome.offer_local_ocr


def test_markitdown_missing_is_no_longer_an_error_for_an_office_file() -> None:
    """2026-10-16: MarkItDown missing reads the file with QUILL's own reader."""

    def _missing(path: Path) -> str:
        raise ImportError("markitdown not available")

    corpus = Path(__file__).resolve().parents[2] / "corpus" / "office"
    outcome = convert_born_digital(corpus / "report.docx", deps=_Deps(markitdown=_missing))
    assert outcome.tier == TIER_OWN_READER
    assert "## Highlights" in outcome.text
    assert "QUILL's own Word reader" in outcome.reader


def test_an_unreadable_office_file_is_a_sentence_not_an_install_prompt() -> None:
    def _missing(path: Path) -> str:
        raise ImportError("markitdown not available")

    with pytest.raises(DocConvertError) as excinfo:
        convert_born_digital(Path("no-such-report.docx"), deps=_Deps(markitdown=_missing))
    message = str(excinfo.value)
    assert "no-such-report.docx" in message
    assert "not installed" not in message
    assert "Download Optional Components" not in message


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
