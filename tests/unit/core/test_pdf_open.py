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


# -- item 28: outline targets, nesting and doubtful pages ---------------------- #


def test_an_outline_entry_lands_on_its_title_inside_the_page() -> None:
    text = "Cover\fIntro text runs on here.\nChapter 2\nBody.\fThird"
    places = outline_places(text, [("Chapter 2", 2)])
    assert places == [("Chapter 2, page 2", text.index("Chapter 2"))]


def test_a_title_mentioned_mid_sentence_is_not_a_reliable_match() -> None:
    # Only a title that starts a line counts; a mention inside prose does not.
    text = "a\fWe come back to the Summary later.\nMore."
    assert outline_places(text, [("Summary", 2)]) == [("Summary, page 2", 2)]


def test_no_match_falls_back_to_the_page_start() -> None:
    text = "one\ftwo\fthree"
    assert outline_places(text, [("Missing", 3)]) == [("Missing, page 3", 8)]
    assert outline_places(text, [("A", 2)]) == [("A, page 2", 4)]  # too short to trust


def test_a_title_is_matched_with_spacing_and_case_forgiven() -> None:
    text = "x\fCHAPTER   two\nbody"
    assert outline_places(text, [("Chapter Two", 2)])[0][1] == 2


def test_duplicate_titles_on_one_page_land_on_successive_matches() -> None:
    text = "p1\fSummary\nfirst\nSummary\nsecond"
    offsets = outline_bookmark_offsets(text, [("Summary", 2), ("Summary", 2)])
    assert offsets == {"Summary": 3, "Summary (2)": text.index("Summary\nsecond")}


def test_nesting_is_said_in_go_to_and_nothing_else() -> None:
    text = "Part One\nChapter 1\fSection 1.1\nbody"
    outline = [("Part One", 1), ("Chapter 1", 1), ("Section 1.1", 2)]
    labels = [label for label, _ in outline_places(text, outline, (1, 2, 3))]
    assert labels == [
        "Part One, page 1",
        "Chapter 1, level 2, page 1",
        "Section 1.1, level 3, page 2",
    ]
    # Triples carry their own level; old pairs with no levels read as before.
    assert outline_places(text, [("Section 1.1", 2, 2)])[0][0] == "Section 1.1, level 2, page 2"
    assert outline_places(text, outline)[1][0] == "Chapter 1, page 1"


def test_the_reader_seam_takes_pairs_or_triples() -> None:
    found = read_pdf_for_open(
        Path("report.pdf"),
        extract=lambda _path, *, password=None: _result(f"{_PAGE}\f{_PAGE}"),
        read_outline=lambda _path, *, password=None: [("A", 1, 1), ("B", 2, 2), ("C", 2)],
    )
    assert found.outline == (("A", 1), ("B", 2), ("C", 2))
    assert found.outline_levels == (1, 2, 1)
    metadata = found.metadata()
    assert metadata["pdf_outline"] == [("A", 1), ("B", 2), ("C", 2)]
    assert metadata["pdf_outline_levels"] == [1, 2, 1]


def test_a_flat_outline_adds_no_levels_key() -> None:
    assert "pdf_outline_levels" not in _read(_PAGE, outline=[("A", 1)]).metadata()


def test_the_provenance_travels_with_the_document() -> None:
    result = _result(f"{_PAGE}\f{_PAGE}")
    result.page_engines = ["pdfplumber", "pypdf"]
    result.page_unreadable = [0, 3]
    found = read_pdf_for_open(
        Path("report.pdf"),
        extract=lambda _path, *, password=None: result,
        read_outline=lambda _path, *, password=None: [],
    )
    metadata = found.metadata()
    assert metadata["page_engines"] == ["pdfplumber", "pypdf"]
    assert metadata["page_unreadable"] == [0, 3]
    assert found.doubtful_pages == [2]


def test_the_doubtful_pages_sentence() -> None:
    from quill.core.pdf_open import doubtful_pages_sentence

    assert doubtful_pages_sentence([]) == ""
    assert doubtful_pages_sentence([3]) == "Page 3 may read poorly."
    assert doubtful_pages_sentence([9, 2, 5]) == "Pages 2, 5 and 9 may read poorly."
    assert doubtful_pages_sentence(range(1, 12)) == (
        "11 pages may read poorly, starting with page 1."
    )


def test_the_open_summary_says_which_pages_may_read_poorly() -> None:
    found = PdfOpen(
        text="x",
        engine="pdfplumber",
        page_count=3,
        page_scores=(100, 12, 100),
        page_engines=("pdfplumber", "pypdf", "pdfplumber"),
    )
    assert opened_summary(found) == (
        "Opened as text, 3 pages. Page 2 may read poorly. "
        "Saving makes a new file; the PDF is not changed."
    )
