"""Regression: opening a docx with a real Word equation preserves the math as text.

Locks in already-correct behavior (verified empirically against MarkItDown and
Pandoc, both of which convert a native <m:oMath> equation back to readable
LaTeX-ish text) so a future MarkItDown/Pandoc upgrade or engine-default change
cannot silently regress it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("docx")
pytest.importorskip("markitdown")

from quill.io.docx_writer import rich_to_docx_bytes
from quill.io.rtf_model import markdown_to_rich
from quill.io.structured import read_structured_document


def _pandoc_available() -> bool:
    from quill.core.external_tools import get_external_tool_status

    return get_external_tool_status("pandoc").installed


pytestmark = pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")


def _write_math_docx(tmp_path: Path) -> Path:
    """Write a docx whose equation is a real <m:oMath>, not the writer's literal-text fallback."""
    rich = markdown_to_rich("Pythagorean theorem: \\(a^2 + b^2 = c^2\\)\n")
    data = rich_to_docx_bytes(rich)
    path = tmp_path / "math.docx"
    path.write_bytes(data)
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "oMath" in xml, "fixture docx has no real OMML equation to round-trip"
    return path


def test_default_engine_preserves_equation_text(tmp_path: Path) -> None:
    path = _write_math_docx(tmp_path)
    document = read_structured_document(path, docx_engine="auto")
    assert "a" in document.text and "2" in document.text
    assert "Pythagorean theorem" in document.text


def test_pandoc_engine_preserves_equation_text(tmp_path: Path) -> None:
    path = _write_math_docx(tmp_path)
    document = read_structured_document(path, docx_engine="pandoc")
    assert "a" in document.text and "2" in document.text
    assert "Pythagorean theorem" in document.text
