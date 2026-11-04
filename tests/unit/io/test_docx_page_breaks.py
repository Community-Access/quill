"""Word page breaks survive opening, editing and saving.

Ctrl+Enter in Word stores ``<w:br w:type="page"/>`` inside a run, which
python-docx reads as no text at all. Until 2026-11-03 the reader turned every
such break into an empty paragraph, so the first save of a Word document
quietly removed every page break in it.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.io.docx_reader import python_docx_available, read_docx_rich
from quill.io.docx_writer import rich_to_docx_bytes
from quill.io.rtf_model import InlineSpan, RichDocument, RichParagraph, rich_to_rtf, rtf_to_rich

pytestmark = pytest.mark.skipif(not python_docx_available(), reason="python-docx not installed")


def _shape(document: RichDocument) -> list[tuple[str, str]]:
    return [(p.style, p.text()) for p in document.paragraphs]


def test_a_page_break_the_writer_made_reads_back_as_a_page_break(tmp_path: Path) -> None:
    source = RichDocument(
        paragraphs=[
            RichParagraph(spans=[InlineSpan(text="Page one")]),
            RichParagraph(style="pagebreak"),
            RichParagraph(spans=[InlineSpan(text="Page two")]),
        ]
    )
    target = tmp_path / "doc.docx"
    target.write_bytes(rich_to_docx_bytes(source))
    assert _shape(read_docx_rich(target)) == [
        ("paragraph", "Page one"),
        ("pagebreak", ""),
        ("paragraph", "Page two"),
    ]


def test_a_break_inside_a_paragraph_splits_it(tmp_path: Path) -> None:
    import docx
    from docx.enum.text import WD_BREAK

    source = docx.Document()
    paragraph = source.add_paragraph("Before")
    run = paragraph.add_run(" bold")
    run.bold = True
    run.add_break(WD_BREAK.PAGE)
    run.add_text("after")
    target = tmp_path / "split.docx"
    source.save(str(target))

    rich = read_docx_rich(target)
    assert _shape(rich) == [
        ("paragraph", "Before bold"),
        ("pagebreak", ""),
        ("paragraph", "after"),
    ]
    # The run's formatting follows its text to both sides of the break.
    assert rich.paragraphs[0].spans[1].bold
    assert rich.paragraphs[2].spans[0].bold


def test_page_break_before_on_a_paragraph_is_a_break(tmp_path: Path) -> None:
    import docx

    source = docx.Document()
    source.add_paragraph("One")
    source.add_paragraph("Two").paragraph_format.page_break_before = True
    target = tmp_path / "before.docx"
    source.save(str(target))
    assert _shape(read_docx_rich(target)) == [
        ("paragraph", "One"),
        ("pagebreak", ""),
        ("paragraph", "Two"),
    ]


def test_a_word_line_break_is_still_not_a_page_break(tmp_path: Path) -> None:
    import docx

    source = docx.Document()
    run = source.add_paragraph().add_run("line one")
    run.add_break()
    run.add_text("line two")
    target = tmp_path / "line.docx"
    source.save(str(target))
    assert [p.style for p in read_docx_rich(target).paragraphs] == ["paragraph"]


def test_open_edit_and_save_keeps_the_break(tmp_path: Path) -> None:
    """The whole rich-mode path: Word -> RTF for the control -> Word again."""
    source = RichDocument(
        paragraphs=[
            RichParagraph(spans=[InlineSpan(text="Page one")]),
            RichParagraph(style="pagebreak"),
            RichParagraph(spans=[InlineSpan(text="Page two")]),
        ]
    )
    target = tmp_path / "doc.docx"
    target.write_bytes(rich_to_docx_bytes(source))
    rtf = rich_to_rtf(read_docx_rich(target))
    assert "\\page" in rtf
    saved = rich_to_docx_bytes(rtf_to_rich(rtf))
    xml = zipfile.ZipFile(io.BytesIO(saved)).read("word/document.xml").decode("utf-8")
    assert xml.count('w:type="page"') == 1
