"""A Kindle book, once open, saves and exports through QUILL's own writers, with
its headings, pictures and their alt text carried through (Jeff, 2026-11-23)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from quill.io.export import pandoc_export_source, write_document_as
from quill.io.mobi_open import absolute_pictures, carry_pictures, read_mobi_document
from tests.unit.io.mobi_fixture import PNG_PIXEL, build_mobi

BOOK = (
    '<p><font size="6"><b>Garden Handbook</b></font></p><p>How it works.</p>'
    '<p><img recindex="00001" alt="A rain chart"></p>'
    '<p><font size="4"><b>Rules</b></font></p><p>Be kind.</p>'
)


@pytest.fixture
def book(tmp_path: Path) -> Path:
    folder = tmp_path / "books"
    folder.mkdir()
    path = folder / "garden.mobi"
    path.write_bytes(build_mobi(BOOK, pictures=(PNG_PIXEL,)))
    return path


def _save(book: Path, tmp_path: Path, suffix: str) -> Path:
    out = tmp_path / "saved"
    out.mkdir(exist_ok=True)
    return write_document_as(read_mobi_document(book), out / f"garden{suffix}")


@pytest.mark.parametrize("suffix", [".md", ".txt"])
def test_markdown_and_text_keep_headings_and_their_pictures(
    book: Path, tmp_path: Path, suffix: str
) -> None:
    saved = _save(book, tmp_path, suffix)
    text = saved.read_text(encoding="utf-8")
    assert text.startswith("# Garden Handbook\n") and "\n## Rules\n" in text
    assert "![A rain chart](garden_pictures/picture-1.png)" in text
    assert (saved.parent / "garden_pictures" / "picture-1.png").read_bytes() == PNG_PIXEL


def test_html_keeps_headings_pictures_and_alt_text(book: Path, tmp_path: Path) -> None:
    saved = _save(book, tmp_path, ".html")
    page = saved.read_text(encoding="utf-8")
    assert '<h1 id="garden-handbook">Garden Handbook</h1>' in page
    assert '<h2 id="rules">Rules</h2>' in page
    assert '<img src="garden_pictures/picture-1.png" alt="A rain chart">' in page
    assert (saved.parent / "garden_pictures" / "picture-1.png").is_file()


def test_word_keeps_headings_and_the_alt_text(book: Path, tmp_path: Path) -> None:
    pytest.importorskip("docx")
    saved = _save(book, tmp_path, ".docx")
    xml = zipfile.ZipFile(saved).read("word/document.xml").decode("utf-8")
    assert "Heading1" in xml and "Heading2" in xml
    assert "Garden Handbook" in xml and "A rain chart" in xml


def test_rich_text_keeps_headings(book: Path, tmp_path: Path) -> None:
    rtf = _save(book, tmp_path, ".rtf").read_text(encoding="latin-1")
    assert "Garden Handbook" in rtf and "\\outlinelevel0" in rtf


def test_save_as_in_the_books_own_folder_copies_nothing(book: Path) -> None:
    document = read_mobi_document(book)
    write_document_as(document, book.with_suffix(".md"))
    assert sorted(p.name for p in book.parent.iterdir()) == [
        "garden.md",
        "garden.mobi",
        "garden_pictures",
    ]


def test_a_folder_that_cannot_be_copied_is_said_not_lost(book: Path, tmp_path: Path) -> None:
    text = read_mobi_document(book).text
    blocked = tmp_path / "out" / "garden_pictures"
    blocked.parent.mkdir()
    blocked.write_text("a file where the folder would go")
    said = carry_pictures(text, book, tmp_path / "out" / "garden.md")
    assert said.startswith("The pictures could not be copied beside garden.md;")
    assert said.endswith(f"they are still in {book.parent / 'garden_pictures'}.")


def test_export_hands_pandoc_the_text_with_absolute_pictures(book: Path) -> None:
    document = read_mobi_document(book)
    source = pandoc_export_source(document)
    assert source.suffix == ".md" and source.parent != book.parent
    picture = (book.parent / "garden_pictures" / "picture-1.png").resolve().as_posix()
    assert source.read_text(encoding="utf-8") == absolute_pictures(document.text, book.parent)
    assert f"![A rain chart](<{picture}>)" in source.read_text(encoding="utf-8")
    shutil.rmtree(source.parent)


def test_an_ordinary_document_exports_from_its_own_file(tmp_path: Path) -> None:
    from quill.core.document import Document

    path = tmp_path / "notes.md"
    assert pandoc_export_source(Document(text="# x", path=path)) == path


@pytest.mark.parametrize(("format_name", "media"), [("epub", "EPUB/media/"), ("docx", "media/")])
def test_pandoc_export_carries_headings_and_pictures(
    book: Path, tmp_path: Path, format_name: str, media: str
) -> None:
    from quill.io.pandoc import PandocUnavailableError, convert_file_with_pandoc

    target = tmp_path / f"garden.{format_name}"
    try:
        convert_file_with_pandoc(
            pandoc_export_source(read_mobi_document(book)),
            target,
            from_format="gfm+hard_line_breaks",
            to_format=format_name,
        )
    except PandocUnavailableError:
        pytest.skip("Pandoc is not installed")
    names = zipfile.ZipFile(target).namelist()
    assert any(media in name for name in names)
    text = " ".join(zipfile.ZipFile(target).read(n).decode("utf-8", "replace") for n in names)
    assert "Garden Handbook" in text and "Rules" in text and "A rain chart" in text
