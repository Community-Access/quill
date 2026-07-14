from __future__ import annotations

import sys
import types
from pathlib import Path

from quill.core.navigation import page_starts
from quill.io import pdf as pdf_module
from quill.io.pdf import PdfExtractionResult, _score_pdf_text, format_pdf_document


def test_score_pdf_text_rewards_real_extraction() -> None:
    assert _score_pdf_text("Hello world" * 20, 2, 2) > _score_pdf_text("", 2, 0)


def test_format_pdf_document_uses_extraction_metadata(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "quill.io.pdf.extract_pdf_text",
        lambda _path: PdfExtractionResult(
            text="Extracted PDF text\n",
            quality_score=72,
            engine="pypdf",
            page_count=1,
            extracted_pages=1,
            page_scores=[72],
        ),
    )

    formatted = format_pdf_document(pdf_path)

    assert "Engine: pypdf" in formatted
    assert "Quality score: 72/100" in formatted
    assert "Extracted PDF text" in formatted


def test_pypdf_extraction_caps_pages_so_a_huge_pdf_cannot_materialize_every_page(
    monkeypatch, tmp_path: Path
) -> None:
    extracted_indices: list[int] = []

    class _StubPage:
        def __init__(self, index: int) -> None:
            self._index = index

        def extract_text(self) -> str:
            extracted_indices.append(self._index)
            return f"page {self._index} text"

    class _LazyPages:
        def __init__(self, total: int) -> None:
            self._total = total

        def __len__(self) -> int:
            return self._total

        def __iter__(self):
            for index in range(self._total):
                yield _StubPage(index)

    class _StubReader:
        def __init__(self, _path: str) -> None:
            self.pages = _LazyPages(100_000)

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _StubReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module._extract_with_pypdf(tmp_path / "huge.pdf")

    assert result.page_count == 100_000
    assert len(extracted_indices) == pdf_module._PDF_MAX_PAGES
    assert result.extracted_pages == pdf_module._PDF_MAX_PAGES


def test_malformed_pdf_returns_empty_text_not_crash(monkeypatch, tmp_path: Path) -> None:
    # M-10: a corrupt PDF that raises a non-ModuleNotFoundError exception in
    # _extract_with_pdfplumber must fall through to _extract_with_pypdf (or the
    # unavailable fallback) rather than propagating the exception to the caller.
    import sys
    import types

    # Make pdfplumber raise a realistic parse error (PDFSyntaxError-style).
    class _FakePdfPlumber:
        @staticmethod
        def open(_path: str) -> object:
            raise ValueError("malformed cross-reference table")

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = _FakePdfPlumber.open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    # Also stub pypdf so it reports "no text" cleanly.
    class _EmptyReader:
        def __init__(self, _path: str) -> None:
            self.pages: list[object] = []

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _EmptyReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module.extract_pdf_text(tmp_path / "corrupt.pdf")
    # Must not raise; the unavailable message or empty text is acceptable.
    assert isinstance(result.text, str)


def test_extract_pdf_text_distinguishes_missing_extractor_from_scanned_pdf(
    monkeypatch, tmp_path: Path
) -> None:
    # #909: no extractor installed vs. an extractor that ran but found no text
    # (scanned/image PDF) are different problems with different remedies, so they
    # must produce different engine tags and messages.
    def _absent(_path: Path) -> object:
        raise ModuleNotFoundError("no module")

    def _empty(_path: Path) -> PdfExtractionResult:
        return PdfExtractionResult(
            text="",
            quality_score=0,
            engine="pypdf",
            page_count=1,
            extracted_pages=0,
            page_scores=[],
        )

    # Both extractors absent -> "not installed" remedy.
    monkeypatch.setattr(pdf_module, "_extract_with_pdfplumber", _absent)
    monkeypatch.setattr(pdf_module, "_extract_with_pypdf", _absent)
    missing = pdf_module.extract_pdf_text(tmp_path / "doc.pdf")
    assert missing.engine == "unavailable"
    assert "not" in missing.text.lower() and "install" in missing.text.lower()

    # An extractor ran but found nothing -> point at OCR, not reinstalling.
    monkeypatch.setattr(pdf_module, "_extract_with_pdfplumber", _empty)
    monkeypatch.setattr(pdf_module, "_extract_with_pypdf", _empty)
    scanned = pdf_module.extract_pdf_text(tmp_path / "scan.pdf")
    assert scanned.engine == "empty"
    assert "ocr" in scanned.text.lower()


def test_encrypted_pdf_reports_encrypted_not_scanned(monkeypatch, tmp_path: Path) -> None:
    # #58: a password-protected PDF must be reported as encrypted (supply/remove
    # the password), not as scanned/image-only (which would point at OCR).
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: True)

    def _raise(_path: Path) -> PdfExtractionResult:
        raise ValueError("encrypted, password required")

    monkeypatch.setattr(pdf_module, "_extract_with_pdfplumber", _raise)
    monkeypatch.setattr(pdf_module, "_extract_with_pypdf", _raise)

    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf")
    assert result.engine == "encrypted"
    assert "encrypted" in result.text.lower()
    assert "password" in result.text.lower()
    assert "ocr" not in result.text.lower()


def test_damaged_pdf_reports_damaged_not_scanned(monkeypatch, tmp_path: Path) -> None:
    # #58: a corrupt PDF that parse-fails must be reported as damaged (repair /
    # re-export), not as scanned/image-only (OCR).
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: False)

    def _raise(_path: Path) -> PdfExtractionResult:
        raise ValueError("malformed cross-reference table")

    def _empty(_path: Path) -> PdfExtractionResult:
        return PdfExtractionResult(
            text="",
            quality_score=0,
            engine="pypdf",
            page_count=0,
            extracted_pages=0,
            page_scores=[],
        )

    monkeypatch.setattr(pdf_module, "_extract_with_pdfplumber", _raise)
    monkeypatch.setattr(pdf_module, "_extract_with_pypdf", _empty)

    result = pdf_module.extract_pdf_text(tmp_path / "corrupt.pdf")
    assert result.engine == "damaged"
    assert "damaged" in result.text.lower() or "corrupt" in result.text.lower()
    # The damaged message must not point the user at the OCR remedy (the scanned
    # path). It may mention that OCR won't help; it must not instruct OCR.
    assert "choose ocr" not in result.text.lower()
    assert "file > import" not in result.text.lower()


def test_is_encrypted_pdf_false_for_plain_pdf_via_stub(monkeypatch, tmp_path: Path) -> None:
    # A readable (non-encrypted) PDF reads is_encrypted=False -> not encrypted.
    class _PlainReader:
        is_encrypted = False

        def __init__(self, _path: str) -> None: ...

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _PlainReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "plain.pdf") is False


def test_is_encrypted_pdf_true_when_empty_password_fails(monkeypatch, tmp_path: Path) -> None:
    class _LockedReader:
        is_encrypted = True

        def __init__(self, _path: str) -> None: ...

        def decrypt(self, _pw: str) -> int:
            return 0  # no password matched

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _LockedReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "locked.pdf") is True


def test_is_encrypted_pdf_false_when_empty_password_unlocks(monkeypatch, tmp_path: Path) -> None:
    # Permissions-only encryption (empty user password opens it) is readable ->
    # must NOT be reported as encrypted.
    class _EmptyPasswordReader:
        is_encrypted = True

        def __init__(self, _path: str) -> None: ...

        def decrypt(self, _pw: str) -> int:
            return 1  # user password matched

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _EmptyPasswordReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "perm.pdf") is False


def test_is_encrypted_pdf_false_when_pypdf_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pypdf", None)
    assert pdf_module._is_encrypted_pdf(tmp_path / "any.pdf") is False


def test_pdfplumber_extraction_joins_pages_with_form_feed(monkeypatch, tmp_path: Path) -> None:
    class _StubPage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _StubPdf:
        def __init__(self) -> None:
            self.pages = [_StubPage("Page one"), _StubPage("Page two"), _StubPage("Page three")]

        def __enter__(self) -> _StubPdf:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = lambda _path: _StubPdf()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    result = pdf_module._extract_with_pdfplumber(tmp_path / "sample.pdf")

    assert result.text.count("\f") == 2
    assert len(page_starts(result.text)) == 3
    assert result.page_count == 3


def test_pypdf_extraction_joins_pages_with_form_feed(monkeypatch, tmp_path: Path) -> None:
    class _StubPage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _StubReader:
        def __init__(self, _path: str) -> None:
            self.pages = [_StubPage("Page one"), _StubPage("Page two")]

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _StubReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module._extract_with_pypdf(tmp_path / "sample.pdf")

    assert result.text.count("\f") == 1
    assert len(page_starts(result.text)) == 2
