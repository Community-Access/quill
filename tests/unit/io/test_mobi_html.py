"""Kindle HTML to a document: inferred headings, lists, tables, links, pictures."""

from __future__ import annotations

from quill.io.mobi_html import (
    HEADINGS_INFERRED_NOTE,
    KindleParagraph,
    heading_levels,
    kindle_html_to_markdown,
)


def _p(text: str, size: int | None = None, *, bold: bool = False, **kw: bool) -> KindleParagraph:
    return KindleParagraph(text=text, size=size, bold=bold, **kw)


# ----------------------------------------------------- heading_levels (pure)


def test_the_largest_size_is_heading_one_and_the_rest_follow() -> None:
    paragraphs = [
        _p("Title", 7, bold=True),
        _p("Body text here."),
        _p("Section", 6, bold=True),
        _p("Sub", 5),
        _p("Minor", 4, bold=True),
    ]
    assert heading_levels(paragraphs) == [1, None, 2, 3, 4]


def test_a_book_whose_title_is_size_six_starts_at_heading_one() -> None:
    assert heading_levels([_p("Title", 6), _p("One", 4, bold=True), _p("x")]) == [1, 2, None]


def test_size_four_needs_bold_and_body_sizes_are_never_headings() -> None:
    assert heading_levels([_p("Plain four", 4), _p("Three", 3, bold=True)]) == [None, None]


def test_long_nested_pictured_or_mixed_paragraphs_stay_paragraphs() -> None:
    long = " ".join(["word"] * 21)
    paragraphs = [
        _p(long, 6),
        _p("In a list", 6, nested=True),
        _p("With a picture", 6, has_picture=True),
        _p("Mixed sizes"),  # size None
        _p("", 6),
    ]
    assert heading_levels(paragraphs) == [None] * 5


def test_a_size_most_paragraphs_use_is_body_text() -> None:
    paragraphs = [_p(f"Line {n}", 5) for n in range(8)] + [_p("Title", 7), _p("x")]
    assert heading_levels(paragraphs) == [None] * 8 + [1, None]


def test_more_than_six_sizes_stop_at_heading_six() -> None:
    paragraphs = [_p(f"S{size}", size) for size in range(14, 4, -1)]
    assert heading_levels(paragraphs)[-1] == 6


# -------------------------------------------------- the whole conversion


KINDLE = (
    '<html><head><guide><reference type="toc" filepos=0000000100 /></guide></head><body>'
    '<p height="1em" width="0pt"> <a></a><font size="6"><font color="#17365d">Garden '
    "Handbook</font></font></p>"
    '<p height="3em">How the garden works &amp; why.</p><mbp:pagebreak></mbp:pagebreak>'
    '<p><font size="4"><b>1. Getting a plot</b></font></p>'
    '<ol><li value="1"><p height="1em">Fill in the form.</p></li><a></a>'
    '<li value="2"><p>Pay the fee.</p><p>Or ask.</p></li></ol>'
    "<ul><li><p>Water twice a week.</p></li></ul>"
    '<table><tr><td><p><font size="2"><b>Day</b></font></p></td><td><p><b>Who</b></p></td></tr>'
    "<tr><td><p>Monday</p></td><td><p>Beds 1 to 10</p></td></tr></table>"
    '<p>See the <a href="https://www.usa.gov/"><font color="#0563c1"><u>USA.gov page</u></font>'
    "</a> or <a filepos=0000000042>Fig. 3</a>.</p>"
    '<p><img recindex="00002" width="5"></p>'
    '<p><img recindex="00001" alt="A rain chart"></p>'
    '<p><img recindex="00009"></p>'
    '<p><img recindex="00003" alt="image00012.jpg"></p>'
    "<p>Done.</p><mbp:pagebreak/></body></html>"
)


def _convert(source: str = KINDLE) -> tuple[str, int, list[int]]:
    asked: list[int] = []

    def link(index: int) -> str | None:
        asked.append(index)
        return None if index == 9 else f"pics/picture-{index}.png"

    text, headings = kindle_html_to_markdown(source, link)
    return text, headings, asked


def test_a_kindle_book_reads_as_a_document() -> None:
    text, headings, asked = _convert()
    assert headings == 2
    assert text == (
        "# Garden Handbook\n\n"
        "How the garden works & why.\n\n"
        "## 1. Getting a plot\n\n"
        "1. Fill in the form.\n"
        "2. Pay the fee. Or ask.\n\n"
        "- Water twice a week.\n\n"
        "| Day | Who |\n|---|---|\n| Monday | Beds 1 to 10 |\n\n"
        "See the [USA.gov page](https://www.usa.gov/) or Fig. 3.\n\n"
        "![Picture 1](pics/picture-2.png)\n\n"
        "![A rain chart](pics/picture-1.png)\n\n"
        "![Picture 4](pics/picture-3.png)\n\n"  # a file name is no description
        "Done.\n"
    )
    assert asked == [2, 1, 9, 3]  # a picture the book does not have is left out


def test_real_headings_mean_nothing_is_inferred() -> None:
    text, headings, _asked = _convert('<h2>Real</h2><p><font size="7">Big</font></p>')
    assert headings == 0
    assert text == "## Real\n\nBig\n"


def test_a_heading_paragraph_never_closed_ends_at_the_next_block() -> None:
    text, headings, _asked = _convert(
        '<p><font size="6">Title</font><p>Body one.</p><p>Body two.</p>'
    )
    assert headings == 1
    assert text == "# Title\n\nBody one.\n\nBody two.\n"


def test_a_table_without_a_bold_first_row_keeps_its_rows() -> None:
    text, _h, _a = _convert("<table><tr><td>a</td><td>b</td></tr></table>")
    assert text == "|  |  |\n|---|---|\n| a | b |\n"


def test_the_note_is_one_sentence_said_once() -> None:
    assert HEADINGS_INFERRED_NOTE.endswith(".") and HEADINGS_INFERRED_NOTE.count(". ") == 0
