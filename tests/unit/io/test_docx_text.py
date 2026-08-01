"""python-docx Word extraction (#1279).

These build a real .docx with python-docx (a base dependency) and read it back,
so the test exercises the actual OOXML boundary rather than a mocked one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.docx_text import read_docx_text

docx = pytest.importorskip("docx")


def _write_sample(path: Path) -> None:
    document = docx.Document()
    document.add_heading("Chapter One", level=1)
    document.add_paragraph("An ordinary body paragraph.")
    document.add_heading("A Sub Heading", level=2)
    document.add_paragraph("First bullet", style="List Bullet")
    document.add_paragraph("Second bullet", style="List Bullet")
    document.add_paragraph("A numbered item", style="List Number")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Rows"
    table.cell(1, 1).text = "2"
    document.save(str(path))


def test_read_docx_text_renders_headings_lists_and_tables(tmp_path: Path) -> None:
    target = tmp_path / "sample.docx"
    _write_sample(target)

    text = read_docx_text(target)

    assert text is not None
    assert "# Chapter One" in text
    assert "## A Sub Heading" in text
    assert "An ordinary body paragraph." in text
    assert "- First bullet" in text
    assert "- Second bullet" in text
    assert "1. A numbered item" in text
    assert "| Name | Value |" in text
    assert "| --- | --- |" in text
    assert "| Rows | 2 |" in text


def test_read_docx_text_keeps_document_order(tmp_path: Path) -> None:
    target = tmp_path / "ordered.docx"
    _write_sample(target)

    text = read_docx_text(target) or ""
    lines = [line for line in text.splitlines() if line.strip()]

    assert lines[0] == "# Chapter One"
    assert lines.index("## A Sub Heading") < lines.index("- First bullet")
    assert lines.index("- First bullet") < lines.index("| Name | Value |")


def test_read_docx_text_adds_no_banner(tmp_path: Path) -> None:
    # #1279: the extract is the document's own text -- nothing prepended.
    target = tmp_path / "sample.docx"
    _write_sample(target)

    text = read_docx_text(target) or ""

    assert "DOCX Extract" not in text
    assert text.startswith("# Chapter One")


def test_read_docx_text_returns_none_for_an_unreadable_file(tmp_path: Path) -> None:
    # A file python-docx cannot open must degrade to the caller's fallback, not raise.
    target = tmp_path / "broken.docx"
    target.write_bytes(b"PK\x03\x04not really a docx")

    assert read_docx_text(target) is None


def test_read_docx_text_returns_none_for_an_empty_document(tmp_path: Path) -> None:
    target = tmp_path / "empty.docx"
    docx.Document().save(str(target))

    assert read_docx_text(target) is None
