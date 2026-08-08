from __future__ import annotations

import zipfile
from pathlib import Path

from quill.core.epub import load_epub_book, render_epub_book


def test_load_epub_book_reads_ncx_order(tmp_path: Path) -> None:
    target = tmp_path / "book.epub"
    toc = (
        '<?xml version="1.0"?>'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">'
        "<navMap>"
        '<navPoint id="a">'
        "<navLabel><text>Start</text></navLabel>"
        '<content src="text/ch1.xhtml"/>'
        "</navPoint>"
        "</navMap>"
        "</ncx>"
    )
    chapter = "<html><body><h1>One</h1><p>Hello EPUB</p></body></html>"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("toc.ncx", toc)
        archive.writestr("text/ch1.xhtml", chapter)
    book = load_epub_book(target)
    assert book.chapters[0].title == "Start"
    assert "Hello EPUB" in book.chapters[0].text
    assert book.chapters[0].headings[0].title == "One"
    assert book.chapters[0].headings[0].level == 1


def test_render_epub_book_includes_chapter_titles(tmp_path: Path) -> None:
    target = tmp_path / "book.epub"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", "<html><body><p>First</p></body></html>")
    book = load_epub_book(target)
    report = render_epub_book(book)
    assert "# EPUB:" in report
    assert "## 1." in report


def test_load_epub_book_collects_multiple_headings(tmp_path: Path) -> None:
    target = tmp_path / "headings.epub"
    chapter = "<html><body><h1>Intro</h1><p>Hello</p><h2>Deep Dive</h2><p>More</p></body></html>"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    assert [heading.title for heading in book.chapters[0].headings] == ["Intro", "Deep Dive"]
    assert [heading.level for heading in book.chapters[0].headings] == [1, 2]


def test_true_headings_render_inline_for_single_key_navigation(tmp_path: Path) -> None:
    # Real headings must appear in the rendered body (as Markdown ``#`` lines)
    # so single-key H navigation can walk them -- previously the body was
    # flattened and the headings vanished from the text.
    target = tmp_path / "inline.epub"
    chapter = "<html><body><h1>Intro</h1><p>Hello</p><h2>Deep Dive</h2><p>More</p></body></html>"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    report = render_epub_book(book)
    assert "### Intro" in report  # h1 nested two levels under the ## chapter
    assert "#### Deep Dive" in report
    assert book.chapters[0].headings_inferred is False


def test_headings_inferred_from_class_when_no_true_tags(tmp_path: Path) -> None:
    # A hand-made chapter with no <h1>-<h6> tags: infer headings from class
    # names so navigation and the chapter outline still work.
    target = tmp_path / "inferred.epub"
    chapter = (
        "<html><body>"
        '<p class="chapterTitle">The Beginning</p>'
        "<p>Once upon a time.</p>"
        '<p class="subhead">A Turn</p>'
        "<p>Then things happened.</p>"
        "</body></html>"
    )
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    chapter_out = book.chapters[0]
    assert chapter_out.headings_inferred is True
    assert [h.title for h in chapter_out.headings] == ["The Beginning", "A Turn"]
    assert "The Beginning" in chapter_out.body
    report = render_epub_book(book)
    assert "### The Beginning" in report


def test_headings_inferred_from_standalone_bold_line(tmp_path: Path) -> None:
    target = tmp_path / "bold.epub"
    chapter = (
        "<html><body>"
        "<p><b>A Bold Title</b></p>"
        "<p>An ordinary paragraph of body text that is not a heading.</p>"
        "</body></html>"
    )
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    assert [h.title for h in book.chapters[0].headings] == ["A Bold Title"]
    assert book.chapters[0].headings_inferred is True


def test_long_bold_run_is_not_treated_as_a_heading(tmp_path: Path) -> None:
    target = tmp_path / "emphasis.epub"
    long_bold = (
        "<p><b>This is a very long bold sentence that is clearly emphasis "
        "inside a paragraph and not a short standalone title line</b></p>"
    )
    chapter = f"<html><body>{long_bold}<p>Body.</p></body></html>"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    assert book.chapters[0].headings == ()
    assert book.chapters[0].headings_inferred is False


def test_epub_math_parsing_extracts_mathml(tmp_path: Path) -> None:
    target = tmp_path / "math_mathml.epub"
    chapter = (
        "<html><body>"
        '<p>MathML: <math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<mfrac><mn>1</mn><mn>2</mn></mfrac></math> inside text.</p>"
        "</body></html>"
    )
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    assert "[Math Equation: the fraction 1 over 2]" in book.chapters[0].text


def test_epub_math_parsing_extracts_latex_classes(tmp_path: Path) -> None:
    target = tmp_path / "math_latex_class.epub"
    chapter = (
        '<html><body><p>LaTeX span: <span class="math">x^2 + y^2 = z^2</span>.</p></body></html>'
    )
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    # Since latex2mathml is installed in the test environment, it should convert and speak it:
    assert "[Math Equation: x squared plus y squared equals z squared]" in book.chapters[0].text


def test_epub_math_parsing_extracts_latex_delimiters(tmp_path: Path) -> None:
    target = tmp_path / "math_latex_delimiters.epub"
    chapter = (
        "<html><body><p>Inline: \\( a^2 + b^2 = c^2 \\) and block: $$ x = y $$.</p></body></html>"
    )
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("chapters/one.xhtml", chapter)
    book = load_epub_book(target)
    assert "[Math Equation: a squared plus b squared equals c squared]" in book.chapters[0].text
    assert "[Math Equation: x equals y]" in book.chapters[0].text
