"""The highlighted runs in a ``.docx``, standard library only.

Item 39 (highlighted passages in Word documents). QUILL's rich Word editing
reads highlights through python-docx; but a Word file opened as text -- QUILL's
read-extract choice, a ``.docm``, or a build that somehow lost python-docx
(both editors carry it and lxml since 2026-10-17) -- keeps the words
and drops the formatting, so its highlights were simply gone. This walks the
same ``word/document.xml`` QUILL's own text reader walks
(:mod:`quill.io.office_word`, with the same safe archive and XML guards) and
returns each highlighted run with the paragraph it sits in, for
:func:`quill.core.highlights.align_runs` to place on whatever text the editor
is showing.

Read: ``<w:highlight w:val="...">`` set directly on a run. A highlight that
comes only from a character style is not followed: Word's Highlight button
always applies it directly and never makes a style. Paragraphs inside tables
and content controls are walked in body order. Deleted tracked changes are
skipped, as the text reader skips them, because they are not text a reader of
the document sees.

wx-free; strict-typed. Raises what :func:`quill.io.office_word.read_docx_xml`
raises for a missing part, a non-package or damaged XML.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element

from quill.core.highlights import HighlightRun, highlight_name
from quill.core.safe_archive import open_zip
from quill.core.safe_xml import fromstring as safe_xml_fromstring
from quill.io.office_word import paragraph_text

__all__ = ["WORD_HIGHLIGHT_SUFFIXES", "read_docx_highlight_runs"]

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

#: The Word package formats whose highlights this can read.
WORD_HIGHLIGHT_SUFFIXES = frozenset({".docx", ".docm"})


def _w(name: str) -> str:
    return f"{{{_W}}}{name}"


def _run_colour(run: Element) -> str | None:
    properties = run.find(_w("rPr"))
    if properties is None:
        return None
    mark = properties.find(_w("highlight"))
    if mark is None:
        return None
    return highlight_name(mark.get(_w("val")))


def _run_words(run: Element) -> str:
    parts: list[str] = []
    for child in run:
        if child.tag == _w("t") and child.text:
            parts.append(child.text)
        elif child.tag == _w("tab"):
            parts.append("\t")
    return "".join(parts)


def _runs_in_order(node: Element) -> list[Element]:
    """The ``<w:r>`` elements of a paragraph in reading order, deletions left out."""
    found: list[Element] = []
    for child in node:
        if child.tag == _w("del"):
            continue
        if child.tag == _w("r"):
            found.append(child)
        elif child.tag != _w("pPr"):
            found.extend(_runs_in_order(child))
    return found


def _paragraph_runs(paragraph: Element) -> list[HighlightRun]:
    words = paragraph_text(paragraph)
    context = " ".join(words.split()) if "\n" in words else words.strip()
    lead = len(words) - len(words.lstrip())
    runs: list[HighlightRun] = []
    position = 0
    current_colour: str | None = None
    current_text = ""
    current_offset = -1
    for run in _runs_in_order(paragraph):
        text = _run_words(run)
        colour = _run_colour(run)
        if colour is not None and colour == current_colour:
            current_text += text
        else:
            if current_colour is not None and current_text.strip():
                runs.append(HighlightRun(current_colour, current_text, context, current_offset))
            current_colour = colour
            current_text = text if colour is not None else ""
            current_offset = position - lead if colour is not None else -1
        position += len(text)
    if current_colour is not None and current_text.strip():
        runs.append(HighlightRun(current_colour, current_text, context, current_offset))
    return [_trimmed(run) for run in runs]


def _trimmed(run: HighlightRun) -> HighlightRun:
    """Leading/trailing spaces off a run: a highlighted space is not a word to go to."""
    stripped = run.text.strip()
    shift = len(run.text) - len(run.text.lstrip())
    offset = run.offset + shift if run.offset >= 0 else run.offset
    return HighlightRun(run.colour, stripped, run.context, offset)


def read_docx_highlight_runs(path: Path) -> list[HighlightRun]:
    """Every highlighted run in the body of the Word document at *path*, in order."""
    with open_zip(path) as archive:
        body_xml = archive.read("word/document.xml")
    root = safe_xml_fromstring(body_xml)
    body = root.find(_w("body"))
    if body is None:
        return []
    runs: list[HighlightRun] = []
    for paragraph in body.iter(_w("p")):
        runs.extend(_paragraph_runs(paragraph))
    return runs
