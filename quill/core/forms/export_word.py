"""A form as a printable Word document, and its large-print version (wordpress.md 17a.7).

wx-free. Built with python-docx, which QUILL already uses for Word output
(:mod:`quill.io.docx_writer`), from :func:`quill.core.forms.print_layout.blocks`,
so the paper form asks exactly what the web form asks.

On paper a question is a real heading (the form's title is Heading 1, each
page Heading 2, each section Heading 3), so a screen reader moves through the
document by question. A written answer gets lines to write on; a choice gets a
box to check, drawn as the ballot-box character every Word font has. Required
is the word "(required)", never an asterisk or a colour.

The large-print version (*large_print*) sets body text at 18 point and
headings larger, with generous spacing, as large-print guidance asks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.forms import model as M
from quill.core.forms import print_layout as pl
from quill.core.forms.errors import FormError

#: Body and heading sizes, in points: (normal, large print).
BODY_POINTS = (11, 18)
HEADING_POINTS = ((20, 28), (16, 24), (13, 20))
#: A line to write on, and a box to check.
WRITE_LINE = "_" * 60
WRITE_LINE_LARGE = "_" * 36
BOX = "☐"


class FormWordExportError(FormError):
    """The Word document could not be written (python-docx missing, or the file)."""

    code = "QUILL-FORMS-EXPORT-WORD"


def docx_available() -> bool:
    try:
        import docx  # noqa: F401
    except ImportError:
        return False
    return True


def build(model: M.Model, *, large_print: bool = False) -> Any:
    """The python-docx ``Document`` for *model*."""
    try:
        import docx
        from docx.shared import Pt
    except ImportError as exc:  # pragma: no cover - python-docx ships with QUILL
        raise FormWordExportError(
            "Word documents need python-docx, which is not installed."
        ) from exc
    size = 1 if large_print else 0
    document = docx.Document()
    styles = document.styles
    body = styles["Normal"]
    body.font.size = Pt(BODY_POINTS[size])
    body.paragraph_format.space_after = Pt(BODY_POINTS[size] // 2)
    for level, points in enumerate(HEADING_POINTS, 1):
        styles[f"Heading {level}"].font.size = Pt(points[size])
    title = str(model.get("title") or "Form")
    document.core_properties.title = title
    document.add_heading(title, level=1)
    if model.get("description"):
        document.add_paragraph(str(model["description"]))
    line = WRITE_LINE_LARGE if large_print else WRITE_LINE
    for block in pl.blocks(model):
        if block.kind == "page":
            document.add_heading(block.label, level=2)
            if block.help:
                document.add_paragraph(block.help)
        elif block.kind == "section":
            document.add_heading(block.label, level=3)
            if block.help:
                document.add_paragraph(block.help)
        elif block.kind == "text":
            document.add_paragraph(block.label)
        else:
            _question(document, block, line)
    return document


def _question(document: Any, block: pl.Block, line: str) -> None:
    heading = document.add_paragraph()
    heading.add_run(pl.question_heading(block)).bold = True
    heading.paragraph_format.keep_with_next = True
    if block.help:
        helped = document.add_paragraph(block.help)
        helped.paragraph_format.keep_with_next = True
    how = pl.how_to_answer(block)
    if how and block.choices:
        document.add_paragraph(how).paragraph_format.keep_with_next = True
    for choice in block.choices:
        document.add_paragraph(f"{BOX} {choice}")
    if not block.choices:
        for _ in range(block.lines):
            document.add_paragraph(line)


def write(model: M.Model, path: Path, *, large_print: bool = False) -> Path:
    """Write *model* to *path* as a Word document; returns the path written."""
    document = build(model, large_print=large_print)
    try:
        document.save(str(path))
    except OSError as exc:
        raise FormWordExportError(
            f"QUILL could not save {path.name}: {exc.strerror or exc}."
        ) from exc
    return path


def write_responses(
    title: str, responses: list[tuple[str, list[tuple[str, str]]]], path: Path
) -> Path:
    """Responses as a Word document: a heading for each, then each question and answer.

    *responses* is ``[(heading, [(question, answer), ...]), ...]`` -- already
    words, from :mod:`quill.core.forms.responses`, so this only lays them out.
    """
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - python-docx ships with QUILL
        raise FormWordExportError(
            "Word documents need python-docx, which is not installed."
        ) from exc
    document = docx.Document()
    document.core_properties.title = title
    document.add_heading(title, level=1)
    for heading, answers in responses:
        document.add_heading(heading, level=2)
        for question, answer in answers:
            asked = document.add_paragraph()
            asked.add_run(question).bold = True
            asked.paragraph_format.keep_with_next = True
            document.add_paragraph(answer)
    try:
        document.save(str(path))
    except OSError as exc:
        raise FormWordExportError(
            f"QUILL could not save {path.name}: {exc.strerror or exc}."
        ) from exc
    return path


__all__ = ["FormWordExportError", "build", "docx_available", "write", "write_responses"]
