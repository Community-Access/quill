"""Real PDFs through the real reader: the corpus in tests/corpus/pdf.

Every file here was drawn by ``tests/corpus/pdf/build_pdf_corpus.py`` (pypdf
only, Helvetica, a few kilobytes each), so its text, page order and outline are
known exactly. Nothing is mocked: pdfplumber and pypdf read the files, the
repair pipeline runs, the score chooses, and ``quill.core.pdf_open`` resolves
the outline -- the path both editors take on File > Open.

The latency and memory budget at the end is measured against a ceiling, with
the baseline recorded in ``docs/design/2026-10-16-pdf-text-reliability.md``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import time
import tracemalloc
from pathlib import Path

import pytest

pytest.importorskip("pdfplumber")
pytest.importorskip("pypdf")

from quill.core.navigation import page_start_for_number  # noqa: E402
from quill.core.pdf_open import (  # noqa: E402
    opened_summary,
    outline_bookmark_offsets,
    outline_places,
    read_pdf_for_open,
)
from quill.io.docconvert import convert_pdf_text_layer  # noqa: E402
from quill.io.pdf import extract_pdf_text, format_pdf_document  # noqa: E402

CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "pdf"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_pdf_corpus", CORPUS / "build_pdf_corpus.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _page(text: str, number: int) -> str:
    start = page_start_for_number(text, number)
    assert start is not None, f"no page {number}"
    end = text.find("\f", start)
    return text[start : end if end >= 0 else len(text)]


def test_the_corpus_is_all_there_and_small() -> None:
    names = set(_builder().CORPUS)
    on_disk = {path.name for path in CORPUS.glob("*.pdf")}
    assert names == on_disk
    assert all((CORPUS / name).stat().st_size < 8_000 for name in names)


def test_clean_prose_reads_whole_with_numbers_and_identifiers_intact() -> None:
    result = extract_pdf_text(CORPUS / "clean_prose.pdf")
    assert result.page_engines == ["pdfplumber", "pdfplumber"]  # fast path, both pages
    assert result.quality_score == 100
    first = _page(result.text, 1)
    assert first.startswith("Chapter One\nThe committee met on a Tuesday")
    assert "the international exchange added ISBN 978-0-306-40615-7" in first
    assert "1,234 books" in first
    assert _page(result.text, 2).startswith("The second page continues the minutes.")
    assert "4,512.75 pounds" in result.text


def test_two_columns_read_down_each_column_in_turn() -> None:
    text = extract_pdf_text(CORPUS / "two_columns.pdf").text
    assert text.startswith("Flood Report\n")
    left_end = text.index("the volunteers who worked until dawn.")
    right_start = text.index("Repairs to the bridge will begin in spring")
    assert text.index("The river rose slowly through the night") < left_end < right_start
    # The old reader ran the columns together row by row.
    assert "the night Repairs" not in text


def test_numbered_and_bulleted_items_keep_their_own_lines() -> None:
    lines = extract_pdf_text(CORPUS / "numbered_list.pdf").text.splitlines()
    starts = [line[:3] for line in lines]
    assert starts.count("1. ") == 1 and "2. " in starts and "3. " in starts
    assert sum(1 for line in lines if line.startswith("- ")) == 2


def test_letter_spacing_reads_as_words_not_letters() -> None:
    result = extract_pdf_text(CORPUS / "letter_spaced.pdf")
    assert result.text.startswith("CHAPTER ONE\n")
    assert "Wide letters are hard to read" in result.text
    assert "when every one stands alone" in result.text
    # pdfplumber spelled the paragraph out a letter at a time; pypdf won.
    assert result.page_engines == ["pypdf"]


def test_two_long_table_rows_stay_two_rows_with_their_figures() -> None:
    text = extract_pdf_text(CORPUS / "table_rows.pdf").text
    rows = [line for line in text.splitlines() if "distribution centre" in line]
    assert len(rows) == 2
    assert rows[0].split()[-3:] == ["1,250", "18.75", "23,437.50"]
    assert rows[1].split()[-3:] == ["980", "18.75", "18,375.00"]


def test_damaged_encodings_are_kept_and_reported_not_deleted() -> None:
    found = read_pdf_for_open(CORPUS / "damaged_encoding.pdf")
    assert found.page_count == 3 and found.text.count("\f") == 2
    assert found.page_scores[0] < 40  # replacement characters never score 100
    page_two = _page(found.text, 2)
    assert "net bo holds" in page_two  # kept, not "net bo"
    assert found.doubtful_pages == [1, 2]
    assert "Pages 1 and 2 may read poorly." in opened_summary(found)
    assert _page(found.text, 3).startswith("to the timetable")


def test_a_nested_outline_lands_on_each_title_inside_its_page() -> None:
    found = read_pdf_for_open(CORPUS / "nested_outline.pdf")
    text = found.text
    assert [title for title, _page in found.outline] == [
        "Part One",
        "Chapter 1",
        "Summary",
        "Not on the page",
        "Chapter 2",
        "Summary",
    ]
    assert found.outline_levels == (1, 2, 3, 3, 2, 3)
    places = dict(outline_places(text, found.outline, found.outline_levels))
    assert places["Part One, page 1"] == 0
    assert places["Chapter 1, level 2, page 1"] == text.index("\nChapter 1\n") + 1
    page_two = page_start_for_number(text, 2)
    page_three = page_start_for_number(text, 3)
    assert places["Summary, level 3, page 2"] == text.index("Summary", page_two)
    # No reliable match on the page: its start.
    assert places["Not on the page, level 3, page 2"] == page_two
    # "Chapter 2" sits under a long line; it was not swallowed, so it is found.
    assert places["Chapter 2, level 2, page 3"] == text.index("\nChapter 2\n") + 1
    assert places["Summary, level 3, page 3"] == text.index("Summary", page_three)
    # Duplicate titles stay distinct bookmarks at distinct places.
    bookmarks = outline_bookmark_offsets(text, found.outline)
    assert bookmarks["Summary"] != bookmarks["Summary (2)"]
    assert bookmarks["Summary (2)"] == text.index("Summary", page_three)


def test_blank_edge_pages_keep_exact_page_offsets() -> None:
    found = read_pdf_for_open(CORPUS / "blank_edges.pdf")
    assert found.page_count == 3
    assert found.text.startswith("\fThe committee")
    assert page_start_for_number(found.text, 2) == 1
    assert page_start_for_number(found.text, 3) == found.text.rindex("\f") + 1
    assert found.doubtful_pages == []
    assert found.quality_score == 100


def test_a_scanned_page_among_text_pages_is_doubtful_and_keeps_its_place() -> None:
    found = read_pdf_for_open(CORPUS / "mixed_scan.pdf")
    assert found.page_engines == ("pdfplumber", "image-only", "pdfplumber")
    assert found.doubtful_pages == [2]
    assert _page(found.text, 2) == ""
    assert _page(found.text, 3).startswith("to the timetable")
    assert not found.looks_scanned  # some pages have text: OCR stays an offer, not a default


def test_an_encrypted_pdf_opens_only_with_its_password() -> None:
    pytest.importorskip("cryptography", reason="AES needs the cryptography package")
    password = _builder().FIXTURE_PASSWORD
    locked = read_pdf_for_open(CORPUS / "encrypted.pdf")
    assert locked.needs_password and not locked.password_rejected
    wrong = read_pdf_for_open(CORPUS / "encrypted.pdf", password="not-it")
    assert wrong.needs_password and wrong.password_rejected
    opened = read_pdf_for_open(CORPUS / "encrypted.pdf", password=password)
    assert opened.has_text and opened.text.startswith("Private minutes\n")
    assert opened.outline == (("Private minutes", 1),)
    assert password not in repr(opened) and password not in str(opened.metadata())


def test_every_entry_point_reads_the_same_pages() -> None:
    path = CORPUS / "two_columns.pdf"
    opened = read_pdf_for_open(path).text
    assert format_pdf_document(path) == opened
    assert convert_pdf_text_layer(path).text == opened


def test_reading_never_changes_the_pdf() -> None:
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CORPUS.glob("*.pdf")}
    for path in CORPUS.glob("*.pdf"):
        read_pdf_for_open(path)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CORPUS.glob("*.pdf")}
    assert before == after


# -- the budget ---------------------------------------------------------------- #

#: Ceilings, per page, generous for a loaded CI box. Measured on the development
#: machine (see the design note): about 38 ms per clean page and 53 ms per
#: questionable page, against a baseline of 35 and 49.
_CLEAN_MS_PER_PAGE = 250
_QUESTIONABLE_MS_PER_PAGE = 400
#: Peak traced memory for the whole read. The old reader peaked at 429 MB on 200
#: pages because pages were never released; the new one stays under 7 MB.
_PEAK_MB = 48


@pytest.mark.perf
def test_clean_pages_pay_for_one_extractor_and_stay_in_budget(tmp_path: Path) -> None:
    path = _builder().build_long(tmp_path / "long.pdf", 60)
    start = time.perf_counter()
    tracemalloc.start()
    try:
        result = extract_pdf_text(path)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert result.page_engines == ["pdfplumber"] * 60  # every page on the fast path
    assert elapsed_ms / 60 < _CLEAN_MS_PER_PAGE
    assert peak / 1_000_000 < _PEAK_MB


@pytest.mark.perf
def test_questionable_pages_compare_readings_within_budget(tmp_path: Path) -> None:
    path = _builder().build_long(tmp_path / "spaced.pdf", 20, spaced=True)
    start = time.perf_counter()
    result = extract_pdf_text(path)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert set(result.page_engines) == {"pypdf"}  # pdfplumber's letters lost every page
    assert result.quality_score == 100
    assert elapsed_ms / 20 < _QUESTIONABLE_MS_PER_PAGE
