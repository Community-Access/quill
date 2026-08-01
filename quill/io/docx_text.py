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


def _render_body(document: Any) -> list[str]:
    """Render paragraphs and tables in document order."""
    from docx.table import Table  # type: ignore[import-untyped]
    from docx.text.paragraph import Paragraph  # type: ignore[import-untyped]

    lines: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        tag = str(child.tag)
        if tag.endswith("}p"):
            rendered = _render_paragraph(Paragraph(child, document))
            if rendered is not None:
                lines.append(rendered)
        elif tag.endswith("}tbl"):
            table_lines = _render_table(Table(child, document))
            if table_lines:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.extend(table_lines)
                lines.append("")
    return lines


def _render_paragraph(paragraph: Any) -> str | None:
    """One body paragraph as text, or ``None`` when it is empty."""
    text = (paragraph.text or "").strip()
    if not text:
        return None
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


def _render_table(table: Any) -> list[str]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [" ".join((cell.text or "").split()) for cell in row.cells]
        if any(cell for cell in cells):
            rows.append(cells)
    if not rows:
        return []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(padded[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in padded[1:])
    return lines
