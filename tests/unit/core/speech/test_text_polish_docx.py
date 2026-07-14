"""Richer .docx extraction: tables, footnotes, and header/footer text (§1.2)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from quill.core.speech.text_polish import extract_sections, extract_text

_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _p(text: str, *, heading: bool = False) -> str:
    ppr = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _cell(text: str) -> str:
    return f"<w:tc>{_p(text)}</w:tc>"


def _make_docx(path: Path) -> None:
    document = (
        f"<w:document {_NS}><w:body>"
        + _p("Title Here", heading=True)
        + _p("Body paragraph.")
        + "<w:tbl>"
        + f"<w:tr>{_cell('Name')}{_cell('Age')}</w:tr>"
        + f"<w:tr>{_cell('Alice')}{_cell('30')}</w:tr>"
        + "</w:tbl></w:body></w:document>"
    )
    footnotes = (
        f"<w:footnotes {_NS}>"
        f'<w:footnote w:id="0" w:type="separator">{_p("---")}</w:footnote>'
        f'<w:footnote w:id="1">{_p("A real footnote.")}</w:footnote>'
        "</w:footnotes>"
    )
    header = f"<w:hdr {_NS}>{_p('Running Header')}</w:hdr>"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document)
        zf.writestr("word/footnotes.xml", footnotes)
        zf.writestr("word/header1.xml", header)


def test_extract_text_includes_tables_footnotes_headers(tmp_path: Path) -> None:
    docx = tmp_path / "doc.docx"
    _make_docx(docx)
    text = extract_text(docx)
    assert "Title Here" in text and "Body paragraph." in text
    # Table rows read as "cell, cell".
    assert "Name, Age" in text
    assert "Alice, 30" in text
    # Header text and the real footnote are included; the separator placeholder is not.
    assert "Running Header" in text
    assert "A real footnote." in text
    assert "---" not in text


def test_extract_sections_structures_tables_and_footnote_section(tmp_path: Path) -> None:
    docx = tmp_path / "doc.docx"
    _make_docx(docx)
    sections = extract_sections(docx)
    titles = [s.title for s in sections]
    assert "Title Here" in titles
    assert "Footnotes" in titles  # footnotes become a trailing section
    body = next(s.text for s in sections if s.title == "Title Here")
    assert "Name, Age" in body and "Alice, 30" in body
    notes = next(s.text for s in sections if s.title == "Footnotes")
    assert "A real footnote." in notes
