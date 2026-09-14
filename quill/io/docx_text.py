"""Word (.docx) text extraction through python-docx (#1279).

QUILL's fallback Word reader used to walk ``word/document.xml`` by hand and emit
one flat line per paragraph: no headings, no lists, no tables. That is what a
packaged install actually used, because the better reader (MarkItDown) is an
optional download -- so users read Word documents through the weakest path QUILL
has and reported the result as a bug.

python-docx is already a *base* dependency (it powers rich Word mode), so every
install has a much better reader available at zero download cost. This module
renders a document's body in order -- headings as ``#`` levels, list paragraphs
as Markdown bullets/numbers, tables as Markdown tables -- matching the shape the
rest of QUILL's extracts use.

wx-free. Returns text only; the caller owns metadata. Raises nothing of its own:
callers degrade to the raw-XML extract when this returns ``None``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quill.core.markdown_breaks import hard_break_suffix

#: Spelled as chr() so a scripted edit cannot turn them into real breaks.
NEWLINE = chr(10)
RETURN = chr(13)

#: How a Word hard return is written into Markdown. A backslash rather than two
#: trailing spaces because this app is written for people who cannot see the
#: screen: a reader says nothing for two spaces, no editor shows them, and most
#: tools strip trailing whitespace on save -- destroying the break silently.
#: Both spellings are read back (quill.core.markdown_breaks); only one is
#: written. Callers with a user preference to honour pass ``hard_break``.
_DEFAULT_BREAK = hard_break_suffix("backslash")

_HEADING_STYLE = re.compile(r"^heading (\d)$", re.IGNORECASE)

#: Word's built-in list styles. Numbering beyond "is this a list" is not
#: reconstructed: Markdown renumbers ordered items anyway, and a wrong number is
#: worse than a consistent one.
_BULLET_STYLES = ("list bullet", "list paragraph")
_NUMBER_STYLES = ("list number",)


def read_docx_text(path: Path) -> str | None:
    """Render ``path`` as Markdown-shaped text, or ``None`` if python-docx cannot.

    ``None`` means "use the fallback": python-docx is missing, or the file is not
    a readable OOXML package, or it produced nothing at all.
    """
    try:
        import docx  # type: ignore[import-untyped]
    except ImportError:
        return None
    try:
        document = docx.Document(str(path))
        lines = _render_body(document)
    except Exception:  # noqa: BLE001 - any reader failure degrades to the raw extract
        return None
    if not any(line.strip() for line in lines):
        return None
    return "\n".join(lines).strip("\n") + "\n"


def _is_list_line(line: str) -> bool:
    return line.startswith("- ") or line.startswith("1. ")


def _render_body(document: Any, *, hard_break: str = _DEFAULT_BREAK) -> list[str]:
    """Render paragraphs and tables in document order.

    Paragraphs are separated by a **blank line**, which is what makes them
    paragraphs. They used to be joined with a single newline, and Markdown reads
    consecutive lines as one soft-wrapped paragraph -- so a whole Word chapter
    arrived in QUILL as a single run-on paragraph (#1488). Consecutive list
    items are the exception: a blank line between them makes the list loose,
    which is a different document.
    """
    from docx.table import Table  # type: ignore[import-untyped]
    from docx.text.paragraph import Paragraph  # type: ignore[import-untyped]

    lines: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        tag = str(child.tag)
        if tag.endswith("}p"):
            rendered = _render_paragraph(Paragraph(child, document), hard_break=hard_break)
            if rendered is not None:
                if (
                    lines
                    and lines[-1] != ""
                    and not (_is_list_line(rendered) and _is_list_line(lines[-1]))
                ):
                    lines.append("")
                lines.append(rendered)
        elif tag.endswith("}tbl"):
            table_lines = _render_table(Table(child, document))
            if table_lines:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.extend(table_lines)
                lines.append("")
    return lines


def _render_paragraph(paragraph: Any, *, hard_break: str = _DEFAULT_BREAK) -> str | None:
    """One body paragraph as text, or ``None`` when it is empty.

    A Word **hard return** (Shift+Enter, ``w:br``) reaches us as a newline
    inside the paragraph's text, and a bare newline in Markdown is a soft wrap
    that renders as a space -- so a scene break written as three lines in one
    paragraph came out as one run-on line (#1488). Each interior newline becomes
    a real Markdown hard break instead, which is the same thing the author
    typed.
    """
    text = (paragraph.text or "").strip()
    if not text:
        return None
    if NEWLINE in text or RETURN in text:
        pieces = [piece.rstrip() for piece in text.replace(RETURN, NEWLINE).split(NEWLINE)]
        text = (hard_break + NEWLINE).join(piece for piece in pieces if piece)
    style = _style_name(paragraph)
    heading = _HEADING_STYLE.match(style)
    if heading:
        level = min(int(heading.group(1)), 6)
        return f"{'#' * level} {text}"
    if style == "title":
        return f"# {text}"
    if style == "subtitle":
        return f"## {text}"
    if any(style.startswith(name) for name in _NUMBER_STYLES):
        return f"1. {text}"
    if any(style.startswith(name) for name in _BULLET_STYLES) or _has_numbering(paragraph):
        return f"- {text}"
    return text


def _style_name(paragraph: Any) -> str:
    try:
        return str(paragraph.style.name or "").strip().lower()
    except Exception:  # noqa: BLE001 - a document with a broken style table still reads
        return ""


def _has_numbering(paragraph: Any) -> bool:
    """True when the paragraph carries direct numbering (``w:numPr``)."""
    try:
        return paragraph._p.pPr is not None and paragraph._p.pPr.numPr is not None
    except Exception:  # noqa: BLE001
        return False


def read_docx_xml_text(path: Path) -> str:
    """Last-resort Word extract: walk ``word/document.xml`` for paragraph text.

    Used when :func:`read_docx_text` cannot read the file. #1279: no synthetic
    "# DOCX Extract" banner -- the text the user opens is the document's own, and
    provenance lives in ``source_metadata`` (same call EDS-21 made for RTF).
    """
    from quill.core.safe_archive import open_zip
    from quill.core.safe_xml import fromstring as safe_xml_fromstring

    with open_zip(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = safe_xml_fromstring(xml_bytes.decode("utf-8"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
            if isinstance(node.text, str)
        ]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        return "(no extractable text)\n"
    return "\n".join(paragraphs).rstrip() + "\n"


def _cell_text(cell: Any) -> str:
    """One table cell flattened to a line and escaped for a Markdown table.

    A cell whose own text contains "|" would otherwise split into two columns,
    making the rendered table ragged and throwing off cell-by-cell table
    navigation ("column 2 of 4" in a three-column table). Escape as GFM does --
    the same escaping ``docx_reader`` applies -- so the pipe stays cell text.
    """
    text = " ".join((cell.text or "").split())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _render_table(table: Any) -> list[str]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [_cell_text(cell) for cell in row.cells]
        if any(cell for cell in cells):
            rows.append(cells)
    if not rows:
        return []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(padded[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in padded[1:])
    return lines
