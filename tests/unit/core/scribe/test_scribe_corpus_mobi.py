"""Scribe's Kindle (MOBI) books from Pneuma's corpus open as documents.

Run only with ``QUILL_SCRIBE_CORPUS`` set (``corpus.needs_corpus``). Each book is
copied into the test's own folder first, because its pictures are saved beside
it and the corpus is only ever read.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from quill.io.mobi_html import HEADINGS_INFERRED_NOTE
from quill.io.mobi_open import read_mobi_document
from tests.unit.core.scribe import corpus

pytestmark = corpus.needs_corpus

#: Per book: words its text holds, its first headings by level, its pictures.
EXPECTED: dict[str, tuple[tuple[str, ...], list[str], int]] = {
    corpus.NIST: (
        ("Organizational Profile", "Target Profile"),
        ["# 3. Introduction to CSF Profiles and Tiers", "## 3.1. CSF Profiles"],
        1,
    ),
    corpus.SCAN: (
        ("MAKING BUTTER", "Agricultural Education"),
        ["# .E. Touch HOW TEACHERS MAY USE FARMERS' BULLETIN 876, MAKING BUTTER ON THE FARM"],
        1,
    ),
    corpus.GARDEN: (
        ("Maple Street Community Garden", "two wheelbarrows", "| Day | Morning | Evening |"),
        ["# Community Garden Handbook", "## 1. Getting a plot", "## 2. Garden rules"],
        1,
    ),
    corpus.MATH: (
        ("commutation classes", "symmetric group"),
        ["# ON THE NUMBER OF COMMUTATION CLASSES OF THE LONGEST ELEMENT IN THE SYMMETRIC GROUP"],
        6,
    ),
}


def _opened(tmp_path: Path, stem: str) -> tuple[Path, str, dict[str, object]]:
    source = corpus.output("mobi", stem)
    assert source is not None
    copy = tmp_path / source.name
    shutil.copyfile(source, copy)
    document = read_mobi_document(copy)
    return copy, document.text, document.source_metadata


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_each_book_opens_with_its_text_headings_and_pictures(tmp_path: Path, stem: str) -> None:
    words, headings, picture_count = EXPECTED[stem]
    copy, text, meta = _opened(tmp_path, stem)
    flat = " ".join(text.split())
    for phrase in words:
        assert " ".join(phrase.split()) in flat, phrase
    heading_lines = [line for line in text.splitlines() if line.startswith("#")]
    assert heading_lines[: len(headings)] == headings
    assert meta["headings_inferred"] == len(heading_lines)
    assert meta["open_note"] == HEADINGS_INFERRED_NOTE
    links = re.findall(r"!\[Picture \d+\]\(([^)]+)\)", text)
    assert len(links) == picture_count == meta["picture_count"]
    for link in links:
        picture = copy.parent / link
        assert picture.is_file() and picture.read_bytes()[:3] == b"\xff\xd8\xff"
    assert "language" not in meta  # Scribe says "C", which is no language (F5)
    assert "mbp:" not in text and "filepos" not in text and "recindex" not in text


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_each_book_saves_and_exports_with_headings_and_pictures(tmp_path: Path, stem: str) -> None:
    from quill.io.export import pandoc_export_source, write_document_as
    from quill.io.pandoc import PandocUnavailableError, convert_file_with_pandoc

    copy, text, meta = _opened(tmp_path, stem)
    first_heading = next(line for line in text.splitlines() if line.startswith("# "))[2:]
    out = tmp_path / "saved"
    out.mkdir()
    for suffix in (".md", ".html", ".txt", ".rtf", ".docx"):
        saved = write_document_as(read_mobi_document(copy), out / f"{stem}{suffix}")
        assert saved.stat().st_size > 0
    page = (out / f"{stem}.html").read_text(encoding="utf-8")
    assert "<h1 " in page and page.count("<img ") == meta["picture_count"]
    assert 'alt="Picture 1"' in page
    for link in re.findall(r'<img src="([^"]+)"', page):
        assert (out / link).is_file()  # the pictures came along
    assert first_heading.split()[0] in (out / f"{stem}.rtf").read_text(encoding="latin-1")
    try:
        convert_file_with_pandoc(
            pandoc_export_source(read_mobi_document(copy)),
            out / f"{stem}.epub",
            from_format="gfm+hard_line_breaks",
            to_format="epub",
        )
    except PandocUnavailableError:
        return
    import zipfile

    media = [n for n in zipfile.ZipFile(out / f"{stem}.epub").namelist() if "/media/" in n]
    assert len(media) == meta["picture_count"]
