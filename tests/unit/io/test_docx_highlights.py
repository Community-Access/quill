"""Highlights in real Word files: read without python-docx, and saved without loss.

Item 39 (2026-10-16). The fixtures are real ``.docx`` packages written by
python-docx -- the same library Word documents meet in QUILL's rich mode -- and
read back by the standard-library reader QUILL Lite and read-extract use.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.core.highlights import align_runs
from quill.io.docx_highlights import read_docx_highlight_runs

docx = pytest.importorskip("docx")
WD = pytest.importorskip("docx.enum.text").WD_COLOR_INDEX


def _word_file(path: Path) -> Path:
    document = docx.Document()
    paragraph = document.add_paragraph("The ")
    paragraph.add_run("budget is final").font.highlight_color = WD.YELLOW
    paragraph.add_run(" unless the ")
    paragraph.add_run("board").font.highlight_color = WD.BRIGHT_GREEN
    paragraph.add_run(" objects.")
    document.add_heading("Risks", 1)
    paragraph = document.add_paragraph()
    paragraph.add_run("Teal ").font.highlight_color = WD.TEAL
    paragraph.add_run("note").font.highlight_color = WD.TEAL
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[1].paragraphs[0].add_run("cell mark").font.highlight_color = WD.PINK
    document.save(str(path))
    return path


def test_runs_come_back_with_colour_words_and_paragraph(tmp_path: Path) -> None:
    runs = read_docx_highlight_runs(_word_file(tmp_path / "plan.docx"))
    assert [(r.colour, r.text) for r in runs] == [
        ("yellow", "budget is final"),
        ("green", "board"),
        ("teal", "Teal note"),  # two runs of one colour are one passage
        ("pink", "cell mark"),
    ]
    assert runs[0].context == "The budget is final unless the board objects."
    assert runs[0].offset == 4


def test_they_land_on_the_text_quill_lite_shows(tmp_path: Path) -> None:
    from quill.io.office_text import read_office_text_preferring_own

    path = _word_file(tmp_path / "plan.docx")
    text = read_office_text_preferring_own(path).text
    placed = align_runs(read_docx_highlight_runs(path), text)
    assert [text[p.start : p.end] for p in placed] == [
        "budget is final",
        "board",
        "Teal note",
        "cell mark",
    ]


def test_a_deleted_tracked_change_is_not_a_passage(tmp_path: Path) -> None:
    body = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p>"
        '<w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>kept</w:t></w:r>'
        '<w:del w:id="1" w:author="a"><w:r><w:rPr><w:highlight w:val="red"/></w:rPr>'
        "<w:delText>gone</w:delText></w:r></w:del>"
        '<w:r><w:rPr><w:highlight w:val="none"/></w:rPr><w:t> plain</w:t></w:r>'
        "</w:p></w:body></w:document>"
    )
    path = tmp_path / "tracked.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", body)
    assert [(r.colour, r.text) for r in read_docx_highlight_runs(path)] == [("yellow", "kept")]


def test_rich_mode_save_and_reopen_keeps_every_colour(tmp_path: Path) -> None:
    """docx -> rich -> RTF -> rich -> docx: the path a rich-mode save takes.

    Before 2026-10-16 the RTF writer dropped teal and pink outright, and the
    Word writer turned every ``#RRGGBB`` value the RTF reader returns into
    yellow.
    """
    from quill.io.docx_reader import read_docx_rich
    from quill.io.docx_writer import rich_to_docx_bytes
    from quill.io.rtf_model import rich_to_rtf, rtf_to_rich

    rich = read_docx_rich(_word_file(tmp_path / "plan.docx"))
    saved = tmp_path / "saved.docx"
    saved.write_bytes(rich_to_docx_bytes(rtf_to_rich(rich_to_rtf(rich))))
    reopened = docx.Document(io.BytesIO(saved.read_bytes()))
    colours = [
        (run.text, run.font.highlight_color)
        for paragraph in reopened.paragraphs
        for run in paragraph.runs
        if run.font.highlight_color is not None
    ]
    assert ("budget is final", WD.YELLOW) in colours
    assert ("board", WD.BRIGHT_GREEN) in colours
    assert any(colour == WD.TEAL for _text, colour in colours)
    assert [(r.colour, r.text) for r in read_docx_highlight_runs(saved)][:3] == [
        ("yellow", "budget is final"),
        ("green", "board"),
        ("teal", "Teal note"),
    ]


def test_a_removed_highlight_is_gone_after_save(tmp_path: Path) -> None:
    from quill.io.docx_reader import read_docx_rich
    from quill.io.docx_writer import rich_to_docx_bytes

    rich = read_docx_rich(_word_file(tmp_path / "plan.docx"))
    for paragraph in rich.paragraphs:
        for span in paragraph.spans:
            if span.text == "board":
                span.highlight = None
    saved = tmp_path / "saved.docx"
    saved.write_bytes(rich_to_docx_bytes(rich))
    assert "board" not in [r.text for r in read_docx_highlight_runs(saved)]
