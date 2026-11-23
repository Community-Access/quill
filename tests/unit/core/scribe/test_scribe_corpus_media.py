"""Scribe for Documents' braille, audio and DAISY on real Scribe output.

BRF: the braille view opens every file at its real size (40 by 25,
and 32 by 25 for the large-print variant), form feeds end its pages, case is
ignored, the tab in source 3 and the UTF-8 bytes in source 4 are flagged and
kept, never dropped (F4), the braille code is named EBAE, and the validation
and proofing tools run on every file.

MP3 and DAISY (``QUILL_SCRIBE_CORPUS``): the MP3's length matches Pneuma's
check to within a second; the DAISY book unpacks into its own folder, opens
from ``dtb.ncx`` with its chapters, and is not stopped by its missing pictures
or its ``Z39.86-2002`` label (F3).
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from quill.core.brf_ascii import detect_cell_width
from quill.core.brf_document import BRFDocument
from quill.core.brf_page_map import build_page_map
from quill.core.brf_validator import KIND_NON_BRF_ASCII, validate_brf
from quill.io.open_read import read_open_document
from tests.unit.core.scribe import corpus

pytestmark = corpus.needs_corpus

BRAILLE = [*corpus.SOURCES, f"{corpus.NIST}-large-print"]


def _open(stem: str) -> tuple[bytes, object]:
    path = corpus.output("brf", stem)
    raw = path.read_bytes()
    doc, _book = read_open_document(path, ".brf")
    return raw, doc


# --------------------------------------------------------------------- BRF


@pytest.mark.parametrize("stem", BRAILLE)
def test_the_braille_view_opens_every_brf_at_its_size(stem: str) -> None:
    raw, doc = _open(stem)
    meta = doc.source_metadata  # type: ignore[attr-defined]
    facts = corpus.validation("brf", stem)
    assert meta["source_kind"] == "brf"
    assert meta["brf_cell_width"] == facts["max_cells"] == (32 if "large" in stem else 40)
    assert meta["brf_line_height"] == 25
    assert meta["brf_form_feed_count"] == facts["form_feeds"]
    # Nothing is lost: the text is the file, byte for byte.
    assert doc.text.encode("utf-8") == raw  # type: ignore[attr-defined]


@pytest.mark.parametrize("stem", BRAILLE)
def test_form_feeds_end_the_pages(stem: str) -> None:
    _raw, doc = _open(stem)
    text = doc.text  # type: ignore[attr-defined]
    page_map = build_page_map(BRFDocument.from_text_and_suffix(text, "brf"), mode="form_feed")
    with_text = [p for p in page_map.pages if text[p.start_offset : p.end_offset].strip()]
    assert len(with_text) == corpus.validation("brf", stem)["form_feeds"]
    assert all(p.has_form_feed for p in with_text)
    lines = [len(text[p.start_offset : p.end_offset].split("\r\n")) - 1 for p in with_text]
    assert max(lines) <= 25


@pytest.mark.parametrize("stem", [corpus.NIST, corpus.SCAN, f"{corpus.NIST}-large-print"])
def test_lowercase_braille_is_not_flagged(stem: str) -> None:
    raw, doc = _open(stem)
    assert any(b in raw for b in b"abcdefghijklmnopqrstuvwxyz")  # Scribe writes lowercase
    meta = doc.source_metadata  # type: ignore[attr-defined]
    assert meta["brf_non_ascii_count"] == 0 and meta["brf_tab_count"] == 0
    assert validate_brf(doc.text) == []  # type: ignore[attr-defined]


def test_the_tab_in_source_3_is_flagged_and_kept() -> None:
    raw, doc = _open(corpus.GARDEN)
    meta = doc.source_metadata  # type: ignore[attr-defined]
    assert meta["brf_tab_count"] == raw.count(b"\t") > 0
    assert all(doc.text[i] == "\t" for i in meta["brf_tab_offsets"])  # type: ignore[attr-defined]
    warnings = validate_brf(doc.text)  # type: ignore[attr-defined]
    assert len(warnings) == raw.count(b"\t")
    assert {w.kind for w in warnings} == {KIND_NON_BRF_ASCII}
    assert warnings[0].message == (
        "Tab character: not a braille cell, so it shows as blank space of no fixed width. "
        "Replace it with spaces."
    )
    assert meta["brf_unshown_count"] == len(warnings)  # the open count agrees


def test_the_utf8_bytes_in_source_4_are_flagged_and_kept() -> None:
    raw, doc = _open(corpus.MATH)
    assert b"\xc2\xb4" in raw
    meta = doc.source_metadata  # type: ignore[attr-defined]
    assert meta["brf_non_ascii_count"] == raw.count(b"\xc2\xb4")
    assert doc.encoding == "utf-8"  # type: ignore[attr-defined]  # saved back as it came
    warnings = validate_brf(doc.text)  # type: ignore[attr-defined]
    assert [w.message for w in warnings] == ["Character ´ (U+00B4) is not valid braille ASCII."] * (
        raw.count(b"\xc2\xb4")
    )


def test_the_open_sentence_says_once_what_is_not_braille() -> None:
    from quill.core.brf_progress import format_open_announcement, unshown_count

    _raw, doc = _open(corpus.GARDEN)
    count = unshown_count(doc.source_metadata)  # type: ignore[attr-defined]
    said = format_open_announcement(
        page_count=3, restored=False, braille_page=1, line=1, cell=1, print_page="", unshown=count
    )
    assert said == (
        f"BRF file opened. 3 braille pages detected. {count} characters are not braille cells; "
        "Validate BRF Layout lists them."
    )
    one = format_open_announcement(
        page_count=1, restored=False, braille_page=1, line=1, cell=1, print_page="", unshown=1
    )
    assert one.endswith("1 character is not a braille cell; Validate BRF Layout lists it.")
    clean = format_open_announcement(
        page_count=1, restored=False, braille_page=1, line=1, cell=1, print_page=""
    )
    assert clean == "BRF file opened. 1 braille page detected."


def test_a_plain_brf_keeps_the_usual_width() -> None:
    assert detect_cell_width("short\r\nlines\r\n\x0c") == 40
    one_page = "x" * 30 + "\r\n" + " " * 27 + "#a\r\n\x0c"
    assert detect_cell_width(one_page) == 40  # one page is not enough to tell


def test_scribes_braille_code_is_named_ebae() -> None:
    from quill.core.braille_detect import CANDIDATE_TABLES

    labels = dict(CANDIDATE_TABLES)
    table = "en-us-g2.ctb".removesuffix(".ctb")  # the corpus README's table
    assert "EBAE" in labels[table] and "UEB" not in labels[table]


@pytest.mark.parametrize("stem", BRAILLE)
def test_the_proofing_tools_run_on_every_brf(stem: str) -> None:
    from quill.core.brf_proofing import export_report, mark_proofed, progress_summary
    from quill.core.brf_sidecar import BRFSidecar

    _raw, doc = _open(stem)
    pages = corpus.validation("brf", stem)["form_feeds"]
    sidecar = BRFSidecar()
    mark_proofed(sidecar, 1)
    assert "1 page proofed." in progress_summary(sidecar, page_count=pages, current_page=1)
    report = export_report(sidecar, document_name=f"{stem}.brf", page_count=pages)
    assert f"Braille pages: {pages}" in report


# ----------------------------------------------------------- MP3 and DAISY


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_the_mp3_length_matches_pneumas_check(stem: str) -> None:
    from quill.core.speech.book_file import BookReadError, read_book

    folder = corpus.require_full()
    try:
        book = read_book(folder / "mp3" / f"{stem}.mp3")
    except BookReadError as error:
        pytest.skip(f"this computer cannot read MP3 lengths: {error}")
    expected = corpus.validation("mp3", stem)["seconds"]
    assert abs(book.total_ms / 1000 - expected) <= 1.0


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_the_daisy_book_opens_from_its_ncx_with_chapters(stem: str, tmp_path: Path) -> None:
    from quill.core.media import parse_ncx, resolve_heading_times
    from quill.core.scribe.results import daisy_entry

    folder = corpus.require_full()
    book = tmp_path / f"{stem}.zip"
    shutil.copyfile(folder / "daisy" / f"{stem}-daisy3.zip", book)
    ncx = daisy_entry(book)
    assert ncx is not None and ncx.name == "dtb.ncx"
    assert book.with_suffix("") in ncx.parents  # its own folder, never outside it
    opf = (ncx.parent / "dtb.opf").read_text(encoding="utf-8")
    assert "Z39.86-2002" in opf  # the label Scribe writes; it does not stop the book
    headings = parse_ncx(ncx.read_text(encoding="utf-8"))
    assert len(headings) >= 3

    def smil(name: str) -> str | None:
        found = ncx.parent / name
        return found.read_text(encoding="utf-8") if found.is_file() else None

    timed = resolve_heading_times(headings, smil)
    assert all(h.time_ms is not None and (ncx.parent / h.audio_src).is_file() for h in timed)
    facts = corpus.validation("daisy", stem)
    assert facts["dtbook_images_missing_from_zip"] >= 1  # the pictures it does not carry


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_studio_says_why_scribes_split_book_gives_no_markers(stem: str, tmp_path: Path) -> None:
    """Scribe's DAISY audio is split, one MP3 per section, so its times cannot
    be laid on the one MP3 as they are: Studio writes no markers and the
    result sentence says why, rather than writing wrong ones."""
    from quill.core.scribe.narration import Markers, daisy_chapters
    from quill.core.scribe.results import daisy_entry

    folder = corpus.require_full()
    book = tmp_path / f"{stem}.zip"
    shutil.copyfile(folder / "daisy" / f"{stem}-daisy3.zip", book)
    ncx = daisy_entry(book)
    assert ncx is not None
    chapters, files = daisy_chapters(ncx)
    assert chapters == [] and len(files) > 1
    phrase = Markers(reason=f"the DAISY book has {len(files)} audio files").phrase
    assert phrase == f"with no chapter markers, because the DAISY book has {len(files)} audio files"


def test_a_daisy_zip_never_unpacks_outside_its_folder(tmp_path: Path) -> None:
    from quill.core.scribe.results import daisy_entry

    book = tmp_path / "book.zip"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("../escaped.txt", "no")
        archive.writestr("book/dtb.ncx", "<ncx/>")
    assert daisy_entry(book) == tmp_path / "book" / "book" / "dtb.ncx"
    assert not (tmp_path / "escaped.txt").exists()


@pytest.mark.parametrize("stem", BRAILLE)
def test_the_open_count_is_what_the_validator_lists(stem: str) -> None:
    _raw, doc = _open(stem)
    listed = [w for w in validate_brf(doc.text) if w.kind == KIND_NON_BRF_ASCII]  # type: ignore[attr-defined]
    assert doc.source_metadata["brf_unshown_count"] == len(listed)  # type: ignore[attr-defined]


def test_del_and_vt_are_counted_and_listed_but_unicode_braille_is_not_counted() -> None:
    from quill.core.brf_ascii import count_unshown
    from quill.core.brf_validator import KIND_UNICODE_BRAILLE

    text = ",a\x7fb\x0bc\u2800d\te\r\n\x0cpage two\r\n"
    warnings = validate_brf(text)
    kinds = [w.kind for w in warnings if w.kind in (KIND_NON_BRF_ASCII, KIND_UNICODE_BRAILLE)]
    assert kinds.count(KIND_NON_BRF_ASCII) == 3 == count_unshown(text)  # DEL, VT, tab
    assert kinds.count(KIND_UNICODE_BRAILLE) == 1  # its own finding, not in the count
    messages = [w.message for w in warnings if w.kind == KIND_NON_BRF_ASCII]
    assert "Character U+007F is not valid braille ASCII." in messages
