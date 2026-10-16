"""The one PDF open both editors share (quill.core.pdf_open).

Two halves. Fakes for the reader's every outcome -- text, locked, wrong
password, damaged, no reader, no text layer, too little text -- and for OCR on
open with both engines, so none of it needs a real engine. And a few real PDFs
written by pypdf, because the point of the module is that QUILL and QUILL Lite
read *the same file* the same way, and only a real file proves the page breaks
and the outline survive the reader.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import pdf_open
from quill.core.navigation import page_position
from quill.core.pdf_open import (
    ENGINE_OCR,
    PdfOpen,
    ocr_finished_sentence,
    ocr_pdf_for_open,
    ocr_started_sentence,
    opened_summary,
    outline_bookmark_offsets,
    outline_places,
    page_places,
    password_prompt,
    read_pdf_for_open,
    save_refusal,
    scanned_question,
)
from quill.io.docconvert import DocConvertError, _Deps
from quill.io.ocr import OcrLine, OcrResult

_PAGE = "This page has a sentence or two of real words on it, enough to count as text. "


def _result(text: str, *, engine: str = "pdfplumber", pages: int = 2, read: int | None = None):
    return SimpleNamespace(
        text=text,
        engine=engine,
        page_count=pages,
        extracted_pages=pages,
        quality_score=80 if text.strip() else 0,
        page_scores=[80] * (pages if read is None else read),
    )


def _read(text: str, *, outline=(), **kwargs: Any) -> PdfOpen:
    return read_pdf_for_open(
        Path("report.pdf"),
        extract=lambda _path, *, password=None: _result(text, **kwargs),
        read_outline=lambda _path, *, password=None: list(outline),
    )


# -- what the reader found -------------------------------------------------- #


def test_a_text_pdf_opens_with_its_pages_and_outline() -> None:
    text = f"{_PAGE}\f{_PAGE}"
    found = _read(text, outline=[("Introduction", 1), ("Results", 2)])
    assert found.text == text.rstrip() + "\n"
    assert found.page_count == 2
    assert found.outline == (("Introduction", 1), ("Results", 2))
    assert found.has_text and not found.looks_scanned
    assert not found.needs_password and not found.refused


def test_the_metadata_is_what_quills_document_carried_before() -> None:
    found = _read(f"{_PAGE}\f{_PAGE}", outline=[("Introduction", 1)])
    metadata = found.metadata()
    assert metadata["source_kind"] == "pdf"
    assert metadata["engine"] == "pdfplumber"
    assert metadata["page_count"] == 2
    assert metadata["pdf_outline"] == [("Introduction", 1)]
    assert "pdf_outline" not in _read(_PAGE, pages=1).metadata()


def test_a_locked_pdf_asks_and_a_wrong_password_is_told_apart() -> None:
    locked = read_pdf_for_open(
        Path("a.pdf"),
        extract=lambda _p, *, password=None: _result("(locked)", engine="encrypted", pages=0),
        read_outline=lambda _p, *, password=None: [],
    )
    assert locked.needs_password and not locked.password_rejected
    wrong = read_pdf_for_open(
        Path("a.pdf"),
        password="guess",
        extract=lambda _p, *, password=None: _result("(locked)", engine="encrypted", pages=0),
        read_outline=lambda _p, *, password=None: [],
    )
    assert wrong.needs_password and wrong.password_rejected
    # The password went to the reader and nowhere else: not on the result.
    assert "guess" not in repr(wrong)


def test_the_password_reaches_the_reader_and_the_outline() -> None:
    seen: list[str | None] = []

    def extract(_p: Path, *, password: str | None = None):
        seen.append(password)
        return _result(_PAGE, pages=1)

    def outline(_p: Path, *, password: str | None = None):
        seen.append(password)
        return []

    read_pdf_for_open(Path("a.pdf"), password="s3cret", extract=extract, read_outline=outline)
    assert seen == ["s3cret", "s3cret"]


@pytest.mark.parametrize("engine", ["damaged", "unavailable"])
def test_damaged_and_readerless_pdfs_open_nothing(engine: str) -> None:
    found = PdfOpen(text="(It is damaged.)\n", engine=engine)
    assert found.refused and not found.has_text and not found.looks_scanned


def test_no_text_layer_and_too_little_text_both_look_scanned() -> None:
    assert PdfOpen(text="(No selectable text.)\n", engine="empty").looks_scanned
    thin = PdfOpen(text="Cover\fpage 2\f\f\f", engine="pdfplumber", page_count=4)
    assert thin.looks_scanned and thin.has_text
    assert not PdfOpen(text=ENGINE_OCR, engine=ENGINE_OCR).looks_scanned


def test_the_outline_is_not_read_when_the_reader_saw_no_pages() -> None:
    called: list[bool] = []
    read_pdf_for_open(
        Path("a.pdf"),
        extract=lambda _p, *, password=None: _result("", engine="empty", pages=0),
        read_outline=lambda _p, *, password=None: called.append(True) or [],
    )
    assert called == []


# -- where things are -------------------------------------------------------- #


def test_outline_places_land_on_the_page_as_the_text_is_now() -> None:
    text = "one\ftwo\fthree"
    places = outline_places(text, [("Start", 1), ("Middle", 2), ("Gone", 9), ("bad",)])
    assert places == [("Start, page 1", 0), ("Middle, page 2", 4)]
    # An edit above page 2 moves where page 2 starts, and the entry follows.
    edited = "one, longer now\ftwo\fthree"
    assert outline_places(edited, [("Middle", 2)]) == [("Middle, page 2", 16)]


def test_outline_bookmarks_get_unique_names() -> None:
    offsets = outline_bookmark_offsets("a\fb\fc", [("Intro", 1), ("Intro", 2), ("Intro\n 1", 3)])
    assert offsets == {"Intro": 0, "Intro (2)": 2, "Intro 1": 4}


def test_page_places_only_for_real_pages() -> None:
    assert page_places("no pages here") == []
    assert page_places("a\fb\fc") == [("1", 0), ("2", 2), ("3", 4)]
    assert page_position("no pages", 3) is None
    assert page_position("a\fb\fc", 0) == (1, 3)
    assert page_position("a\fb\fc", 3) == (2, 3)
    assert page_position("a\fb\fc", 99) == (3, 3)


# -- OCR on open --------------------------------------------------------------- #


def _fake_pages(count: int):
    def render(_path: Path, work_dir: Path) -> list[Path]:
        return [work_dir / f"page-{n}.png" for n in range(1, count + 1)]

    return render


def test_ocr_on_open_joins_pages_with_form_feeds_using_windows_ocr() -> None:
    read: list[str | None] = []

    def recognize(image: Path, language: str | None) -> OcrResult:
        read.append(language)
        return OcrResult(text=f"Words from {image.stem}\n", engine="windows")

    deps = _Deps(
        tesseract_ready=lambda: False,
        windows_ocr_ready=lambda: True,
        windows_ocr_image=recognize,
        pdf_page_images=_fake_pages(3),
    )
    scanned = PdfOpen(text="(none)", engine="empty", page_count=3, outline=(("Part", 2),))
    found = ocr_pdf_for_open(Path("scan.pdf"), scanned, language="eng", deps=deps)
    assert found.engine == ENGINE_OCR
    assert found.text == "Words from page-1\fWords from page-2\fWords from page-3\n"
    assert found.page_count == 3
    assert found.outline == (("Part", 2),)  # the outline survives the OCR
    assert found.ocr_confidence < 0  # Windows OCR reports none; never made up
    # Windows OCR uses the Windows languages, never Tesseract's "eng".
    assert read == [None, None, None]


def test_ocr_on_open_prefers_tesseract_and_keeps_its_confidence() -> None:
    def tesseract(image: Path, language: str) -> OcrResult:
        return OcrResult(
            text=f"T {image.stem}\n",
            engine="tesseract",
            lines=[OcrLine(text=f"T {image.stem}", confidence=91.0)],
        )

    deps = _Deps(
        tesseract_ready=lambda: True,
        ocr_image=tesseract,
        windows_ocr_ready=lambda: pytest.fail("Windows OCR asked while Tesseract was there"),
        pdf_page_images=_fake_pages(2),
    )
    found = ocr_pdf_for_open(Path("scan.pdf"), PdfOpen(text="", engine="empty"), deps=deps)
    assert found.text == "T page-1\fT page-2\n"
    assert found.ocr_confidence == pytest.approx(91.0)
    assert "confidence 91" in ocr_finished_sentence(found)


def test_ocr_on_open_with_no_engine_says_so_in_a_sentence() -> None:
    deps = _Deps(tesseract_ready=lambda: False, windows_ocr_ready=lambda: False)
    with pytest.raises(DocConvertError, match="No OCR engine is available on this computer"):
        ocr_pdf_for_open(Path("scan.pdf"), PdfOpen(text="", engine="empty"), deps=deps)


# -- what is said ------------------------------------------------------------- #


def test_the_sentences() -> None:
    assert password_prompt("a.pdf", incorrect=False).startswith("a.pdf is password-protected")
    assert password_prompt("a.pdf", incorrect=True).startswith("That password did not open")
    question = scanned_question("scan.pdf", 12, some_text=False)
    assert "(12 pages)" in question and "Nothing is uploaded" in question
    assert "No opens nothing" in question
    assert "No opens the little text" in scanned_question("s.pdf", 1, some_text=True)
    assert "(" not in scanned_question("s.pdf", 0, some_text=False).split("\n")[0]
    assert ocr_started_sentence(1) == "Scanned; reading 1 page with OCR on this computer"
    assert ocr_started_sentence(0) == "Scanned; reading the pages with OCR on this computer"
    summary = opened_summary(
        PdfOpen(text="x", engine="pdfplumber", page_count=3, outline=(("A", 1),))
    )
    assert summary == (
        "Opened as text, 3 pages, 1 outline entry in Go To. "
        "Saving makes a new file; the PDF is not changed."
    )
    truncated = opened_summary(
        PdfOpen(text="x", engine="pdfplumber", page_count=350, page_scores=(1,) * 200)
    )
    assert "the first 200 read" in truncated


def test_quills_save_refusal_is_unchanged_by_moving_to_the_shared_sentence() -> None:
    said = save_refusal(
        "report.pdf", ".pdf", app_name="QUILL", formats="Markdown, Word, HTML, RTF, or text"
    )
    assert said + ", or use File > Export." == (
        "report.pdf was opened as extracted text. QUILL cannot write .pdf files "
        "directly, so saving over the original would destroy it. Choose a new name "
        "and format (Markdown, Word, HTML, RTF, or text), or use File > Export."
    )


# -- real files ----------------------------------------------------------------- #


def _write_pdf(path: Path, pages: list[str], *, outline=(), password: str | None = None) -> Path:
    """A real PDF, text drawn in Helvetica, with an outline and maybe a password."""
    pypdf = pytest.importorskip("pypdf")
    pytest.importorskip("pdfplumber")
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = pypdf.PdfWriter()
    font = writer._add_object(
        DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
    )
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
    for title, number in outline:
        writer.add_outline_item(title, number - 1)
    if password:
        writer.encrypt(password, algorithm="AES-128")
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_a_real_pdf_opens_with_form_feed_pages_and_its_outline(tmp_path: Path) -> None:
    pdf = _write_pdf(
        tmp_path / "two.pdf",
        [f"First page. {_PAGE}", f"Second page. {_PAGE}"],
        outline=[("One", 1), ("Two", 2)],
    )
    found = read_pdf_for_open(pdf)
    assert found.page_count == 2
    assert found.text.count("\f") == 1
    assert found.text.startswith("First page.")
    assert found.outline == (("One", 1), ("Two", 2))
    assert not found.looks_scanned
    assert outline_places(found.text, found.outline)[1][0] == "Two, page 2"


def test_a_real_locked_pdf_opens_only_with_its_password(tmp_path: Path) -> None:
    pytest.importorskip("cryptography", reason="AES needs the cryptography package")
    pdf = _write_pdf(tmp_path / "locked.pdf", [f"Private. {_PAGE}"], password="pw")
    assert read_pdf_for_open(pdf).needs_password
    wrong = read_pdf_for_open(pdf, password="nope")
    assert wrong.needs_password and wrong.password_rejected
    opened = read_pdf_for_open(pdf, password="pw")
    assert opened.has_text and opened.text.startswith("Private.")


def test_the_module_imports_no_wx() -> None:
    source = Path(pdf_open.__file__).read_text(encoding="utf-8")
    assert "import wx" not in source
