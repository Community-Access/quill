"""Native header/footer export (#892 follow-up): real DOCX parts, real RTF groups.

The Header/Footer Builder spec previously only drew at print time; these tests
pin that a save now writes it into the file itself — a live Word PAGE field
(never a frozen number), the three-zone tabbed layout, the Roman/start page
numbering, and the different-first-page split — and that a blank spec (or any
export failure) leaves the save untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.header_footer import HeaderFooterSpec, PageNumberStyle
from quill.io.header_footer_export import inject_rtf_header_footer, spec_has_content
from quill.io.rtf import markdown_to_rtf

_CTX = {"title": "Report", "filename": "report.rtf", "date": "2026-07-11"}


def test_spec_has_content_distinguishes_blank_from_real() -> None:
    assert spec_has_content(None) is False
    assert spec_has_content(HeaderFooterSpec()) is False
    assert spec_has_content(HeaderFooterSpec(footer_right="{page}")) is True
    assert spec_has_content(HeaderFooterSpec(first_page_header_center="x")) is True


def test_rtf_injection_writes_header_footer_groups_with_live_page_field() -> None:
    rtf = markdown_to_rtf("Body text")
    spec = HeaderFooterSpec(header_left="{title}", footer_right="Page {page}")
    out = inject_rtf_header_footer(rtf, spec, **_CTX)
    assert "{\\header" in out and "{\\footer" in out
    assert "Report" in out
    # The page number is a live field, never a frozen digit.
    assert "{\\field{\\*\\fldinst PAGE}}" in out
    # Injected into the preamble, before the body.
    assert out.index("{\\header") < out.index("Body text")
    # The document still opens/parses as RTF (round-trip smoke).
    from quill.io.rtf import rtf_to_markdown

    assert "Body text" in rtf_to_markdown(out)


def test_rtf_injection_carries_first_page_and_numbering_controls() -> None:
    rtf = markdown_to_rtf("Body")
    spec = HeaderFooterSpec(
        footer_center="{page}",
        first_page_different=True,
        first_page_footer_center="cover",
        page_number_style=PageNumberStyle.ROMAN,
        start_page_number=3,
    )
    out = inject_rtf_header_footer(rtf, spec, **_CTX)
    assert "\\titlepg" in out
    assert "{\\footerf" in out and "cover" in out
    assert "\\pgnlcrm" in out
    assert "\\pgnstarts3" in out


def test_rtf_injection_is_a_no_op_for_blank_spec_or_odd_input() -> None:
    rtf = markdown_to_rtf("Body")
    assert inject_rtf_header_footer(rtf, None, **_CTX) == rtf
    assert inject_rtf_header_footer(rtf, HeaderFooterSpec(), **_CTX) == rtf
    junk = "not an rtf document"
    assert inject_rtf_header_footer(junk, HeaderFooterSpec(footer_left="x"), **_CTX) == junk


def test_write_rtf_document_injects_the_saved_spec(tmp_path: Path, monkeypatch) -> None:
    from quill.core.document import Document
    from quill.io.rtf import write_rtf_document

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    target = tmp_path / "report.rtf"
    from quill.core.header_footer_store import HeaderFooterStore, key_for

    store = HeaderFooterStore.load()
    store.set(key_for(target), HeaderFooterSpec(footer_right="{page}"))

    document = Document(text="Hello", path=target)
    write_rtf_document(document, target)
    saved = target.read_text(encoding="cp1252")
    assert "{\\footer" in saved and "PAGE" in saved


def test_docx_export_writes_real_header_footer_parts(tmp_path: Path, monkeypatch) -> None:
    docx = pytest.importorskip("docx")
    from quill.core.document import Document
    from quill.core.header_footer_store import HeaderFooterStore, key_for
    from quill.io.docx_writer import write_docx

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    target = tmp_path / "report.docx"
    store = HeaderFooterStore.load()
    store.set(
        key_for(target),
        HeaderFooterSpec(
            header_left="{title}",
            footer_right="Page {page}",
            page_number_style=PageNumberStyle.ROMAN,
            start_page_number=2,
        ),
    )
    write_docx(Document(text="Hello world", path=target), target)

    saved = docx.Document(str(target))
    section = saved.sections[0]
    header_text = "\n".join(p.text for p in section.header.paragraphs)
    assert "report" in header_text  # {title} = the filename stem, as at print time
    footer_xml = section.footer.paragraphs[0]._p.xml
    assert "PAGE" in footer_xml and "fldSimple" in footer_xml
    assert "ROMAN" in footer_xml
    sect_xml = section._sectPr.xml
    assert "lowerRoman" in sect_xml and 'w:start="2"' in sect_xml


def test_docx_export_without_a_spec_stays_clean(tmp_path: Path, monkeypatch) -> None:
    docx = pytest.importorskip("docx")
    from quill.core.document import Document
    from quill.io.docx_writer import write_docx

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    target = tmp_path / "plain.docx"
    write_docx(Document(text="Hello", path=target), target)
    saved = docx.Document(str(target))
    header_text = "".join(p.text for p in saved.sections[0].header.paragraphs)
    assert header_text.strip() == ""
