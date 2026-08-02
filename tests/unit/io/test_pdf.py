from __future__ import annotations

import sys
import types
from pathlib import Path

from quill.core.navigation import page_starts
from quill.io import pdf as pdf_module
from quill.io.pdf import PdfExtractionResult, _score_pdf_text, format_pdf_document


def test_score_pdf_text_rewards_real_extraction() -> None:
    assert _score_pdf_text("Hello world" * 20, 2, 2) > _score_pdf_text("", 2, 0)


def test_format_pdf_document_returns_text_without_a_banner(monkeypatch, tmp_path: Path) -> None:
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

    # #1279: the extract is the PDF's text and nothing else. Engine, quality
    # score, and page counts live in source_metadata and are reported by the open
    # announcement and the Document Intake Report instead of being prepended to
    # the user's document.
    assert formatted == "Extracted PDF text\n"
    assert "# PDF Extract" not in formatted
    assert "Engine:" not in formatted


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
    def _absent(_path: Path, *, password: str | None = None) -> object:
        raise ModuleNotFoundError("no module")

    def _empty(_path: Path, *, password: str | None = None) -> PdfExtractionResult:
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

    def _raise(_path: Path, *, password: str | None = None) -> PdfExtractionResult:
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

    def _raise(_path: Path, *, password: str | None = None) -> PdfExtractionResult:
        raise ValueError("malformed cross-reference table")

    def _empty(_path: Path, *, password: str | None = None) -> PdfExtractionResult:
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


def test_extract_pdf_text_threads_password_to_pdfplumber(monkeypatch, tmp_path: Path) -> None:
    # #58 follow-up: a supplied password must reach pdfplumber.open so an encrypted
    # PDF unlocks and extracts like any other file.
    seen_passwords: list[str] = []

    class _StubPage:
        def extract_text(self) -> str:
            return "Unlocked page text"

    class _StubPdf:
        def __init__(self) -> None:
            self.pages = [_StubPage()]

        def __enter__(self) -> _StubPdf:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    def _open(_path: str, password: str = "") -> _StubPdf:
        seen_passwords.append(password)
        return _StubPdf()

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = _open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf", password="s3cret")

    assert seen_passwords == ["s3cret"]
    assert result.engine == "pdfplumber"
    assert "Unlocked page text" in result.text


def test_extract_pdf_text_reports_wrong_password_distinctly(monkeypatch, tmp_path: Path) -> None:
    # A wrong password on an encrypted PDF must produce a distinct "not correct"
    # message (so the open flow can re-prompt) while staying engine="encrypted".
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: True)

    def _raise(_path: Path, *, password: str | None = None) -> PdfExtractionResult:
        raise ValueError("bad password")

    monkeypatch.setattr(pdf_module, "_extract_with_pdfplumber", _raise)
    monkeypatch.setattr(pdf_module, "_extract_with_pypdf", _raise)

    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf", password="wrong")
    assert result.engine == "encrypted"
    assert "not correct" in result.text.lower()
    assert "ocr" not in result.text.lower()


def test_extract_with_pypdf_decrypts_with_supplied_password(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    class _StubPage:
        def extract_text(self) -> str:
            return "Decrypted"

    class _LockedReader:
        is_encrypted = True

        def __init__(self, _path: str) -> None:
            self.pages = [_StubPage()]

        def decrypt(self, pw: str) -> int:
            seen.append(pw)
            return 1

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _LockedReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module._extract_with_pypdf(tmp_path / "locked.pdf", password="open-me")

    assert seen == ["open-me"]
    assert "Decrypted" in result.text


class _OutlineDest:
    def __init__(self, title: object) -> None:
        self.title = title


def _install_outline_reader(monkeypatch, reader_cls: type) -> None:
    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = reader_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)


def test_extract_pdf_outline_flattens_tree_and_makes_pages_one_based(
    monkeypatch, tmp_path: Path
) -> None:
    d1 = _OutlineDest("Chapter 1")
    d2 = _OutlineDest("Section 1.1")
    d3 = _OutlineDest("Chapter 2")

    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            # pypdf nests child bookmarks as a sub-list after their parent.
            self.outline = [d1, [d2], d3]
            self._pages = {id(d1): 0, id(d2): 1, id(d3): 5}

        def get_destination_page_number(self, dest: object) -> int:
            return self._pages[id(dest)]

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "book.pdf")
    assert outline == [("Chapter 1", 1), ("Section 1.1", 2), ("Chapter 2", 6)]


def test_extract_pdf_outline_skips_blank_titles_and_unresolvable_dests(
    monkeypatch, tmp_path: Path
) -> None:
    good = _OutlineDest("Intro")
    blank = _OutlineDest("   ")
    broken = _OutlineDest("Broken")

    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            self.outline = [good, blank, broken]

        def get_destination_page_number(self, dest: object) -> int:
            if dest is broken:
                raise ValueError("no destination")
            return 0

    _install_outline_reader(monkeypatch, _Reader)

    assert pdf_module.extract_pdf_outline(tmp_path / "book.pdf") == [("Intro", 1)]


def test_extract_pdf_outline_returns_empty_when_pypdf_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pypdf", None)
    assert pdf_module.extract_pdf_outline(tmp_path / "book.pdf") == []


def test_extract_pdf_outline_decrypts_with_password(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []
    dest = _OutlineDest("Locked Chapter")

    class _Reader:
        is_encrypted = True

        def __init__(self, _path: str) -> None:
            self.outline = [dest]

        def decrypt(self, pw: str) -> int:
            seen.append(pw)
            return 1

        def get_destination_page_number(self, _dest: object) -> int:
            return 2

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "locked.pdf", password="pw")
    assert seen == ["pw"]
    assert outline == [("Locked Chapter", 3)]


def test_extract_pdf_outline_caps_entry_count(monkeypatch, tmp_path: Path) -> None:
    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            count = pdf_module._PDF_MAX_OUTLINE_ENTRIES + 50
            self.outline = [_OutlineDest(f"H{i}") for i in range(count)]

        def get_destination_page_number(self, _dest: object) -> int:
            return 0

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "huge-toc.pdf")
    assert len(outline) == pdf_module._PDF_MAX_OUTLINE_ENTRIES


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
    fake_pdfplumber.open = lambda _path, password="": _StubPdf()  # type: ignore[attr-defined]
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
