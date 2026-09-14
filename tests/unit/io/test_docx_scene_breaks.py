"""A Word document arrives as the paragraphs it was written as (#1488).

Two defects in the Word reader, both found by building the document the reporter
described and reading it back:

1. **Every paragraph merged into one.** Paragraphs were joined with a single
   newline, and Markdown reads consecutive lines as one soft-wrapped paragraph,
   so an entire chapter arrived as one run-on block.
2. **Hard returns vanished.** A Word Shift+Enter reaches us as a newline inside
   the paragraph's text, and a bare newline in Markdown renders as a space --
   so a scene break written as three tight lines came back as one long line.

Together they meant a Word document could not survive the trip at all, which is
a bigger claim than the report made and is why these tests build real ``.docx``
files rather than asserting on a fixture somebody wrote by hand.
"""

from __future__ import annotations

import pytest

docx = pytest.importorskip("docx")

from quill.core.browser_preview import render_preview_body  # noqa: E402
from quill.io.docx_text import read_docx_text  # noqa: E402

NEWLINE = chr(10)
BACKSLASH = chr(92)


def _scene_document(tmp_path):
    """The reporter's own shape: a scene block, then two ordinary paragraphs."""
    path = tmp_path / "scene.docx"
    document = docx.Document()
    block = document.add_paragraph()
    first = block.add_run("United States,")
    first.add_break()
    second = block.add_run("Illinois,")
    second.add_break()
    block.add_run("Chicago,")
    document.add_paragraph("Friday, September 04, 2026, 9:42 p.m.")
    document.add_paragraph("The prose of the scene begins here.")
    document.save(str(path))
    return path


def test_separate_word_paragraphs_stay_separate(tmp_path) -> None:
    """They were joined with one newline, which Markdown reads as a soft wrap --
    so the whole document came back as a single paragraph."""
    text = read_docx_text(_scene_document(tmp_path))
    assert render_preview_body(text, "markdown").count("<p>") == 3


def test_a_word_hard_return_survives_as_a_hard_return(tmp_path) -> None:
    """The scene block is three lines of one paragraph, exactly as it was
    typed -- not one run-on line, and not three paragraphs."""
    html = render_preview_body(read_docx_text(_scene_document(tmp_path)), "markdown")
    scene = html.split("</p>")[0]
    assert scene.count("<br>") == 2
    assert "United States," in scene
    assert "Chicago," in scene


def test_the_scene_block_has_no_blank_lines_in_the_editor_text(tmp_path) -> None:
    """The reporter's complaint in its own terms: the editor must not show blank
    lines that the render then silently drops."""
    text = read_docx_text(_scene_document(tmp_path))
    scene = text.split(NEWLINE * 2)[0]
    assert scene.count(NEWLINE) == 2  # three lines, no blank line between them


def test_the_break_is_written_in_the_audible_spelling(tmp_path) -> None:
    """Two trailing spaces would be invisible to the person this was reported
    by, and stripped by half the tools that touch the file afterwards."""
    text = read_docx_text(_scene_document(tmp_path))
    assert BACKSLASH + NEWLINE in text


def test_the_caller_can_ask_for_the_other_spelling(tmp_path) -> None:
    """For a document going somewhere that only understands the older form."""
    from quill.io.docx_text import _render_body

    document = docx.Document(str(_scene_document(tmp_path)))
    # One list element per Word paragraph, so the scene block is a single string
    # carrying its own interior line breaks -- which is what has to be inspected.
    text = NEWLINE.join(_render_body(document, hard_break="  "))
    assert "  " + NEWLINE in text
    assert BACKSLASH not in text


def test_consecutive_list_items_do_not_gain_blank_lines(tmp_path) -> None:
    """A blank line between items makes the list loose, which is a different
    document -- so the paragraph separator has to know to skip them."""
    path = tmp_path / "list.docx"
    document = docx.Document()
    document.add_paragraph("Before the list.")
    document.add_paragraph("First", style="List Bullet")
    document.add_paragraph("Second", style="List Bullet")
    document.save(str(path))
    text = read_docx_text(path)
    assert "- First" + NEWLINE + "- Second" in text


def test_headings_are_still_headings(tmp_path) -> None:
    """The separator change must not disturb what already worked."""
    path = tmp_path / "heads.docx"
    document = docx.Document()
    document.add_paragraph("Chapter One", style="Heading 1")
    document.add_paragraph("Body text.")
    document.save(str(path))
    html = render_preview_body(read_docx_text(path), "markdown")
    assert "<h1" in html
    assert "<p>Body text.</p>" in html


def test_an_empty_document_still_returns_nothing(tmp_path) -> None:
    path = tmp_path / "empty.docx"
    docx.Document().save(str(path))
    assert read_docx_text(path) is None
