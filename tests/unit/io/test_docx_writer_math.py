"""End-to-end: math text through the native docx writer produces a real equation."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("docx")

from quill.io import docx_writer
from quill.io.rtf_model import markdown_to_rich


def _pandoc_available() -> bool:
    from quill.core.external_tools import get_external_tool_status

    return get_external_tool_status("pandoc").installed


@pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")
def test_inline_math_produces_real_omath(tmp_path: Path) -> None:
    rich = markdown_to_rich("Pythagorean theorem: \\(a^2 + b^2 = c^2\\)\n")
    data = docx_writer.rich_to_docx_bytes(rich)
    out = tmp_path / "math.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "oMath" in xml
    assert "Pythagorean theorem:" in xml


@pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")
def test_display_math_produces_real_omath(tmp_path: Path) -> None:
    rich = markdown_to_rich("$$a^2+b^2=c^2$$\n")
    data = docx_writer.rich_to_docx_bytes(rich)
    out = tmp_path / "math_block.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "oMath" in xml


def test_falls_back_to_literal_text_without_pandoc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a real OMML fragment available, math text stays literal rather than vanishing."""
    monkeypatch.setattr(docx_writer, "omml_fragment_for_latex", lambda *a, **k: None)
    rich = markdown_to_rich("Pythagorean theorem: \\(a^2 + b^2 = c^2\\)\n")
    data = docx_writer.rich_to_docx_bytes(rich)
    out = tmp_path / "fallback.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "oMath" not in xml
    assert "a^2 + b^2 = c^2" in xml


def test_plain_text_unaffected(tmp_path: Path) -> None:
    rich = markdown_to_rich("Just an ordinary paragraph, $5 and all.\n")
    data = docx_writer.rich_to_docx_bytes(rich)
    out = tmp_path / "plain.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "oMath" not in xml
    assert "$5" in xml
