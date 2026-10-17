r"""A Word document through the real Rich Edit control, saved three times.

Both editors edit a ``.docx`` the same way (``quill.core.docx_open``): Word ->
RichDocument -> RTF -> the native rich control -> RTF -> RichDocument -> Word.
A fake control cannot see what the real one writes, and the real one is where
the 2026-10-17 bugs were:

* it writes a heading's ``\b\fsN`` *before* its ``\outlinelevel``, so the RTF
  reader took the heading's own bold and ladder size for authored formatting;
  on the second save Heading 5 (11.5 pt, read back as 11) fell off the ladder
  and came back from Word as bold Normal text;
* it ends its RTF with a paragraph mark of its own, so every save added one
  blank paragraph at the end of the document.

Skips where the native control is not (no Windows, no comtypes). It creates the
control in a hidden frame and sends no input.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

docx = pytest.importorskip("docx")


@pytest.fixture()
def wrapper(wx_session_app):
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    frame = wx.Frame(None)
    control = create_richedit_rtf(wx, frame, wx.TE_MULTILINE)
    surface = getattr(control, "quill_richedit", None)
    if surface is None or not surface.rtf_available():
        frame.Destroy()
        pytest.skip("no native Rich Edit / TOM on this build")
    surface.set_text_mode("rich")
    yield surface
    frame.Destroy()
    wx_session_app.Yield()


def _document(path: Path) -> Path:
    document = docx.Document()
    for level in range(1, 7):
        document.add_heading(f"Level {level}", level=level)
    paragraph = document.add_paragraph("Body with ")
    paragraph.add_run("bold").bold = True
    table = document.add_table(rows=2, cols=2)
    for (row, col), text in {(0, 0): "Name", (0, 1): "Age", (1, 0): "Ann", (1, 1): "40"}.items():
        table.cell(row, col).text = text
    document.add_paragraph("After the table")
    document.save(str(path))
    return path


def test_every_heading_level_and_the_table_survive_three_saves(wrapper, tmp_path: Path) -> None:
    from quill.core import docx_open

    path = _document(tmp_path / "levels.docx")
    for _save in range(3):
        wrapper.set_rtf(docx_open.read_docx_as_rtf(path).encode("utf-8"))
        rtf = bytes(wrapper.get_rtf()).decode("latin-1")
        path.write_bytes(docx_open.rtf_to_docx_bytes(rtf))
    reopened = docx.Document(str(path))
    paragraphs = [(p.style.name, p.text) for p in reopened.paragraphs]
    assert paragraphs[:6] == [(f"Heading {n}", f"Level {n}") for n in range(1, 7)]
    assert paragraphs[-1] == ("Normal", "After the table"), "no blank paragraphs grew"
    # A heading's bold and size are its style's, not direct formatting.
    for paragraph in reopened.paragraphs[:6]:
        assert all(run.bold is None and run.font.size is None for run in paragraph.runs)
    body = reopened.paragraphs[6]
    assert [(run.text, run.bold) for run in body.runs] == [("Body with ", None), ("bold", True)]
    rows = [[cell.text for cell in row.cells] for row in reopened.tables[0].rows]
    assert rows == [["Name", "Age"], ["Ann", "40"]]
